"""Проверки структуры на временном Хабе, без рабочего хранилища."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[3] / 'modules/planning/scripts/reminders_structure.py'
m = None
SYNC_SOURCE_OVERRIDE = None
if SOURCE.exists():
    spec = importlib.util.spec_from_file_location('structure_subject', SOURCE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)


class Native:
    def __init__(self):
        self.lists = [{'id': 'l1', 'name': 'Первый', 'group_id': 'n1'}, {'id': 'l2', 'name': 'Второй', 'group_id': 'n2'}]
        self.rows = {'l1': [], 'l2': [dict(id='parent', title='Проект', version=1, list_id='l2'), dict(id='task', title='Дело', version=1, list_id='l2', parent_id='parent')]}
        self.calls = []
        self.hook = None
    def call(self, tool, args):
        self.calls.append((tool, args))
        if self.hook:
            self.hook(tool, args)
        if tool == 'list_lists':
            return {'lists': copy.deepcopy(self.lists)}
        if tool == 'find_reminders':
            return {'reminders': copy.deepcopy(self.rows[args['list']])}
        raise AssertionError('write tool: ' + tool)


class StructureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='structure-')
        self.addCleanup(self.temp.cleanup)
        self.hub = Path(self.temp.name).resolve()
        (self.hub / 'ai/project-cards').mkdir(parents=True)
        (self.hub / 'projects/demo').mkdir(parents=True)
        self.card = self.hub / 'ai/project-cards/demo.md'
        self.card.write_text('Project ID: demo\nStatus: active\nprimary_archiproject: a\n')
        (self.hub / 'ai/project-registry.md').write_text(f'## demo\nStatus: active\nPath: {self.hub}/projects/demo\nCard: ai/project-cards/demo.md\n')
        self.arch = self.hub / 'ai/archiprojects.md'
        self.arch.write_text(''.join('## '+g+'\n```yaml\nid: '+g+'\nname: '+g+'\nstatus: active\nkind: group\n```\n' for g in ('a', 'b', 'sub')))
        self.config = dict(version=1, binary='/tmp/fake', allowlist_file=str(self.hub/'ai/lists.json'), projects={'demo': dict(parent_id='parent', list_id='l1', list_name='Первый', tasks={'t': {'reminder_id': 'task'}})}, structure=dict(enabled=True, groups_allowlist_file=str(self.hub/'ai/groups.json'), native_groups={'n1':'a', 'n2':'b'}, list_roles={'l1':{'kind':'direct'},'l2':{'kind':'direct'}}, projects={'demo':{'group':'a','list_id':'l1'}}, subgroups={}, journal_file='ai/structure-journal.json'))
        (self.hub/'ai/lists.json').write_text(json.dumps(['l1','l2']))
        (self.hub/'ai/groups.json').write_text(json.dumps(['n1','n2']))
        self.config_path = self.hub/'ai/reminders-sync.json'
        self.save_config()
        self.native = Native()
    def save_config(self):
        self.config_path.write_text(json.dumps(self.config))
    def run_reconcile(self, apply=False):
        self.assertIsNotNone(m, 'structure implementation missing')
        return m.reconcile_structure(self.hub, self.config, apply=apply, native=self.native)
    def assert_blocked(self, error):
        before = self.card.read_text()
        result = self.run_reconcile(True)
        self.assertFalse(result['ok'])
        self.assertIn(error, str(result['items']))
        self.assertIn('demo', result['blocked_projects'])
        self.assertEqual(before, self.card.read_text())
        return result
    def test_move_dry_run_and_apply(self):
        before = {p: p.read_bytes() for p in self.hub.rglob('*') if p.is_file()}
        result = self.run_reconcile()
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['config']['projects']['demo']['list_id'], 'l2')
        self.assertEqual(result['config']['structure']['projects']['demo']['group'], 'b')
        self.assertEqual(before, {p:p.read_bytes() for p in self.hub.rglob('*') if p.is_file()})
        result = self.run_reconcile(True)
        self.assertTrue(result['ok'], result)
        self.assertIn('primary_archiproject: b', self.card.read_text())
        self.assertEqual(json.loads(self.config_path.read_text())['projects']['demo']['list_id'],'l2')
        self.assertTrue((self.hub/'ai/structure-journal.json').exists())
    def test_missing_child_or_history_blocks(self):
        self.native.rows['l2'].pop()
        self.assert_blocked('missing_bound_child')
        self.native.rows['l2'].append(dict(id='task',title='Дело',version=1,list_id='l2',parent_id='parent'))
        self.config['projects']['demo']['history'] = {'old':{'task_id':'t','project_id':'demo','original_id':'task'}}
        self.save_config()
        self.assert_blocked('missing_bound_child')
    def test_unknown_group_and_absent_group_metadata(self):
        self.native.lists[1]['group_id']='unknown'
        self.assert_blocked('unknown_native_group')
        self.native.lists[1].pop('group_id')
        self.assert_blocked('missing_group_metadata')
    def test_duplicate_or_nested_parent_blocks(self):
        self.native.rows['l1'].append(dict(self.native.rows['l2'][0],list_id='l1'))
        self.assert_blocked('duplicate_reminder')
        self.native.rows['l1']=[]
        self.native.rows['l2'][0]['parent_id']='other'
        self.assert_blocked('parent_is_subtask')
    def test_three_way_conflict_and_convergence(self):
        self.card.write_text(self.card.read_text().replace('primary_archiproject: a','primary_archiproject: none'))
        self.assert_blocked('structure_two_sided_conflict')
        self.card.write_text(self.card.read_text().replace('primary_archiproject: none','primary_archiproject: b'))
        self.assertTrue(self.run_reconcile(True)['ok'])
    def test_null_group_maps_to_none(self):
        self.native.lists[1]['group_id']=None
        self.assertTrue(self.run_reconcile(True)['ok'])
        self.assertIn('primary_archiproject: none',self.card.read_text())
    def test_subgroup_moves_parent_preserves_primary(self):
        self.config['structure']['list_roles']['l2']={'kind':'subgroup','archiproject_id':'sub'}
        self.config['structure']['subgroups']={'sub':{'parent':'a','list_id':'l2'}}
        self.card.write_text(self.card.read_text().replace('primary_archiproject: a','primary_archiproject: sub'))
        self.config['structure']['projects']['demo']['group']='sub'
        self.arch.write_text(self.arch.read_text().replace('id: sub\n','id: sub\nparent: a\n'))
        self.save_config()
        result=self.run_reconcile(True)
        self.assertTrue(result['ok'],result)
        self.assertIn('primary_archiproject: sub',self.card.read_text())
        self.assertIn('parent: b',self.arch.read_text())
        canonical_path=Path(__file__).resolve().parents[5]/'scripts/archiprojects.py'
        spec=importlib.util.spec_from_file_location('canonical_arch_parser',canonical_path)
        canonical=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(canonical)
        self.assertEqual(canonical.parse_groups(self.arch)['sub']['parent'],'b')
        self.config=json.loads(self.config_path.read_text())
        self.native.lists[1]['group_id']=None
        result=self.run_reconcile(True)
        self.assertTrue(result['ok'],result)
        self.assertIsNone(canonical.parse_groups(self.arch)['sub']['parent'])
    def test_foreign_identity_and_bound_child_blocks(self):
        self.native.rows['l2'][1]['notes']='--- Hub metadata ---\nHub Task ID: t\nHub project: other\n--- /Hub metadata ---'
        self.assert_blocked('foreign_identity')
    def test_stale_snapshot_prevents_writes(self):
        count=0
        def hook(tool,args):
            nonlocal count
            if tool=='list_lists':
                count+=1
                if count==2:self.native.rows['l2'][1]['version']=2
        self.native.hook=hook
        self.assert_blocked('structure_snapshot_changed')
    def test_config_card_registry_cas_and_symlink(self):
        def hook(tool,args):
            if len(self.native.calls)==4:self.card.write_text(self.card.read_text()+'User edit\n')
        self.native.hook=hook
        result=self.run_reconcile(True)
        self.assertFalse(result['ok'])
        self.assertIn('structure_file_changed',str(result))
        self.assertIn('primary_archiproject: a',self.card.read_text())
        self.native.hook=None
        self.card.rename(self.card.with_suffix('.target'))
        self.card.symlink_to(self.card.with_suffix('.target'))
        self.assert_blocked('unsafe_path')
    def test_recovery_refuses_third_state_and_dry_run_no_write(self):
        original=m.atomic_write
        count=0
        def crash(path,data):
            nonlocal count
            count+=1
            if count==3:raise OSError('simulated crash')
            original(path,data)
        m.atomic_write=crash
        try:result=self.run_reconcile(True)
        finally:m.atomic_write=original
        self.assertFalse(result['ok'])
        journal=self.hub/'ai/structure-journal.json'
        self.assertTrue(journal.exists())
        before=journal.read_bytes()
        self.assertFalse(self.run_reconcile()['ok'])
        self.assertEqual(before,journal.read_bytes())
        self.card.write_text('third state')
        config_before=self.config_path.read_bytes()
        self.assertFalse(self.run_reconcile(True)['ok'])
        self.assertEqual('third state',self.card.read_text())
        self.assertEqual(config_before,self.config_path.read_bytes())
        self.assertEqual(json.loads(journal.read_text())['status'],'pending')
    def test_recovery_completes_every_interrupted_write(self):
        original=m.atomic_write
        for fail_at in range(1,5):
            with self.subTest(fail_at=fail_at):
                self.setUp()
                count=0
                def crash(path,data):
                    nonlocal count
                    count+=1
                    if count==fail_at:raise OSError('simulated crash')
                    original(path,data)
                m.atomic_write=crash
                try:self.run_reconcile(True)
                finally:m.atomic_write=original
                result=self.run_reconcile(True)
                self.assertTrue(result['ok'],result)
                self.assertIn('primary_archiproject: b',self.card.read_text())
                self.assertEqual(json.loads(self.config_path.read_text())['projects']['demo']['list_id'],'l2')
    def test_snapshot_incomplete_missing_list_or_bad_card(self):
        self.native.lists.pop()
        self.assert_blocked('missing_allowed_list')
        self.native.lists.append({'id':'l2','name':'Второй','group_id':'n2'})
        self.card.write_text(self.card.read_text()+'primary_archiproject: a\n')
        self.assert_blocked('invalid_project_card')
    def test_recurrence_copy_left_in_old_list_blocks(self):
        code=m.hashlib.sha256(b'demo\0t').hexdigest()[:12]
        self.native.rows['l1'].append(dict(id='copy',title='Копия',version=1,list_id='l1',parent_id='parent',completed=True,notes='Хаб: '+code))
        self.assert_blocked('incomplete_project_tree')
    def test_shared_list_moves_only_actual_projects(self):
        self.native.rows['l1']=self.native.rows['l2']
        self.native.rows['l2']=[]
        for row in self.native.rows['l1']:row['list_id']='l1'
        self.native.lists[0]['group_id']='n2'
        self.assertTrue(self.run_reconcile(True)['ok'])
        self.assertIn('primary_archiproject: b',self.card.read_text())
        self.assertEqual(json.loads(self.config_path.read_text())['projects']['demo']['list_id'],'l1')
    def test_config_change_before_commit_blocks(self):
        def hook(tool,args):
            if len(self.native.calls)==4:self.config_path.write_text(self.config_path.read_text()+' ')
        self.native.hook=hook
        self.assert_blocked('structure_file_changed')
    def test_pagination_blocks(self):
        call=self.native.call
        def incomplete(tool,args):
            value=call(tool,args)
            if tool=='find_reminders':value['more']=1
            return value
        self.native.call=incomplete
        self.assert_blocked('incomplete_reminder_snapshot')
    def test_subgroup_cycle_blocks(self):
        self.config['structure']['list_roles']['l2']={'kind':'subgroup','archiproject_id':'sub'}
        self.config['structure']['subgroups']={'sub':{'parent':None,'list_id':'l2'}}
        self.config['structure']['native_groups']['n2']='sub'
        self.save_config()
        self.assert_blocked('archiproject_cycle')
    def test_invalid_group_metadata_in_empty_list_blocks(self):
        self.native.lists[0].pop('group_id')
        self.assert_blocked('missing_group_metadata')
    def test_subgroup_reports_inactive_descendants(self):
        self.config['structure']['list_roles']['l2']={'kind':'subgroup','archiproject_id':'sub'}
        self.config['structure']['subgroups']={'sub':{'parent':None,'list_id':'l2'}}
        (self.hub/'projects/old').mkdir()
        (self.hub/'ai/project-registry.md').write_text((self.hub/'ai/project-registry.md').read_text()+f'## old\nStatus: archived\nPath: {self.hub}/projects/old\nCard: ai/project-cards/old.md\n')
        (self.hub/'ai/project-cards/old.md').write_text('Project ID: old\nStatus: archived\nprimary_archiproject: sub\n')
        self.save_config()
        result=self.run_reconcile()
        self.assertTrue(result['ok'],result)
        report=next(x for x in result['items'] if x.get('action')=='structure_subgroup_parent')
        self.assertIn('old',report['affected_projects'])
    def test_recovery_stale_native_snapshot_blocks(self):
        original=m.atomic_write
        count=0
        def crash(path,data):
            nonlocal count
            count+=1
            if count==3:raise OSError('simulated crash')
            original(path,data)
        m.atomic_write=crash
        try:self.run_reconcile(True)
        finally:m.atomic_write=original
        self.native.rows['l2'][1]['version']=2
        self.assertFalse(self.run_reconcile(True)['ok'])
    def test_recovery_revalidates_registry_before_writes(self):
        original=m.atomic_write
        count=0
        def crash(path,data):
            nonlocal count
            count+=1
            if count==2:raise OSError('simulated crash')
            original(path,data)
        m.atomic_write=crash
        try:self.run_reconcile(True)
        finally:m.atomic_write=original
        registry=self.hub/'ai/project-registry.md'
        registry.write_text(registry.read_text()+'# Параллельное изменение реестра\n')
        before=self.card.read_text()
        result=self.run_reconcile(True)
        self.assertFalse(result['ok'])
        self.assertEqual(self.card.read_text(),before)
        self.assertIn('structure_recovery_guard_changed',str(result))
    def test_project_scoped_pending_journal_guard(self):
        journal=self.hub/'ai/structure-journal.json'
        journal.write_text(json.dumps({'version':1,'status':'pending','files':[]}))
        self.assertEqual(m.pending_structure_projects(self.hub,self.config),['demo'])
    def sync_module(self):
        source=SOURCE.with_name('reminders_sync.py')
        spec=importlib.util.spec_from_file_location('integration_sync',source)
        sync=importlib.util.module_from_spec(spec)
        if SYNC_SOURCE_OVERRIDE is None:
            spec.loader.exec_module(sync)
        else:
            exec(compile(SYNC_SOURCE_OVERRIDE,str(source),'exec'),sync.__dict__)
        class Project:
            def __init__(*args):pass
            def rows(self):return {}
        sync.HubProject=Project
        return sync
    def test_integration_structure_precedes_tasks(self):
        sync=self.sync_module()
        self.config['projects']['demo']['tasks']={}
        self.native.rows['l2'].pop()
        self.save_config()
        class Tasks:
            def get(inner,rid,lid):
                self.assertEqual(lid,'l2')
                return dict(id=rid,list_id=lid,title='Проект',version=1)
            def children(inner,binding):return []
        result=sync.sync(self.hub,self.config,False,native=Tasks(),structure_native=self.native)
        self.assertTrue(result['ok'],result)
        self.assertEqual(result['items'][0]['action'],'structure_project')
    def test_integration_conflict_and_pending_guard_block_tasks(self):
        sync=self.sync_module()
        reached=[]
        class Tasks:
            def get(inner,*args):
                reached.append(args)
                raise AssertionError('blocked project reached tasks')
        self.native.lists[1]['group_id']='unknown'
        result=sync.sync(self.hub,self.config,False,native=Tasks(),structure_native=self.native)
        self.assertFalse(result['ok'])
        (self.hub/'ai/structure-journal.json').write_text(json.dumps({'version':1,'status':'pending','files':[]}))
        result=sync.sync(self.hub,self.config,False,project='demo',native=Tasks())
        self.assertFalse(result['ok'])
        self.assertIn('structure_recovery_required',str(result))
        self.assertEqual(reached,[])
    def test_subgroup_conflict_blocks_all_descendants_only(self):
        for pid,group in [('second','sub'),('independent','a')]:
            (self.hub/f'projects/{pid}').mkdir()
            registry=self.hub/'ai/project-registry.md'
            registry.write_text(registry.read_text()+f'## {pid}\nStatus: active\nPath: {self.hub}/projects/{pid}\nCard: ai/project-cards/{pid}.md\n')
            (self.hub/f'ai/project-cards/{pid}.md').write_text(f'Project ID: {pid}\nStatus: active\nprimary_archiproject: {group}\n')
            self.config['projects'][pid]=dict(parent_id=pid,list_id='l1',list_name='Первый',tasks={})
            self.config['structure']['projects'][pid]={'group':group,'list_id':'l1'}
            self.native.rows['l1'].append(dict(id=pid,list_id='l1',title=pid,version=1))
        self.config['structure']['list_roles']['l2']={'kind':'subgroup','archiproject_id':'sub'}
        self.config['structure']['subgroups']={'sub':{'parent':None,'list_id':'l2'}}
        self.card.write_text(self.card.read_text().replace('primary_archiproject: a','primary_archiproject: sub'))
        self.config['structure']['projects']['demo']['group']='sub'
        self.arch.write_text(self.arch.read_text().replace('id: sub\n','id: sub\nparent: a\n'))
        self.save_config()
        result=self.run_reconcile()
        self.assertEqual(result['blocked_projects'],['demo','second'])
        self.assertNotIn('independent',result['blocked_projects'])
    def test_actual_find_rows_need_no_list_id(self):
        for row in self.native.rows['l2']:
            row.pop('list_id')
            row['list']='Второй'
        self.assertTrue(self.run_reconcile()['ok'])
    def test_foreign_malformed_marker_does_not_block_independent_project(self):
        (self.hub/'projects/other').mkdir()
        registry=self.hub/'ai/project-registry.md'
        registry.write_text(registry.read_text()+f'## other\nStatus: active\nPath: {self.hub}/projects/other\nCard: ai/project-cards/other.md\n')
        (self.hub/'ai/project-cards/other.md').write_text('Project ID: other\nStatus: active\nprimary_archiproject: a\n')
        self.config['projects']['other']=dict(parent_id='other-root',list_id='l1',list_name='Первый',tasks={'u':{'reminder_id':'other-task'}})
        self.config['structure']['projects']['other']={'group':'a','list_id':'l1'}
        self.native.rows['l1']=[dict(id='other-root',title='Другой',version=1,list_id='l1'),dict(id='other-task',title='Дело',version=1,list_id='l1',parent_id='other-root')]
        self.native.rows['l2'][1]['notes']='Хаб: invalid'
        self.save_config()
        result=self.run_reconcile()
        self.assertEqual(result['blocked_projects'],['demo'])
    def test_unchanged_subgroup_needs_no_unrelated_inactive_card(self):
        self.config['structure']['list_roles']['l2']={'kind':'subgroup','archiproject_id':'sub'}
        self.config['structure']['subgroups']={'sub':{'parent':'b','list_id':'l2'}}
        self.arch.write_text(self.arch.read_text().replace('id: sub\n','id: sub\nparent: b\n'))
        registry=self.hub/'ai/project-registry.md'
        registry.write_text(registry.read_text()+f'## old\nStatus: archived\nPath: {self.hub}/projects/old\nCard: ai/project-cards/old.md\n')
        self.save_config()
        self.assertTrue(self.run_reconcile()['ok'])
    def test_legacy_project_marker_is_valid_only_for_bound_parent(self):
        self.native.rows['l2'][0]['notes']='Hub project: demo'
        self.assertTrue(self.run_reconcile()['ok'])
        self.native.rows['l2'][1]['notes']='Hub project: demo'
        self.assert_blocked('foreign_identity')
    def test_recovery_rejects_changed_runtime_before_native_read(self):
        original=m.atomic_write
        count=0
        def crash(path,data):
            nonlocal count
            count+=1
            if count==2:raise OSError('simulated crash')
            original(path,data)
        m.atomic_write=crash
        try:self.run_reconcile(True)
        finally:m.atomic_write=original
        journal=self.hub/'ai/structure-journal.json'
        value=json.loads(journal.read_text())
        value['config']['binary']='/tmp/unapproved'
        journal.write_text(json.dumps(value))
        calls=len(self.native.calls)
        result=self.run_reconcile(True)
        self.assertFalse(result['ok'])
        self.assertEqual(len(self.native.calls),calls)
        self.assertIn('structure_recovery_config_mismatch',str(result))
    def test_recovery_rejects_nonstructural_journal_payloads(self):
        original=m.atomic_write
        count=0
        def crash(path,data):
            nonlocal count
            count+=1
            if count==2:raise OSError('simulated crash')
            original(path,data)
        m.atomic_write=crash
        try:self.run_reconcile(True)
        finally:m.atomic_write=original
        journal=self.hub/'ai/structure-journal.json'
        saved=json.loads(journal.read_text())
        for variant in ('card','config','guard'):
            with self.subTest(variant=variant):
                value=copy.deepcopy(saved)
                if variant=='card':value['files'][0]['after']+='Injected content\n'
                if variant=='config':
                    row=next(x for x in value['files'] if x['path']=='ai/reminders-sync.json')
                    after=json.loads(row['after'])
                    after['binary']='/tmp/unapproved'
                    row['after']=json.dumps(after)
                if variant=='guard':value['guards'][0]['path']='/tmp/unapproved-read'
                journal.write_text(json.dumps(value))
                calls=len(self.native.calls)
                before=self.card.read_text()
                result=self.run_reconcile(True)
                self.assertFalse(result['ok'])
                self.assertEqual(before,self.card.read_text())
                self.assertEqual(calls,len(self.native.calls))
                self.assertIn('unsafe_structure_journal',str(result))
    def test_recovery_without_config_entry_requires_exact_current_config(self):
        original=m.atomic_write
        count=0
        def crash(path,data):
            nonlocal count
            count+=1
            if count==2:raise OSError('simulated crash')
            original(path,data)
        m.atomic_write=crash
        try:self.run_reconcile(True)
        finally:m.atomic_write=original
        journal=self.hub/'ai/structure-journal.json'
        value=json.loads(journal.read_text())
        value['files']=[row for row in value['files'] if row['path']!='ai/reminders-sync.json']
        value['config']['structure']['projects']['demo']['group']='none'
        value['files'][0]['after']=value['files'][0]['after'].replace('primary_archiproject: b','primary_archiproject: none')
        journal.write_text(json.dumps(value))
        before=self.card.read_text()
        result=self.run_reconcile(True)
        self.assertFalse(result['ok'])
        self.assertEqual(before,self.card.read_text())
        self.assertIn('unsafe_structure_journal',str(result))
    def missing_primary_fixture(self):
        text=Path(__file__).with_name('structure-card-missing-primary.fixture.md').read_text()
        pid='idei-proektov'
        (self.hub/'projects'/pid).mkdir()
        self.card=self.hub/f'ai/project-cards/{pid}.md'
        self.card.write_text(text)
        (self.hub/'ai/project-cards/demo.md').unlink()
        (self.hub/'ai/project-registry.md').write_text(f'## {pid}\nStatus: active\nPath: {self.hub}/projects/{pid}\nCard: ai/project-cards/{pid}.md\n')
        self.config['projects'][pid]=self.config['projects'].pop('demo')
        self.config['structure']['projects'][pid]=self.config['structure']['projects'].pop('demo')
        self.config['structure']['projects'][pid]['group']='none'
        self.save_config()
        return text,pid
    def test_exact_existing_card_missing_primary_is_none_without_writes(self):
        text,pid=self.missing_primary_fixture()
        binding=self.config['projects'][pid]
        binding.update(list_id='l2',list_name='Второй')
        self.config['structure']['projects'][pid]['list_id']='l2'
        self.native.lists[1]['group_id']=None
        self.save_config()
        before={p:p.read_bytes() for p in self.hub.rglob('*') if p.is_file()}
        result=self.run_reconcile(True)
        self.assertTrue(result['ok'],result)
        self.assertEqual(result['items'],[])
        self.assertEqual(before,{p:p.read_bytes() for p in self.hub.rglob('*') if p.is_file()})
        canonical_path=Path(__file__).resolve().parents[5]/'scripts/archiprojects.py'
        spec=importlib.util.spec_from_file_location('missing_primary_canonical',canonical_path)
        canonical=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(canonical)
        card=next(card for card in canonical.read_cards(self.hub) if card['project_id']==pid)
        self.assertIsNone(card['primary_archiproject'])
        self.assertEqual(canonical.validate(self.hub),[])
    def test_missing_primary_move_adds_only_one_field(self):
        text,pid=self.missing_primary_fixture()
        result=self.run_reconcile()
        self.assertTrue(result['ok'],result)
        self.assertEqual(self.card.read_text(),text)
        result=self.run_reconcile(True)
        self.assertTrue(result['ok'],result)
        changed=self.card.read_text()
        self.assertEqual(changed.count('primary_archiproject:'),1)
        self.assertIn('primary_archiproject: b\n',changed)
        self.assertEqual(changed.replace('primary_archiproject: b\n',''),text)
    def test_empty_malformed_duplicate_primary_stays_blocked(self):
        text,pid=self.missing_primary_fixture()
        for field in ('primary_archiproject:\n',' primary_archiproject: none\n','primary_archiproject none\n','primary_archiproject: none\nprimary_archiproject: b\n'):
            with self.subTest(field=field):
                self.card.write_text(text+field)
                before=self.card.read_text()
                result=self.run_reconcile(True)
                self.assertFalse(result['ok'])
                self.assertEqual(result['blocked_projects'],[pid])
                self.assertIn('invalid_project_card',str(result))
                self.assertEqual(before,self.card.read_text())
    def test_subgroup_scope_accepts_unrelated_missing_primary(self):
        self.config['structure']['list_roles']['l2']={'kind':'subgroup','archiproject_id':'sub'}
        self.config['structure']['subgroups']={'sub':{'parent':None,'list_id':'l2'}}
        (self.hub/'projects/old').mkdir()
        registry=self.hub/'ai/project-registry.md'
        registry.write_text(registry.read_text()+f'## old\nStatus: archived\nPath: {self.hub}/projects/old\nCard: ai/project-cards/old.md\n')
        (self.hub/'ai/project-cards/old.md').write_text('Project ID: old\nStatus: archived\n')
        self.save_config()
        result=self.run_reconcile(True)
        self.assertTrue(result['ok'],result)
        self.assertIn('parent: b',self.arch.read_text())
    def test_missing_primary_addition_recovers_and_rejects_extra_payload(self):
        text,pid=self.missing_primary_fixture()
        original=m.atomic_write
        count=0
        def crash(path,data):
            nonlocal count
            count+=1
            if count==2:raise OSError('simulated crash')
            original(path,data)
        m.atomic_write=crash
        try:self.run_reconcile(True)
        finally:m.atomic_write=original
        journal=self.hub/'ai/structure-journal.json'
        self.assertTrue(journal.exists())
        saved=json.loads(journal.read_text())
        value=copy.deepcopy(saved)
        card_row=next(row for row in value['files'] if row['path']==str(self.card.relative_to(self.hub)))
        card_row['after']+='primary_archiproject: a\n'
        journal.write_text(json.dumps(value))
        self.assertFalse(self.run_reconcile(True)['ok'])
        self.assertEqual(self.card.read_text(),text)
        journal.write_text(json.dumps(saved))
        result=self.run_reconcile(True)
        self.assertTrue(result['ok'],result)
        self.assertEqual(self.card.read_text().replace('primary_archiproject: b\n',''),text)
    def test_recovery_rejects_missing_primary_noop_normalization(self):
        text,pid=self.missing_primary_fixture()
        original=m.atomic_write
        count=0
        def crash(path,data):
            nonlocal count
            count+=1
            if count==2:raise OSError('simulated crash')
            original(path,data)
        m.atomic_write=crash
        try:self.run_reconcile(True)
        finally:m.atomic_write=original
        journal=self.hub/'ai/structure-journal.json'
        value=json.loads(journal.read_text())
        value['files']=[row for row in value['files'] if row['path']!='ai/reminders-sync.json']
        value['files'][0]['after']=text+'primary_archiproject: none\n'
        journal.write_text(json.dumps(value))
        before=self.card.read_text()
        calls=len(self.native.calls)
        result=self.run_reconcile(True)
        self.assertFalse(result['ok'])
        self.assertEqual(before,self.card.read_text())
        self.assertEqual(len(self.native.calls),calls)
        self.assertIn('unsafe_structure_journal',str(result))
    def test_disabled_is_noop(self):
        self.config.pop('structure')
        self.native.call=lambda *args:self.fail('disabled read')
        self.assertEqual(self.run_reconcile()['config'],self.config)

if __name__=='__main__':unittest.main()
