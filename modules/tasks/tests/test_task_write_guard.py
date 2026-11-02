"""Проверка отказа до изменения канонического файла задач."""
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/task_records.py'

class TaskWriteGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.hub = Path(self.tmp.name) / 'hub'
        self.project = self.hub / 'projects/page-a'
        (self.project / 'ai').mkdir(parents=True)
        (self.hub / 'ai').mkdir()
        (self.hub / 'ai/project-registry.md').write_text(
            f'# Реестр\n\n## page-a\nStatus: active\nPath: {self.project}\n')
        self.target = self.project / 'ai/current-task.md'
        self.original = '# Текущая задача\n\nStatus: empty\n'
        self.target.write_text(self.original)

    def write(self, text, kind='current', digest=None):
        return subprocess.run(['python3', str(SCRIPT), 'write', '--hub', str(self.hub),
            '--project-id', 'page-a', '--kind', kind, '--expected-sha256',
            digest or hashlib.sha256(self.target.read_bytes()).hexdigest()],
            input=text, text=True, capture_output=True)

    def assert_rejected(self, text, code, kind='current'):
        before = self.target.read_bytes()
        r = self.write(text, kind)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn(code, r.stderr)
        self.assertEqual(self.target.read_bytes(), before)

    def test_valid_empty_record_is_saved(self):
        content = self.original + '\nПоследний результат сохранён.\n'
        r = self.write(content)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.target.read_text(), content)
        self.assertEqual(json.loads(r.stdout)['result'], 'written')

    def test_idle_status_is_rejected_before_replacement(self):
        self.assert_rejected('# Текущая задача\n\nStatus: idle\n', 'invalid_current_task_id')

    def test_active_record_without_task_id_is_rejected(self):
        self.assert_rejected('# Задача\nStatus: active\n\n## Goal\nРабота\n', 'invalid_current_task_id')

    def test_completed_paused_record_is_rejected(self):
        self.target = self.project / 'ai/paused-tasks.md'
        self.target.write_text('# Приостановленные задачи\n\n## Paused tasks\n')
        self.assert_rejected('### 2026-10-21 — Фактура\nTask ID: TASK-page-a-20261021-001\nStatus: completed\n', 'invalid_paused_record', 'paused')

    def test_stale_content_hash_preserves_newer_work(self):
        digest = hashlib.sha256(self.target.read_bytes()).hexdigest()
        newer = self.original + '\nИзменение другой сессии.\n'
        self.target.write_text(newer)
        r = self.write(self.original, digest=digest)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn('task_file_changed', r.stderr)
        self.assertEqual(self.target.read_text(), newer)

    def test_symlink_target_is_rejected(self):
        outside = Path(self.tmp.name) / 'outside.md'
        outside.write_text(self.original)
        self.target.unlink()
        self.target.symlink_to(outside)
        self.assert_rejected(self.original + '\nИзменение\n', 'unsafe_task_path')

    def test_unrecognized_heading_is_rejected(self):
        self.target = self.project / 'ai/future-tasks.md'
        self.target.write_text('# Будущие задачи\n\n## Future tasks\n')
        self.assert_rejected('### Задача без идентификатора\nStatus: ready\n', 'unrecognized_heading', 'future')

    DONE = ('# Текущая задача\n\nTask ID: TASK-page-a-20261024-003\nStatus: done\n\n'
            '## Goal\n\nПеренести задачи.\n')
    NEXT = ('# Текущая задача\n\nTask ID: TASK-page-a-20261028-002\nStatus: active\n\n'
            '## Goal\n\nПровести аудит.\n')
    FUTURE = '# Будущие задачи\n\n## Future tasks\n'

    def test_replacing_task_kept_nowhere_else_is_rejected(self):
        (self.project / 'ai/future-tasks.md').write_text(self.FUTURE)
        self.target.write_text(self.DONE)
        self.assert_rejected(self.NEXT, 'task_id_lost:TASK-page-a-20261024-003')

    def test_replacing_task_already_moved_to_future_is_saved(self):
        (self.project / 'ai/future-tasks.md').write_text(
            self.FUTURE + '\n### TASK-page-a-20261024-003 — Перенос\n\nStatus: done\n\nCreated: 2026-10-24\n')
        self.target.write_text(self.DONE)
        r = self.write(self.NEXT)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.target.read_text(), self.NEXT)

    def test_explicit_removal_allows_consented_physical_deletion(self):
        (self.project / 'ai/future-tasks.md').write_text(self.FUTURE)
        self.target.write_text(self.DONE)
        r = subprocess.run(['python3', str(SCRIPT), 'write', '--hub', str(self.hub),
            '--project-id', 'page-a', '--kind', 'current', '--expected-sha256',
            hashlib.sha256(self.target.read_bytes()).hexdigest(),
            '--allow-removal', 'TASK-page-a-20261024-003'],
            input=self.original, text=True, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.target.read_text(), self.original)

if __name__ == '__main__':
    unittest.main()
