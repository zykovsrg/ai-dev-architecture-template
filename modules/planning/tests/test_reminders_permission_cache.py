"""Повторная проверка разрешений на временных квитанциях, без приложения."""
import json
import unittest
from unittest.mock import patch
from test_reminders_project_list_cancellation import ProjectListCancellationTests, m


class PermissionCacheTests(ProjectListCancellationTests):
    def setUp(self):
        super().setUp()
        self.plan = dict(version=2, allowlist_sha256=m.digest(self.standard.read_bytes()))
        self.folder = self.permission_receipt(['Работа', 'Новый'])
        self.reads = m.sync.reads_module()

    def check(self):
        return m.terminal_allowlist_matches(self.hub, self.config, self.plan,
                                          m.digest(self.standard.read_bytes()))

    def test_repeated_receipt_is_parsed_once(self):
        with self.reads.run_scope(), patch.object(m.json, 'loads', wraps=json.loads) as loads:
            self.assertTrue(self.check())
            first = loads.call_count
            self.assertGreater(first, 0)
            self.assertTrue(self.check())
            self.assertEqual(loads.call_count, first)

    def test_state_bytes_change_even_with_same_metadata(self):
        import os
        state = self.folder / 'state.json'
        with self.reads.run_scope():
            self.assertTrue(self.check())
            stamp = state.stat()
            old = state.read_text()
            state.write_text(old.replace('complete', 'tampered'))
            os.utime(state, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
            self.assertEqual(state.stat().st_size, stamp.st_size)
            self.assertFalse(self.check())

    def test_plan_bytes_change_and_receipt_removal(self):
        with self.reads.run_scope():
            self.assertTrue(self.check())
            path = self.folder / 'plan.json'
            raw = path.read_bytes()
            path.write_bytes(raw + b' ')
            self.assertFalse(self.check())
            path.write_bytes(raw)
            self.assertTrue(self.check())
            path.unlink()
            self.assertFalse(self.check())

    def test_original_and_path_are_part_of_identity(self):
        with self.reads.run_scope():
            self.assertTrue(self.check())
            original_path = self.hub / 'ai/reminders-allowlist.json'
            raw_original = original_path.read_bytes()
            original_path.write_bytes(raw_original + b' ')
            self.assertFalse(self.check())
            original_path.write_bytes(raw_original)
            path = self.folder / 'plan.json'
            edge = m.permission_edge(self.hub, self.folder.parent, path, raw_original.decode(),
                                     path.read_bytes(), (self.folder / 'state.json').read_bytes())
            self.assertIsNotNone(edge)
            wrong_path = self.folder.parent / '00000000-0000-0000-0000-000000000099' / 'plan.json'
            self.assertIsNone(m.permission_edge(self.hub, self.folder.parent, wrong_path,
                                               raw_original.decode(), path.read_bytes(),
                                               (self.folder / 'state.json').read_bytes()))

    def test_cache_does_not_survive_scope_or_apply_outside_scope(self):
        with patch.object(m.json, 'loads', wraps=json.loads) as loads:
            with self.reads.run_scope():
                self.assertTrue(self.check())
            first = loads.call_count
            with self.reads.run_scope():
                self.assertTrue(self.check())
            self.assertGreater(loads.call_count, first)
            first = loads.call_count
            self.assertTrue(self.check())
            self.assertTrue(self.check())
            self.assertGreaterEqual(loads.call_count - first, 2 * first // 2)


for name in dir(ProjectListCancellationTests):
    if name.startswith('test_') and name not in PermissionCacheTests.__dict__:
        setattr(PermissionCacheTests, name, None)
del ProjectListCancellationTests
