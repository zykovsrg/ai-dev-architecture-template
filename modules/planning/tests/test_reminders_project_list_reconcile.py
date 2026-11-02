"""Трёхсторонняя сверка отдельных списков на временном Хабе, без приложения."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(os.environ.get('PROJECT_LIST_RECONCILE_SCRIPTS', Path(__file__).resolve().parents[1] / 'scripts'))
spec = importlib.util.spec_from_file_location('project_list_reconcile_structure', SCRIPTS / 'reminders_structure.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Native:
    def __init__(self):
        self.lists = [dict(id=lid, name=name, group_id='n1', account_id='account')
                      for lid, name in [('lp', 'Проект'), ('sibling', 'Соседний проект')]]
        self.groups = [dict(id=nid, name=name, account_id='account') for nid, name in [('n1', 'Работа'), ('n2', 'Личное')]]
        self.rows = {lid: [dict(id=rid, title=rid, version='1', list_id=lid, parent_id=parent, notes='Личная заметка', completed=False)
                          for rid, parent in entries] for lid, entries in [('lp', [('task', None), ('nested', 'task')]), ('sibling', [('other-task', None)])]}
        self.calls = []
        self.ignore_move = False
    def call(self, tool, args):
        self.calls.append((tool, copy.deepcopy(args)))
        if tool == 'list_lists': return dict(lists=copy.deepcopy(self.lists), groups=copy.deepcopy(self.groups))
        if tool == 'find_reminders': return dict(reminders=copy.deepcopy(self.rows[args['list']]), count=len(self.rows[args['list']]))
        if tool == 'get_reminder': return copy.deepcopy(next(row for rows in self.rows.values() for row in rows if row['id'] == args['id']))
        if tool == 'manage_list':
            row = next(row for row in self.lists if row['id'] == args['list'])
            if args['expected_group_id'] != row['group_id']: raise ValueError('stale_group')
            if not self.ignore_move: row['group_id'] = args['group']
            return copy.deepcopy(row)
        raise AssertionError('unexpected write: ' + tool)


class ProjectListReconcileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='project-list-reconcile-')
        self.addCleanup(self.temp.cleanup)
        self.hub = Path(self.temp.name).resolve()
        (self.hub / 'ai/project-cards').mkdir(parents=True)
        registry = ''
        for pid, group in [('demo', 'a'), ('sibling', 'a')]:
            (self.hub / 'projects' / pid).mkdir(parents=True)
            (self.hub / 'ai/project-cards' / (pid + '.md')).write_text(f'Project ID: {pid}\nStatus: active\nprimary_archiproject: {group}\n')
            registry += f'## {pid}\nStatus: active\nPath: {self.hub}/projects/{pid}\nCard: ai/project-cards/{pid}.md\n'
        (self.hub / 'ai/project-registry.md').write_text(registry)
        groups = [('a', None), ('b', None), ('sub', 'a'), ('sub-two', 'a'), ('sub-b', 'b')]
        (self.hub / 'ai/archiprojects.md').write_text(''.join(f'## {gid}\n```yaml\nid: {gid}\nname: {gid}\nstatus: active\nkind: group\n' + (f'parent: {parent}\n' if parent else '') + '```\n' for gid, parent in groups))
        self.config = dict(version=1, binary='/private/tmp/never-run', allowlist_file=str(self.hub / 'ai/lists.json'),
                           projects={pid:dict(layout='project_list', list_id=lid, list_name=name, native_group_id='n1', tasks={'t':dict(reminder_id=rid)}, history={})
                                     for pid, lid, name, rid in [('demo', 'lp', 'Проект', 'task'), ('sibling', 'sibling', 'Соседний проект', 'other-task')]},
                           structure=dict(enabled=True, bidirectional=True, groups_allowlist_file=str(self.hub / 'ai/groups.json'), group_ids_allowlist_file=str(self.hub / 'ai/group-ids.json'),
                                          native_groups={'n1':'a', 'n2':'b'}, list_roles={lid:dict(kind='project', project_id=pid) for pid, lid in [('demo', 'lp'), ('sibling', 'sibling')]},
                                          projects={pid:dict(group='a', list_id=lid) for pid, lid in [('demo', 'lp'), ('sibling', 'sibling')]}, subgroups={}, journal_file='ai/structure-journal.json'))
        for name, value in [('lists', ['lp', 'sibling']), ('groups', ['Работа', 'Личное']), ('group-ids', ['n1', 'n2'])]:
            (self.hub / 'ai' / (name + '.json')).write_text(json.dumps(value))
        self.native = Native()
        self.save()
    def save(self): (self.hub / 'ai/reminders-sync.json').write_text(m.encoded(self.config))
    def card(self, group): (self.hub / 'ai/project-cards/demo.md').write_text(f'Project ID: demo\nStatus: active\nprimary_archiproject: {group}\n')
    def run_reconcile(self, apply=True):
        result = m.reconcile_structure(self.hub, self.config, apply=apply, native=self.native)
        if apply and result['ok']: self.config = result['config']
        return result
    def writes(self): return [(tool, args) for tool, args in self.native.calls if tool in {'manage_list', 'update_reminder', 'create_reminder'}]
    def assert_success(self, result, group, native):
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['config']['structure']['projects']['demo']['group'], group)
        self.assertEqual(result['config']['projects']['demo']['native_group_id'], native)
        self.assertEqual(self.native.lists[0]['group_id'], native)
        self.assertEqual(result['config']['projects']['sibling'], self.config['projects']['sibling'])
        self.assertEqual(self.native.lists[1]['group_id'], 'n1')

    def test_virtual_subgroups_keep_logical_placement_without_native_writes(self):
        for baseline, current in [('a', 'sub'), ('sub', 'sub-two')]:
            with self.subTest(baseline=baseline, current=current):
                self.config['structure']['projects']['demo']['group'] = baseline
                self.card(current); self.save()
                rows = copy.deepcopy(self.native.rows)
                result = self.run_reconcile()
                self.assert_success(result, current, 'n1')
                self.assertEqual(self.writes(), [])
                self.assertEqual(self.native.rows, rows)
                repeated = self.run_reconcile()
                self.assertTrue(repeated['ok'], repeated)
                self.assertEqual(repeated['items'], [])
                self.assertEqual(self.writes(), [])

    def test_outgoing_ancestor_group_moves_only_owned_list_with_compare_and_readback(self):
        self.card('sub-b')
        rows = copy.deepcopy(self.native.rows)
        result = self.run_reconcile()
        self.assert_success(result, 'sub-b', 'n2')
        self.assertEqual(self.native.rows, rows)
        self.assertEqual(self.writes(), [('manage_list', dict(action='update', list='lp', group='n2', expected_group_id='n1'))])
        journal = json.loads((self.hub / 'ai/structure-journal.json').read_text())
        self.assertEqual(journal['status'], 'complete')
        self.assertEqual(journal['steps'], [dict(kind='list', id='lp', group='n2', projects=['demo'])])
        self.assertEqual(self.run_reconcile()['items'], [])
        self.assertEqual(len(self.writes()), 1)

    def test_outgoing_none_moves_whole_list(self):
        self.card('none')
        result = self.run_reconcile()
        self.assert_success(result, 'none', None)
        self.assertEqual(self.writes(), [('manage_list', dict(action='update', list='lp', group=None, expected_group_id='n1'))])

    def test_outgoing_from_none_uses_known_current_account(self):
        self.config['projects']['demo']['native_group_id'] = None
        self.config['structure']['projects']['demo']['group'] = 'none'
        self.native.lists[0]['group_id'] = None
        self.card('sub-b'); self.save()
        result = self.run_reconcile()
        self.assert_success(result, 'sub-b', 'n2')
        self.assertEqual(self.writes(), [('manage_list', dict(action='update', list='lp', group='n2', expected_group_id=None))])

    def test_incoming_native_group_updates_card_and_both_baselines(self):
        self.native.lists[0]['group_id'] = 'n2'
        result = self.run_reconcile()
        self.assert_success(result, 'b', 'n2')
        self.assertIn('primary_archiproject: b', (self.hub / 'ai/project-cards/demo.md').read_text())
        self.assertEqual(self.writes(), [])
        self.assertEqual(self.run_reconcile()['items'], [])

    def test_two_sided_conflict_requires_existing_scoped_resolution(self):
        self.card('sub'); self.native.lists[0]['group_id'] = 'n2'
        result = self.run_reconcile(False)
        self.assertFalse(result['ok'], result)
        issue = next(item for item in result['items'] if item.get('project') == 'demo')
        self.assertEqual(issue['error'], 'structure_two_sided_conflict')
        self.assertEqual({key:issue['resolution'][key] for key in ('base', 'hub', 'remote', 'list_id')}, dict(base='a', hub='sub', remote='b', list_id='lp'))
        self.assertEqual(self.writes(), [])
        self.config['structure']['resolutions'] = {'project:demo':dict(issue['resolution'], choice='hub')}
        self.save()
        self.assert_success(self.run_reconcile(), 'sub', 'n1')
        self.assertEqual(self.config['structure']['resolutions'], {})

    def test_resolution_is_stale_when_project_list_native_pin_changes(self):
        self.card('sub'); self.native.lists[0]['group_id'] = 'n2'
        preview = self.run_reconcile(False)
        issue = next(item for item in preview['items'] if item.get('project') == 'demo')
        self.assertIn('resolution', issue)
        self.config['structure']['resolutions'] = {'project:demo':dict(issue['resolution'], choice='hub')}
        self.config['projects']['demo']['native_group_id'] = None
        self.save()
        result = self.run_reconcile()
        self.assertFalse(result['ok'], result)
        self.assertIn('structure_resolution_stale', str(result))
        self.assertEqual(self.writes(), [])

    def test_pinned_project_account_blocks_consistent_foreign_snapshot(self):
        self.config['projects']['demo']['account_id'] = 'expected-account'
        self.native.lists[0]['account_id'] = 'foreign-account'
        for group in self.native.groups: group['account_id'] = 'foreign-account'
        self.card('b'); self.save()
        before = {p:p.read_bytes() for p in self.hub.rglob('*') if p.is_file()}
        result = self.run_reconcile()
        self.assertFalse(result['ok'], result)
        self.assertIn('structure_account_unproven', str(result))
        self.assertEqual(result['blocked_projects'], ['demo'])
        self.assertEqual(self.writes(), [])
        self.assertEqual(self.native.lists[0]['group_id'], 'n1')
        self.assertEqual(before, {p:p.read_bytes() for p in self.hub.rglob('*') if p.is_file()})
        # The same accepted account pin must permit a real move.
        self.native.lists[0]['account_id'] = 'expected-account'
        for group in self.native.groups: group['account_id'] = 'expected-account'
        self.assert_success(self.run_reconcile(), 'b', 'n2')

    def test_account_proof_blocks_foreign_or_unknown_source_and_destination(self):
        for fault in ('destination', 'source', 'list', 'incoming'):
            with self.subTest(fault=fault):
                original = copy.deepcopy((self.native.lists, self.native.groups))
                self.card('b' if fault != 'incoming' else 'a')
                if fault == 'destination': self.native.groups[1]['account_id'] = 'foreign'
                if fault == 'source': self.native.groups[0]['account_id'] = 'foreign'
                if fault == 'list': self.native.lists[0].pop('account_id')
                if fault == 'incoming':
                    self.native.lists[0]['group_id'] = 'n2'; self.native.groups[1]['account_id'] = 'foreign'
                result = self.run_reconcile()
                self.assertFalse(result['ok'], result)
                self.assertIn('structure_account_unproven', str(result))
                self.assertEqual(self.writes(), [])
                self.native.lists, self.native.groups = original

    def test_identity_role_and_full_tree_guards_precede_relocation(self):
        self.card('b')
        for fault, error in [('role', 'project_list_structure_conflict'), ('identity', 'foreign_identity'), ('missing', 'missing_bound_child'), ('incomplete', 'incomplete_project_tree')]:
            with self.subTest(fault=fault):
                state = copy.deepcopy((self.config, self.native.rows))
                if fault == 'role': self.config['structure']['list_roles']['lp']['project_id'] = 'sibling'
                if fault == 'identity': self.native.rows['lp'][0]['notes'] = 'Hub project: sibling'
                if fault == 'missing': self.native.rows['lp'] = []
                if fault == 'incomplete': self.native.rows['sibling'].append(dict(id='copy', title='Копия', version='1', list_id='sibling', notes='Hub project: demo'))
                self.save()
                result = self.run_reconcile()
                self.assertFalse(result['ok'], result)
                self.assertIn(error, str(result))
                self.assertIn('demo', result['blocked_projects'])
                self.assertEqual(self.writes(), [])
                self.config, self.native.rows = state

    def add_incoming_subgroup_parent(self):
        self.card('sub'); self.config['structure']['projects']['demo']['group'] = 'sub'
        self.config['structure']['list_roles']['container'] = dict(kind='subgroup', archiproject_id='sub')
        self.config['structure']['subgroups']['sub'] = dict(parent='a', list_id='container')
        self.native.lists.append(dict(id='container', name='Подгруппа', group_id='n2', account_id='account'))
        self.native.rows['container'] = []
        (self.hub / 'ai/lists.json').write_text(json.dumps(['lp', 'sibling', 'container']))
        self.save()

    def test_project_list_follows_accepted_subgroup_parent_without_flattening(self):
        self.add_incoming_subgroup_parent()
        result = self.run_reconcile()
        self.assert_success(result, 'sub', 'n2')
        self.assertEqual(m.load_groups((self.hub / 'ai/archiprojects.md').read_text())['sub']['parent'], 'b')
        self.assertIn('primary_archiproject: sub', (self.hub / 'ai/project-cards/demo.md').read_text())
        self.assertEqual(self.writes(), [('manage_list', dict(action='update', list='lp', group='n2', expected_group_id='n1'))])
        self.assertEqual(self.run_reconcile()['items'], [])

    def test_subgroup_parent_acceptance_rolls_back_if_descendant_account_unproven(self):
        self.add_incoming_subgroup_parent()
        self.native.groups[1]['account_id'] = 'foreign'
        before = {p:p.read_bytes() for p in self.hub.rglob('*') if p.is_file()}
        result = self.run_reconcile()
        self.assertFalse(result['ok'], result)
        self.assertIn('structure_account_unproven', str(result))
        self.assertEqual(result['blocked_projects'], ['demo'])
        self.assertEqual(result['config']['structure']['subgroups']['sub']['parent'], 'a')
        self.assertEqual(self.writes(), [])
        self.assertEqual(before, {p:p.read_bytes() for p in self.hub.rglob('*') if p.is_file()})

    def test_projected_graph_rejection_prevents_native_and_local_commit(self):
        self.card('b')
        before = {p:p.read_bytes() for p in self.hub.rglob('*') if p.is_file()}
        validate = m.validate_project_list
        def final_reject(pid, binding, snap, config, *args, **kwargs):
            result = validate(pid, binding, snap, config, *args, **kwargs)
            if pid == 'demo' and not kwargs.get('reconcile_location'):
                raise ValueError('projected_graph_rejected')
            return result
        with patch.object(m, 'validate_project_list', final_reject):
            result = self.run_reconcile()
        self.assertFalse(result['ok'], result)
        self.assertEqual(result['blocked_projects'], ['demo'])
        self.assertEqual(result['config']['projects']['demo'], self.config['projects']['demo'])
        self.assertEqual(result['config']['structure']['projects']['demo']['group'], 'a')
        self.assertEqual(self.writes(), [])
        self.assertEqual(before, {p:p.read_bytes() for p in self.hub.rglob('*') if p.is_file()})

    def test_native_readback_failure_keeps_pending_journal_and_local_baseline(self):
        self.card('b'); self.native.ignore_move = True
        result = self.run_reconcile()
        self.assertFalse(result['ok'], result)
        self.assertIn('structure_readback_failed', str(result))
        pending = json.loads((self.hub / 'ai/structure-journal.json').read_text())
        self.assertEqual(pending['status'], 'pending')
        self.assertEqual(json.loads((self.hub / 'ai/reminders-sync.json').read_text())['structure']['projects']['demo']['group'], 'a')
        self.native.ignore_move = False
        self.config = json.loads((self.hub / 'ai/reminders-sync.json').read_text())
        self.assert_success(self.run_reconcile(), 'b', 'n2')


if __name__ == '__main__': unittest.main()
