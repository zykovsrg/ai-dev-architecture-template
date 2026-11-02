"""Проверки архива на синтетическом Хабе. Приложения не вызываются."""
import copy, importlib.util, json, os, shutil, tempfile, unittest, uuid
from pathlib import Path
from unittest.mock import patch

SOURCE=Path(os.environ.get('ARCHIVE_SOURCE',str(Path(__file__).parents[1]/'scripts/reminders_archive.py')))
spec=importlib.util.spec_from_file_location('archive_test_module',SOURCE)
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
M=a.load_sync()
REAL=Path('/Users/zykovsrg/Documents/vibecode/_ai-hub')

class Native:
    def __init__(self, lid,gid,account,rid):
        self.groups=[dict(id=gid,name='Хадасса',account_id=account)]
        self.lists={lid:dict(id=lid,name='Демо',group_id=gid,account_id=account)}
        self.rows={rid:dict(id=rid,title='Написать текст',list_id=lid,list='Демо',version='v1',completed=False,notes='Личная заметка')}
        self.calls=[];self.fail=None
    def call(self,tool,args):
        self.calls.append((tool,copy.deepcopy(args)))
        if tool=='list_lists':
            return dict(groups=copy.deepcopy(self.groups),lists=[dict(l,total=sum(r['list_id']==lid for r in self.rows.values()),open=sum(r['list_id']==lid and not r.get('completed') for r in self.rows.values())) for lid,l in self.lists.items()])
        if tool=='find_reminders':
            rows=[copy.deepcopy(r) for r in self.rows.values() if r['list_id']==args['list']]
            return dict(reminders=rows,count=len(rows))
        if tool=='get_reminder':return copy.deepcopy(self.rows[args['id']])
        if tool=='manage_group':
            group=dict(id=str(uuid.uuid4()).upper(),name=args['group'],account_id=self.groups[0]['account_id']);self.groups.append(group);return dict(group=group)
        if tool=='manage_list':
            row=self.lists[args['list']]
            if row['group_id']!=args['expected_group_id']:raise ValueError('version')
            if self.fail=='move-before':self.fail=None;raise TimeoutError('before_move')
            row['group_id']=args['group']
            if self.fail=='move-after':self.fail=None;raise TimeoutError('after_move')
            return dict(list=copy.deepcopy(row))
        raise AssertionError(tool)
    def get(self,rid,lid,*_):
        row=self.call('get_reminder',dict(id=rid));assert row['list_id']==lid;return row
    def update(self,row,fields):
        actual=self.rows[row['id']]
        if actual['version']!=row['version']:raise ValueError('version')
        if self.fail=='task-before':self.fail=None;raise TimeoutError('before_task')
        actual.update(fields);actual['version']=actual['version']+'x'
        if self.fail=='task-after':self.fail=None;raise TimeoutError('after_task')

