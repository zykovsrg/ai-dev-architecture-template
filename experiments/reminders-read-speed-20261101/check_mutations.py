"""Каждый новый тест: исходник, связанная мутация, успешный повтор."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
source = root / 'modules/planning/scripts'
tests = root / 'modules/planning/tests'
structure = 'reminders_structure.py'
helper = 'reminders_project_lists.py'
line = "        details = detail_module.detailed_rows(native, lid) if batch else None\n"
mutations = [
 ('test_batch_preserves_exact_legacy_snapshot_and_reduces_calls', structure,
  "batch = detailed and value.get('detailed_reminder_snapshot') is True", 'batch = False'),
 ('test_absent_capability_keeps_legacy_detail_reads', structure,
  "batch = detailed and value.get('detailed_reminder_snapshot') is True", 'batch = detailed'),
 ('test_shallow_snapshot_keeps_narrow_detail_read', structure,
  "batch = detailed and value.get('detailed_reminder_snapshot') is True", "batch = (detailed or bool(detailed_ids)) and value.get('detailed_reminder_snapshot') is True"),
 ('test_summary_projection_drift_is_rejected', structure,
  "if batch and detail_module.summary_projection(detail) != detail_module.summary_projection(row):", 'if False:'),
 ('test_extra_detail_row_is_rejected', structure,
  "if batch and set(details) != {row.get('id') for row in rows}:", 'if False:'),
 ('test_invalid_batch_protocol_is_not_silently_downgraded', helper,
  "not isinstance(listing, list) or value.get('detail') is not True or", 'not isinstance(listing, list) or'),
 ('test_cyclic_batch_hierarchy_is_rejected', helper,
  '    validate_detailed_parents(result)\n', '    # Мутация: не проверять цикл родителей.\n'),
 ('test_each_snapshot_reads_fresh_details_and_child_order', structure, line,
  """        details = None
        if batch:
            if not hasattr(native, '_stale_batch'): native._stale_batch = {}
            if lid not in native._stale_batch: native._stale_batch[lid] = detail_module.detailed_rows(native, lid)
            details = native._stale_batch[lid]
"""),
]
results = []
with tempfile.TemporaryDirectory(prefix='reminders-batch-mutations-') as temp:
    scripts = Path(temp) / 'scripts'
    shutil.copytree(source, scripts, ignore=shutil.ignore_patterns('__pycache__'))
    env = dict(os.environ, STRUCTURE_BATCH_SOURCE=str(scripts / structure), PYTHONDONTWRITEBYTECODE='1')
    for name, filename, before, after in mutations:
        target = scripts / filename
        original = target.read_text()
        assert original.count(before) == 1, (name, original.count(before))
        command = [sys.executable, '-B', '-m', 'unittest', 'test_reminders_structure_batch.BatchSnapshotTests.' + name]
        run = lambda: subprocess.run(command, cwd=tests, env=env, text=True, capture_output=True)
        good = run()
        target.write_text(original.replace(before, after))
        bad = run()
        target.write_text(original)
        again = run()
        passed = good.returncode == 0 and bad.returncode != 0 and 'FAILED (failures=' in bad.stderr and again.returncode == 0
        results.append(dict(test=name, file=filename, before=before, after=after, clean=good.returncode,
                            mutated=bad.returncode, restored=again.returncode, verified=passed, evidence=bad.stderr))
        print(name, 'подтверждён' if passed else 'НЕ ПОДТВЕРЖДЁН', flush=True)
Path(__file__).with_name('mutations.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
raise SystemExit(0 if all(row['verified'] for row in results) else 1)
