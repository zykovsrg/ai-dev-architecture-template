"""Синтетические проверки переноса. Нативное приложение не вызывается."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/reminders_project_lists.py'
def module():
    spec = importlib.util.spec_from_file_location('migration_test', SCRIPT)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m

class Fake:
    def __init__(self):
        self.lists = [dict(id='old', name='Работа', account_id='account', group_id='group')]
        self.groups = [dict(id='group', name='Группа', account_id='account')]
        self.rows = {i:dict(id=i, title=i, notes='Точный текст\n', due='2026-10-27T10:30:00+03:00', repeat=None,
                    completed=i=='history', version=1, list='Работа', list_id='old', parent_id=None if i in ('parent','neighbor') else 'parent')
                     for i in ('parent','task','history','unbound','neighbor')}
        self.rows['task']['repeat']={'frequency':'weekly','interval':2}
        self.writes=[]; self.fail=None; self.truncated=False; self.account_supported=True
    def creation_account(self):
        if not self.account_supported: raise ValueError('creation_account_unverifiable')
        return 'account'
    def call(self, tool, args):
        if tool=='list_lists':
            lists=copy.deepcopy(self.lists);groups=copy.deepcopy(self.groups)
            for row in lists:
                items=[x for x in self.rows.values() if x['list_id']==row['id']];row['total']=len(items);row['open']=sum(not x['completed'] for x in items)
            for group in groups:group['lists']=[x['name'] for x in lists if x['group_id']==group['id']]
            return dict(lists=lists,groups=groups,guarded_list_creation=self.account_supported)
        if tool=='find_reminders':
            rows=[copy.deepcopy(x) for x in self.rows.values() if x['list_id']==args['list']]
            return dict(reminders=rows,count=len(rows),has_more=self.truncated)
        if tool=='get_reminder':
            row=copy.deepcopy(self.rows[args['id']]); row['subtasks']=[i for i,x in self.rows.items() if x.get('parent_id')==row['id']]
            return row
        self.writes.append((tool,copy.deepcopy(args)))
        if tool=='manage_list':
            if args['action']=='create':
                assert args['expected_account_id']=='account'
                row=dict(id='new',name=args['list'],account_id='account',group_id=None);self.lists.append(row)
            else:
                row=next(x for x in self.lists if x['id']==args['list']); assert row['group_id']==args['expected_group_id'];row['group_id']=args['group']
        elif tool=='update_reminder':
            row=self.rows[args['id']]; assert row['version']==args['version'];row.update(list_id=args['list'],list='Проект',parent_id=None,version=row['version']+1)
        else: raise AssertionError(tool)
        if self.fail==('create' if tool=='manage_list' and args['action']=='create' else tool):
            self.fail=None;raise TimeoutError('unknown_result')
        return copy.deepcopy(row)

class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.hub=Path(self.temp.name).resolve();(self.hub/'ai').mkdir();self.project=self.hub/'projects/demo';self.project.mkdir(parents=True);(self.project/'ai').mkdir()
        (self.hub/'ai/project-registry.md').write_text('## demo\nStatus: active\nPath: '+str(self.project)+'\n')
        for name in ('current-task.md','future-tasks.md','paused-tasks.md'):(self.project/'ai'/name).write_text('synthetic '+name)
        self.config=dict(version=1,binary='/private/tmp/fake',allowlist_file=str(self.hub/'ai/reminders-allowlist.json'),projects={'demo':dict(list_id='old',list_name='Работа',parent_id='parent',tasks={'t':{'reminder_id':'task'}},history={'history':{'original_id':'task','task_id':'t','project_id':'demo'}})},structure={'list_roles':{'old':{'kind':'group','group_id':'canonical'}},'projects':{'demo':{'list_id':'old','group':'canonical'}}})
        (self.hub/'ai/reminders-allowlist.json').write_text('{"names":["Работа"]}\n');self.save()
        self.m=module();self.native=Fake()
        self.native.rows['history']['notes']='Хаб: '+self.m.load_sync().compact_code('demo','t')
    def save(self):(self.hub/'ai/reminders-sync.json').write_text(json.dumps(self.config,ensure_ascii=False))
    def prepare(self):
        p=self.m.permission_preview(self.hub,'Проект');self.m.permission_apply(p['plan'],p['sha256'],True)
        return self.m.preview(self.hub,'demo','Проект','group',self.native)
    def apply(self,p):return self.m.apply(p['plan'],p['sha256'],True,self.native)
    def test_end_to_end_preserves_rows_and_retired_parent(self):
        before=copy.deepcopy(self.native.rows);p=self.prepare();self.assertEqual(self.native.writes,[])
        result=self.apply(p);self.assertEqual(result['phase'],'complete')
        for rid in ('task','history','unbound'):
            after=self.native.rows[rid];self.assertEqual(after['list_id'],'new');self.assertIsNone(after['parent_id'])
            for key,value in before[rid].items():
                if key not in ('list','list_id','parent_id','version'):self.assertEqual(after[key],value)
        self.assertEqual(self.native.rows['neighbor'],before['neighbor'])
        c=json.loads((self.hub/'ai/reminders-sync.json').read_text());b=c['projects']['demo']
        self.assertEqual(b['retired_parent']['snapshot'],self.native.call('get_reminder',{'id':'parent'}))
        self.assertEqual(c['structure']['projects']['demo']['group'],'canonical');self.assertNotIn('unbound',b['tasks'])
        count=len(self.native.writes);self.apply(p);self.assertEqual(len(self.native.writes),count)
    def test_permission_exact_scope_and_immutable_original(self):
        original=(self.hub/'ai/reminders-allowlist.json').read_bytes();p=self.m.permission_preview(self.hub,'Проект')
        with self.assertRaisesRegex(ValueError,'approval'):self.m.permission_apply(p['plan'],p['sha256'],False)
        with self.assertRaisesRegex(ValueError,'sha256'):self.m.permission_apply(p['plan'],'bad',True)
        self.m.permission_apply(p['plan'],p['sha256'],True)
        self.assertEqual((self.hub/'ai/reminders-allowlist.json').read_bytes(),original)
        self.assertEqual(json.loads((self.hub/'ai/reminders-standard-allowlist.json').read_text())['names'],['Работа','Проект'])
    def test_stale_guards_stop_before_writes(self):
        for kind in ('remote','config','canonical','permission'):
            with self.subTest(kind=kind):
                self.setUp()
                p=self.prepare()
                if kind=='remote':self.native.rows['task']['notes']='external'
                elif kind=='config':self.config['extra']=1;self.save()
                elif kind=='canonical':(self.project/'ai/future-tasks.md').write_text('external')
                else:(self.hub/'ai/reminders-standard-allowlist.json').write_text('{"names":["Работа","Проект","foreign"]}')
                with self.assertRaisesRegex(ValueError,'changed|stale'):self.apply(p)
                self.assertEqual(self.native.writes,[])
    def test_reject_truncated_nested_bound_cancel_and_account(self):
        for kind in ('truncated','nested','bound','cancel','account','name'):
            with self.subTest(kind=kind):
                if kind=='truncated':self.native.truncated=True
                elif kind=='nested':self.native.rows['unbound']['parent_id']='task'
                elif kind=='bound':self.config['projects']['demo']['tasks']['t']['reminder_id']='missing';self.save()
                elif kind=='cancel':self.config['projects']['demo']['tasks']['t']['cancellation']={ 'status':'committed'};self.save()
                elif kind=='account':self.native.groups[0]['account_id']='foreign'
                else:self.native.lists.append(dict(id='conflict',name='Проект',account_id='account',group_id=None))
                with self.assertRaises(ValueError):self.m.preview(self.hub,'demo','Проект','group',self.native)
                self.assertEqual(self.native.writes,[]);self.setUp()
    def test_unknown_creation_requires_exact_adopt(self):
        p=self.prepare();self.native.fail='create'
        with self.assertRaises(TimeoutError):self.apply(p)
        with self.assertRaisesRegex(ValueError,'recovery_required'):self.apply(p)
        self.assertEqual(len([x for x in self.native.writes if x[1].get('action')=='create']),1)
        self.m.adopt(p['plan'],p['sha256'],'new',True,self.native)
        self.assertEqual(self.apply(p)['phase'],'complete')
    def test_unknown_update_resumes_without_duplicate(self):
        p=self.prepare();self.native.fail='update_reminder'
        with self.assertRaises(TimeoutError):self.apply(p)
        self.assertEqual(self.m.pending_projects(self.hub,self.config),{'demo'})
        self.assertEqual(self.apply(p)['phase'],'complete')
        self.assertEqual(len([x for x in self.native.writes if x[0]=='update_reminder']),3)
        self.assertEqual(self.m.pending_projects(self.hub,json.loads((self.hub/'ai/reminders-sync.json').read_text())),set())
    def test_native_account_capability_required_before_creation(self):
        p=self.prepare();self.native.account_supported=False
        with self.assertRaisesRegex(ValueError,'creation_account_unverifiable'):self.apply(p)
        self.assertEqual(self.native.writes,[])
    def test_pending_blocks_sync_notes_and_structure_even_missing_journal(self):
        p=self.prepare();self.native.fail='update_reminder'
        with self.assertRaises(TimeoutError):self.apply(p)
        c=json.loads((self.hub/'ai/reminders-sync.json').read_text());m=self.m.load_sync()
        for result in (m.sync(self.hub,c,apply=True,native=self.native),m.sync_notes(self.hub,c,apply=True,native=self.native),m.structure_module().reconcile_structure(self.hub,c,apply=True,native=self.native)):
            self.assertFalse(result['ok']);self.assertEqual(result['items'][0]['error'],'migration_recovery_required')
        Path(p['plan']).unlink()
        self.assertEqual(self.m.pending_projects(self.hub,c),{'demo'})
    def test_standard_allowlist_selection_preserves_cancellation(self):
        from unittest.mock import patch
        c=copy.deepcopy(self.config);c['standard_allowlist_file']=str(self.hub/'ai/reminders-standard-allowlist.json')
        m=self.m.load_sync()
        class Result: returncode=0;stdout='{}';stderr=''
        with patch.object(m.subprocess,'run',return_value=Result()) as run:
            m.Native(c).call('list_lists',{})
            self.assertEqual(run.call_args.kwargs['env']['HUB_REMINDERS_ALLOWED_LISTS_FILE'],c['standard_allowlist_file'])
            m.Native(c).call('hub_cancel_status',{})
            self.assertEqual(run.call_args.kwargs['env']['HUB_REMINDERS_ALLOWED_LISTS_FILE'],c['allowlist_file'])
        structural=m.structure_module()
        with patch.object(structural.subprocess,'run',return_value=Result()) as run:
            c['structure']['groups_allowlist_file']='/private/tmp/groups'
            structural.StructureNative(c).call('list_lists',{})
            self.assertEqual(run.call_args.kwargs['env']['HUB_REMINDERS_ALLOWED_LISTS_FILE'],c['standard_allowlist_file'])
    def test_unknown_group_update_resumes_exact_state(self):
        p=self.prepare();self.native.fail='manage_list'
        with self.assertRaises(TimeoutError):self.apply(p)
        self.assertEqual(self.apply(p)['phase'],'complete')
        self.assertEqual(len([x for x in self.native.writes if x[1].get('action')=='update']),1)
    def test_adopt_rejects_nonempty_foreign_or_grouped_list(self):
        p=self.prepare();self.native.fail='create'
        with self.assertRaises(TimeoutError):self.apply(p)
        self.native.lists[-1]['account_id']='foreign'
        with self.assertRaisesRegex(ValueError,'destination_changed'):self.m.adopt(p['plan'],p['sha256'],'new',True,self.native)
        self.native.lists[-1]['account_id']='account';self.native.lists[-1]['group_id']='group'
        with self.assertRaisesRegex(ValueError,'destination_changed'):self.m.adopt(p['plan'],p['sha256'],'new',True,self.native)
    def test_resume_rejects_external_edit_and_stale_receipt(self):
        p=self.prepare();self.native.fail='update_reminder'
        with self.assertRaises(TimeoutError):self.apply(p)
        moved=next(x for x in self.native.rows.values() if x['list_id']=='new');moved['notes']='external'
        count=len(self.native.writes)
        with self.assertRaisesRegex(ValueError,'remote_changed'):self.apply(p)
        self.assertEqual(len(self.native.writes),count)
    def test_prepare_destination_pauses_before_reminder_mutations(self):
        p=self.prepare();result=self.m.apply(p['plan'],p['sha256'],True,self.native,prepare_only=True)
        self.assertEqual(result['phase'],'destination_ready')
        self.assertEqual(self.native.lists[-1]['group_id'],'group')
        self.assertEqual([x for x in self.native.writes if x[0]=='update_reminder'],[])
        c=json.loads((self.hub/'ai/reminders-sync.json').read_text());self.assertEqual(c['projects']['demo']['parent_id'],'parent')
        self.assertEqual(self.apply(p)['phase'],'complete')
    def test_tampered_final_config_cannot_authorize_unplanned_config(self):
        p=self.prepare();self.apply(p);folder=Path(p['plan']).parent;count=len(self.native.writes)
        state=json.loads((folder/'state.json').read_text());forged=json.loads((self.hub/'ai/reminders-sync.json').read_text());forged['extra']='unauthorized'
        raw=self.m.encoded(forged);state['final_config']=raw;(folder/'state.json').write_text(json.dumps(state));(self.hub/'ai/reminders-sync.json').write_text(raw)
        with self.assertRaisesRegex(ValueError,'config_changed|invalid_final'):self.apply(p)
        self.assertEqual(len(self.native.writes),count)
    def test_done_receipt_and_parent_snapshot_are_exact(self):
        p=self.prepare();self.apply(p)
        self.native.rows['task']['version']+=1
        with self.assertRaisesRegex(ValueError,'receipt_changed'):self.apply(p)
    def test_derived_metadata_changes_but_identity_stays_guarded(self):
        p=self.prepare()
        try:result=self.apply(p)
        except ValueError as exc:self.fail('Own derived metadata blocked: '+str(exc))
        self.assertEqual(result['phase'],'complete')
        self.native.groups[0]['name']='external'
        with self.assertRaisesRegex(ValueError,'metadata_changed'):self.apply(p)
    def test_permission_file_without_approved_receipt_is_insufficient(self):
        p=self.prepare()
        for folder in (self.hub/'ai/reminders-project-lists').iterdir():
            plan=json.loads((folder/'plan.json').read_text())
            if plan['kind']=='permission':
                state=json.loads((folder/'state.json').read_text());state['phase']='preview';(folder/'state.json').write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError,'permission_consent_missing'):self.apply(p)
        self.assertEqual(self.native.writes,[])
    def test_corrupt_history_rejected_before_journal_or_writes(self):
        for kind in ('original','task','project','completed','marker','missing'):
            with self.subTest(kind=kind):
                self.setUp()
                history=self.config['projects']['demo']['history']['history']
                if kind=='original':history['original_id']='missing-original'
                elif kind=='task':history['task_id']='missing-task'
                elif kind=='project':history['project_id']='foreign'
                elif kind=='completed':self.native.rows['history']['completed']=False
                elif kind=='marker':self.native.rows['history']['notes']='unmarked'
                else:history.pop('original_id')
                self.save()
                with self.assertRaisesRegex(ValueError,'invalid_recurrence_history'):
                    self.m.preview(self.hub,'demo','Проект','group',self.native)
                self.assertEqual(self.native.writes,[])
                self.assertFalse((self.hub/'ai/reminders-project-lists').exists())
    def test_bound_marker_requires_exact_project_and_task(self):
        self.config['projects']['demo']['tasks']['other']={'reminder_id':'unbound'};self.save()
        self.native.rows['task']['notes']='Хаб: '+self.m.load_sync().compact_code('demo','other')
        with self.assertRaisesRegex(ValueError,'bound_child_identity_mismatch'):
            self.m.preview(self.hub,'demo','Проект','group',self.native)
        self.assertEqual(self.native.writes,[])
        self.assertFalse((self.hub/'ai/reminders-project-lists').exists())
    def test_tampered_plan_and_state_are_rejected(self):
        p=self.prepare();path=Path(p['plan']);plan=json.loads(path.read_text());plan['list_name']='wrong';path.write_text(json.dumps(plan))
        with self.assertRaisesRegex(ValueError,'sha256'):self.apply(p)
        self.assertEqual(self.native.writes,[])

if __name__=='__main__':unittest.main()
