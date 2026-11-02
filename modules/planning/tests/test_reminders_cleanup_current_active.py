import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).parents[1] / 'scripts' / 'reminders_old_list_cleanup.py'
spec = importlib.util.spec_from_file_location('cleanup_current_active_subject', SCRIPT)
cleanup = importlib.util.module_from_spec(spec); spec.loader.exec_module(cleanup)
PLANNING = Path(__file__).parents[1] / 'scripts'

def load_module(name):
    module_spec = importlib.util.spec_from_file_location(name, PLANNING / f'{name}.py')
    module = importlib.util.module_from_spec(module_spec); module_spec.loader.exec_module(module); return module

structure_adapter_module = load_module('reminders_structure')
project_adapter_module = load_module('reminders_project_lists')


class SummarySource:
    def __init__(self, list_id, list_name, rows):
        self.list_id, self.list_name, self.rows = list_id, list_name, rows
    def call(self, tool, args):
        if tool == 'list_lists':
            return {'lists': [{'id': self.list_id, 'name': self.list_name,
                              'account_id': '60000000-0000-4000-8000-000000000001',
                              'group_id': None, 'total': len(self.rows)}], 'groups': []}
        if tool == 'find_reminders':
            if args.get('list') != self.list_id:
                raise AssertionError('requested list UUID must be exact')
            return {'reminders': self.rows, 'count': len(self.rows)}
        raise AssertionError(tool)


class CancellationAdapter:
    def __init__(self, source): self.source = source
    def call(self, tool, args): return self.source.call(tool, args)


class StructureAdapter:
    def __init__(self, source): self.source = source
    def call(self, tool, args): return self.source.call(tool, args)


class CleanupCurrentActiveTests(unittest.TestCase):
    def context(self, rows=None):
        list_id = '10000000-0000-4000-8000-000000000001'
        rid = '20000000-0000-4000-8000-000000000001'
        list_name = 'current'
        rows = rows if rows is not None else [{'id': rid, 'list': list_name, 'title': 'task', 'version': 'v1'}]
        config = {'projects': {'p': {'list_id': list_id, 'list_name': list_name}},
                  'structure': {'list_roles': {list_id: {'kind': 'direct'}}, 'projects': {}}}
        raw = json.dumps(config, sort_keys=True)
        class Sync:
            @staticmethod
            def validate_binding_ids(_config): return None
        class Helper:
            @staticmethod
            def load_sync(): return Sync
            @staticmethod
            def config_read(_hub): return config, raw
            @staticmethod
            def metadata(native): return native.call('list_lists', {})
        with tempfile.TemporaryDirectory(dir='/private/tmp') as temp:
            hub = Path(temp)
            for adapter in (CancellationAdapter, StructureAdapter):
                native = adapter(SummarySource(list_id, list_name, rows))
                yield hub, config['projects']['p'], native, Helper, rid

    def test_actual_native_adapters_accept_source_summary_without_list_id(self):
        list_id = '10000000-0000-4000-8000-000000000001'
        rid = '20000000-0000-4000-8000-000000000001'
        list_name = 'current'
        rows = [{'id': rid, 'list': list_name, 'title': 'task', 'version': 'v1'}]
        config = {'binary': '/fake/native', 'standard_allowlist_file': '/dev/null',
                  'structure': {'groups_allowlist_file': '/dev/null',
                                'list_roles': {list_id: {'kind': 'direct'}}, 'projects': {}},
                  'projects': {'p': {'list_id': list_id, 'list_name': list_name}}}
        config_raw = json.dumps(config, sort_keys=True)
        class Sync:
            @staticmethod
            def Native(_config): return object()
            @staticmethod
            def structure_module(): return structure_adapter_module
            @staticmethod
            def validate_binding_ids(_config): return None
        class Helper:
            @staticmethod
            def load_sync(): return Sync
            @staticmethod
            def config_read(_hub): return config, config_raw
            @staticmethod
            def metadata(native): return native.call('list_lists', {})
        source = SummarySource(list_id, list_name, rows)
        def run(argv, **_kwargs):
            value = source.call(argv[2], json.loads(argv[3]))
            class Result:
                returncode = 0
                stderr = ''
                stdout = json.dumps(value)
            return Result()
        with tempfile.TemporaryDirectory(dir='/private/tmp') as temp, \
             patch.object(structure_adapter_module, 'standard_allowlist', return_value='/dev/null'), \
             patch.object(structure_adapter_module.subprocess, 'run', side_effect=run), \
             patch.object(project_adapter_module, 'load_sync', return_value=Sync):
            hub = Path(temp)
            adapters = [structure_adapter_module.StructureNative(config), project_adapter_module.Native(config)]
            for adapter in adapters:
                actual = cleanup._current_active_ids(hub, adapter, Helper, 'p', config['projects']['p'])
                self.assertEqual(actual, {rid})

    def test_source_summary_without_list_id_is_owned_by_requested_uuid_for_both_adapters(self):
        for hub, binding, native, helper, rid in self.context():
            actual = cleanup._current_active_ids(hub, native, helper, 'p', binding)
            self.assertEqual(actual, {rid})

    def test_summary_name_mismatch_fails_closed_without_list_id(self):
        for hub, binding, native, helper, _rid in self.context(
                [{'id': '20000000-0000-4000-8000-000000000001', 'list': 'foreign', 'title': 'task'}]):
            with self.assertRaisesRegex(ValueError, 'cleanup_forfeiture_active_reminder_identity_invalid'):
                cleanup._current_active_ids(hub, native, helper, 'p', binding)

    def test_explicit_wrong_list_id_fails_closed(self):
        for hub, binding, native, helper, _rid in self.context(
                [{'id': '20000000-0000-4000-8000-000000000001', 'list': 'current',
                  'list_id': '10000000-0000-4000-8000-000000000002'}]):
            with self.assertRaisesRegex(ValueError, 'cleanup_forfeiture_active_reminder_identity_invalid'):
                cleanup._current_active_ids(hub, native, helper, 'p', binding)

    def test_short_summary_page_fails_closed(self):
        for hub, binding, native, helper, _rid in self.context([]):
            source = native.source
            source.rows = []
            source.call = lambda tool, args: ({'lists': [{'id': source.list_id, 'name': source.list_name,
                'account_id': '60000000-0000-4000-8000-000000000001', 'group_id': None, 'total': 1}], 'groups': []}
                if tool == 'list_lists' else {'reminders': [], 'count': 0})
            with self.assertRaisesRegex(ValueError, 'cleanup_forfeiture_current_list_rows_incomplete'):
                cleanup._current_active_ids(hub, native, helper, 'p', binding)


if __name__ == '__main__': unittest.main()
