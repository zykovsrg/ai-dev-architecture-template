"""Общий снимок чтения «Напоминаний» за запуск; без вызовов приложения."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

SCRIPTS = Path(__file__).parents[1] / 'scripts'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


ENV = {'HUB_REMINDERS_ALLOWED_LISTS_FILE': '/allow.json'}


class FakeApp:
    def __init__(self, lists=('A', 'B', 'C')):
        self.lists = list(lists)
        self.calls = []
        self.changed_meta = False
        self.failing_list = None
        self.delay = 0
        self.active = 0
        self.peak = 0
        self.lock = threading.Lock()

    def result(self, value, code=0):
        return subprocess.CompletedProcess([], code, json.dumps(value), '')

    def __call__(self, tool, args):
        with self.lock:
            self.calls.append(tool)
            self.active += 1; self.peak = max(self.peak, self.active)
        try:
            if self.delay: time.sleep(self.delay)
            if tool == 'list_lists':
                count = sum(1 for name in self.calls if name == 'list_lists')
                names = self.lists + (['new'] if self.changed_meta and count > 1 else [])
                return self.result({'lists': [{'id': name, 'name': name} for name in names], 'groups': []})
            if tool == 'find_reminders':
                if args['list'] == self.failing_list: return self.result({}, 1)
                return self.result({'reminders': [{'id': args['list'] + '-1', 'list_id': args['list']}]})
            return self.result({'ok': True})
        finally:
            with self.lock: self.active -= 1

    def count(self, tool):
        return sum(1 for name in self.calls if name == tool)


class ReadsTests(unittest.TestCase):
    def setUp(self):
        self.reads = load('reads_under_test', SCRIPTS / 'reminders_reads.py')
        self.app = FakeApp()

    def call(self, tool, args=None, env=ENV):
        return self.reads.call('/bin/app', env, tool, args or {}, self.app)

    def full_scan(self):
        meta = json.loads(self.call('list_lists').stdout)
        rows = [json.loads(self.call('find_reminders', {'list': row['id'], 'include_completed': True, 'limit': 500}).stdout)
                for row in meta['lists']]
        self.call('list_lists')
        return rows

    def test_outside_scope_every_call_reaches_app(self):
        self.full_scan(); self.full_scan()
        self.assertEqual(self.app.count('list_lists'), 4)
        self.assertEqual(self.app.count('find_reminders'), 6)

    def test_repeated_full_scans_read_app_once(self):
        with self.reads.run_scope():
            first = self.full_scan(); second = self.full_scan()
        self.assertEqual(first, second)
        self.assertEqual(self.app.count('list_lists'), 2)
        self.assertEqual(self.app.count('find_reminders'), 3)

    def test_metadata_change_during_snapshot_disables_cache(self):
        self.app.changed_meta = True
        with self.reads.run_scope():
            self.full_scan(); self.full_scan()
        self.assertEqual(self.app.count('find_reminders'), 3 + 3 + 4)

    def test_failed_list_read_disables_cache(self):
        self.app.failing_list = 'B'
        with self.reads.run_scope():
            self.call('list_lists')
            self.assertEqual(self.call('find_reminders', {'list': 'A', 'include_completed': True, 'limit': 500}).returncode, 0)
        self.assertEqual(self.app.count('find_reminders'), 4)

    def test_write_drops_snapshot(self):
        with self.reads.run_scope():
            self.full_scan()
            self.call('update_reminder', {'id': 'A-1', 'version': '1'})
            self.full_scan()
        self.assertEqual(self.app.count('find_reminders'), 6)

    def test_snapshot_reads_lists_in_parallel(self):
        self.app.lists = [str(index) for index in range(8)]
        self.app.delay = 0.05
        with self.reads.run_scope():
            self.call('list_lists')
        self.assertGreater(self.app.peak, 1)

    def test_list_read_exception_disables_cache_without_failing_metadata(self):
        app = self.app
        def runner(tool, args):
            if tool == 'find_reminders' and args['list'] == 'B':
                raise subprocess.TimeoutExpired('app', 50)
            return app(tool, args)
        with self.reads.run_scope():
            try:
                result = self.reads.call('/bin/app', ENV, 'list_lists', {}, runner)
            except subprocess.TimeoutExpired:
                self.fail('ошибка чтения списка вышла из перечня списков')
            self.assertEqual(result.returncode, 0)
            self.call('find_reminders', {'list': 'A', 'include_completed': True, 'limit': 500})
        self.assertEqual(app.count('find_reminders'), 3)

    def test_write_in_other_scope_drops_snapshot(self):
        with self.reads.run_scope():
            self.full_scan()
            self.reads.call('/bin/cancel', {'HUB_REMINDERS_ALLOWED_LISTS_FILE': '/other.json'},
                            'hub_cancel_reminder', {'id': 'A-1'}, self.app)
            self.call('list_lists')
        self.assertEqual(self.app.count('list_lists'), 4)

    def test_refresh_makes_next_read_fresh(self):
        with self.reads.run_scope():
            self.full_scan()
            self.reads.refresh()
            self.call('find_reminders', {'list': 'A', 'include_completed': True, 'limit': 500})
        self.assertEqual(self.app.count('find_reminders'), 4)

    def test_cancel_status_reaches_app_once_until_write(self):
        status = {'plan': '/p.json', 'plan_sha256': 'a' * 64, 'id': 'A-1'}
        with self.reads.run_scope():
            first = self.call('hub_cancel_status', status)
            self.assertEqual(self.call('hub_cancel_status', status), first)
            self.call('hub_cancel_status', dict(status, id='B-1'))
            self.call('update_reminder', {'id': 'A-1', 'version': '1'})
            self.call('hub_cancel_status', status)
        self.assertEqual(self.app.count('hub_cancel_status'), 3)

    def test_failed_cancel_status_is_asked_again(self):
        status = {'plan': '/p.json', 'plan_sha256': 'a' * 64, 'id': 'A-1'}
        app = self.app
        def runner(tool, args):
            app(tool, args)
            return app.result({'error': 'busy'}, 1)
        with self.reads.run_scope():
            self.reads.call('/bin/app', ENV, 'hub_cancel_status', status, runner)
            self.reads.call('/bin/app', ENV, 'hub_cancel_status', status, runner)
        self.assertEqual(app.count('hub_cancel_status'), 2)

    def test_scope_separates_allowlists(self):
        with self.reads.run_scope():
            self.full_scan()
            self.call('list_lists', env={'HUB_REMINDERS_ALLOWED_LISTS_FILE': '/other.json'})
        self.assertEqual(self.app.count('list_lists'), 4)


class MemoTests(unittest.TestCase):
    def setUp(self):
        self.reads = load('memo_reads_under_test', SCRIPTS / 'reminders_reads.py')
        self.runs = 0

    def verify(self, stable=True):
        def run():
            self.runs += 1
            return self.runs, stable
        return run

    def test_memo_reuses_result_within_scope(self):
        with self.reads.run_scope():
            self.assertEqual(self.reads.memo('key', self.verify()), 1)
            self.assertEqual(self.reads.memo('key', self.verify()), 1)
        self.assertEqual(self.runs, 1)

    def test_memo_outside_scope_always_verifies(self):
        self.reads.memo('key', self.verify()); self.reads.memo('key', self.verify())
        self.assertEqual(self.runs, 2)

    def test_memo_skips_result_when_files_changed_during_check(self):
        with self.reads.run_scope():
            self.reads.memo('key', self.verify(stable=False)); self.reads.memo('key', self.verify(stable=False))
        self.assertEqual(self.runs, 2)

    def test_run_scope_keeps_bytecode_in_temporary_folder(self):
        saved = sys.dont_write_bytecode, sys.pycache_prefix
        with self.reads.run_scope():
            self.assertFalse(sys.dont_write_bytecode)
            folder = sys.pycache_prefix
            self.assertTrue(folder and Path(folder).is_dir())
        self.assertEqual((sys.dont_write_bytecode, sys.pycache_prefix), saved)
        self.assertFalse(Path(folder).exists())


class ReceiptMemoTests(unittest.TestCase):
    def setUp(self):
        sys.modules.pop('hub_reminders_reads', None)
        self.addCleanup(sys.modules.pop, 'hub_reminders_reads', None)
        self.cleanup = load('memo_cleanup_under_test', SCRIPTS / 'reminders_old_list_cleanup.py')
        self.reads = load('memo_receipt_reads_under_test', SCRIPTS / 'reminders_reads.py')
        sys.modules['hub_reminders_reads'] = self.reads
        temp = tempfile.TemporaryDirectory(dir='/private/tmp'); self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name).resolve() / 'op'
        self.folder.mkdir()
        for name in ('receipt.json', 'plan.json', 'state.json'):
            (self.folder / name).write_text('{}')
        self.reference = {'path': str(self.folder / 'receipt.json'), 'sha256': '0' * 64}
        self.checks = 0
        def contents(hub, reference, expected_parent_id=None, reminder_id=None):
            self.checks += 1
            return {'checked': self.checks}
        self.cleanup._verify_receipt_contents = contents

    def test_receipt_is_checked_again_after_file_change(self):
        with self.reads.run_scope():
            self.cleanup._verify_receipt(None, self.reference)
            self.cleanup._verify_receipt(None, self.reference)
            self.assertEqual(self.checks, 1)
            state = self.folder / 'state.json'
            state.write_text('{"phase": "complete"}')
            self.cleanup._verify_receipt(None, self.reference)
        self.assertEqual(self.checks, 2)


class SharedSnapshotTests(unittest.TestCase):
    def test_sync_and_structure_natives_share_one_snapshot(self):
        sys.modules.pop('hub_reminders_reads', None)
        self.addCleanup(sys.modules.pop, 'hub_reminders_reads', None)
        sync = load('reads_sync_under_test', SCRIPTS / 'reminders_sync.py')
        structure = sync.structure_module()
        temp = tempfile.TemporaryDirectory(dir='/private/tmp'); self.addCleanup(temp.cleanup)
        root = Path(temp.name).resolve()
        for name in ('reminders-allowlist.json', 'groups.json'):
            (root / name).write_text('{}')
        config = {'binary': '/bin/app', 'allowlist_file': str(root / 'reminders-allowlist.json'),
                  'structure': {'groups_allowlist_file': str(root / 'groups.json')}}
        app = FakeApp()
        def run(argv, **_):
            return app(argv[2], json.loads(argv[3]))
        with mock.patch('subprocess.run', run), sync.reads_module().run_scope():
            sync.Native(config).call('list_lists', {})
            reader = structure.StructureNative(config)
            for _ in range(2):
                reader.call('list_lists', {})
                for name in app.lists:
                    reader.call('find_reminders', {'list': name, 'include_completed': True, 'limit': 500})
                reader.call('list_lists', {})
        self.assertEqual(app.count('list_lists'), 2)
        self.assertEqual(app.count('find_reminders'), 3)
        with mock.patch('subprocess.run', run), sync.reads_module().run_scope():
            sync.Native(config).call('list_lists', {})
            structure.fresh_reads()
            reader.call('find_reminders', {'list': 'A', 'include_completed': True, 'limit': 500})
        # Перед проверкой записи структура читает приложение заново.
        self.assertEqual(app.count('find_reminders'), 3 + 3 + 1)


if __name__ == '__main__':
    unittest.main()
