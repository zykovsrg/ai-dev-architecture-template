import contextlib
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).parents[1] / 'scripts' / 'reminders_old_list_cleanup.py'
spec = importlib.util.spec_from_file_location('old_list_cleanup_apply', SCRIPT)
cleanup = importlib.util.module_from_spec(spec); spec.loader.exec_module(cleanup)


class HubStub:
    @staticmethod
    def safe(path):
        path = Path(path)
        if not path.is_absolute() or path != path.resolve() or any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError('unsafe_path')
        return path

    @staticmethod
    @contextlib.contextmanager
    def locked(_hub):
        yield

    @staticmethod
    def reset_cache(_native):
        return None

    @staticmethod
    def sha(value):
        return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()

    @staticmethod
    def encoded(value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n'

    @staticmethod
    def durable(path, value, exclusive=False):
        Path(path).write_text(value)

    @staticmethod
    def load_sync():
        class Sync:
            @staticmethod
            def validate_binding_ids(config): return None
        return Sync

    @staticmethod
    def config_read(hub):
        raw = (hub / 'ai/reminders-sync.json').read_text()
        return json.loads(raw), raw

    @staticmethod
    def metadata(native):
        return {'lists': list(native.lists.values()), 'groups': []}

    @staticmethod
    def rows(native, list_id):
        return {rid: row for rid, row in native.reminders.items() if row['list_id'] == list_id}


class NativeStub:
    def __init__(self, lists, reminders):
        self.lists = lists
        self.reminders = reminders
        self.effects = []
        self.calls = 0
        self.fail_before_once = False
        self.fail_after_once = False
        self.partial_then_fail_once = False
        self.on_last_effect = None

    def call(self, tool, args):
        if tool != 'manage_list':
            raise AssertionError(tool)
        if set(args) != {'action', 'list', 'confirm_delete_reminders'} or args['action'] != 'delete' or args['confirm_delete_reminders'] is not True:
            raise AssertionError(args)
        self.calls += 1
        lid = args['list']
        if self.fail_before_once:
            self.fail_before_once = False
            raise TimeoutError('unknown before effect')
        if self.partial_then_fail_once:
            self.partial_then_fail_once = False
            matching = [rid for rid, row in self.reminders.items() if row['list_id'] == lid]
            for rid in matching[:max(1, len(matching) // 2)]:
                self.reminders.pop(rid)
            self.lists[lid]['total'] = len([r for r in self.reminders.values() if r['list_id'] == lid])
            self.lists[lid]['open'] = self.lists[lid]['total']
            raise TimeoutError('partial native result')
        self.effects.append(lid)
        self.lists.pop(lid)
        self.reminders = {rid: row for rid, row in self.reminders.items() if row['list_id'] != lid}
        if self.fail_after_once:
            self.fail_after_once = False
            raise TimeoutError('unknown after effect')
        if len(self.effects) == 18 and self.on_last_effect:
            self.on_last_effect()
        return {'ok': True}


class CleanupApplyTests(unittest.TestCase):
    def test_preview_orders_smallest_nonempty_list_first_and_empty_last(self):
        ids = ['id-z', 'id-b', 'id-a', 'id-empty']
        inventory = {'lists': {
            'id-z': {'name': 'Zulu', 'total': 2},
            'id-b': {'name': 'Beta', 'total': 1},
            'id-a': {'name': 'Alpha', 'total': 1},
            'id-empty': {'name': 'Хадасса', 'total': 0},
        }}
        self.assertEqual(cleanup._ordered_candidate_ids(ids, inventory),
                         ['id-a', 'id-b', 'id-z', 'id-empty'])

    def test_preview_rejects_unrecognized_delete_driver(self):
        with self.assertRaisesRegex(ValueError, '^cleanup_delete_driver_invalid$'):
            cleanup.preview('/unused', '/unused', '0' * 64, delete_driver='unknown')

    def test_preview_cli_exposes_immutable_driver_choice(self):
        result = subprocess.run([sys.executable, str(SCRIPT), 'preview', '--help'],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertIn('--delete-driver', result.stdout)
        self.assertIn('reminders_ui', result.stdout)

    def test_cli_apply_reaches_plan_validation_without_native_effects(self):
        result = subprocess.run([sys.executable, str(SCRIPT), 'apply', '--plan',
            '/private/tmp/no-such-cleanup-plan/plan.json', '--sha256', '0' * 64, '--approve'],
            capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('FileNotFoundError', result.stderr)
        self.assertNotIn('NameError', result.stderr)

    def fixture(self):
        root = Path(tempfile.mkdtemp(dir='/private/tmp')).resolve()
        (root / 'ai/reminders-list-cleanups').mkdir(parents=True)
        (root / 'ai').joinpath('reminders-sync.json').write_text('{}')
        old = [f'00000000-0000-4000-8000-{i:012X}' for i in range(1, 19)]
        protected = [f'10000000-0000-4000-8000-{i:012X}' for i in range(1, 77)]
        parents = [f'30000000-0000-4000-8000-{i:012X}' for i in range(1, 75)]
        refusal = [f'50000000-0000-4000-8000-{i:012X}' for i in range(1, 6)]
        lists = {}
        reminders = {}
        for i, lid in enumerate(old):
            assigned = parents[i::18]
            lists[lid] = {'id': lid, 'name': f'old-{i}', 'account_id': '60000000-0000-4000-8000-000000000001',
                           'group_id': None, 'open': len(assigned), 'total': len(assigned)}
            for rid in assigned:
                reminders[rid] = {'id': rid, 'list_id': lid, 'title': f'old parent {rid}', 'version': 'v1'}
        survivor_ids = [f'20000000-0000-4000-8000-{i:012X}' for i in range(1, 627)]
        for i, lid in enumerate(protected):
            assigned = survivor_ids[i::76]
            lists[lid] = {'id': lid, 'name': f'active-{i}', 'account_id': '60000000-0000-4000-8000-000000000001',
                          'group_id': None, 'open': len(assigned), 'total': len(assigned),
                          'kind': 'project', 'project_id': f'p{i}'}
            for rid in assigned:
                reminders[rid] = {'id': rid, 'list_id': lid, 'title': f'working {rid}', 'version': 'w1',
                                  'notes': 'preserve me', 'tags': ['reviewed']}
        bindings = {}
        for i, parent in enumerate(parents):
            bindings[f'p{i}'] = {'layout': 'project_list', 'list_id': protected[i],
                'list_name': lists[protected[i]]['name'], 'parent_id': None, 'tasks': {},
                'retired_parent': {'id': parent}}
        subgroups = {'seo': {'list_id': old[1], 'parent': 'hadassah'},
                     'promo': {'list_id': old[2], 'parent': 'hadassah'},
                     'businka': {'list_id': old[3], 'parent': 'dela'},
                     'kept': {'list_id': protected[0], 'parent': 'other'}}
        defaults = {'hadassah': old[0], 'personal': protected[1]}
        config = {'projects': bindings, 'structure': {'subgroups': subgroups,
            'group_default_lists': defaults, 'projects': {'logical': {'group': 'hadassah'}}, 'list_roles':
            {**{lid: {'kind': 'direct'} for lid in old},
             **{lid: {'kind': 'project', 'project_id': f'p{i}'} for i, lid in enumerate(protected)}}}}
        config_raw = json.dumps(config, sort_keys=True, indent=2) + '\n'
        (root / 'ai/reminders-sync.json').write_text(config_raw)
        consent = {'state': 'restoration_forfeited',
                   'statement': 'Удалить без сохранения возможности восстановить эти пять задач — быстрее',
                   'reminder_ids': refusal}
        proofs = {rid: {'project_id': 'sample', 'task_id': f'task-{i}', 'reminder_id': rid,
                        'operation_id': '40000000-0000-4000-8000-000000000002', 'plan_sha256': '0' * 64,
                        'native_status': {'state': 'deleted', 'version': f'v{i}',
                                          'snapshot': {'id': rid, 'version': f'v{i}',
                                                       'list_id': old[0], 'list': 'old-0'}}}
                  for i, rid in enumerate(refusal)}
        plan = {'kind': 'old_list_cleanup', 'protocol': 1, 'operation': '40000000-0000-4000-8000-000000000001',
            'hub': str(root), 'config_raw': config_raw, 'config_sha256': hashlib.sha256(config_raw.encode()).hexdigest(),
            'scope_sha256': 'a' * 64, 'candidate_list_ids': old, 'protected_list_ids': protected,
            'protected_reminder_ids': survivor_ids, 'retired_parent_ids': parents,
            'affected_projects': list(bindings), 'restore_refusal_ids': refusal,
            'restore_refusal_proofs': proofs, 'restoration_forfeit_consent': consent,
            'removed_structure_references': cleanup._structure_reference_snapshot(config, set(old)),
            'inventory': {'lists': lists, 'reminders': reminders}}
        folder = root / 'ai/reminders-list-cleanups' / plan['operation']; folder.mkdir()
        plan_raw = (json.dumps(plan, sort_keys=True, indent=2) + '\n').encode()
        (folder / 'plan.json').write_bytes(plan_raw)
        digest = hashlib.sha256(plan_raw).hexdigest()
        (folder / 'state.json').write_text(json.dumps({'protocol': 1, 'plan_sha256': digest,
            'approved': False, 'phase': 'preview', 'completed_lists': [], 'write_intent': None}))
        return root, plan, digest, NativeStub(lists, reminders)

    def ui_fixture(self):
        root, plan, _, native = self.fixture()
        plan['delete_driver'] = 'reminders_ui'
        path = root / 'ai/reminders-list-cleanups' / plan['operation'] / 'plan.json'
        raw = json.dumps(plan, sort_keys=True, indent=2) + '\n'; path.write_text(raw)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        state_path = path.with_name('state.json'); state = json.loads(state_path.read_text())
        state.update(plan_sha256=digest); state_path.write_text(json.dumps(state))
        return root, plan, digest, native, path

    def test_apply_requires_explicit_approval_without_native_effect(self):
        root, plan, digest, native = self.fixture()
        original = cleanup._modules
        cleanup._modules = lambda: HubStub
        try:
            with self.assertRaisesRegex(ValueError, 'explicit_approval_required'):
                cleanup.apply(str(root / 'ai/reminders-list-cleanups' / plan['operation'] / 'plan.json'), digest,
                              approve=False, native=native)
            self.assertEqual(native.effects, [])
        finally:
            cleanup._modules = original

    def test_reminders_ui_returns_one_durable_handoff_without_sdk_delete(self):
        root, plan, digest, native, path = self.ui_fixture()
        state_path = path.with_name('state.json')
        state = json.loads(state_path.read_text()); state['plan_sha256'] = digest; state_path.write_text(json.dumps(state))
        original = cleanup._modules; cleanup._modules = lambda: HubStub
        try:
            result = cleanup.apply(str(path), digest, approve=True, native=native)
            self.assertEqual(result['phase'], 'awaiting_ui_delete')
            self.assertEqual(result['action']['list_id'], plan['candidate_list_ids'][0])
            self.assertEqual(result['action']['name'], 'old-0')
            self.assertEqual(result['action']['group_id'], None)
            self.assertEqual(result['action']['expected_count'], len([r for r in plan['inventory']['reminders'].values() if r['list_id'] == plan['candidate_list_ids'][0]]))
            self.assertEqual(len(native.effects), 0)
            self.assertEqual(native.calls, 0)
            intent = json.loads(state_path.read_text())
            self.assertEqual(intent['write_intent'], plan['candidate_list_ids'][0])
            second = cleanup.apply(str(path), digest, approve=True, native=native)
            self.assertEqual(second, result)
            self.assertEqual(native.calls, 0)
        finally:
            cleanup._modules = original

    def test_reminders_ui_reconciles_exact_removal_and_hands_off_next(self):
        root, plan, digest, native, path = self.ui_fixture()
        state_path = path.with_name('state.json'); state = json.loads(state_path.read_text()); state['plan_sha256'] = digest; state_path.write_text(json.dumps(state))
        original = cleanup._modules; cleanup._modules = lambda: HubStub
        try:
            first = cleanup.apply(str(path), digest, approve=True, native=native)
            removed = plan['candidate_list_ids'][0]
            native.lists.pop(removed)
            native.reminders = {rid: row for rid, row in native.reminders.items() if row['list_id'] != removed}
            next_action = cleanup.apply(str(path), digest, approve=True, native=native)
            self.assertEqual(next_action['phase'], 'awaiting_ui_delete')
            self.assertEqual(next_action['action']['list_id'], plan['candidate_list_ids'][1])
            state = json.loads(state_path.read_text())
            self.assertEqual(state['completed_lists'], [removed])
            self.assertEqual(state['write_intent'], plan['candidate_list_ids'][1])
            self.assertEqual(len(native.effects), 0)
        finally:
            cleanup._modules = original

    def test_reminders_ui_partial_or_foreign_result_fails_closed(self):
        root, plan, digest, native, path = self.ui_fixture()
        original = cleanup._modules; cleanup._modules = lambda: HubStub
        try:
            cleanup.apply(str(path), digest, approve=True, native=native)
            target = plan['candidate_list_ids'][0]
            rid = next(rid for rid, row in native.reminders.items() if row['list_id'] == target)
            native.reminders.pop(rid)
            with self.assertRaisesRegex(ValueError, 'cleanup_candidate_count_mismatch|cleanup_ui_partial_or_foreign_change'):
                cleanup.apply(str(path), digest, approve=True, native=native)
            self.assertEqual(native.calls, 0)
        finally:
            cleanup._modules = original
        root, plan, digest, native, path = self.ui_fixture()
        original = cleanup._modules; cleanup._modules = lambda: HubStub
        try:
            cleanup.apply(str(path), digest, approve=True, native=native)
            native.lists[plan['candidate_list_ids'][1]]['open'] += 1
            with self.assertRaisesRegex(ValueError, 'cleanup_candidate_metadata_changed'):
                cleanup.apply(str(path), digest, approve=True, native=native)
            self.assertEqual(native.calls, 0)
        finally:
            cleanup._modules = original
        root, plan, digest, native, path = self.ui_fixture()
        original = cleanup._modules; cleanup._modules = lambda: HubStub
        try:
            cleanup.apply(str(path), digest, approve=True, native=native)
            foreign = '90000000-0000-4000-8000-000000000001'
            native.lists[foreign] = {'id': foreign, 'name': 'foreign', 'account_id': '60000000-0000-4000-8000-000000000001',
                                     'group_id': None, 'open': 0, 'total': 0}
            with self.assertRaisesRegex(ValueError, 'cleanup_live_list_set_changed'):
                cleanup.apply(str(path), digest, approve=True, native=native)
            self.assertEqual(native.calls, 0)
        finally:
            cleanup._modules = original

    def test_reminders_ui_rejects_protected_snapshot_change(self):
        root, plan, digest, native, path = self.ui_fixture()
        original = cleanup._modules; cleanup._modules = lambda: HubStub
        try:
            cleanup.apply(str(path), digest, approve=True, native=native)
            rid = plan['protected_reminder_ids'][0]
            native.reminders[rid]['notes'] = 'foreign edit'
            with self.assertRaisesRegex(ValueError, 'protected_reminder_changed'):
                cleanup.apply(str(path), digest, approve=True, native=native)
            self.assertEqual(native.calls, 0)
        finally:
            cleanup._modules = original

    def test_reminders_ui_driver_is_bound_to_the_immutable_plan(self):
        root, plan, digest, native, path = self.ui_fixture()
        raw = path.read_text().replace('reminders_ui', 'native')
        path.write_text(raw)
        original = cleanup._modules; cleanup._modules = lambda: HubStub
        try:
            with self.assertRaisesRegex(ValueError, 'cleanup_plan_sha256_mismatch'):
                cleanup.apply(str(path), digest, approve=True, native=native)
            self.assertEqual(native.calls, 0)
        finally:
            cleanup._modules = original

    def test_reminders_ui_rejects_nonunique_visible_list_name(self):
        metadata = {'lists': [
            {'id': 'candidate', 'name': 'same'},
            {'id': 'protected', 'name': 'same'},
        ]}
        with self.assertRaisesRegex(ValueError, '^cleanup_ui_name_not_unique$'):
            cleanup._check_unique_ui_names(metadata, {'candidate'})

    def test_reminders_ui_config_compare_and_swap_rejects_stale_final_write(self):
        root, plan, digest, native, path = self.ui_fixture()
        original = cleanup._modules; cleanup._modules = lambda: HubStub
        try:
            result = cleanup.apply(str(path), digest, approve=True, native=native)
            for lid in plan['candidate_list_ids']:
                self.assertEqual(result['phase'], 'awaiting_ui_delete')
                self.assertEqual(result['action']['list_id'], lid)
                native.lists.pop(lid)
                native.reminders = {rid: row for rid, row in native.reminders.items() if row['list_id'] != lid}
                if lid == plan['candidate_list_ids'][-1]:
                    (root / 'ai/reminders-sync.json').write_text('{"foreign":true}')
                    with self.assertRaisesRegex(ValueError, '^cleanup_config_changed$'):
                        cleanup.apply(str(path), digest, approve=True, native=native)
                    break
                result = cleanup.apply(str(path), digest, approve=True, native=native)
            self.assertEqual(native.calls, 0)
        finally:
            cleanup._modules = original

    def test_apply_deletes_only_approved_lists_and_preserves_all_working_fields(self):
        root, plan, digest, native = self.fixture()
        original = cleanup._modules
        cleanup._modules = lambda: HubStub
        try:
            result = cleanup.apply(str(root / 'ai/reminders-list-cleanups' / plan['operation'] / 'plan.json'), digest,
                                   approve=True, native=native)
            self.assertEqual(result['phase'], 'complete')
            self.assertEqual(len(native.effects), 18)
            self.assertEqual(set(native.lists), set(plan['protected_list_ids']))
            self.assertEqual(set(native.reminders), set(plan['protected_reminder_ids']))
            self.assertTrue(all(row.get('notes') == 'preserve me' and row.get('tags') == ['reviewed']
                                for row in native.reminders.values()))
            final = json.loads((root / 'ai/reminders-sync.json').read_text())
            self.assertEqual(len(final['structure']['list_roles']), 76)
            self.assertEqual(set(final['structure']['subgroups']), {'kept'})
            self.assertEqual(final['structure']['subgroups']['kept'],
                             {'list_id': plan['protected_list_ids'][0], 'parent': 'other'})
            self.assertEqual(final['structure']['group_default_lists'],
                             {'personal': plan['protected_list_ids'][1]})
            self.assertEqual(final['structure']['projects'], {'logical': {'group': 'hadassah'}})
            self.assertEqual(sum(bool(binding.get('retired_parent_cleanup')) for binding in final['projects'].values()), 74)
            receipt = json.loads(Path(result['receipt']['path']).read_text())
            self.assertEqual(receipt['removed_structure_references'], plan['removed_structure_references'])
            self.assertEqual(cleanup._verify_receipt(root, result['receipt']), receipt)
        finally:
            cleanup._modules = original

    def test_unknown_result_after_effect_is_confirmed_without_duplicate_delete(self):
        root, plan, digest, native = self.fixture(); native.fail_after_once = True
        original = cleanup._modules; cleanup._modules = lambda: HubStub
        try:
            result = cleanup.apply(str(root / 'ai/reminders-list-cleanups' / plan['operation'] / 'plan.json'), digest,
                                   approve=True, native=native)
            self.assertEqual(result['phase'], 'complete')
            self.assertEqual(native.calls, 18)
            self.assertEqual(len(native.effects), 18)
        finally:
            cleanup._modules = original

    def test_unknown_result_before_effect_requires_readback_then_safe_resume(self):
        root, plan, digest, native = self.fixture(); native.fail_before_once = True
        original = cleanup._modules; cleanup._modules = lambda: HubStub
        path = str(root / 'ai/reminders-list-cleanups' / plan['operation'] / 'plan.json')
        try:
            with self.assertRaisesRegex(RuntimeError, 'cleanup_native_result_unknown_after_readback'):
                cleanup.apply(path, digest, approve=True, native=native)
            self.assertEqual(native.calls, 1)
            self.assertEqual(native.effects, [])
            result = cleanup.apply(path, digest, approve=True, native=native)
            self.assertEqual(result['phase'], 'complete')
            self.assertEqual(native.calls, 19)
            self.assertEqual(len(native.effects), 18)
        finally:
            cleanup._modules = original

    def test_partial_native_delete_resumes_only_the_same_approved_list(self):
        root, plan, digest, native = self.fixture(); native.partial_then_fail_once = True
        original = cleanup._modules; cleanup._modules = lambda: HubStub
        path = str(root / 'ai/reminders-list-cleanups' / plan['operation'] / 'plan.json')
        try:
            with self.assertRaisesRegex(RuntimeError, 'cleanup_native_result_unknown_after_readback'):
                cleanup.apply(path, digest, approve=True, native=native)
            self.assertEqual(native.calls, 1)
            result = cleanup.apply(path, digest, approve=True, native=native)
            self.assertEqual(result['phase'], 'complete')
            self.assertEqual(native.effects[0], plan['candidate_list_ids'][0])
            self.assertEqual(len(native.effects), 18)
            self.assertEqual(set(native.reminders), set(plan['protected_reminder_ids']))
        finally:
            cleanup._modules = original

    def test_stale_config_stops_before_first_native_effect(self):
        root, plan, digest, native = self.fixture()
        (root / 'ai/reminders-sync.json').write_text('{"changed":true}')
        original = cleanup._modules; cleanup._modules = lambda: HubStub
        try:
            with self.assertRaisesRegex(ValueError, 'cleanup_config_changed'):
                cleanup.apply(str(root / 'ai/reminders-list-cleanups' / plan['operation'] / 'plan.json'), digest,
                               approve=True, native=native)
            self.assertEqual(native.effects, [])
        finally:
            cleanup._modules = original

    def test_final_config_cas_preserves_concurrent_change_after_native_deletes(self):
        root, plan, digest, native = self.fixture()
        config_path = root / 'ai/reminders-sync.json'
        native.on_last_effect = lambda: config_path.write_text('{"concurrent":true}')
        original = cleanup._modules; cleanup._modules = lambda: HubStub
        try:
            with self.assertRaisesRegex(ValueError, 'cleanup_config_cas_failed'):
                cleanup.apply(str(root / 'ai/reminders-list-cleanups' / plan['operation'] / 'plan.json'), digest,
                               approve=True, native=native)
            self.assertEqual(config_path.read_text(), '{"concurrent":true}')
            self.assertEqual(len(native.effects), 18)
        finally:
            cleanup._modules = original


if __name__ == '__main__':
    unittest.main()
