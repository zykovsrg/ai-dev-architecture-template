import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).parents[1] / 'scripts' / 'reminders_old_list_cleanup.py'
spec = importlib.util.spec_from_file_location('forfeiture_current_area', SCRIPT)
cleanup = importlib.util.module_from_spec(spec); spec.loader.exec_module(cleanup)
FIXTURE = Path(__file__).with_name('test_reminders_old_list_cleanup.py')
fixture_spec = importlib.util.spec_from_file_location('forfeiture_receipt_fixture', FIXTURE)
fixture = importlib.util.module_from_spec(fixture_spec); fixture_spec.loader.exec_module(fixture)

ACCOUNT = '60000000-0000-4000-8000-000000000001'


class CurrentNative:
    def __init__(self, lists, rows):
        self.lists = lists
        self.rows = rows
        self.calls = []
        self.empty_metadata = False
        self.omit_row = None
        self.unstable_metadata = False
        self.metadata_reads = 0

    def call(self, tool, args):
        self.calls.append((tool, args))
        if tool == 'list_lists':
            self.metadata_reads += 1
            lists = [] if self.empty_metadata else self.lists
            if self.unstable_metadata and self.metadata_reads > 1:
                lists = [dict(lists[0], total=lists[0]['total'] + 1), *lists[1:]]
            return {'lists': [dict(row) for row in lists], 'groups': []}
        if tool == 'find_reminders':
            rows = [dict(row) for row in self.rows if row['list_id'] == args['list']]
            if self.omit_row is not None:
                rows = [row for row in rows if row['id'] != self.omit_row]
            return {'reminders': rows, 'count': len(rows)}
        raise AssertionError(tool)


class ForfeitureCurrentAreaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='/private/tmp')
        self.addCleanup(self.temp.cleanup)
        self.hub = Path(self.temp.name).resolve()
        (self.hub / 'ai').mkdir()
        self.reference, self.parent_id, self.requested = fixture.OldListCleanupContractTests.completed_receipt(self.hub)
        self.receipt = json.loads(Path(self.reference['path']).read_text())
        self.all_refusals = list(self.receipt['restore_refusal_ids'])
        self.reference['restore_refusal_ids'] = [self.requested]

        self.lists = []
        self.rows = []
        self.bindings = {}
        self.roles = {}
        for index, lid in enumerate(self.receipt['protected_list_ids']):
            pid = 'sample' if index == 0 else 'project-' + str(index)
            name = 'current-' + str(index)
            self.lists.append({'id': lid, 'name': name, 'account_id': ACCOUNT, 'group_id': None,
                               'open': 2, 'total': 2, 'shared': False})
            for offset in range(2):
                rid = f'90000000-0000-4000-8000-{index * 2 + offset + 1:012X}'
                self.rows.append({'id': rid, 'list_id': lid, 'list': name, 'title': f'task-{index}-{offset}'})
            binding = {'layout': 'project_list', 'parent_id': None, 'list_id': lid,
                       'list_name': name, 'account_id': ACCOUNT, 'tasks': {}, 'history': {}}
            self.bindings[pid] = binding
            self.roles[lid] = {'kind': 'project', 'project_id': pid}
        self.binding = self.bindings['sample']
        self.binding.update(retired_parent={'id': self.parent_id},
                            retired_parent_cleanup=self.reference,
                            restoration_forfeit_state={'state': 'restoration_forfeited',
                                                       'reminder_ids': [self.requested]})
        allowlist = self.hub / 'ai/reminders-allowlist.json'
        allowlist.write_text('{"names":[]}')
        self.config = {'allowlist_file': str(allowlist), 'projects': self.bindings,
                       'structure': {'list_roles': self.roles}}
        (self.hub / 'ai/reminders-sync.json').write_text(json.dumps(self.config))
        self.native = CurrentNative(self.lists, self.rows)

        helper_spec = importlib.util.spec_from_file_location('forfeiture_project_lists', SCRIPT.with_name('reminders_project_lists.py'))
        self.helper = importlib.util.module_from_spec(helper_spec); helper_spec.loader.exec_module(self.helper)
        original_sync_loader = self.helper.load_sync
        class Sync:
            @staticmethod
            def validate_binding_ids(config): return original_sync_loader().validate_binding_ids(config)
            @staticmethod
            def cancellation_module():
                class Cancellation:
                    @staticmethod
                    def verify_forfeiture_proof(_hub, _proof): return True
                return Cancellation
        self.helper.load_sync = lambda: Sync
        original_modules = cleanup._modules
        cleanup._modules = lambda: self.helper
        self.addCleanup(lambda: setattr(cleanup, '_modules', original_modules))

    def check(self):
        return cleanup.restoration_forfeited_for_binding(self.hub, self.binding, self.requested, self.native)

    def test_all_receipt_refusals_are_checked_when_local_reference_is_a_subset(self):
        other = next(rid for rid in self.all_refusals if rid != self.requested)
        self.rows.append({'id': other, 'list_id': self.lists[0]['id'], 'list': self.lists[0]['name'], 'title': 'reappeared refused task'})
        self.lists[0]['total'] += 1; self.lists[0]['open'] += 1
        with self.assertRaisesRegex(ValueError, '^cleanup_forfeited_reminder_active$'):
            self.check()

    def test_empty_native_metadata_cannot_prove_absence(self):
        self.native.empty_metadata = True
        with self.assertRaisesRegex(ValueError, '^cleanup_forfeiture_current_scope_incomplete$'):
            self.check()

    def test_truncated_rows_without_more_flag_fail_against_current_list_total(self):
        self.native.omit_row = self.rows[0]['id']
        with self.assertRaisesRegex(ValueError, '^cleanup_forfeiture_current_list_rows_incomplete$'):
            self.check()

    def test_metadata_must_be_stable_before_and_after_row_scan(self):
        self.native.unstable_metadata = True
        with self.assertRaisesRegex(ValueError, '^cleanup_forfeiture_current_area_changed$'):
            self.check()

    def test_terminal_binding_must_match_current_config_identity(self):
        path = self.hub / 'ai/reminders-sync.json'
        current = json.loads(path.read_text())
        current['projects']['sample']['future_config_field'] = 'changed during read'
        path.write_text(json.dumps(current))
        with self.assertRaisesRegex(ValueError, '^cleanup_forfeiture_current_project_identity_changed$'):
            self.check()

    def test_normal_edit_create_cancel_restore_and_new_project_use_current_totals(self):
        self.assertTrue(self.check())
        self.rows[0]['title'] = 'edited current task'
        self.assertTrue(self.check())
        created = {'id': '91000000-0000-4000-8000-000000000001',
                   'list_id': self.lists[0]['id'], 'list': self.lists[0]['name'],
                   'title': 'new ordinary task'}
        self.rows.append(created); self.lists[0]['total'] += 1; self.lists[0]['open'] += 1
        self.assertTrue(self.check())
        self.rows.remove(created); self.lists[0]['total'] -= 1; self.lists[0]['open'] -= 1
        self.assertTrue(self.check())
        self.rows.append(created); self.lists[0]['total'] += 1; self.lists[0]['open'] += 1
        self.assertTrue(self.check())

        lid = '91000000-0000-4000-8000-000000000002'
        pid = 'new-project'
        name = 'new current project'
        self.lists.append({'id': lid, 'name': name, 'account_id': ACCOUNT, 'group_id': None,
                           'open': 1, 'total': 1, 'shared': False})
        self.rows.append({'id': '91000000-0000-4000-8000-000000000003',
                          'list_id': lid, 'list': name, 'title': 'new project task'})
        self.bindings[pid] = {'layout': 'project_list', 'parent_id': None, 'list_id': lid,
                              'list_name': name, 'account_id': ACCOUNT, 'tasks': {}, 'history': {}}
        self.roles[lid] = {'kind': 'project', 'project_id': pid}
        self.config['projects'] = self.bindings; self.config['structure']['list_roles'] = self.roles
        (self.hub / 'ai/reminders-sync.json').write_text(json.dumps(self.config))
        self.assertTrue(self.check())

    def test_cleanup_reference_without_local_refusals_is_not_forfeited(self):
        del self.reference['restore_refusal_ids']
        del self.binding['restoration_forfeit_state']
        self.assertFalse(self.check())
        self.assertEqual(self.native.calls, [])

    def test_missing_local_refusals_with_forfeit_state_fails_closed(self):
        del self.reference['restore_refusal_ids']
        with self.assertRaisesRegex(ValueError, '^cleanup_forfeiture_config_state_invalid$'):
            self.check()

    def test_present_malformed_local_refusals_fail_closed(self):
        self.reference['restore_refusal_ids'] = None
        del self.binding['restoration_forfeit_state']
        with self.assertRaisesRegex(ValueError, '^cleanup_forfeiture_config_state_invalid$'):
            self.check()


if __name__ == '__main__':
    unittest.main()
