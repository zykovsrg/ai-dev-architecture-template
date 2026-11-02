"""Поведение узкого снимка на выдуманных деревьях; внешние инструменты не изменяются."""
import importlib.util
import contextlib
import hashlib
import io
import json
import sys
from unittest.mock import patch
import os
from pathlib import Path
import stat
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FilesystemMutationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='filesystem-unit-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.source = self.base / 'source'
        self.source.mkdir()
        self.fs = load('domain_filesystem', ROOT / 'scripts/mutation-filesystem.py')
        self.legacy = load('domain_legacy', ROOT / 'scripts/mutation-test.py')
        for name in ('scripts', 'tests', 'modules/core/data', 'modules/knowledge/skills/hub-knowledge-enable',
                     'getting-started', 'docs/empty', 'docs/audits', 'docs/superpowers'):
            (self.source / name).mkdir(parents=True, exist_ok=True)
        for name, text in {'README.md': '# Настоящее руководство\n', 'docs/usage.md': '# Применение\n',
                           'getting-started/start.md': '# Начало\n', 'docs/audits/excluded.md': 'исключено',
                           'docs/superpowers/excluded.md': 'исключено', 'docs/image.bin': 'не текст',
                           'modules/core/data/.gitignore': '.DS_Store\nbuild/\n',
                           'modules/knowledge/skills/hub-knowledge-enable/SKILL.md': 'настоящий навык\n',
                           'scripts/domain.py': 'def answer():\n    return 1\n',
                           'tests/oracle.py': 'def check(value):\n    assert value\n'}.items():
            (self.source / name).write_text(text)
        self.copy = self.base / 'variant'

    def item(self, operation, **extra):
        return dict(id='fixture', suite='demo', expected_ids=['fixture.Test.test_value'],
                    source=self.fs.OPERATIONS[operation], operation=operation, **extra)

    def prepare(self, item, protected=()):
        return self.fs.prepare_change(self.source, item, protected, self.legacy.mutate)

    def test_snapshot_contains_real_documents_and_excludes_audits(self):
        state = self.fs.snapshot(self.source, self.copy)
        self.assertTrue((self.copy / 'README.md').is_file())
        for name in ('README.md', 'docs/usage.md', 'getting-started/start.md'):
            self.assertEqual((self.copy / name).read_bytes(), (self.source / name).read_bytes())
        self.assertTrue((self.copy / 'docs/empty').is_dir())
        self.assertFalse((self.copy / 'docs/audits').exists())
        self.assertFalse((self.copy / 'docs/superpowers').exists())
        self.assertFalse((self.copy / 'docs/image.bin').exists())
        self.assertEqual(set(self.fs.active_documents(self.copy, state)),
                         {'README.md', 'docs/usage.md', 'getting-started/start.md'})

    def test_state_observes_empty_directories_and_file_modes(self):
        before = self.fs.read_state(self.source)
        (self.source / 'scripts/empty').mkdir()
        self.assertNotEqual(self.fs.read_state(self.source), before)
        self.assertIn('scripts/empty', self.fs.read_state(self.source)['directories'])
        before = self.fs.read_state(self.source)
        (self.source / 'scripts/domain.py').chmod(0o600)
        self.assertNotEqual(self.fs.read_state(self.source), before)

    def test_create_file_has_exact_bytes_mode_and_restores_absence(self):
        item = self.item('create_file', content='#!/usr/bin/env bash\nexit 0\n')
        change = self.prepare(item)
        baseline = self.fs.snapshot(self.source, self.copy)
        expected = self.fs.apply_change(self.copy, change, baseline)
        target = self.copy / item['source']
        self.assertEqual(target.read_bytes(), b'#!/usr/bin/env bash\nexit 0\n')
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o644)
        self.assertEqual(self.fs.read_state(self.copy), expected)
        self.fs.restore_change(self.copy, change)
        self.assertFalse(target.exists())
        self.assertEqual(self.fs.read_state(self.copy), baseline)
        self.assertFalse((self.source / item['source']).exists())

    def test_create_empty_directory_is_observed_and_restored(self):
        change = self.prepare(self.item('create_empty_dir'))
        baseline = self.fs.snapshot(self.source, self.copy)
        expected = self.fs.apply_change(self.copy, change, baseline)
        self.assertEqual(stat.S_IMODE((self.copy / 'template').stat().st_mode), 0o755)
        self.assertEqual(list((self.copy / 'template').iterdir()), [])
        self.assertNotEqual(expected, baseline)
        self.fs.restore_change(self.copy, change)
        self.assertFalse((self.copy / 'template').exists())
        self.assertEqual(self.fs.read_state(self.copy), baseline)

    def test_delete_restores_original_bytes_and_mode(self):
        item = self.item('delete_file')
        original = self.source / item['source']
        original.chmod(0o600)
        change = self.prepare(item)
        baseline = self.fs.snapshot(self.source, self.copy)
        self.fs.apply_change(self.copy, change, baseline)
        self.assertFalse((self.copy / item['source']).exists())
        self.fs.restore_change(self.copy, change)
        restored = self.copy / item['source']
        self.assertEqual(restored.read_bytes(), 'настоящий навык\n'.encode())
        self.assertEqual(stat.S_IMODE(restored.stat().st_mode), 0o600)
        self.assertEqual(self.fs.read_state(self.copy), baseline)
        self.assertEqual(original.read_bytes(), restored.read_bytes())

    def test_gitignore_has_only_exact_exception(self):
        item = dict(id='ignore', suite='demo', expected_ids=['fixture'], source='modules/core/data/.gitignore',
                    symbol='@document', before='.DS_Store\n', after='')
        change = self.prepare(item)
        baseline = self.fs.snapshot(self.source, self.copy)
        self.fs.apply_change(self.copy, change, baseline)
        self.assertEqual((self.copy / item['source']).read_text(), 'build/\n')
        self.fs.restore_change(self.copy, change)
        self.assertEqual(self.fs.read_state(self.copy), baseline)
        with self.assertRaises(ValueError):
            self.prepare(dict(item, before='build/\n'))

    def test_paths_links_and_oracle_files_are_rejected(self):
        for path in ('scripts//domain.py', 'scripts/./domain.py', '../outside', str(self.source / 'scripts/domain.py')):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.fs.checked_path(self.source, path)
        item = dict(id='oracle', suite='demo', expected_ids=['fixture'], source='tests/oracle.py', symbol='check',
                    before='assert value', after='assert not value')
        with self.assertRaises(ValueError):
            self.prepare(item, [self.source / 'tests/oracle.py'])
        alias = self.source / 'tests/alias.py'
        os.link(self.source / 'tests/oracle.py', alias)
        with self.assertRaises(ValueError):
            self.prepare(dict(item, source='tests/alias.py'), [self.source / 'tests/oracle.py'])
        link = self.source / 'scripts/link.py'
        link.symlink_to(self.source / 'scripts/domain.py')
        with self.assertRaises(ValueError):
            self.fs.checked_path(self.source, 'scripts/link.py')

    def test_operation_rejects_unknown_fields_and_wrong_targets(self):
        item = self.item('create_file', content='#!/usr/bin/env bash\nexit 0\n')
        for invalid in (dict(item, command='touch outside'), dict(item, source='scripts/other.sh'),
                        dict(item, symbol='@shell'), dict(item, content='other'), dict(item, operation='rename')):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.prepare(invalid)
        (self.source / item['source']).write_text('существует')
        with self.assertRaises(ValueError):
            self.prepare(item)

    def test_missing_active_documents_are_an_error(self):
        (self.source / 'getting-started/start.md').unlink()
        with self.assertRaises(ValueError):
            self.fs.active_documents(self.source, self.fs.read_state(self.source))

    def test_restore_never_follows_replaced_parent(self):
        item = self.item('delete_file')
        change = self.prepare(item)
        baseline = self.fs.snapshot(self.source, self.copy)
        self.fs.apply_change(self.copy, change, baseline)
        parent = (self.copy / item['source']).parent
        parent.rmdir()
        outside = self.base / 'outside'
        outside.mkdir()
        parent.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.fs.restore_change(self.copy, change)
        self.assertEqual(list(outside.iterdir()), [])

    def test_extra_directory_prevents_applying_change(self):
        change = self.prepare(self.item('create_empty_dir'))
        baseline = self.fs.snapshot(self.source, self.copy)
        (self.copy / 'scripts/unrelated').mkdir()
        with self.assertRaises(ValueError):
            self.fs.apply_change(self.copy, change, baseline)
        self.assertFalse((self.copy / 'template').exists())

    def test_shell_suite_accepts_only_three_exact_scripts(self):
        strict = load('domain_strict', ROOT / 'scripts/mutation-test-strict.py')
        (self.source / 'tests/helpers').mkdir()
        (self.source / 'tests/helpers/shell-scenarios.sh').write_text('# fixture')
        accepted = ('scripts/assistant-workflows-test.sh', 'scripts/hub-smoke-test.sh',
                    'scripts/test-refresh-session-inventory.sh')
        rejected = ('scripts/architecture-test.sh', 'scripts/arbitrary-test.sh')
        for path in accepted + rejected:
            (self.source / path).write_text('# fixture')
            suite = dict(framework='shell', args=[path], helpers=['tests/helpers/shell-scenarios.sh'])
            if path in accepted:
                self.assertIsNone(strict.suite_paths(self.source, suite))
            else:
                with self.assertRaises(ValueError):
                    strict.suite_paths(self.source, suite)

    def runner_config(self):
        return dict(schema_version=2,
                    legacy_sha256=hashlib.sha256((ROOT / 'scripts/mutation-test.py').read_bytes()).hexdigest(),
                    capture_sha256=hashlib.sha256((ROOT / 'scripts/test-method-capture.py').read_bytes()).hexdigest(),
                    filesystem_helper_sha256=hashlib.sha256((ROOT / 'scripts/mutation-filesystem.py').read_bytes()).hexdigest(),
                    suites={'demo': dict(framework='unittest', args=['discover', '-s', 'tests', '-p', 'test_fixture.py', '-q'])},
                    mutations=[dict(self.item('create_file', content='#!/usr/bin/env bash\nexit 0\n'),
                                    expected_ids=['test_fixture.Fixture.test_absent'])])

    def run_runner(self, config, output, tool_root=ROOT):
        catalog = self.base / 'catalog.json'
        catalog.write_text(json.dumps(config))
        strict = load('domain_strict', tool_root / 'scripts/mutation-test-strict.py')
        with patch.object(sys, 'argv', ['strict', '--source', str(self.source), '--catalog', str(catalog),
                                      '--output', str(output)]), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = strict.main()
        return code, json.loads(output.read_text()) if output.is_file() else None

    def test_runner_requires_explicit_helper_pin_for_new_operations(self):
        config = self.runner_config()
        config.pop('filesystem_helper_sha256')
        code, report = self.run_runner(config, self.base / 'report.json')
        self.assertEqual(code, 2)
        self.assertEqual(report['executions'], [])
        self.assertIn('явное закрепление', report['error'])

    def test_runner_new_operation_has_own_proof_and_preserves_source(self):
        (self.source / 'tests/test_fixture.py').write_text(
            'from pathlib import Path\nimport unittest\nROOT = Path(__file__).resolve().parents[1]\n'
            'class Fixture(unittest.TestCase):\n    def test_absent(self):\n'
            '        self.assertFalse((ROOT / "scripts/update-installed-architecture.sh").exists())\n')
        before = self.fs.read_state(self.source)
        code, report = self.run_runner(self.runner_config(), self.source / 'docs/audits/report.json')
        self.assertEqual(code, 0, report.get('error'))
        self.assertTrue(report['proof_gate'])
        row = report['mutations'][0]
        self.assertEqual(row['status'], 'detected')
        self.assertEqual(row['mutant']['view']['own_assertion_ids'], ['test_fixture.Fixture.test_absent'])
        self.assertEqual(row['restored_tree_state'], before)
        self.assertEqual(report['canonical_tree_state_after'], before)
        self.assertEqual(self.fs.read_state(self.source), before)
        self.assertEqual(len(report['active_document_hashes']), 3)
        self.assertTrue(any(path.endswith('/filesystem.py') for path in report['copied_tools_sha256']))

    def test_runner_rejects_output_in_active_documentation(self):
        output = self.source / 'docs/report.json'
        code, report = self.run_runner(self.runner_config(), output)
        self.assertEqual(code, 2)
        self.assertIsNone(report)
        self.assertFalse((self.source / 'docs/report-artifacts').exists())

    def copy_runner_tools(self):
        tool_root = self.base / 'runner'
        (tool_root / 'scripts').mkdir(parents=True)
        for name in ('mutation-test.py', 'mutation-test-strict.py', 'mutation-filesystem.py', 'test-method-capture.py'):
            shutil.copy2(ROOT / 'scripts' / name, tool_root / 'scripts' / name)
        return tool_root

    def test_helper_is_not_imported_before_pin_verification(self):
        config = self.runner_config()
        tool_root = self.copy_runner_tools()
        helper = tool_root / 'scripts/mutation-filesystem.py'
        marker = self.base / 'helper-imported'
        helper.write_text(helper.read_text() + '\nfrom pathlib import Path\nPath(' + repr(str(marker)) + ').write_text("loaded")\n')
        code, report = self.run_runner(config, self.base / 'report.json', tool_root)
        self.assertEqual(code, 2)
        self.assertFalse(marker.exists(), 'Незакреплённый помощник уже исполнялся')
        self.assertEqual(report['executions'], [])
        self.assertIn('Закреплённый инструмент изменён', report['error'])

    def test_external_tool_cannot_be_replaced_with_same_bytes_symlink(self):
        config = self.runner_config()
        tool_root = self.copy_runner_tools()
        external = tool_root / 'scripts/test-method-capture.py'
        identical = self.base / 'same-capture.py'
        shutil.copy2(external, identical)
        (self.source / 'tests/test_fixture.py').write_text(
            'from pathlib import Path\nimport unittest\n'
            'class Fixture(unittest.TestCase):\n    def test_absent(self):\n'
            '        tool = Path(' + repr(str(external)) + ')\n'
            '        if not tool.is_symlink():\n            tool.unlink()\n'
            '            tool.symlink_to(' + repr(str(identical)) + ')\n'
            '        self.assertFalse((Path(__file__).resolve().parents[1] / "scripts/update-installed-architecture.sh").exists())\n')
        code, report = self.run_runner(config, self.base / 'report.json', tool_root)
        self.assertEqual(code, 2)
        self.assertFalse(report['proof_gate'])
        self.assertIn('Изменены канонические инструменты', report.get('error', ''))
        self.assertTrue(external.is_symlink())
        self.assertEqual(external.read_bytes(), identical.read_bytes())

    def test_output_under_template_does_not_create_canonical_tree(self):
        output = self.source / 'template/report.json'
        code, report = self.run_runner(self.runner_config(), output)
        self.assertEqual(code, 2)
        self.assertIsNone(report)
        self.assertFalse((self.source / 'template').exists())


if __name__ == '__main__':
    unittest.main()
