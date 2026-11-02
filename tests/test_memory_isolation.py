"""Проверки границ чтения памяти на полностью выдуманных проектах."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'modules/tasks/scripts/read-compact-task-index.py'


def load_index():
    scripts = str(SOURCE.parent)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location('memory_isolation_index', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MemoryIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.hub = Path(self.temporary.name) / 'hub'
        (self.hub / 'ai').mkdir(parents=True)
        self.module = load_index()
        self.alpha = self.project('alpha')
        self.beta = self.project('beta')
        self.registry([('alpha', 'active', self.alpha), ('beta', 'active', self.beta)])

    def project(self, name, path=None, task_project=None):
        path = path or self.hub / 'projects' / name
        (path / 'ai').mkdir(parents=True)
        project = task_project or name
        (path / 'ai/current-task.md').write_text(
            f'Status: active\nTask ID: TASK-{project}-20260911-001\n\n## Goal\n\nCurrent {name}\n',
            encoding='utf-8')
        (path / 'ai/future-tasks.md').write_text(
            f'### TASK-{project}-20260911-002 — Future {name}\n\nStatus: ready\n',
            encoding='utf-8')
        (path / 'ai/paused-tasks.md').write_text(
            f'### 2026-09-11 — Paused {name}\n\nTask ID: TASK-{project}-20260911-003\nStatus: paused\n',
            encoding='utf-8')
        return path

    def registry(self, entries):
        (self.hub / 'ai/project-registry.md').write_text(
            '\n'.join(f'## {name}\nStatus: {status}\nPath: {path}\n' for name, status, path in entries),
            encoding='utf-8')

    def record_opens(self):
        opened = []
        original = Path.open

        def tracking_open(path, *args, **kwargs):
            opened.append(path.resolve())
            return original(path, *args, **kwargs)

        return opened, mock.patch.object(Path, 'open', new=tracking_open)

    def assert_no_reads_below(self, opened, root):
        self.assertFalse([str(path) for path in opened if path.is_relative_to(root.resolve())],
                         'Запрещённая память не должна даже открываться')

    def test_archived_project_is_never_opened(self):
        self.registry([('alpha', 'active', self.alpha), ('beta', 'archived', self.beta)])
        opened, tracking = self.record_opens()
        with tracking:
            rows = self.module.build_index(self.hub)
        self.assert_no_reads_below(opened, self.beta)
        self.assertEqual({row['project_id'] for row in rows}, {'alpha'})
        self.assertEqual(len(rows), 3)

    def test_foreign_group_is_never_opened(self):
        opened, tracking = self.record_opens()
        with mock.patch.object(self.module, 'resolve_group_project_ids', return_value={'alpha'}) as membership:
            with tracking:
                rows = self.module.build_index(self.hub, 'chosen')
        membership.assert_called_once_with(self.hub.resolve(), 'chosen')
        self.assert_no_reads_below(opened, self.beta)
        self.assertEqual({row['project_id'] for row in rows}, {'alpha'})

    def test_intermediate_directory_link_cannot_read_other_project_memory(self):
        # A real project directory points through its ai directory into a neighbour.
        for path in (self.alpha / 'ai').iterdir():
            path.unlink()
        (self.alpha / 'ai').rmdir()
        (self.alpha / 'ai').symlink_to(self.beta / 'ai', target_is_directory=True)
        self.registry([('alpha', 'active', self.alpha)])
        opened, tracking = self.record_opens()
        with tracking:
            with self.assertRaises(ValueError):
                self.module.build_index(self.hub)
        self.assert_no_reads_below(opened, self.beta)

    def test_record_file_link_is_rejected_even_inside_own_project(self):
        canonical = self.alpha / 'ai/current-task.md'
        target = self.alpha / 'ai/private-current.md'
        canonical.rename(target)
        canonical.symlink_to(target)
        self.registry([('alpha', 'active', self.alpha)])
        opened, tracking = self.record_opens()
        with tracking:
            with self.assertRaisesRegex(ValueError, 'unsafe canonical task record'):
                self.module.build_index(self.hub)
        self.assertNotIn(target.resolve(), opened)

    def test_registry_cannot_grant_access_outside_projects_root(self):
        outside = self.project('outside', Path(self.temporary.name) / 'outside')
        self.registry([('outside', 'active', outside)])
        opened, tracking = self.record_opens()
        with tracking:
            with self.assertRaisesRegex(ValueError, 'invalid registered project path'):
                self.module.build_index(self.hub)
        self.assert_no_reads_below(opened, outside)

    def test_discovery_opens_only_canonical_task_records(self):
        private = self.alpha / 'ai/private.md'
        private.write_text('### TASK-alpha-20260911-999 — Private memory\n\nStatus: ready\n', encoding='utf-8')
        self.registry([('alpha', 'active', self.alpha)])
        opened, tracking = self.record_opens()
        with tracking:
            rows = self.module.build_index(self.hub)
        expected = {self.alpha / 'ai' / name for name in ('current-task.md', 'future-tasks.md', 'paused-tasks.md')}
        actual = {path for path in opened if path.is_relative_to(self.alpha.resolve())}
        self.assertEqual(actual, {path.resolve() for path in expected})
        self.assertEqual({Path(row['source_path']).resolve() for row in rows}, actual)
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(set(row) == {'project_id', 'task_id', 'title', 'status', 'due', 'source_kind', 'source_path'} for row in rows))


if __name__ == '__main__':
    unittest.main()
