import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).parents[1] / 'scripts' / 'reminders_old_list_cleanup.py'
spec = importlib.util.spec_from_file_location('old_list_cleanup', SCRIPT)
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)


class OldListCleanupContractTests(unittest.TestCase):
    @staticmethod
    def completed_receipt(root, removed_references=None):
        operation = '40000000-0000-4000-8000-000000000001'
        old = [f'00000000-0000-4000-8000-{i:012X}' for i in range(1, 19)]
        parents = [f'30000000-0000-4000-8000-{i:012X}' for i in range(1, 75)]
        protected = [f'10000000-0000-4000-8000-{i:012X}' for i in range(1, 77)]
        records = [f'20000000-0000-4000-8000-{i:012X}' for i in range(1, 627)]
        refusal = [f'50000000-0000-4000-8000-{i:012X}' for i in range(1, 6)]
        snapshot = {rid: {'id': rid, 'list_id': protected[(i % 76)], 'list': f'active-{i % 76}',
                          'title': f'working {i}', 'version': f'v{i}'}
                    for i, rid in enumerate(records)}
        old_list_snapshot = {lid: {'id': lid, 'name': f'old-{i}', 'account_id': '60000000-0000-4000-8000-000000000001'}
                             for i, lid in enumerate(old)}
        all_reminders = dict(snapshot)
        parent_snapshot = {}
        for i, rid in enumerate(parents):
            row = {'id': rid, 'list_id': old[i % len(old)], 'list': f'old-{i % len(old)}', 'version': f'p{i}'}
            all_reminders[rid] = row; parent_snapshot[rid] = row
        protected_list_snapshot = {lid: {'id': lid, 'name': f'active-{i}',
            'account_id': '60000000-0000-4000-8000-000000000001', 'group_id': None,
            'open': 9, 'total': 9, 'shared': False} for i, lid in enumerate(protected)}
        plan = {'kind': 'old_list_cleanup', 'protocol': 1, 'operation': operation,
                'candidate_list_ids': old, 'retired_parent_ids': parents,
                'protected_list_ids': protected, 'restore_refusal_ids': refusal,
                'inventory': {'reminders': all_reminders, 'lists': {**old_list_snapshot, **protected_list_snapshot}}}
        consent = {'state': 'restoration_forfeited',
                   'statement': 'Удалить без сохранения возможности восстановить эти пять задач — быстрее',
                   'reminder_ids': refusal}
        proofs = {rid: {'project_id': 'sample', 'task_id': f'task-{i}', 'reminder_id': rid,
                        'operation_id': operation, 'plan_sha256': '0' * 64,
                        'native_status': {'state': 'deleted', 'version': f'v{i}',
                                          'snapshot': {'id': rid, 'version': f'v{i}',
                                                       'list_id': old[0], 'list': 'old-0'}}}
                  for i, rid in enumerate(refusal)}
        plan['restore_refusal_proofs'] = proofs
        plan['restoration_forfeit_consent'] = consent
        config = {'structure': {
            'subgroups': {'old-group': {'list_id': old[0], 'name': 'old-0'},
                          'active-group': {'list_id': protected[0], 'name': 'active-0'}},
            'group_default_lists': {'old-default': old[1], 'active-default': protected[1]}}}
        config_raw = json.dumps(config, sort_keys=True, indent=2) + '\n'
        if removed_references is None:
            removed_references = {'subgroups': {'old-group': {'list_id': old[0], 'name': 'old-0'}},
                                  'group_default_lists': {'old-default': old[1]}}
        plan['config_raw'] = config_raw
        plan['config_sha256'] = hashlib.sha256(config_raw.encode()).hexdigest()
        plan['removed_structure_references'] = removed_references
        plan_raw = (json.dumps(plan, sort_keys=True, indent=2) + '\n').encode()
        plan_sha = hashlib.sha256(plan_raw).hexdigest()
        folder = root / 'ai' / 'reminders-list-cleanups' / operation
        folder.mkdir(parents=True)
        (folder / 'plan.json').write_bytes(plan_raw)
        receipt = {'protocol': 1, 'state': 'complete', 'operation': operation,
                   'plan_sha256': plan_sha, 'deleted_list_ids': old, 'deleted_parent_ids': parents,
                   'deleted_list_snapshots': old_list_snapshot,
                   'deleted_parent_snapshots': parent_snapshot,
                   'protected_list_ids': protected, 'protected_reminder_count': 626,
                   'protected_reminder_snapshot': snapshot, 'restore_refusal_ids': refusal,
                   'restore_refusal_proofs': proofs,
                   'restoration_forfeit_consent': consent,
                   'removed_structure_references': removed_references}
        receipt_raw = (json.dumps(receipt, sort_keys=True, indent=2) + '\n').encode()
        (folder / 'receipt.json').write_bytes(receipt_raw)
        receipt_sha = hashlib.sha256(receipt_raw).hexdigest()
        (folder / 'state.json').write_text(json.dumps({'protocol': 1, 'phase': 'complete',
            'plan_sha256': plan_sha, 'receipt_sha256': receipt_sha}))
        reference = {'operation': operation, 'path': str(folder / 'receipt.json'),
                     'sha256': receipt_sha, 'restore_refusal_ids': refusal}
        return reference, parents[0], refusal[0]

    @staticmethod
    def sample_scope():
        old_lists = [f'00000000-0000-4000-8000-{i:012X}' for i in range(1, 19)]
        protected_ids = [f'10000000-0000-4000-8000-{i:012X}' for i in range(1, 77)]
        survivor_ids = [f'20000000-0000-4000-8000-{i:012X}' for i in range(1, 627)]
        parent_ids = [f'30000000-0000-4000-8000-{i:012X}' for i in range(1, 75)]
        candidates = []
        for i, list_id in enumerate(old_lists):
            assigned = parent_ids[i::18]
            candidates.append({'list': {'id': list_id, 'name': f'old-{i}', 'total': len(assigned)},
                               'role': {'kind': 'direct'}, 'expected_after_parent_cleanup_count': 0,
                               'deletion_blockers': ['structure_role_present'],
                               'other_ids': [], 'subgroup_ids': [], 'project_ids': [],
                               'retired_parent_ids': assigned,
                               'full_snapshot': [{'id': rid, 'list_id': list_id, 'list': f'old-{i}'}
                                                 for rid in assigned]})
        scope = {
            'candidate_old_lists': 18, 'candidate_list_ids': old_lists,
            'protected_project_list_count': 76,
            'protected_project_lists': [{'list': {'id': lid}} for lid in protected_ids],
            'preserve_current_content_system_list_id': protected_ids[0],
            'survivor_records': [{'id': rid} for rid in survivor_ids],
            'retired_parent_records': [{'reminder_id': rid, 'project_id': f'project-{n}',
                'snapshot': {'id': rid, 'list_id': old_lists[n % 18], 'list': f'old-{n % 18}'}}
                for n, rid in enumerate(parent_ids)],
            'retired_parent_wrappers': 74, 'candidates': candidates,
        }
        return {'kind': 'old_list_removal_readonly_preview', 'version': 1, 'cleanup_scope': scope}

    def test_scope_rejects_any_change_to_frozen_hash(self):
        self.assertTrue(callable(getattr(cleanup, 'load_frozen_scope', None)))
        raw = b'{"kind":"old_list_removal_readonly_preview","version":1}'
        with self.assertRaisesRegex(ValueError, 'scope_sha256_mismatch'):
            cleanup.load_frozen_scope(raw, '0' * 64)

    def test_plan_keeps_exact_uuid_and_explicit_soft_delete_confirmation(self):
        self.assertTrue(callable(getattr(cleanup, 'delete_arguments', None)))
        row = {'id': '038FBFCF-5094-463C-9E16-E3B1B828A274', 'total': 3}
        self.assertEqual(cleanup.delete_arguments(row), {
            'action': 'delete', 'list': row['id'], 'confirm_delete_reminders': True,
        })

    def test_historical_restore_refusal_is_limited_to_five_pinned_ids(self):
        self.assertTrue(callable(getattr(cleanup, 'restore_refused', None)))
        blocked = {'A0000000-0000-4000-8000-000000000001'}
        self.assertTrue(cleanup.restore_refused(blocked, next(iter(blocked))))
        self.assertFalse(cleanup.restore_refused(blocked, 'A0000000-0000-4000-8000-000000000002'))

    def test_scope_accepts_only_the_full_fixed_counts(self):
        self.assertTrue(callable(getattr(cleanup, 'validate_scope', None)))
        scope = self.sample_scope()
        actual = cleanup.validate_scope(scope)
        self.assertEqual((len(actual['candidate_list_ids']), len(actual['retired_parent_ids']),
                          len(actual['protected_list_ids']), len(actual['survivor_ids'])), (18, 74, 76, 626))

    def test_scope_rejects_protected_target_in_deletion_set(self):
        self.assertTrue(callable(getattr(cleanup, 'validate_scope', None)))
        scope = self.sample_scope()
        scope['cleanup_scope']['candidate_list_ids'][0] = scope['cleanup_scope']['protected_project_lists'][0]['list']['id']
        with self.assertRaisesRegex(ValueError, 'cleanup_scope_protected_overlap'):
            cleanup.validate_scope(scope)

    def test_protected_snapshot_compares_every_field(self):
        self.assertTrue(callable(getattr(cleanup, 'same_protected_snapshot', None)))
        before = {'R1': {'id': 'R1', 'title': 'task', 'version': 'v1', 'notes': 'kept'}}
        after = {'R1': {'id': 'R1', 'title': 'task', 'version': 'v1', 'notes': 'changed'}}
        with self.assertRaisesRegex(ValueError, 'protected_reminder_changed'):
            cleanup.same_protected_snapshot(before, after)

    def test_verified_receipt_replaces_only_a_missing_retired_parent(self):
        self.assertTrue(callable(getattr(cleanup, 'retired_parent_cleaned', None)))
        with tempfile.TemporaryDirectory(dir='/private/tmp') as directory:
            root = Path(directory).resolve()
            reference, parent_id, _ = self.completed_receipt(root)
            binding = {'retired_parent': {'id': parent_id}, 'retired_parent_cleanup': reference}
            self.assertTrue(cleanup.retired_parent_cleaned(root, binding))

    def test_restore_refusal_uses_receipt_pinned_uuid(self):
        self.assertTrue(callable(getattr(cleanup, 'restore_refused_for_binding', None)))
        with tempfile.TemporaryDirectory(dir='/private/tmp') as directory:
            root = Path(directory).resolve()
            reference, parent_id, blocked = self.completed_receipt(root)
            binding = {'retired_parent': {'id': parent_id}, 'retired_parent_cleanup': reference}
            self.assertTrue(cleanup.restore_refused_for_binding(root, binding, blocked))
            self.assertFalse(cleanup.restore_refused_for_binding(root, binding,
                '50000000-0000-4000-8000-000000000006'))

    def test_structure_validation_accepts_verified_absence_only(self):
        self.assertTrue(callable(getattr(cleanup, 'retired_parent_cleaned', None)))
        spec = importlib.util.spec_from_file_location('candidate_structure',
            SCRIPT.parent / 'reminders_structure.py')
        structure = importlib.util.module_from_spec(spec); spec.loader.exec_module(structure)
        with tempfile.TemporaryDirectory(dir='/private/tmp') as directory:
            reference, parent_id, _ = self.completed_receipt(Path(directory))
            config = {'projects': {'sample': {'retired_parent': {'id': parent_id},
                                               'retired_parent_cleanup': reference}}}
            self.assertEqual(structure.retired_parent_ids(config, {'reminders': {}}), {parent_id})

    def test_historical_restore_refusal_has_no_native_effect(self):
        spec = importlib.util.spec_from_file_location('candidate_historical',
            SCRIPT.parent / 'reminders_historical.py')
        historical = importlib.util.module_from_spec(spec); spec.loader.exec_module(historical)
        with tempfile.TemporaryDirectory(dir='/private/tmp') as directory:
            root = Path(directory); (root / 'ai').mkdir();
            reference, parent_id, blocked = self.completed_receipt(root)
            (root / 'ai/reminders-sync.json').write_text('{}')
            task_id = 'TASK-sample-20261028-001'
            link = {'reminder_id': blocked, 'cancellation': {'operation_id': 'x'}}
            config = {'projects': {'sample': {'retired_parent': {'id': parent_id},
                'retired_parent_cleanup': reference, 'tasks': {task_id: link}}}}
            (root / 'ai/reminders-sync.json').write_text(json.dumps(config))
            class Coordinator:
                @staticmethod
                def document_bytes(path): return Path(path).read_bytes()
                @staticmethod
                def cancelled_link(item, plan, sha): return item['link']
            class Native:
                calls = []
            plan = {'items': [{'project_id': 'sample', 'task_id': task_id, 'reminder_id': blocked,
                               'link': link}]}
            state = {'approved': True, 'items': {blocked: {'phase': 'committed'}}}
            with self.assertRaisesRegex(ValueError, 'historical_restore_retired_by_user_choice'):
                historical.restore_preview(Coordinator(), root, root / 'unused', 'sha', config,
                                           Native(), plan, state)
            self.assertEqual(Native.calls, [])

    def test_cleanup_journal_blocks_affected_projects_until_complete(self):
        spec = importlib.util.spec_from_file_location('candidate_project_lists',
            SCRIPT.parent / 'reminders_project_lists.py')
        project_lists = importlib.util.module_from_spec(spec); spec.loader.exec_module(project_lists)
        with tempfile.TemporaryDirectory(dir='/private/tmp') as directory:
            hub = Path(directory).resolve(); (hub / 'ai/reminders-project-lists').mkdir(parents=True)
            operation = '40000000-0000-4000-8000-000000000001'
            folder = hub / 'ai/reminders-list-cleanups' / operation; folder.mkdir(parents=True)
            plan_raw = json.dumps({'kind': 'old_list_cleanup', 'operation': operation,
                'affected_projects': ['sample']}).encode()
            plan_sha = hashlib.sha256(plan_raw).hexdigest()
            (folder / 'plan.json').write_bytes(plan_raw)
            (folder / 'state.json').write_text(json.dumps({'phase': 'deleting', 'plan_sha256': plan_sha}))
            class Sync:
                @staticmethod
                def task_reassignment_pending(*args): return set()
                @staticmethod
                def external_retirement_module(): return None
            project_lists.load_sync = lambda: Sync
            self.assertEqual(project_lists.pending_projects(hub, {'projects': {'sample': {}}}), {'sample'})
            (folder / 'state.json').write_text(json.dumps({'phase': 'complete', 'plan_sha256': plan_sha}))
            self.assertEqual(project_lists.pending_projects(hub, {'projects': {'sample': {}}}), set())

    def test_partial_snapshot_change_is_allowed_only_for_current_intent(self):
        self.assertTrue(callable(getattr(cleanup, '_candidate_progress', None)))
        first, second = '00000000-0000-4000-8000-000000000001', '00000000-0000-4000-8000-000000000002'
        row1 = {'id': '30000000-0000-4000-8000-000000000001', 'list_id': first, 'version': 'v1'}
        row2 = {'id': '30000000-0000-4000-8000-000000000002', 'list_id': second, 'version': 'v2'}
        changed2 = dict(row2, version='changed')
        plan = {'candidate_list_ids': [first, second], 'retired_parent_ids': [row1['id'], row2['id']],
                'inventory': {'lists': {first: {'id': first, 'open': 1, 'total': 1},
                                        second: {'id': second, 'open': 1, 'total': 1}},
                              'reminders': {row1['id']: row1, row2['id']: row2}}}
        metadata = {'lists': [plan['inventory']['lists'][first], plan['inventory']['lists'][second]]}
        inventory = {'lists': dict((row['id'], row) for row in metadata['lists']),
                     'reminders': {row1['id']: row1, row2['id']: changed2}}
        with self.assertRaisesRegex(ValueError, 'cleanup_candidate_snapshot_changed'):
            cleanup._candidate_progress(plan, metadata, inventory, set(), intent=first)

    def test_receipt_rejects_references_not_taken_from_saved_config(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as directory:
            hub = Path(directory).resolve()
            reference, parent, _ = self.completed_receipt(
                hub, removed_references={'subgroups': {}, 'group_default_lists': {}})
            with self.assertRaisesRegex(ValueError, 'cleanup_receipt_structure_reference_snapshot_invalid'):
                cleanup._verify_receipt(hub, reference, expected_parent_id=parent)

    def test_final_config_removes_only_retired_roles_and_pins_receipt(self):
        self.assertTrue(callable(getattr(cleanup, '_final_config', None)))
        old = [f'00000000-0000-4000-8000-{i:012X}' for i in range(1, 19)]
        active = [f'10000000-0000-4000-8000-{i:012X}' for i in range(1, 77)]
        parents = [f'30000000-0000-4000-8000-{i:012X}' for i in range(1, 75)]
        projects = {}
        for i, parent in enumerate(parents):
            projects[f'p{i}'] = {'layout': 'project_list', 'list_id': active[i], 'list_name': f'active-{i}',
                'parent_id': None, 'tasks': {}, 'retired_parent': {'id': parent}}
        config = {'projects': projects, 'structure': {'list_roles':
            {**{lid: {'kind': 'direct'} for lid in old},
             **{lid: {'kind': 'project', 'project_id': f'p{i}'} for i, lid in enumerate(active)}},
            'subgroups': {'old-group': {'list_id': old[0]}, 'active-group': {'list_id': active[0]}},
            'group_default_lists': {'old-default': old[1], 'active-default': active[1]}}}
        removed = {'subgroups': {'old-group': {'list_id': old[0]}},
                   'group_default_lists': {'old-default': old[1]}}
        plan = {'candidate_list_ids': old, 'retired_parent_ids': parents,
                'restore_refusal_ids': [], 'removed_structure_references': removed}
        reference = {'operation': '40000000-0000-4000-8000-000000000001', 'path': '/private/tmp/r.json', 'sha256': 'a' * 64}
        result = cleanup._final_config(config, plan, reference, {'removed_structure_references': removed})
        self.assertEqual(set(result['structure']['list_roles']), set(active))
        self.assertEqual(result['structure']['subgroups'], {'active-group': {'list_id': active[0]}})
        self.assertEqual(result['structure']['group_default_lists'], {'active-default': active[1]})
        self.assertEqual(len([b for b in result['projects'].values() if b.get('retired_parent_cleanup')]), 74)


if __name__ == '__main__':
    unittest.main()
