"""Изолированные проверки входящей копии и доказанных исчезновений."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = Path(os.environ.get('AUTHORITY_CORE_SCRIPTS', ROOT / 'modules/planning/scripts'))
spec = importlib.util.spec_from_file_location('authority_core_subject', SCRIPTS / 'reminders_sync.py')
sync = importlib.util.module_from_spec(spec); spec.loader.exec_module(sync)
RID, PID, LID, ACCOUNT, GROUP = [str(uuid.UUID(int=i)) for i in range(1,6)]
TID = 'TASK-demo-20261027-001'

class Native:
    def __init__(self):
        self.lists = [dict(id=LID,name='Работа',account_id=ACCOUNT,group_id=GROUP)]
        self.groups = [dict(id=GROUP,name='Группа',account_id=ACCOUNT)]
        self.rows = {PID:dict(id=PID,title='Проект',list='Работа',list_id=LID,version=1,completed=False),
                     RID:dict(id=RID,title='Из приложения',due='2026-11-02T11:00:00+03:00',list='Работа',list_id=LID,parent_id=PID,version=2,completed=False,notes='Личная заметка')}
        self.writes=[]; self.incomplete=False
    def call(self, tool, args):
        if tool == 'list_lists': return dict(lists=[dict(r,total=sum(t['list_id']==r['id'] for t in self.rows.values())) for r in copy.deepcopy(self.lists)],groups=copy.deepcopy(self.groups))
        if tool == 'find_reminders':
            rows=[copy.deepcopy(r) for r in self.rows.values() if r['list_id']==args['list']]
            return dict(reminders=rows,count=len(rows),has_more=self.incomplete)
        self.writes.append((tool,args)); raise AssertionError('pull must not write native: '+tool)
    def get(self,rid,lid,*args): return copy.deepcopy(self.rows[rid])
    def children(self,b): return [copy.deepcopy(r) for r in self.rows.values() if r['list_id']==b['list_id'] and r.get('parent_id')==b.get('parent_id')]
    def update(self,*args): self.writes.append(args); raise AssertionError('native update forbidden')

class AuthorityCoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.hub=Path(self.tmp.name).resolve()
        (self.hub/'ai').mkdir(); (self.hub/'scripts').mkdir(); self.project=self.hub/'projects/demo'; (self.project/'ai').mkdir(parents=True)
        shutil.copyfile(ROOT/'modules/tasks/scripts/task_records.py',self.hub/'scripts/task_records.py')
        for source in SCRIPTS.glob('*.py'): shutil.copyfile(source,self.hub/'scripts'/source.name)
        (self.hub/'ai/project-registry.md').write_text(f'## demo\nName: Проект\nStatus: active\nPath: {self.project}\n')
        self.files={k:self.project/'ai'/n for k,n in sync.NAMES.items()}
        self.files['current'].write_text('# Текущая задача\nStatus: empty\n'); self.files['paused'].write_text('# Пауза\n')
        self.files['future'].write_text(f'# Будущие задачи\n\n### {TID} — Локальный текст\nStatus: ready\nDue: 2026-12-31\nЗапланировано: 2026-10-30.\n\nКонтекст.\n')
        self.allow=self.hub/'ai/reminders-allowlist.json'; self.allow.write_text(json.dumps({'names':['Работа']}))
        self.config=dict(version=1,binary='/private/tmp/never-run',allowlist_file=str(self.allow),projects={'demo':dict(list_id=LID,list_name='Работа',parent_id=PID,account_id=ACCOUNT,native_group_id=GROUP,tasks={TID:dict(reminder_id=RID,last_hub_title='Раньше',last_remote_title='Раньше',last_hub_day='2026-10-25',last_remote_day='2026-10-25')},history={})},task_authority=dict(mode='reminders',deletions='cancel',journal='ai/reminders-authority/'+str(uuid.uuid4()),sha256='a'*64))
        self.native=Native(); self.save()
        self.activation=dict(statement='Удалённые задачи считать отменёнными с историей',deletion_policy='cancel')
        self.helper=types.SimpleNamespace(validate_activation=lambda hub,c:self.activation,project_path=lambda h,c,p:None)
    def authority(self):
        self.assertTrue(hasattr(sync,'authority_module'),'Нет единого исполнителя входящей сверки')
        authority=sync.authority_module()
        self.addCleanup(patch.stopall)
        patch.object(authority,'archive_module',return_value=self.helper).start()
        return authority
    def save(self): (self.hub/'ai/reminders-sync.json').write_text(json.dumps(self.config,ensure_ascii=False))
    def row(self): return sync.HubProject(self.hub,'demo').rows()[TID]
    def pull(self): return sync.sync(self.hub,self.config,True,native=self.native,reconcile=False)
    def test_remote_fields_win_and_local_unbound_never_published(self):
        self.authority()
        self.files['future'].write_text(self.files['future'].read_text()+'\n### TASK-demo-20261027-002 — Локальная\nStatus: ready\n')
        with patch.object(sync.subprocess,'run',side_effect=AssertionError('external writer forbidden')):
            result=self.pull()
        self.assertTrue(result['ok'],result); row=self.row()
        self.assertEqual((row['title'],row['planned_day'],row['due']),('Из приложения','2026-11-02','2026-12-31'))
        self.assertTrue(all(i.get('remote_fields',[])==[] for i in result['items'])); self.assertEqual(self.native.writes,[])
        self.assertNotIn('TASK-demo-20261027-002',self.config['projects']['demo']['tasks'])
    def test_unchecked_done_reopens_last_open_status(self):
        self.authority(); self.files['future'].write_text(self.files['future'].read_text().replace('Status: ready','Status: done'))
        self.config['projects']['demo']['tasks'][TID].update(last_completed=True,last_open_status='blocked');self.save()
        result=self.pull(); self.assertTrue(result['ok'],result); self.assertEqual(self.row()['status'],'blocked'); self.assertEqual(self.native.writes,[])
    def test_remote_completion_remembers_open_status(self):
        self.authority(); self.files['future'].write_text(self.files['future'].read_text().replace('Status: ready','Status: blocked'));self.native.rows[RID]['completed']=True
        result=self.pull();self.assertTrue(result['ok'],result);self.assertEqual(self.row()['status'],'done');self.assertEqual(self.config['projects']['demo']['tasks'][TID]['last_open_status'],'blocked')
    def test_repeating_live_instance_stays_open_without_native_write(self):
        self.authority(); self.native.rows[RID]['repeat']={'frequency':'daily'}; self.native.rows[RID]['completed']=True
        result=self.pull();self.assertTrue(result['ok'],result);self.assertEqual(self.row()['status'],'ready');self.assertEqual(self.native.rows[RID]['repeat'],{'frequency':'daily'});self.assertEqual(self.native.writes,[])
    def test_preview_missing_uuid_never_creates_journal(self):
        a=self.authority(); self.native.rows.pop(RID)
        result=a.prepare_pull(sync,self.hub,self.config,native=self.native)
        self.assertTrue(result['stop']);self.assertEqual(result['items'][0]['action'],'external_retirement');self.assertFalse((self.hub/'ai/reminders-external-retirements').exists());self.assertEqual(self.row()['status'],'ready')
    def test_apply_missing_uuid_uses_receipt_and_internal_writer(self):
        self.authority(); self.native.rows.pop(RID)
        with patch.object(sync.subprocess,'run',side_effect=AssertionError('external writer forbidden')):
            result=self.pull()
        self.assertTrue(result['ok'],result);self.assertEqual(self.row()['status'],'dropped')
        c=sync.load_config(self.hub);self.assertIn('external_retirement',c['projects']['demo']['tasks'][TID]);self.assertEqual(self.native.writes,[])
        plan=next((self.hub/'ai/reminders-external-retirements').glob('*/plan.json'));intent=json.loads(plan.read_text())['user_intent']
        self.assertEqual(intent['statement'],self.activation['statement']);self.assertEqual(intent['basis']['kind'],'standing_policy')
    def test_missing_expected_list_is_not_deletion(self):
        a=self.authority();self.native.lists=[];self.native.rows={}
        result=a.prepare_pull(sync,self.hub,self.config,True,native=self.native)
        self.assertEqual(result['blocked_projects'],{'demo'});self.assertIn('expected_list',result['items'][0]['error']);self.assertTrue(result['cancellation_disabled'])
        self.assertEqual(self.row()['status'],'ready')
    def test_wrong_account_is_not_deletion(self):
        a=self.authority();self.native.rows.pop(RID);self.native.lists[0]['account_id']=str(uuid.uuid4())
        result=a.prepare_pull(sync,self.hub,self.config,True,native=self.native)
        self.assertEqual(result['blocked_projects'],{'demo'});self.assertIn('account',result['items'][0]['error'])
    def test_wrong_group_is_not_deletion(self):
        a=self.authority();self.native.rows.pop(RID);self.native.lists[0]['group_id']=None
        result=a.prepare_pull(sync,self.hub,self.config,True,native=self.native)
        self.assertEqual(result['blocked_projects'],{'demo'});self.assertIn('group',result['items'][0]['error'])
    def test_pagination_is_not_deletion(self):
        a=self.authority();self.native.rows.pop(RID);self.native.incomplete=True
        result=a.prepare_pull(sync,self.hub,self.config,True,native=self.native)
        self.assertEqual(result['blocked_projects'],{'demo'});self.assertIn('incomplete',result['items'][0]['error'])
    def test_invalid_activation_stops_before_read(self):
        self.authority();self.helper.validate_activation=lambda *a:(_ for _ in ()).throw(ValueError('activation_rejected'))
        with patch.object(self.native,'call',side_effect=AssertionError('native read too early')):
            with self.assertRaisesRegex(ValueError,'activation_rejected'):self.pull()
    def test_adopted_archive_is_narrow_task_access(self):
        a=self.authority();(self.hub/'ai/project-registry.md').write_text((self.hub/'ai/project-registry.md').read_text().replace('Status: active','Status: archived'))
        self.config['projects']['demo']['archive']={'journal':'historic'};self.save();self.helper.project_path=lambda *args:self.project
        self.assertEqual(sync.registered(self.hub),{});self.assertEqual(sync.task_projects(self.hub,self.config),{'demo':self.project});self.assertEqual(self.row()['task_id'],TID);self.assertEqual([row['task_id'] for row in sync.inventory(self.hub)],[TID])
    def test_archive_expected_group_comes_from_verified_receipt(self):
        a=self.authority();self.config['projects']['demo']['archive']={'journal':'historic'};self.save()
        archive_group=str(uuid.uuid4());self.native.lists[0]['group_id']=archive_group;self.native.groups=[dict(id=archive_group,name='Архив',account_id=ACCOUNT)]
        self.helper.archive_group=lambda *args:archive_group
        result=a.prepare_pull(sync,self.hub,self.config,native=self.native)
        self.assertFalse(result['stop']);self.assertFalse(result.get('cancellation_disabled',False));self.assertEqual(result['items'],[])
    def test_unchecked_done_without_saved_status_falls_back_to_ready(self):
        self.authority();self.files['future'].write_text(self.files['future'].read_text().replace('Status: ready','Status: done'))
        result=self.pull();self.assertTrue(result['ok'],result);self.assertEqual(self.row()['status'],'ready')
    def test_unchecked_done_reopens_saved_idea_status(self):
        self.authority();self.files['future'].write_text(self.files['future'].read_text().replace('Status: ready','Status: done'))
        self.config['projects']['demo']['tasks'][TID]['last_open_status']='idea';self.save()
        result=self.pull();self.assertTrue(result['ok'],result);self.assertEqual(self.row()['status'],'idea')
    def test_missing_completed_uuid_is_cancelled_with_original_history(self):
        self.authority();self.files['future'].write_text(self.files['future'].read_text().replace('Status: ready','Status: done'));self.native.rows.pop(RID)
        result=self.pull();self.assertTrue(result['ok'],result);self.assertEqual(self.row()['status'],'dropped')
        plan=next((self.hub/'ai/reminders-external-retirements').glob('*/plan.json'))
        self.assertIn('Status: done',json.loads(plan.read_text())['projects']['demo']['before_texts']['future'])
    def test_real_activation_pull_gateway_and_next_pull_share_one_policy(self):
        self.assertTrue(hasattr(sync,'authority_module'),'Нет единого исполнителя входящей сверки')
        self.config.pop('task_authority');self.save()
        helper=sync.authority_module().archive_module()
        plan=helper.preview(self.hub,'Главная копия в приложении; удаление отменяет с историей.',self.native)
        helper.apply(plan['plan'],plan['sha256'],True,self.native)
        self.config=sync.load_config(self.hub)
        result=self.pull();self.assertTrue(result['ok'],result);self.assertEqual(self.row()['planned_day'],'2026-11-02');self.assertEqual(self.native.writes,[])
        self.native.rows[RID]['due']='2026-11-04T11:00:00+03:00'
        def explicit_update(remote,fields):
            self.assertEqual(remote['version'],self.native.rows[RID]['version'])
            self.native.writes.append(copy.deepcopy(fields));self.native.rows[RID].update(fields,version=remote['version']+1)
        self.native.update=explicit_update
        before=self.files['future'].read_text();desired=before.replace('Из приложения','Правка через Хаб')
        sync.gateway_module().write_from_text(sync.parser_for(self.hub),self.hub,'demo','future',sync.hashlib.sha256(before.encode()).hexdigest(),desired,native=self.native)
        self.assertEqual(self.native.writes,[{'title':'Правка через Хаб'}]);self.assertEqual(self.row()['planned_day'],'2026-11-04')
        self.config=sync.load_config(self.hub);result=self.pull();self.assertTrue(result['ok'],result)
        self.assertEqual(self.native.writes,[{'title':'Правка через Хаб'}]);self.assertEqual(self.row()['title'],'Правка через Хаб')
    def real_archived_fixture(self):
        self.assertTrue(hasattr(sync,'authority_module'),'Нет единого исполнителя входящей сверки')
        with patch.dict(os.environ,ARCHIVE_SOURCE=str(SCRIPTS/'reminders_archive.py')):
            spec=importlib.util.spec_from_file_location('core_archive_fixture',ROOT/'modules/planning/tests/test_reminders_archive.py')
            fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
        f=fixture.ArchiveTests('runTest');f.setUp();self.addCleanup(f.doCleanups)
        for source in SCRIPTS.glob('*.py'):shutil.copyfile(source,f.h/'scripts'/source.name)
        shutil.copyfile(ROOT/'modules/tasks/scripts/task_records.py',f.h/'scripts/task_records.py')
        allow=f.h/'ai/reminders-allowlist.json';allow.write_text(json.dumps({'names':['Демо']}));f.c['allowlist_file']=str(allow);f.savec(f.c)
        path,token=f.plan();f.run_apply(path,token);historical=path.read_bytes()
        helper=sync.authority_module().archive_module();activation=helper.preview(f.h,'Главная копия в приложении; удаление отменяет с историей.',f.native)
        helper.apply(activation['plan'],activation['sha256'],True,f.native)
        f.native.children=lambda binding: [copy.deepcopy(r) for r in f.native.rows.values() if r['list_id']==binding['list_id']]
        return f,path,historical
    def test_real_adopted_archive_pull_preserves_historical_receipt(self):
        f,path,historical=self.real_archived_fixture()
        f.native.rows[f.rid].update(title='Правка в архиве',due='2026-11-02',completed=False,version='v3')
        f.native.children=lambda binding: [copy.deepcopy(r) for r in f.native.rows.values() if r['list_id']==binding['list_id']]
        before=len(f.native.calls);result=sync.sync(f.h,f.current(),True,native=f.native,reconcile=False)
        self.assertTrue(result['ok'],result);row=sync.HubProject(f.h,'demo').rows()[f.tid]
        self.assertEqual((row['title'],row['planned_day'],row['status']),('Правка в архиве','2026-11-02','ready'))
        self.assertEqual(sync.registered(f.h),{});self.assertEqual(path.read_bytes(),historical)
        self.assertFalse(any(name.startswith('manage') for name,args in f.native.calls[before:]))
    def test_real_adopted_archive_missing_uuid_gets_retirement_receipt(self):
        f,path,historical=self.real_archived_fixture();f.native.rows.pop(f.rid)
        result=sync.sync(f.h,f.current(),True,native=f.native,reconcile=False)
        self.assertTrue(result['ok'],result);self.assertEqual(sync.HubProject(f.h,'demo').rows()[f.tid]['status'],'dropped')
        self.assertIn('external_retirement',f.current()['projects']['demo']['tasks'][f.tid]);self.assertEqual(path.read_bytes(),historical)
    def lone_sync(self):
        folder=self.hub/'single-script';folder.mkdir(exist_ok=True);path=folder/'reminders_sync.py';shutil.copyfile(SCRIPTS/'reminders_sync.py',path)
        spec=importlib.util.spec_from_file_location('core_lone_sync',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module
    def test_legacy_source_without_authority_remains_usable(self):
        module=self.lone_sync();self.config.pop('task_authority');self.save()
        link=self.config['projects']['demo']['tasks'][TID];link.update(last_hub_title='Локальный текст',last_remote_title='Локальный текст',last_hub_day='2026-10-30',last_remote_day='2026-10-30');self.save()
        with patch.dict(sys.modules):
            sys.modules.pop('hub_reminders_authority',None)
            result=module.sync(self.hub,self.config,False,native=self.native,reconcile=False)
        self.assertTrue(result['ok'],result)
        import contextlib,io
        output=io.StringIO()
        with patch.dict(sys.modules),patch.object(module,'Native',return_value=self.native),patch.object(sys,'argv',['reminders_sync.py','sync','--hub',str(self.hub)]),contextlib.redirect_stdout(output):
            sys.modules.pop('hub_reminders_authority',None)
            status=module.main()
        self.assertEqual(status,0,output.getvalue());self.assertTrue(json.loads(output.getvalue())['ok'])
    def test_new_mode_without_authority_refuses_before_native(self):
        module=self.lone_sync()
        with patch.dict(sys.modules),patch.object(self.native,'call',side_effect=AssertionError('native read too early')):
            sys.modules.pop('hub_reminders_authority',None)
            with self.assertRaisesRegex(ValueError,'authority_support_missing'):module.sync(self.hub,self.config,True,native=self.native,reconcile=False)
    def test_direct_notes_api_in_new_mode_refuses_before_native(self):
        self.authority();before=self.files['future'].read_text()
        with patch.object(self.native,'call',side_effect=AssertionError('native read too early')):
            with self.assertRaisesRegex(ValueError,'authority_explicit_task_gateway_required'):sync.sync_notes(self.hub,self.config,True,native=self.native)
        self.assertEqual(self.files['future'].read_text(),before);self.assertEqual(self.native.writes,[])
    def test_pinned_group_name_change_is_not_deletion(self):
        a=self.authority();self.native.rows.pop(RID);self.native.groups[0]['name']='Чужая группа'
        pin=self.hub/'ai/group-pins.json';pin.write_text(json.dumps({'groups':{GROUP:'Группа'}}));self.config['structure']={'group_ids_allowlist_file':str(pin)};self.save()
        result=a.prepare_pull(sync,self.hub,self.config,True,native=self.native)
        self.assertEqual(result['blocked_projects'],{'demo'});self.assertIn('group_name',result['items'][0]['error'])
    def add_second_project(self):
        lid,pid,rid=[str(uuid.UUID(int=i)) for i in (7,8,9)];tid='TASK-other-20261027-001';project=self.hub/'projects/other';(project/'ai').mkdir(parents=True)
        for kind,path in self.files.items():(project/'ai'/sync.NAMES[kind]).write_text(path.read_text().replace(TID,tid))
        registry=self.hub/'ai/project-registry.md';registry.write_text(registry.read_text()+f'\n## other\nName: Другой\nStatus: active\nPath: {project}\n')
        self.native.lists.append(dict(id=lid,name='Второй',account_id=ACCOUNT,group_id=GROUP))
        self.native.rows[pid]=dict(self.native.rows[PID],id=pid,list='Второй',list_id=lid)
        self.native.rows[rid]=dict(self.native.rows[RID],id=rid,list='Второй',list_id=lid,parent_id=pid,title='Другой из приложения')
        self.config['projects']['other']=dict(self.config['projects']['demo'],list_id=lid,list_name='Второй',parent_id=pid,tasks={tid:dict(reminder_id=rid)})
        self.allow.write_text(json.dumps({'names':['Работа','Второй']}));self.save()
        return tid,project
    def test_missing_list_blocks_deletion_but_pulls_other_project(self):
        self.authority();tid,project=self.add_second_project();self.native.lists=[row for row in self.native.lists if row['id']!=LID];self.native.rows.pop(RID)
        result=self.pull();self.assertFalse(result['ok'],result);self.assertFalse(result['complete']);self.assertEqual(self.row()['status'],'ready')
        self.assertEqual(sync.HubProject(self.hub,'other').rows()[tid]['planned_day'],'2026-11-02');self.assertEqual(self.native.writes,[])
        self.assertFalse((self.hub/'ai/reminders-external-retirements').exists());self.assertTrue(any(i.get('project')=='demo' and 'expected_list' in i.get('error','') for i in result['items']))
    def test_wrong_account_blocks_owner_but_pulls_other_project(self):
        self.authority();tid,project=self.add_second_project();self.native.lists[0]['account_id']=str(uuid.uuid4());before=self.files['future'].read_text()
        result=self.pull();self.assertFalse(result['ok'],result);self.assertFalse(result['complete']);self.assertEqual(self.files['future'].read_text(),before)
        self.assertEqual(sync.HubProject(self.hub,'other').rows()[tid]['planned_day'],'2026-11-02');self.assertEqual(self.native.writes,[])
        self.assertTrue(any(i.get('project')=='demo' and 'account' in i.get('error','') for i in result['items']))
    def test_pending_explicit_write_stops_pull_before_projection(self):
        self.authority();before=self.files['future'].read_text()
        with patch.object(sync,'gateway_module',create=True,return_value=types.SimpleNamespace(pending_projects=lambda h:{'demo'})):
            result=self.pull()
        self.assertFalse(result['ok'],result);self.assertEqual(result['items'][0]['error'],'task_write_recovery_required');self.assertEqual(self.files['future'].read_text(),before)
    def test_lock_is_shared_reentrant_and_other_process_is_blocked(self):
        a=self.authority();cancel=sync.cancellation_module()
        self.assertIs(a,cancel.sync.authority_module())
        with a.locked(self.hub):
            with cancel.locked(self.hub):
                import fcntl
                with (self.hub/'ai/.reminders-sync.lock').open('a') as stream:
                    with self.assertRaises(BlockingIOError):fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
                import subprocess
                code="import fcntl,sys\nf=open(sys.argv[1],'a')\ntry: fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);print('entered')\nexcept BlockingIOError: print('blocked')\n"
                child=subprocess.run([sys.executable,'-c',code,str(self.hub/'ai/.reminders-sync.lock')],capture_output=True,text=True,timeout=10)
                self.assertEqual(child.returncode,0,child.stderr);self.assertEqual(child.stdout.strip(),'blocked')

if __name__=='__main__':unittest.main()
