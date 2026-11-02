"""Только искусственные проекты и память вместо приложения."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = Path(os.environ.get('REASSIGNMENT_SOURCE', str(ROOT/'modules/planning/scripts/reminders_task_reassignment.py')))
def load():
    if not SCRIPT.exists(): return None
    s=importlib.util.spec_from_file_location('reassignment_subject',SCRIPT)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load()
_cleanup_spec=importlib.util.spec_from_file_location('cleanup_test_fixture',SCRIPT.parent/'reminders_old_list_cleanup.py')
_cleanup=importlib.util.module_from_spec(_cleanup_spec);_cleanup_spec.loader.exec_module(_cleanup)
RID,OLD,DEST,ACCOUNT,GROUP,SOURCE,PARENT,NEIGHBOR=[str(uuid.UUID(int=i)) for i in range(1,9)]
TID='TASK-source-20261027-001'
class Native:
    def __init__(self):
        self.meta=dict(lists=[dict(id=x,name=n,account_id=ACCOUNT,group_id=GROUP,shared=False) for x,n in [(OLD,'Работа'),(DEST,'Общие задачи'),(SOURCE,'Аналитика')]],groups=[dict(id=GROUP,name='Группа',account_id=ACCOUNT)])
        self.rows={RID:dict(id=RID,title='Задача',notes='',due='2026-12-31T11:00:00+03:00',repeat={'frequency':'weekly','interval':2},completed=False,version=1,list='Работа',list_id=OLD,parent_id=None,subtasks=[]),NEIGHBOR:dict(id=NEIGHBOR,title='Сосед',notes='Пользователь',version=1,list='Работа',list_id=OLD,parent_id=None,completed=False,subtasks=[])}
        self.writes=[];self.fail=None
    def call(self,t,a):
        if t=='list_lists':return copy.deepcopy(self.meta)
        if t=='find_reminders':
            rows=[copy.deepcopy(x) for x in self.rows.values() if x['list_id']==a['list']];return dict(reminders=rows,count=len(rows))
        if t=='get_reminder':return copy.deepcopy(self.rows[a['id']])
        self.writes.append((t,copy.deepcopy(a)));assert t=='update_reminder'
        r=self.rows[a['id']];assert r['version']==a['version'];d=next(x for x in self.meta['lists'] if x['id']==a['list'])
        r.update(list_id=a['list'],list=d['name'],parent_id=a['parent_id'],notes=a['notes'],version=r['version']+1)
        if self.fail:self.fail=None;raise TimeoutError('unknown_native_result')
        return copy.deepcopy(r)
class ReassignmentTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(m is not None and callable(getattr(m,'preview',None)),'Отсутствует исполнитель переназначения')
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.hub=Path(self.temp.name).resolve()
        (self.hub/'ai').mkdir();(self.hub/'scripts').mkdir();shutil.copy(ROOT/'modules/tasks/scripts/task_records.py',self.hub/'scripts/task_records.py')
        registry='';self.paths={}
        for pid,name in [('source','Аналитика'),('dest','Общие задачи')]:
            p=self.hub/'projects'/pid/'ai';p.mkdir(parents=True);registry+=f'## {pid}\nName: {name}\nStatus: active\nPath: {p.parent}\n'
            self.paths[pid]={k:p/n for k,n in m.sync.NAMES.items()}
            for k,f in self.paths[pid].items():f.write_text('# Текущая задача\nStatus: empty\n' if k=='current' else '# Задачи\n')
        (self.hub/'ai/project-registry.md').write_text(registry)
        self.paths['source']['future'].write_text(f'# Будущие задачи\n\n### {TID} — Задача\nStatus: ready\nProject: source\nDue: 2026-12-31\nЗапланировано: 2026-10-29.\n\nКонтекст пользователя.\n')
        allow=self.hub/'ai/reminders-allowlist.json';allow.write_text(json.dumps({'names':['Работа','Общие задачи','Аналитика']}))
        self.config=dict(version=1,binary='/private/tmp/never-run',allowlist_file=str(allow),projects={p:dict(layout='project_list',parent_id=None,list_id=l,list_name=n,account_id=ACCOUNT,native_group_id=GROUP,tasks={},history={}) for p,l,n in [('source',SOURCE,'Аналитика'),('dest',DEST,'Общие задачи')]},structure={'list_roles':{DEST:{'kind':'project','project_id':'dest'},SOURCE:{'kind':'project','project_id':'source'},OLD:{'kind':'group','group_id':'work'}},'projects':{'source':{'list_id':SOURCE,'group':'work'},'dest':{'list_id':DEST,'group':'work'}},'native_groups':{GROUP:'work'}})
        self.config['projects']['source']['tasks'][TID]={'reminder_id':RID}
        self.config['projects']['dest']['retired_parent']={'id':PARENT,'list_id':OLD,'snapshot':{'id':PARENT,'list_id':OLD,'list':'Работа','parent_id':None,'subtasks':[],'version':1}}
        self.native=Native();self.native.rows[PARENT]=copy.deepcopy(self.config['projects']['dest']['retired_parent']['snapshot'])
        self.native.rows[PARENT].update(title='Старый родитель',completed=False,notes='')
        self.config['projects']['dest']['retired_parent']['snapshot']=copy.deepcopy(self.native.rows[PARENT])
        self.native.rows[RID]['notes']='Хаб: '+m.sync.compact_code('source',TID)
        self.target=dict(source_project='source',task_id=TID,reminder_id=RID,destination_project='dest')
        self.intent=dict(confirmed=True,statement='Перенести существующую задачу в Общие задачи',target=copy.deepcopy(self.target));self.save()
    def save(self):(self.hub/'ai/reminders-sync.json').write_text(json.dumps(self.config,ensure_ascii=False))
    def read(self):return json.loads((self.hub/'ai/reminders-sync.json').read_text())
    def prepare(self):return m.preview(self.hub,self.target,self.intent,self.native)
    def apply(self,p):return m.apply(p['plan'],p['sha256'],True,self.native)
    def finish(self,p):
        try:return self.apply(p)
        except Exception as error:self.fail('Ожидалось завершение: '+str(error))
    def test_complete_preserves_block_fields_neighbors_uuid_and_history(self):
        before=copy.deepcopy(self.native.rows);self.config['projects']['source']['history']['unrelated']={'original_id':NEIGHBOR,'task_id':'other','project_id':'source'};self.save()
        p=self.prepare();self.assertEqual(self.native.writes,[]);plan=json.loads(Path(p['plan']).read_text());new=plan['new_task_id']
        self.assertTrue(m.sync.HubProject(self.hub,'dest').parser._valid_task_id('dest',new))
        self.assertEqual(self.finish(p)['phase'],'complete');c=self.read()
        self.assertNotIn(TID,c['projects']['source']['tasks']);self.assertEqual(c['projects']['dest']['tasks'][new]['reminder_id'],RID)
        self.assertEqual(c['projects']['source']['history'],self.config['projects']['source']['history']);self.assertEqual(c['projects']['dest']['history'],{})
        self.assertEqual(c['projects']['dest']['retired_parent'],self.config['projects']['dest']['retired_parent'])
        row=m.sync.HubProject(self.hub,'dest').rows()[new];self.assertEqual((row['due'],row['planned_day'],row['status']),('2026-12-31','2026-10-29','ready'))
        self.assertIn('Контекст пользователя.',self.paths['dest']['future'].read_text());self.assertNotIn(TID,self.paths['source']['future'].read_text())
        for key,value in before[RID].items():
            if key not in ('list','list_id','parent_id','version','notes'):self.assertEqual(self.native.rows[RID][key],value)
        self.assertEqual(self.native.rows[NEIGHBOR],before[NEIGHBOR]);self.assertEqual(self.native.rows[PARENT],before[PARENT])
        self.assertEqual(m.sync.creation_identity(self.native.rows[RID],m.sync.compact_identities(c)),('dest',new));self.assertEqual(len(self.native.writes),1)
        self.apply(p);self.assertEqual(len(self.native.writes),1);self.assertEqual(m.pending_projects(self.hub,c),set())
    def test_user_text_is_preserved_and_only_owned_marker_replaced(self):
        self.native.rows[RID]['notes']='Текст врача\n'+self.native.rows[RID]['notes']+'\nАналитика'
        p=self.prepare();self.apply(p);notes=self.native.rows[RID]['notes'];self.assertIn('Текст врача',notes);self.assertTrue(notes.endswith('\nАналитика'));self.assertTrue(notes.startswith('Общие задачи\n'))
    def test_verified_cleanup_refuses_removed_legacy_reassignment_without_effect(self):
        fixture=Path(__file__).with_name('test_reminders_old_list_cleanup.py')
        fs=importlib.util.spec_from_file_location('cleanup_fixture_builder',fixture);fm=importlib.util.module_from_spec(fs);fs.loader.exec_module(fm)
        reference,parent_id,_=fm.OldListCleanupContractTests.completed_receipt(self.hub)
        self.native.meta['lists']=[row for row in self.native.meta['lists'] if row['id']!=OLD]
        self.native.rows.pop(PARENT)
        self.config['structure']['list_roles'].pop(OLD)
        self.config['projects']['dest']['retired_parent']['id']=parent_id
        self.config['projects']['dest']['retired_parent']['snapshot'].update(id=parent_id,list_id=OLD)
        self.config['projects']['dest']['retired_parent_cleanup']=reference;self.save()
        with self.assertRaisesRegex(ValueError,'reassignment_retired_source_removed_by_cleanup'):self.prepare()
        self.assertEqual(self.native.writes,[])
    def test_forged_cleanup_receipt_rejects_reassignment_before_update(self):
        fixture=Path(__file__).with_name('test_reminders_old_list_cleanup.py')
        fs=importlib.util.spec_from_file_location('cleanup_fixture_builder_bad',fixture);fm=importlib.util.module_from_spec(fs);fs.loader.exec_module(fm)
        reference,parent_id,_=fm.OldListCleanupContractTests.completed_receipt(self.hub)
        self.native.meta['lists']=[row for row in self.native.meta['lists'] if row['id']!=OLD]
        self.native.rows.pop(PARENT)
        self.config['projects']['dest']['retired_parent']['id']=parent_id
        self.config['projects']['dest']['retired_parent']['snapshot'].update(id=parent_id,list_id=OLD)
        self.config['structure']['list_roles'].pop(OLD);reference['sha256']='0'*64
        self.config['projects']['dest']['retired_parent_cleanup']=reference;self.save()
        with self.assertRaisesRegex(ValueError,'cleanup_receipt_sha256_mismatch'):self.prepare()
        self.assertEqual(self.native.writes,[])
    def test_guards_reject_before_effect(self):
        for kind in ('intent','uuid','marker','ownership','calendar','dependency','history','pending','placement','children','account','shared','role','recurrence','state','duplicate_binding','unregistered'):
            with self.subTest(kind=kind):
                self.setUp()
                if kind=='intent':self.intent['confirmed']=False
                elif kind=='uuid':self.target['reminder_id']=NEIGHBOR;self.intent['target']=copy.deepcopy(self.target)
                elif kind=='marker':self.native.rows[RID]['notes']='Хаб: 000000000000'
                elif kind=='ownership':self.config['projects']['source']['tasks'][TID]['notes_owner']={'label':'Чужое','snapshot':'Чужое'}
                elif kind in ('calendar','dependency'):self.paths['source']['future'].write_text(self.paths['source']['future'].read_text()+('\nCalendar event: x\n' if kind=='calendar' else '\nDepends on: TASK-source-20261027-002\n'))
                elif kind=='history':self.config['projects']['source']['history']['x']={'original_id':RID,'task_id':TID,'project_id':'source'}
                elif kind=='pending':self.config['projects']['source']['tasks'][TID]['pending_notes']={}
                elif kind=='placement':self.native.rows[RID]['list_id']=SOURCE;self.native.rows[RID]['list']='Аналитика'
                elif kind=='children':self.native.rows[RID]['subtasks']=[NEIGHBOR]
                elif kind=='account':self.native.meta['lists'][1]['account_id']=NEIGHBOR
                elif kind=='shared':self.native.meta['lists'][1]['shared']=True
                elif kind=='role':self.config['structure']['list_roles'][DEST]['project_id']='source'
                elif kind=='recurrence':self.native.rows[RID]['repeat']={'frequency':'unknown'}
                elif kind=='state':self.paths['source']['future'].write_text(self.paths['source']['future'].read_text().replace('Status: ready','Status: done'))
                elif kind=='duplicate_binding':self.config['projects']['dest']['tasks']['TASK-dest-20261027-002']={'reminder_id':RID}
                else:self.target['destination_project']='missing';self.intent['target']=copy.deepcopy(self.target)
                self.save()
                with self.assertRaises((ValueError,KeyError)):self.prepare()
                self.assertEqual(self.native.writes,[])
    def test_stale_all_snapshots_stop_before_update(self):
        for kind in ('canonical','config','permission','registry','metadata','neighbor','retired'):
            with self.subTest(kind=kind):
                self.setUp();p=self.prepare()
                if kind=='canonical':self.paths['dest']['paused'].write_text('Чужая правка')
                elif kind=='config':self.config['extra']=1;self.save()
                elif kind=='permission':(self.hub/'ai/reminders-allowlist.json').write_text('{}')
                elif kind=='registry':q=self.hub/'ai/project-registry.md';q.write_text(q.read_text()+'\n')
                elif kind=='metadata':self.native.meta['lists'][1]['group_id']=NEIGHBOR
                elif kind=='neighbor':self.native.rows[NEIGHBOR]['notes']='Чужая правка'
                else:self.native.rows[PARENT]['version']=2
                with self.assertRaises((ValueError,RuntimeError)):self.apply(p)
                self.assertEqual(self.native.writes,[])
    def test_unknown_native_result_resumes_exact_owned_after_once(self):
        p=self.prepare();self.native.fail=True
        with self.assertRaises(TimeoutError):self.apply(p)
        self.assertEqual(m.pending_projects(self.hub,self.read()),{'source','dest'});self.assertEqual(self.finish(p)['phase'],'complete');self.assertEqual(len(self.native.writes),1)
    def test_unknown_native_result_rejects_foreign_edit(self):
        p=self.prepare();self.native.fail=True
        with self.assertRaises(TimeoutError):self.apply(p)
        self.native.rows[RID]['title']='Чужая правка'
        with self.assertRaisesRegex(ValueError,'remote'):self.apply(p)
        self.assertEqual(len(self.native.writes),1);self.assertEqual(m.pending_projects(self.hub,self.read()),{'source','dest'})
    def test_every_write_window_is_resumable(self):
        for window,timing in [(w,t) for w in range(1,12) for t in ('before','after')]:
            with self.subTest(window=window,timing=timing):
                self.setUp();p=self.prepare();real=m.pl.durable;count=[0]
                def fail(path,data,*args,**kw):
                    count[0]+=1
                    if count[0]==window and timing=='before':raise TimeoutError('write_window')
                    real(path,data,*args,**kw)
                    if count[0]==window and timing=='after':raise TimeoutError('write_window')
                with patch.object(m.pl,'durable',side_effect=fail):
                    try:self.apply(p)
                    except TimeoutError:pass
                self.assertGreaterEqual(count[0],window)
                self.assertEqual(self.finish(p)['phase'],'complete');self.assertEqual(len(self.native.writes),1)
                self.assertNotIn(TID,self.paths['source']['future'].read_text())
                self.assertEqual(sum(t.get('reminder_id')==RID for b in self.read()['projects'].values() for t in b['tasks'].values()),1)
    def test_canonical_write_windows_resume_and_conflict_keeps_neighbor(self):
        for pid in ('dest','source'):
            with self.subTest(pid=pid):
                self.setUp();p=self.prepare();original=m.sync.HubProject.save
                def fail(hp,after,**kw):
                    original(hp,after,**kw)
                    if hp.pid==pid:raise TimeoutError('canonical_window')
                with patch.object(m.sync.HubProject,'save',new=fail):
                    with self.assertRaises(TimeoutError):self.apply(p)
                self.assertEqual(self.finish(p)['phase'],'complete');self.assertEqual(len(self.native.writes),1)
        self.setUp();p=self.prepare()
        with patch.object(m.sync.HubProject,'save',side_effect=TimeoutError('before_canonical')):
            with self.assertRaises(TimeoutError):self.apply(p)
        f=self.paths['dest']['future'];f.write_text(f.read_text()+'\nСоседская правка.\n');before=f.read_bytes()
        with self.assertRaisesRegex(ValueError,'canonical'):self.apply(p)
        self.assertEqual(f.read_bytes(),before);self.assertEqual(len(self.native.writes),1)
    def test_pending_survives_lost_explicit_marker_and_blocks_existing_entrypoints(self):
        p=self.prepare();self.native.fail=True
        with self.assertRaises(TimeoutError):self.apply(p)
        c=self.read();c.pop('project_list_migrations_pending');self.assertEqual(m.pending_projects(self.hub,c),{'source','dest'})
        self.assertEqual(m.sync.migration_pending(self.hub,c),{'source','dest'})
        for result in (m.sync.sync(self.hub,c,True,native=self.native),m.sync.sync_notes(self.hub,c,True,native=self.native)):
            self.assertFalse(result['ok']);self.assertEqual(result['items'][0]['error'],'migration_recovery_required')
    def test_plan_digest_approval_and_state_tampering_rejected(self):
        p=self.prepare()
        with self.assertRaisesRegex(ValueError,'approval'):m.apply(p['plan'],p['sha256'],False,self.native)
        with self.assertRaisesRegex(ValueError,'checksum'):m.apply(p['plan'],'wrong',True,self.native)
        s=Path(p['plan']).with_name('state.json');v=json.loads(s.read_text());v['phase']='native';s.write_text(json.dumps(v))
        with self.assertRaisesRegex(ValueError,'state'):self.apply(p)
        self.assertEqual(self.native.writes,[])
    def test_omitted_nil_parent_and_native_string_versions(self):
        self.native.rows[RID].pop('parent_id');self.native.rows[RID]['version']='before'
        original=self.native.call
        def call(tool,args):
            if tool!='update_reminder':return original(tool,args)
            self.native.writes.append((tool,copy.deepcopy(args)));row=self.native.rows[RID]
            self.assertEqual(args['version'],'before');self.assertIsNone(args['parent_id'])
            row.update(list_id=DEST,list='Общие задачи',notes=args['notes'],version='after');row.pop('parent_id',None)
            return copy.deepcopy(row)
        self.native.call=call;p=self.prepare();self.assertEqual(self.finish(p)['phase'],'complete');self.assertEqual(len(self.native.writes),1)
    def test_byte_cas_detects_newline_only_edits_in_all_six_files_and_config(self):
        for selected in [(p,k) for p in ('source','dest') for k in m.sync.NAMES]+[('config',None)]:
            with self.subTest(selected=selected):
                self.setUp();p=self.prepare();pid,kind=selected
                f=self.hub/'ai/reminders-sync.json' if pid=='config' else self.paths[pid][kind]
                if pid=='config':f.write_bytes(f.read_bytes()+b'\r\n')
                else:f.write_bytes(f.read_bytes().replace(b'\n',b'\r\n'))
                before=f.read_bytes()
                with self.assertRaisesRegex(ValueError,'snapshot|canonical'):self.apply(p)
                self.assertEqual(f.read_bytes(),before);self.assertEqual(self.native.writes,[])
    def test_owned_label_migration_keeps_user_text_and_header_only_id_change(self):
        notes='Аналитика\nТекст врача\n'+self.native.rows[RID]['notes']
        self.native.rows[RID]['notes']=notes;self.config['projects']['source']['tasks'][TID]['notes_owner']={'snapshot':notes,'label':'Аналитика'};self.save()
        f=self.paths['source']['future'];f.write_text(f.read_text()+'\nДословное упоминание проекта.\n')
        p=self.prepare();self.apply(p)
        self.assertEqual(self.native.rows[RID]['notes'].count('Аналитика'),0);self.assertIn('Текст врача',self.native.rows[RID]['notes'])
        self.assertIn('Дословное упоминание проекта.',self.paths['dest']['future'].read_text())
    def test_legacy_line_owner_is_rejected_before_plan_creation(self):
        notes='Хаб: '+m.sync.compact_code('source',TID)+'\nКрайний срок: 31.12.2026'
        self.native.rows[RID]['notes']=notes
        start=notes.index('Крайний срок: ');end=len(notes)
        self.config['projects']['source']['tasks'][TID]['notes_owner']={
            'line':notes[start:end],'start':start,'end':end,'prefix':'','snapshot':notes,
        }
        self.save()
        with self.assertRaisesRegex(ValueError,'legacy_notes_ownership_unsupported'):
            self.prepare()
        self.assertEqual(self.native.rows[RID]['notes'],notes)
        self.assertFalse((self.hub/'ai/reminders-task-reassignments').exists())
        self.assertEqual(self.native.writes,[])
    def test_unknown_binding_metadata_and_external_config_links_fail_closed(self):
        for mode in ('link','config_reference','canonical_field'):
            with self.subTest(mode=mode):
                self.setUp()
                if mode=='link':self.config['projects']['source']['tasks'][TID]['calendar_event_id']='external'
                elif mode=='config_reference':self.config['calendar_tasks']={TID:'external'}
                else:
                    f=self.paths['source']['future'];f.write_text(f.read_text()+'\nUnknown-field: external\n')
                self.save()
                with self.assertRaisesRegex(ValueError,'unsupported|unknown'):self.prepare()
                self.assertEqual(self.native.writes,[])
    def test_config_changes_during_native_preflight_never_overwritten(self):
        p=self.prepare();original=self.native.call;calls=[0]
        def call(tool,args):
            result=original(tool,args)
            if tool=='list_lists':
                calls[0]+=1
                if calls[0]==1:
                    c=self.read();c['foreign']='keep';(self.hub/'ai/reminders-sync.json').write_text(json.dumps(c))
            return result
        self.native.call=call
        with self.assertRaisesRegex(ValueError,'config'):self.apply(p)
        self.assertEqual(self.read()['foreign'],'keep');self.assertEqual(self.native.writes,[])
    def test_production_omitted_shared_flag_and_reject_non_boolean_claims(self):
        for row in self.native.meta['lists']:row.pop('shared')
        p=self.prepare();self.assertEqual(self.finish(p)['phase'],'complete')
        for invalid in (None,0,'false',True):
            with self.subTest(invalid=invalid):
                self.setUp();self.native.meta['lists'][1]['shared']=invalid
                with self.assertRaisesRegex(ValueError,'sharing'):self.prepare()
                self.assertEqual(self.native.writes,[])
    def test_calendar_schedule_and_link_require_separate_decision(self):
        for extra in ('Запланировано: 2026-10-29 10:00-11:00.','Событие: calendar/event · синхронизировано: 2026-11-01 10:00-11:00'):
            with self.subTest(extra=extra):
                self.setUp();f=self.paths['source']['future'];f.write_text(f.read_text()+'\n'+extra+'\n')
                with self.assertRaisesRegex(ValueError,'reference'):self.prepare()
                self.assertEqual(self.native.writes,[])
    def test_other_approved_journal_blocks_before_native_effect(self):
        p=self.prepare();plan=json.loads(Path(p['plan']).read_text());operation=str(uuid.uuid4());plan['operation']=operation
        folder=Path(p['plan']).parent.parent/operation;folder.mkdir();raw=m.pl.encoded(plan);(folder/'plan.json').write_text(raw)
        (folder/'state.json').write_text(m.pl.encoded(dict(sha256=m.pl.sha(raw),phase='intent',approved=True)))
        with self.assertRaisesRegex(ValueError,'pending'):self.apply(p)
        self.assertEqual(self.native.writes,[])
    def test_final_configuration_cas_and_receipt_are_required(self):
        p=self.prepare();original=m.pl.durable
        def interfere(path,data,*args,**kw):
            original(path,data,*args,**kw)
            if Path(path).name=='state.json' and json.loads(data).get('phase')=='verified':
                c=self.read();c['foreign']='keep';(self.hub/'ai/reminders-sync.json').write_text(json.dumps(c))
        with patch.object(m.pl,'durable',side_effect=interfere):
            with self.assertRaisesRegex(ValueError,'config'):self.apply(p)
        self.assertEqual(self.read()['foreign'],'keep');self.assertEqual(len(self.native.writes),1)
        self.setUp();p=self.prepare();receipt=Path(p['plan']).with_name('receipt.json');receipt.write_text('{}')
        with self.assertRaisesRegex(ValueError,'receipt'):self.apply(p)
        self.assertEqual(m.pending_projects(self.hub,self.read()),{'source','dest'})
    def test_actual_legacy_source_schema_and_date_only_plan_are_supported(self):
        binding=self.config['projects']['source']
        for key in ('layout','account_id','native_group_id'):binding.pop(key)
        binding.update(list_id=OLD,list_name='Работа',parent_id=SOURCE)
        link=binding['tasks'][TID];link.update(last_completed=False,last_hub_day='2026-11-01',last_remote_day='2026-11-01',last_hub_title='Задача',last_remote_title='Задача',notes_owner=None,repeating=True)
        f=self.paths['source']['future'];f.write_text(f.read_text().replace('Due: 2026-12-31\n','').replace('2026-10-29','2026-11-01'))
        self.config['project_list_migrations_completed']={'dest':'previous-completed-pin'};self.native.rows[RID].pop('completed');self.save();before=copy.deepcopy(self.native.rows[RID])
        try:p=self.prepare()
        except Exception as error:self.fail('Legacy source должен поддерживаться: '+str(error))
        self.assertEqual(self.finish(p)['phase'],'complete');row=m.sync.HubProject(self.hub,'dest').rows()[p['new_task_id']]
        self.assertEqual(row['planned_day'],'2026-11-01');self.assertIsNone(row['due']);self.assertIsNone(row['scheduled']);self.assertIsNone(row['event_link'])
        self.assertEqual(self.native.rows[RID]['due'],before['due']);self.assertEqual(self.native.rows[RID]['repeat'],before['repeat'])
        self.assertEqual(self.read()['project_list_migrations_completed'],self.config['project_list_migrations_completed'])
    def test_new_id_avoids_destination_canonical_binding_and_history(self):
        candidate=m.new_id(self.hub,'dest',self.config)
        self.config['projects']['dest']['tasks'][candidate]={'reminder_id':NEIGHBOR};self.save()
        p=self.prepare();self.assertNotEqual(p['new_task_id'],candidate);self.assertTrue(m.sync.HubProject(self.hub,'dest').parser._valid_task_id('dest',p['new_task_id']))
    def test_active_completion_contract_rejects_undefined_or_completed_values(self):
        for invalid in (None,0,'false',True):
            with self.subTest(invalid=invalid):
                self.setUp();self.native.rows[RID]['completed']=invalid
                with self.assertRaisesRegex(ValueError,'root'):self.prepare()
                self.assertEqual(self.native.writes,[])
    def test_task_id_references_inside_block_require_separate_decision(self):
        for reference in (TID,'TASK-other-20261027-002'):
            with self.subTest(reference=reference):
                self.setUp();f=self.paths['source']['future'];f.write_text(f.read_text()+'\nСвязь с '+reference+'.\n')
                with self.assertRaisesRegex(ValueError,'reference'):self.prepare()
                self.assertEqual(self.native.writes,[])
if __name__=='__main__':unittest.main()
