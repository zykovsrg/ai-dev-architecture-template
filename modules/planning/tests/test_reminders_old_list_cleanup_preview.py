import hashlib
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).parents[1] / 'scripts' / 'reminders_old_list_cleanup.py'
spec = importlib.util.spec_from_file_location('cleanup_preview_subject', SCRIPT)
cleanup = importlib.util.module_from_spec(spec); spec.loader.exec_module(cleanup)


class Helper:
    @staticmethod
    def sha(value): return hashlib.sha256(value).hexdigest()


class CleanupInitialPreviewTests(unittest.TestCase):
    def context(self):
        candidate = [f'00000000-0000-4000-8000-{i:012X}' for i in range(1, 19)]
        protected = [f'10000000-0000-4000-8000-{i:012X}' for i in range(1, 77)]
        parents = [f'30000000-0000-4000-8000-{i:012X}' for i in range(1, 75)]
        working = [f'20000000-0000-4000-8000-{i:012X}' for i in range(1, 627)]
        account = '60000000-0000-4000-8000-000000000001'
        scope_candidates = []
        candidate_lists = {}
        reminder_rows = {}
        for i, lid in enumerate(candidate):
            assigned = parents[i::18]
            list_row = {'id': lid, 'name': f'old-{i}', 'account_id': account,
                        'group_id': None, 'shared': False, 'total': len(assigned), 'open': len(assigned)}
            rows = [{'id': rid, 'list_id': lid, 'list': list_row['name'], 'version': f'p{j}', 'parent_id': None}
                    for j, rid in enumerate(assigned)]
            candidate_lists[lid] = list_row
            reminder_rows.update({row['id']: row for row in rows})
            scope_candidates.append({'list': list_row, 'role': {'kind': 'direct'},
                'expected_after_parent_cleanup_count': 0, 'deletion_blockers': ['structure_role_present'],
                'other_ids': [], 'subgroup_ids': [], 'project_ids': [],
                'retired_parent_ids': assigned, 'full_snapshot': rows})
        protected_list_rows = {}
        protected_scope = []
        for i, lid in enumerate(protected):
            rows = working[i::76]
            list_row = {'id': lid, 'name': f'active-{i}', 'account_id': account,
                        'group_id': None, 'shared': False, 'total': len(rows), 'open': len(rows)}
            protected_list_rows[lid] = list_row
            protected_scope.append({'list': list_row, 'project_ids': [f'project-list-{i}'], 'snapshot': []})
            for j, rid in enumerate(rows):
                row = {'id': rid, 'list_id': lid, 'list': list_row['name'],
                       'title': f'working-{j}', 'version': f'w{j}'}
                reminder_rows[rid] = row
                protected_scope[-1]['snapshot'].append(copy.deepcopy(row))
        parent_records = []
        for i, rid in enumerate(parents):
            parent_records.append({'project_id': f'project-{i}', 'reminder_id': rid,
                                   'snapshot': copy.deepcopy(reminder_rows[rid])})
        frozen = {'candidate_old_lists': 18, 'candidate_list_ids': candidate,
            'protected_project_list_count': 76, 'protected_project_lists': protected_scope,
            'preserve_current_content_system_list_id': protected[0],
            'survivor_records': [reminder_rows[rid] for rid in working],
            'retired_parent_records': parent_records,
            'retired_parent_wrappers': 74, 'candidates': scope_candidates}
        scope = {'kind': 'old_list_removal_readonly_preview', 'version': 1, 'cleanup_scope': frozen}
        config = {'projects': {row['project_id']: {'retired_parent': {
                    'id': row['reminder_id'], 'list_id': reminder_rows[row['reminder_id']]['list_id'],
                    'snapshot': copy.deepcopy(reminder_rows[row['reminder_id']])}}
                    for row in parent_records},
            'structure': {'subgroups': {}, 'group_default_lists': {}, 'list_roles': {
            **{lid: {'kind': 'direct'} for lid in candidate},
            **{lid: {'kind': 'project', 'project_id': f'p{i}'} for i, lid in enumerate(protected)}}}}
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            hub = Path(tmp).resolve(); (hub / 'ai').mkdir()
            config_raw = b'{}'; (hub / 'ai/reminders-sync.json').write_bytes(config_raw)
            scope['config_sha256'] = hashlib.sha256(config_raw).hexdigest()
            metadata = {'lists': copy.deepcopy(list(candidate_lists.values()) + list(protected_list_rows.values())), 'groups': []}
            inventory = {'lists': copy.deepcopy({**candidate_lists, **protected_list_rows}),
                         'reminders': copy.deepcopy(reminder_rows)}
            yield hub, scope, config, metadata, inventory

    def check(self, mutation=None):
        for hub, scope, config, metadata, inventory in self.context():
            if mutation: mutation(scope, config, metadata, inventory)
            return cleanup._check_initial(scope, config, metadata, inventory, Helper, hub)

    def test_check_initial_accepts_exact_frozen_preview(self):
        checked = self.check()
        self.assertEqual((len(checked['candidate_list_ids']), len(checked['retired_parent_ids']),
                          len(checked['protected_list_ids']), len(checked['survivor_ids'])), (18, 74, 76, 626))

    def test_validate_scope_accepts_real_subgroup_role_mapping(self):
        for _hub, scope, _config, _metadata, _inventory in self.context():
            candidate = scope['cleanup_scope']['candidates'][0]
            candidate['role'] = {'kind': 'subgroup', 'archiproject_id': 'sample-subgroup'}
            candidate['subgroup_ids'] = ['sample-subgroup']
            self.assertEqual(cleanup.validate_scope(scope)['candidate_list_ids'],
                             {row['list']['id'] for row in scope['cleanup_scope']['candidates']})
            return

    def test_check_initial_accepts_sealed_summary_scope_and_subgroup_bindings(self):
        for hub, scope, config, metadata, inventory in self.context():
            candidates = scope['cleanup_scope']['candidates']
            for index, candidate in enumerate(candidates[:3]):
                sid = ['sample-seo', 'sample-promo', 'sample-businka'][index]
                candidate['role'] = {'kind': 'subgroup', 'archiproject_id': sid}
                candidate['subgroup_ids'] = [sid]
                config['structure']['list_roles'][candidate['list']['id']] = candidate['role']
                config['structure']['subgroups'][sid] = {'list_id': candidate['list']['id'], 'parent': 'sample'}
            for candidate in candidates:
                for row in candidate['full_snapshot']:
                    row.pop('list_id', None)
            for parent in scope['cleanup_scope']['retired_parent_records']:
                parent['snapshot'].pop('list_id', None)
            for row in scope['cleanup_scope']['survivor_records']:
                row.pop('list_id', None)
            for protected in scope['cleanup_scope']['protected_project_lists']:
                for row in protected['snapshot']:
                    row.pop('list_id', None)
            checked = cleanup._check_initial(scope, config, metadata, inventory, Helper, hub)
            self.assertEqual(len(checked['retired_parent_ids']), 74)
            return

    def test_check_initial_rejects_parent_config_snapshot_change(self):
        def change(_scope, config, _metadata, _inventory):
            binding = next(iter(config['projects'].values()))
            binding['retired_parent']['snapshot']['version'] = 'changed-version'
        with self.assertRaisesRegex(ValueError, 'cleanup_retired_parent_config_snapshot_changed'):
            self.check(change)

    def test_check_initial_rejects_ambiguous_protected_list_owner(self):
        def change(_scope, _config, metadata, _inventory):
            metadata['lists'][-1]['name'] = metadata['lists'][-2]['name']
        with self.assertRaisesRegex(ValueError, 'cleanup_list_name_ownership_ambiguous'):
            self.check(change)

    def test_check_initial_rejects_foreign_account_candidate(self):
        def change(_s, _c, meta, _i): meta['lists'][0]['account_id'] = '70000000-0000-4000-8000-000000000001'
        with self.assertRaisesRegex(ValueError, 'cleanup_candidate_metadata_changed'): self.check(change)

    def test_check_initial_rejects_shared_candidate(self):
        def change(_s, _c, meta, _i): meta['lists'][0]['shared'] = True
        with self.assertRaisesRegex(ValueError, 'cleanup_shared_list'): self.check(change)

    def test_check_initial_rejects_children_in_candidate(self):
        def change(scope, _c, _m, inventory):
            lid = scope['cleanup_scope']['candidate_list_ids'][0]
            rid = next(rid for rid, row in inventory['reminders'].items() if row['list_id'] == lid)
            inventory['reminders'][rid]['parent_id'] = '30000000-0000-4000-8000-000000000074'
            candidate = next(row for row in scope['cleanup_scope']['candidates'] if row['list']['id'] == lid)
            candidate['full_snapshot'] = [inventory['reminders'][rid] if row['id'] == rid else row
                                          for row in candidate['full_snapshot']]
            parent = next(row for row in scope['cleanup_scope']['retired_parent_records'] if row['reminder_id'] == rid)
            parent['snapshot'] = inventory['reminders'][rid]
        with self.assertRaisesRegex(ValueError, 'cleanup_candidate_has_children'): self.check(change)

    def test_check_initial_rejects_version_change(self):
        def change(scope, _c, _m, inventory):
            rid = scope['cleanup_scope']['retired_parent_records'][0]['reminder_id']
            inventory['reminders'][rid]['version'] = 'foreign-version'
        with self.assertRaisesRegex(ValueError, 'cleanup_candidate_snapshot_changed'): self.check(change)

    def test_check_initial_rejects_current_project_list_in_deletion_roles(self):
        def change(scope, config, _m, _i):
            lid = scope['cleanup_scope']['candidate_list_ids'][0]
            config['structure']['list_roles'][lid] = {'kind': 'project', 'project_id': 'current-pilot'}
        with self.assertRaisesRegex(ValueError, 'cleanup_project_role_protected'): self.check(change)

    def test_cleanup_plan_captures_five_distinct_verified_sdk_statuses(self):
        refusal_ids = [f'50000000-0000-4000-8000-{i:012X}' for i in range(1, 6)]
        rows = {}
        config = {'projects': {}}
        for i, rid in enumerate(refusal_ids):
            pid=f'project-{i}'; tid=f'TASK-{pid}-20261028-001'
            link={'reminder_id':rid,'cancellation':{'operation_id':f'40000000-0000-4000-8000-{i+1:012X}',
                                                     'plan_sha256':f'{i+1:064x}'}}
            config['projects'][pid]={'historical_binding_migration':{'state':'verified'},'tasks':{tid:link}}
            rows[(pid,tid)]={'project_id':pid,'task_id':tid,'status':'dropped'}
        statuses={rid:{'state':'deleted','version':f'v{i}',
                       'snapshot':{'id':rid,'version':f'v{i}','list_id':'60000000-0000-4000-8000-000000000001',
                                   'list':'retired'}} for i,rid in enumerate(refusal_ids)}
        class Native:
            def __init__(self): self.calls=[]
            def cancellation_status(self,args):
                self.calls.append(('cancellation_status', args['id']))
                return statuses[args['id']]
            def call(self,tool,args):
                self.calls.append(('call', tool))
                return {'reminders': [], 'count': 0}
        class Cancellation:
            def verify_cancelled_link(self,hub,row,link,binding,reader,return_status=False):
                if return_status is not True: raise AssertionError('pre-cleanup proof must include SDK status')
                reader.call('find_reminders', {'list':'60000000-0000-4000-8000-000000000001'})
                return reader.call('hub_cancel_status',{'id':link['reminder_id']})
        class Sync:
            @staticmethod
            def cancellation_module(): return Cancellation()
            @staticmethod
            def HubProject(hub,pid):
                class Project:
                    def rows(self): return {tid:row for (project,tid),row in rows.items() if project==pid}
                return Project()
        class Helper:
            @staticmethod
            def load_sync(): return Sync
        native=Native()
        proofs=cleanup._historical_refusal_proofs(Path('/private/tmp'),config,native,Helper)
        self.assertEqual(set(proofs),set(refusal_ids))
        self.assertEqual({rid:proof['native_status'] for rid,proof in proofs.items()},statuses)
        self.assertEqual(sum(call[0] == 'cancellation_status' for call in native.calls), 5)
        self.assertEqual(sum(call == ('call', 'find_reminders') for call in native.calls), 5)


if __name__ == '__main__': unittest.main()