class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.h=Path(self.temp.name).resolve()
        for d in ['ai/project-cards','projects/demo/ai','scripts']:(self.h/d).mkdir(parents=True)
        (self.h/'ai/allowed-roots.md').write_text('- '+str(self.h/'projects')+'\n')
        shutil.copyfile(REAL/'scripts/task_records.py',self.h/'scripts/task_records.py')
        self.lid=str(uuid.uuid4()).upper();self.gid=str(uuid.uuid4()).upper();self.account=str(uuid.uuid4()).upper();self.rid=str(uuid.uuid4()).upper();self.tid='TASK-demo-20261028-001'
        root=self.h/'projects/demo'
        (self.h/'ai/project-registry.md').write_text(f'## demo\nName: Демо\nStatus: active\nPath: {root}\nCard: ai/project-cards/demo.md\n')
        (self.h/'ai/project-cards/demo.md').write_text('Project ID: demo\nName: Демо\nStatus: active\nprimary_archiproject: hadassah-promo\n')
        (root/'ai/current-task.md').write_text('# Текущая задача\n\nStatus: empty\nStage: intake\n\n## Goal\n\nНет активной задачи.\n')
        (root/'ai/paused-tasks.md').write_text('# Приостановленные задачи\n\n## Paused tasks\n')
        (root/'ai/future-tasks.md').write_text(f'# Будущие задачи\n\n## Future tasks\n\n### {self.tid} — Написать текст\n\nStatus: ready\nDue: 2026-10-30\nЗапланировано: 2026-10-28.\n')
        (self.h/'ai/lists.json').write_text(json.dumps(dict(names=['Демо'])))
        (self.h/'ai/groups.json').write_text(json.dumps(dict(names=['Хадасса'])))
        (self.h/'ai/pins.json').write_text(json.dumps(dict(groups={self.gid:'Хадасса'})))
        (self.h/'ai/.reminders-sync.lock').touch()
        self.c=dict(version=1,binary=str(self.h/'binary'),allowlist_file=str(self.h/'ai/lists.json'),projects={'demo':dict(layout='project_list',list_id=self.lid,list_name='Демо',parent_id=None,native_group_id=self.gid,account_id=self.account,tasks={self.tid:dict(reminder_id=self.rid)},history={})},structure=dict(groups_allowlist_file=str(self.h/'ai/groups.json'),group_ids_allowlist_file=str(self.h/'ai/pins.json')))
        self.savec(self.c);self.native=Native(self.lid,self.gid,self.account,self.rid)
        self.before=(root/'ai/future-tasks.md').read_bytes()
    def savec(self,c):(self.h/'ai/reminders-sync.json').write_text(json.dumps(c,ensure_ascii=False))
    def current(self):return json.loads((self.h/'ai/reminders-sync.json').read_text())
    def plan(self):
        r=a.preview(self.h,['demo'],self.native);return Path(r['plan']),r['sha256']
    def run_apply(self,path,token):return a.apply(path,token,True,self.native)
    def test_roundtrip_and_repeat(self):
        p,t=self.plan();self.assertFalse(any(x[0].startswith('manage') for x in self.native.calls))
        self.run_apply(p,t);self.assertTrue(a.verify_current(self.h,self.current(),'demo',self.native))
        self.assertIn('Status: done',(self.h/'projects/demo/ai/future-tasks.md').read_text())
        writes=len([x for x in self.native.calls if x[0].startswith('manage')])
        self.run_apply(p,t);self.assertEqual(writes,len([x for x in self.native.calls if x[0].startswith('manage')]))
        view=a.restore_preview(self.h,'demo',self.native)
        a.restore(self.h,'demo',view['token'],True,self.native)
        self.assertEqual((self.h/'projects/demo/ai/future-tasks.md').read_bytes(),self.before)
        self.assertEqual(self.native.lists[self.lid]['group_id'],self.gid)
        self.assertFalse(self.native.rows[self.rid]['completed'])
    def test_approval_and_checksum(self):
        p,t=self.plan()
        with self.assertRaisesRegex(ValueError,'explicit_approval'):a.apply(p,t,False,self.native)
        with self.assertRaisesRegex(ValueError,'plan_changed'):a.apply(p,'wrong',True,self.native)
        self.assertFalse(self.native.rows[self.rid]['completed'])
    def test_concurrent_local_change(self):
        p,t=self.plan();(self.h/'projects/demo/ai/future-tasks.md').write_text('user change')
        with self.assertRaisesRegex(ValueError,'local_changed'):self.run_apply(p,t)
        self.assertFalse(any(x[0].startswith('manage') for x in self.native.calls))
    def test_foreign_uuid_rejected(self):
        self.native.rows[str(uuid.uuid4())]=dict(id=str(uuid.uuid4()),title='Чужое',list_id=self.lid,version='v1')
        with self.assertRaisesRegex(ValueError,'foreign_or_unbound'):self.plan()
    def test_missing_preserved_not_recreated(self):
        self.native.rows.clear();p,t=self.plan();self.run_apply(p,t)
        self.assertFalse(self.native.rows)
        receipt=a.read_receipt(self.h,self.current(),'demo')
        self.assertEqual(receipt[2]['gap_ids'],[self.rid])
        view=a.restore_preview(self.h,'demo',self.native);a.restore(self.h,'demo',view['token'],True,self.native)
        self.assertFalse(self.native.rows)
    def test_partial_move_resume(self):
        p,t=self.plan();self.native.fail='move-after'
        with self.assertRaises(TimeoutError):self.run_apply(p,t)
        self.assertEqual(a.pending_projects(self.h,self.current()),{'demo'})
        self.run_apply(p,t)
        self.assertTrue(a.verify_current(self.h,self.current(),'demo',self.native))
    def test_partial_completion_resume(self):
        p,t=self.plan();self.native.fail='task-before'
        with self.assertRaises(TimeoutError):self.run_apply(p,t)
        self.run_apply(p,t)
        self.assertTrue(self.native.rows[self.rid]['completed'])
    def test_tampered_receipt_and_native_account(self):
        p,t=self.plan();self.run_apply(p,t)
        self.native.lists[self.lid]['account_id']='wrong'
        if hasattr(self.native,'_archive_snapshot'):del self.native._archive_snapshot
        with self.assertRaisesRegex(ValueError,'identity_changed'):a.verify_current(self.h,self.current(),'demo',self.native)
    def test_inactive_without_receipt_not_skipped(self):
        (self.h/'ai/project-registry.md').write_text((self.h/'ai/project-registry.md').read_text().replace('Status: active','Status: archived'))
        self.assertFalse(a.verify_current(self.h,self.current(),'demo',self.native))
    def test_restore_stale_preview(self):
        p,t=self.plan();self.run_apply(p,t);v=a.restore_preview(self.h,'demo',self.native)
        c=self.current();c['changed']=True;self.savec(c)
        with self.assertRaisesRegex(ValueError,'stale'):a.restore(self.h,'demo',v['token'],True,self.native)

    def archived(self):
        p,t=self.plan();self.run_apply(p,t);return p,t
    def test_restore_card_edit_preserved(self):
        self.archived();card=self.h/'ai/project-cards/demo.md';card.write_text(card.read_text()+'\nUser note KEEP\n')
        with self.assertRaisesRegex(ValueError,'card_changed'):a.restore_preview(self.h,'demo',self.native)
        self.assertIn('User note KEEP',card.read_text())
    def test_restore_native_stale_before_write(self):
        self.archived();view=a.restore_preview(self.h,'demo',self.native)
        self.native.rows[self.rid]['notes']='USER NEW';self.native.rows[self.rid]['version']+='edit'
        before=len(self.native.calls)
        with self.assertRaisesRegex(ValueError,'content_changed|preview_stale'):a.restore(self.h,'demo',view['token'],True,self.native)
        self.assertFalse(any(x[0]=='manage_list' for x in self.native.calls[before:]))
    def test_restore_partial_resume_same_token(self):
        self.archived();view=a.restore_preview(self.h,'demo',self.native);self.native.fail='task-before'
        with self.assertRaises(TimeoutError):a.restore(self.h,'demo',view['token'],True,self.native)
        result=a.restore(self.h,'demo',view['token'],True,self.native)
        self.assertEqual(result['status'],'active');self.assertFalse(self.native.rows[self.rid]['completed'])
        self.assertFalse(self.current().get('archive_pending'))
    def test_restore_local_edit_during_move_preserved(self):
        self.archived();view=a.restore_preview(self.h,'demo',self.native);original=self.native.call
        target=self.h/'projects/demo/ai/future-tasks.md'
        def call(tool,args):
            result=original(tool,args)
            if tool=='manage_list':target.write_text(target.read_text()+'\nUSER KEEP\n')
            return result
        self.native.call=call
        with self.assertRaisesRegex(ValueError,'restore_local_changed'):a.restore(self.h,'demo',view['token'],True,self.native)
        self.assertIn('USER KEEP',target.read_text())
    def test_config_write_journal_gap_resume(self):
        p,t=self.plan();real=M.atomic_json;once=[True]
        def atomic(path,value):
            if path.name=='state.json' and value.get('phase')=='permissions' and not value.get('config_intent') and once[0]:
                once[0]=False;raise RuntimeError('journal IO failed')
            return real(path,value)
        with patch.object(a,'load_sync',return_value=M),patch.object(M,'atomic_json',side_effect=atomic):
            with self.assertRaisesRegex(RuntimeError,'journal IO'):self.run_apply(p,t)
            self.run_apply(p,t)
        self.assertTrue(a.verify_current(self.h,self.current(),'demo',self.native))

    def test_sync_archive_no_writes_and_unknown_inactive_error(self):
        self.archived();c=self.current();before=copy.deepcopy(self.native.rows)
        report=M.sync(self.h,c,apply=False,project='demo',native=self.native,reconcile=False)
        self.assertTrue(report['ok'],report);self.assertIn('archive_verified',[r.get('action')for r in report['items']])
        notes=M.sync_notes(self.h,c,apply=False,project='demo',native=self.native)
        self.assertTrue(notes['ok'],notes);self.assertEqual(before,self.native.rows)
        c['projects']['demo'].pop('archive')
        report=M.sync(self.h,c,apply=False,project='demo',native=self.native,reconcile=False)
        self.assertFalse(report['ok']);self.assertIn('unregistered_or_inactive_project',[r.get('error')for r in report['items']])

    def test_restore_final_config_gap_settled(self):
        p,t=self.archived();view=a.restore_preview(self.h,'demo',self.native);real=M.atomic_json;once=[True]
        def atomic(path,value):
            result=real(path,value)
            if path.name=='reminders-sync.json' and not value['projects']['demo'].get('archive') and once[0]:
                once[0]=False;raise RuntimeError('after final config')
            return result
        with patch.object(a,'load_sync',return_value=M),patch.object(M,'atomic_json',side_effect=atomic):
            with self.assertRaisesRegex(RuntimeError,'final config'):a.restore(self.h,'demo',view['token'],True,self.native)
            result=a.restore(self.h,'demo',view['token'],True,self.native)
        self.assertTrue(result['already_active']);self.assertNotIn('config_intent',json.loads(p.with_name('state.json').read_text()))
        self.assertEqual((self.h/'projects/demo/ai/future-tasks.md').read_bytes(),self.before)

    def test_group_create_exact_returned_uuid(self):
        p,t=self.plan();original=self.native.call
        def call(tool,args):
            result=copy.deepcopy(original(tool,args))
            if tool=='manage_group':self.native.groups[-1]['id']=str(uuid.uuid4()).upper()
            return result
        self.native.call=call
        with self.assertRaisesRegex(ValueError,'created_group_identity_changed'):self.run_apply(p,t)
        self.assertEqual(self.native.lists[self.lid]['group_id'],self.gid)
    def test_gap_reappeared_foreign_list_rejected(self):
        self.native.rows.clear();p,t=self.plan();other=str(uuid.uuid4()).upper()
        self.native.lists[other]=dict(id=other,name='Other',group_id=self.gid,account_id=self.account)
        self.native.rows[self.rid]=dict(id=self.rid,title='Moved',list_id=other,version='v2',completed=False)
        with self.assertRaisesRegex(ValueError,'gap_reappeared'):self.run_apply(p,t)
        self.assertEqual(self.native.lists[self.lid]['group_id'],self.gid)
    def test_pending_blocks_both_structural_entrypoints(self):
        spec=importlib.util.spec_from_file_location('archive_structure_test',SOURCE.with_name('reminders_structure.py'))
        structure=importlib.util.module_from_spec(spec);spec.loader.exec_module(structure)
        c=copy.deepcopy(self.c);c['archive_pending']=dict(projects=['demo']);c['structure']['enabled']=True
        self.assertEqual(structure.migration_pending(self.h,c),{'demo'})
        for entry in [structure.reconcile_structure,structure.reconcile_structure_legacy]:
            report=entry(self.h,c,apply=True,native=self.native)
            self.assertFalse(report['ok']);self.assertEqual(report['blocked_projects'],['demo'])
        self.assertFalse(self.native.calls)
    def test_native_group_plain_cli_answer(self):
        expected=str(uuid.uuid4()).upper()
        result=type('Result',(),dict(returncode=0,stderr='',stdout='Created the group "Архив". id: '+expected+'\n'))()
        with patch.object(M.subprocess,'run',return_value=result):
            self.assertEqual(M.Native(self.c).call('manage_group',dict(action='create',group='Архив'))['id'],expected)

    def test_native_passes_configured_uuid_pins(self):
        result=type('Result',(),dict(returncode=0,stderr='',stdout='{"id":"unchanged"}'))()
        with patch.object(M.subprocess,'run',return_value=result)as run:
            M.Native(self.c).call('manage_list',dict(action='update',list=self.lid,group='archive',expected_group_id=self.gid))
            self.assertEqual(run.call_args.kwargs['env']['HUB_REMINDERS_ALLOWED_GROUP_IDS_FILE'],self.c['structure']['group_ids_allowlist_file'])
        self.assertEqual(json.loads((self.h/'ai/pins.json').read_text()),dict(groups={self.gid:'Хадасса'}))

if __name__=='__main__':unittest.main()
