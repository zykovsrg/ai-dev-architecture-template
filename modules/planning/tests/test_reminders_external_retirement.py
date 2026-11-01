"""Изолированные проверки внешнего исключения; приложение не вызывается."""
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
SCRIPT = Path(os.environ.get('EXTERNAL_RETIREMENT_SOURCE', str(ROOT / 'modules/planning/scripts/reminders_external_retirement.py')))
def load():
    if not SCRIPT.exists(): return None
    spec = importlib.util.spec_from_file_location('external_retirement_subject', SCRIPT)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value
m = load()
RID, PID, LID, ACCOUNT, GROUP, NEW = [str(uuid.UUID(int=i)) for i in range(1,7)]
TID = 'TASK-demo-20261027-001'

class Native:
    def __init__(self):
        self.lists = [dict(id=LID,name='Работа',account_id=ACCOUNT,group_id=GROUP,shared=False)]
        self.groups = [dict(id=GROUP,name='Группа',account_id=ACCOUNT)]
        self.rows = {}; self.calls=[]; self.writes=[]; self.error=None; self.incomplete=False; self.fail_create=False
    def call(self,tool,args):
        self.calls.append((tool,copy.deepcopy(args)))
        if tool == 'list_lists':
            if self.error: return {'error':self.error}
            return dict(lists=copy.deepcopy(self.lists),groups=copy.deepcopy(self.groups),guarded_list_creation=True)
        if tool == 'find_reminders':
            rows=[copy.deepcopy(r) for r in self.rows.values() if r['list_id']==args['list']]
            return dict(reminders=rows,count=len(rows),has_more=self.incomplete)
        if tool == 'get_reminder': return copy.deepcopy(self.rows[args['id']])
        self.writes.append((tool,copy.deepcopy(args)))
        if tool == 'update_reminder':
            row=self.rows[args['id']];assert row['version']==args['version'];destination=next(r for r in self.lists if r['id']==args['list'])
            row.update(list_id=args['list'],list=destination['name'],parent_id=args.get('parent_id'),version=row['version']+1);return copy.deepcopy(row)
        if tool == 'manage_list':
            if args['action']=='create':
                assert args['expected_account_id']==ACCOUNT
                row=dict(id=NEW,name=args['list'],account_id=ACCOUNT,group_id=None,shared=False);self.lists.append(row)
                if self.fail_create: self.fail_create=False;raise TimeoutError('unknown_result')
            else:
                row=next(r for r in self.lists if r['id']==args['list']);assert row['group_id']==args['expected_group_id'];row['group_id']=args['group']
            return copy.deepcopy(row)
        raise AssertionError(tool)
    def get(self,rid,lid,*args): return self.call('get_reminder',{'id':rid})
    def children(self,b): return [copy.deepcopy(r) for r in self.rows.values() if r['list_id']==b['list_id'] and r.get('parent_id')==b.get('parent_id')]

class ExternalRetirementTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(m,'Отсутствует отдельный исполнитель внешнего исключения')
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.hub=Path(self.temp.name).resolve()
        (self.hub/'ai/project-cards').mkdir(parents=True);(self.hub/'scripts').mkdir();self.project=self.hub/'projects/demo';(self.project/'ai').mkdir(parents=True)
        shutil.copyfile(ROOT/'modules/tasks/scripts/task_records.py',self.hub/'scripts/task_records.py')
        (self.hub/'ai/project-registry.md').write_text(f'## demo\nName: Проект\nStatus: active\nPath: {self.project}\nCard: ai/project-cards/demo.md\n')
        (self.hub/'ai/project-cards/demo.md').write_text('Project ID: demo\nStatus: active\nprimary_archiproject: work\n')
        (self.hub/'ai/archiprojects.md').write_text('## work\n```yaml\nid: work\nkind: group\nname: Работа\nstatus: active\nparent:\n```\n')
        (self.hub/'ai/reminders-groups-allowlist.json').write_text(json.dumps({'names':['Группа']}))
        self.paths={k:self.project/'ai'/n for k,n in {'current':'current-task.md','future':'future-tasks.md','paused':'paused-tasks.md'}.items()}
        self.paths['current'].write_text('# Текущая задача\nStatus: empty\n');self.paths['paused'].write_text('# Пауза\n')
        self.paths['future'].write_text(f'# Будущие задачи\n\n### {TID} — Задача\nStatus: ready\nDue: 2026-12-31\n\nКонтекст.\n')
        self.allow=self.hub/'ai/reminders-allowlist.json';self.allow.write_text(json.dumps({'names':['Работа']}))
        self.config=dict(version=1,binary='/private/tmp/never-run',allowlist_file=str(self.allow),projects={'demo':dict(list_id=LID,list_name='Работа',parent_id=PID,tasks={TID:{'reminder_id':RID}},history={})},structure={'list_roles':{LID:{'kind':'group','group_id':'work'}},'projects':{'demo':{'list_id':LID,'group':'work'}},'native_groups':{GROUP:'work'},'groups_allowlist_file':str(self.hub/'ai/reminders-groups-allowlist.json')})
        self.save();self.native=Native();self.targets=[{'project_id':'demo','task_id':TID,'reminder_id':RID}]
        self.intent=dict(confirmed=True,statement='Удалил только эти задачи, они не нужны',targets=copy.deepcopy(self.targets))
    def save(self): (self.hub/'ai/reminders-sync.json').write_text(json.dumps(self.config,ensure_ascii=False))
    def read(self): return json.loads((self.hub/'ai/reminders-sync.json').read_text())
    def prepare(self): return m.preview(self.hub,self.targets,self.intent,self.native)
    def apply(self,p): return m.apply(p['plan'],p['sha256'],True,self.native)
    def verify(self):
        c=self.read();b=c['projects']['demo'];row=m.sync.HubProject(self.hub,'demo').rows()[TID]
        return m.verify_link(self.hub,row,b['tasks'][TID],b,self.native)
    def test_valid_retirement_preserves_link_history_and_due_without_native_write(self):
        p=self.prepare();self.apply(p)
        row=m.sync.HubProject(self.hub,'demo').rows()[TID]
        self.assertEqual(row['status'],'dropped');self.assertEqual(row['due'],'2026-12-31')
        link=self.read()['projects']['demo']['tasks'][TID]
        self.assertEqual(link['reminder_id'],RID);self.assertNotIn('cancellation',link);self.assertEqual(link['external_retirement']['kind'],'external_retirement')
        self.assertTrue(self.verify());self.assertEqual(self.native.writes,[])


    def test_intent_absence_and_exact_binding_guards(self):
        for kind in ('consent','target','binding','active','access','incomplete','foreign_list','count','list_uuid','parent_uuid','binding_scope'):
            with self.subTest(kind=kind):
                self.setUp()
                if kind=='consent':self.intent['confirmed']=False
                elif kind=='target':self.intent['targets']=[]
                elif kind=='binding':self.config['projects']['demo']['tasks'][TID]['reminder_id']=PID;self.save()
                elif kind=='active':self.native.rows[RID]=dict(id=RID,title='Активна',version=1,list='Работа',list_id=LID)
                elif kind=='access':self.native.error='access denied'
                elif kind=='incomplete':self.native.incomplete=True
                elif kind=='foreign_list':self.native.lists[0]['name']='Чужой'
                elif kind=='binding_scope':self.config['projects']['demo']['list_name']='Неразрешённый';self.save()
                elif kind in {'list_uuid','parent_uuid'}:self.config['projects']['demo']['list_id' if kind=='list_uuid' else 'parent_id']='invalid';self.save()
                else:self.native.lists[0]['total']=1
                before=self.paths['future'].read_bytes()
                with self.assertRaises((ValueError,KeyError)):self.prepare()
                self.assertEqual(self.paths['future'].read_bytes(),before);self.assertEqual(self.native.writes,[])
                self.assertFalse((self.hub/'ai/reminders-external-retirements').exists())
    def test_receipt_subject_survives_unrelated_changes_but_stops_active_return(self):
        p=self.prepare();self.apply(p)
        self.paths['future'].write_text(self.paths['future'].read_text()+'\n### TASK-demo-20261027-002 — Сосед\nStatus: ready\n')
        c=self.read();c['unrelated']='kept';self.config=c;self.save()
        self.assertTrue(self.verify())
        self.native.rows[RID]=dict(id=RID,title='Вернулась',version=1,list='Работа',list_id=LID)
        with self.assertRaisesRegex(ValueError,'uuid_active'):self.verify()
        self.assertEqual(self.native.writes,[])
    def test_corrupt_receipt_and_canonical_block_are_not_trusted(self):
        for kind in ('receipt','canonical','plan','state','link'):
            with self.subTest(kind=kind):
                self.setUp();p=self.prepare();self.apply(p)
                if kind=='canonical':self.paths['future'].write_text(self.paths['future'].read_text().replace('Контекст.','Изменённый контекст.'))
                elif kind=='plan':Path(p['plan']).write_text(Path(p['plan']).read_text()+' ')
                elif kind=='state':
                    q=Path(p['plan']).with_name('state.json');v=json.loads(q.read_text());v['approved']=False;q.write_text(json.dumps(v))
                else:
                    c=self.read();c['projects']['demo']['tasks'][TID]['external_retirement' if kind=='receipt' else 'reminder_id']=({} if kind=='receipt' else PID);self.config=c;self.save()
                with self.assertRaises((ValueError,KeyError)):self.verify()
                self.assertEqual(self.native.writes,[])
    def test_pending_journal_blocks_all_sync_and_resumes_own_canonical_write(self):
        p=self.prepare();original=m.cancel.write_texts
        def fail_after(hp,item,*args,**kw):
            original(hp,item,*args,**kw);raise TimeoutError('after_canonical')
        with patch.object(m.cancel,'write_texts',side_effect=fail_after):
            with self.assertRaises(TimeoutError):self.apply(p)
        c=self.read();self.assertEqual(m.pending_projects(self.hub,c),{'demo'})
        self.assertIn('demo',m.sync.migration_pending(self.hub,c))
        for result in (m.sync.sync(self.hub,c,True,native=self.native),m.sync.sync_notes(self.hub,c,True,native=self.native),m.sync.structure_module().reconcile_structure(self.hub,c,True,self.native)):
            self.assertFalse(result['ok'])
        self.assertEqual(self.apply(p)['phase'],'complete');self.assertTrue(self.verify())
        self.assertEqual(m.pending_projects(self.hub,self.read()),set())
    def test_resume_conflict_never_overwrites_neighbors(self):
        p=self.prepare()
        with patch.object(m.cancel,'write_texts',side_effect=TimeoutError('before_canonical')):
            with self.assertRaises(TimeoutError):self.apply(p)
        self.paths['future'].write_text(self.paths['future'].read_text()+'\nСоседская правка.\n');before=self.paths['future'].read_text()
        with self.assertRaisesRegex(ValueError,'snapshot_conflict'):self.apply(p)
        self.assertEqual(self.paths['future'].read_text(),before);self.assertEqual(m.pending_projects(self.hub,self.read()),{'demo'})
    def test_sync_and_structure_exclude_only_verified_external_retirement(self):
        p=self.prepare();self.apply(p);c=self.read();b=c['projects']['demo']
        self.native.rows[PID]=dict(id=PID,title='Проект',version=1,list='Работа',list_id=LID,parent_id=None,completed=False)
        ids=m.sync.structure_module().verified_cancelled_ids(self.hub,'demo',b,c,self.native)
        self.assertEqual(ids,{RID})
        result=m.sync.sync(self.hub,c,False,project='demo',native=self.native)
        self.assertTrue(result['ok'],result);self.assertEqual(self.native.writes,[])
    def test_empty_existing_rebind_creates_exact_group_account_and_preserves_origin(self):
        p=self.prepare();self.apply(p);self.native.lists=[]
        lists=m.sync.migration_module() if hasattr(m.sync,'migration_module') else m.sync.structure_module()
        spec=importlib.util.spec_from_file_location('external_empty_lists',SCRIPT.with_name('reminders_project_lists.py'));lists=importlib.util.module_from_spec(spec);spec.loader.exec_module(lists)
        self.assertTrue(hasattr(lists,'empty_rebind_preview'),'Отсутствует отдельный режим пустой существующей привязки')
        permission=lists.permission_preview(self.hub,'Проект');lists.permission_apply(permission['plan'],permission['sha256'],True)
        q=lists.empty_rebind_preview(self.hub,'demo',self.native)
        result=lists.empty_rebind_apply(q['plan'],q['sha256'],True,self.native)
        self.assertEqual(result['phase'],'complete');b=self.read()['projects']['demo']
        self.assertEqual((b['list_id'],b['parent_id'],b['account_id'],b['native_group_id']),(NEW,None,ACCOUNT,GROUP))
        self.assertEqual(b['external_retirement_rebind']['previous_binding']['list_id'],LID);self.assertNotIn('retired_parent',b)
        self.assertEqual(self.read()['structure']['list_roles'][NEW],{'kind':'project','project_id':'demo'})
        self.assertTrue(self.verify());self.assertEqual([t for t,a in self.native.writes],['manage_list','manage_list'])
        count=len(self.native.writes);lists.empty_rebind_apply(q['plan'],q['sha256'],True,self.native);self.assertEqual(len(self.native.writes),count)


    def lists_module(self):
        spec=importlib.util.spec_from_file_location('external_empty_lists_more',SCRIPT.with_name('reminders_project_lists.py'));lists=importlib.util.module_from_spec(spec);spec.loader.exec_module(lists);return lists
    def prepare_empty(self,source_present=False):
        p=self.prepare();self.apply(p)
        if not source_present:self.native.lists=[]
        lists=self.lists_module();permission=lists.permission_preview(self.hub,'Проект');lists.permission_apply(permission['plan'],permission['sha256'],True)
        return lists,lists.empty_rebind_preview(self.hub,'demo',self.native)
    def test_second_retirement_preserves_first_operation_receipt_and_pending(self):
        first=self.prepare();self.apply(first)
        tid='TASK-demo-20261027-002'
        self.paths['future'].write_text(self.paths['future'].read_text()+f'\n### {tid} — Другая\nStatus: ready\n')
        self.config=self.read();self.config['projects']['demo']['tasks'][tid]={'reminder_id':NEW};self.save()
        targets=[dict(project_id='demo',task_id=tid,reminder_id=NEW)]
        second=m.preview(self.hub,targets,dict(self.intent,targets=targets),self.native);self.apply(second)
        try: first_valid=self.verify()
        except ValueError: first_valid=False
        self.assertTrue(first_valid,'Вторая операция обесценила первую квитанцию')
        c=self.read();b=c['projects']['demo'];row=m.sync.HubProject(self.hub,'demo').rows()[tid]
        self.assertTrue(m.verify_link(self.hub,row,b['tasks'][tid],b,self.native))
        self.assertEqual(m.pending_projects(self.hub,c),set());self.assertEqual(self.native.writes,[])
        self.assertEqual(self.apply(first)['phase'],'complete');self.assertEqual(self.apply(second)['phase'],'complete')
        operation=b['tasks'][TID]['external_retirement']['operation']
        c['external_retirements_completed']['demo'].pop(operation);self.config=c;self.save()
        with self.assertRaisesRegex(ValueError,'retirement_not_committed'):self.verify()
        self.assertEqual(m.pending_projects(self.hub,self.read()),{'demo'})

    def empty_rebind_failure_window(self,point):
        lists,q=self.prepare_empty();durable=lists.durable;remote=lists.empty_rebind_remote;read=lists.config_read;hit=False
        def committed(value):return bool(value.get('project_list_migrations_completed'))
        def crash(path,text):
            nonlocal hit
            value=json.loads(text);is_config=Path(path)==self.hub/'ai/reminders-sync.json'
            target=(is_config and committed(value) if point=='after_final_config' else
                    Path(path)==Path(q['plan']).with_name('state.json') and value.get('phase')=='complete' if 'terminal' in point else
                    is_config and committed(value) and 'demo' not in value.get('project_list_migrations_pending',{}) if 'marker_clear' in point else False)
            if target and not hit:
                hit=True
                if point.startswith('after'):durable(path,text)
                raise TimeoutError(point)
            return durable(path,text)
        def fail_remote(hub,plan,state,config,native):
            nonlocal hit
            if point=='remote_readback' and committed(config) and not hit:hit=True;raise TimeoutError(point)
            return remote(hub,plan,state,config,native)
        def fail_read(hub):
            nonlocal hit
            result=read(hub)
            if point=='config_readback' and committed(result[0]) and not hit:hit=True;raise TimeoutError(point)
            return result
        with patch.object(lists,'durable',side_effect=crash),patch.object(lists,'empty_rebind_remote',side_effect=fail_remote),patch.object(lists,'config_read',side_effect=fail_read):
            with self.assertRaises(TimeoutError):lists.empty_rebind_apply(q['plan'],q['sha256'],True,self.native)
        self.assertTrue(hit)
        c=self.read();state=json.loads(Path(q['plan']).with_name('state.json').read_text());writes=len(self.native.writes)
        if 'marker_clear' in point:self.assertEqual(state['phase'],'complete','Очистка отметки началась до сохранённого complete')
        if point=='after_marker_clear':
            self.assertEqual(state['phase'],'complete');self.assertNotIn('demo',c.get('project_list_migrations_pending',{}))
        else:
            self.assertIn('demo',c.get('project_list_migrations_pending',{}),'Нативная блокировка снята раньше проверенного complete')
            self.assertEqual(lists.pending_projects(self.hub,c),{'demo'});self.assertEqual(m.sync.migration_pending(self.hub,c),{'demo'})
        self.assertEqual(lists.empty_rebind_apply(q['plan'],q['sha256'],True,self.native)['phase'],'complete')
        self.assertEqual(len(self.native.writes),writes);c=self.read()
        self.assertNotIn('demo',c.get('project_list_migrations_pending',{}));self.assertEqual(lists.pending_projects(self.hub,c),set())
        self.assertTrue(self.verify())
    def test_empty_rebind_after_final_config_keeps_native_pending(self):self.empty_rebind_failure_window('after_final_config')
    def test_empty_rebind_config_readback_failure_keeps_native_pending(self):self.empty_rebind_failure_window('config_readback')
    def test_empty_rebind_remote_readback_failure_keeps_native_pending(self):self.empty_rebind_failure_window('remote_readback')
    def test_empty_rebind_before_terminal_state_keeps_native_pending(self):self.empty_rebind_failure_window('before_terminal')
    def test_empty_rebind_after_terminal_state_resumes_marker_cleanup(self):self.empty_rebind_failure_window('after_terminal')
    def test_empty_rebind_before_marker_clear_resumes_without_native_writes(self):self.empty_rebind_failure_window('before_marker_clear')
    def test_empty_rebind_after_marker_clear_has_verified_terminal_state(self):self.empty_rebind_failure_window('after_marker_clear')
    def test_empty_rebind_unfinished_journal_blocks_even_with_completed_digest(self):
        lists,q=self.prepare_empty();durable=lists.durable
        def crash(path,text):
            durable(path,text)
            if Path(path)==self.hub/'ai/reminders-sync.json' and json.loads(text).get('project_list_migrations_completed'):raise TimeoutError('after_final_config')
        with patch.object(lists,'durable',side_effect=crash):
            with self.assertRaises(TimeoutError):lists.empty_rebind_apply(q['plan'],q['sha256'],True,self.native)
        c=self.read();c.get('project_list_migrations_pending',{}).pop('demo',None)
        self.assertEqual(lists.pending_projects(self.hub,c),{'demo'})
    def test_empty_unknown_create_never_retries_and_pending_survives_missing_journal(self):
        lists,q=self.prepare_empty();self.native.fail_create=True
        with self.assertRaises(TimeoutError):lists.empty_rebind_apply(q['plan'],q['sha256'],True,self.native)
        with self.assertRaisesRegex(ValueError,'unknown_creation_do_not_retry'):lists.empty_rebind_apply(q['plan'],q['sha256'],True,self.native)
        self.assertEqual(sum(a.get('action')=='create' for t,a in self.native.writes),1)
        c=self.read();self.assertIn('demo',lists.pending_projects(self.hub,c));Path(q['plan']).unlink();self.assertIn('demo',lists.pending_projects(self.hub,c))
    def test_empty_rebind_rejects_unproven_active_history_role_source_and_name(self):
        for kind in ('active','history','unproven','role','source','parent','name','group','shared'):
            with self.subTest(kind=kind):
                self.setUp();p=self.prepare();self.apply(p);c=self.read();self.native.lists=[]
                if kind=='active':self.paths['future'].write_text(self.paths['future'].read_text()+'\n### TASK-demo-20261027-002 — Активна\nStatus: ready\n')
                elif kind=='history':c['projects']['demo']['history']={NEW:{}}
                elif kind=='unproven':c['projects']['demo']['tasks'][TID].pop('external_retirement')
                elif kind=='role':c['structure']['list_roles'][LID]={'kind':'project','project_id':'demo'}
                elif kind=='source':
                    self.native.lists=[dict(id=LID,name='Работа',account_id=ACCOUNT,group_id=GROUP)];self.native.rows[NEW]=dict(id=NEW,title='Чужая',version=1,list='Работа',list_id=LID)
                elif kind=='parent':
                    self.native.lists=[dict(id=LID,name='Работа',account_id=ACCOUNT,group_id=GROUP)];self.native.rows[PID]=dict(id=PID,title='Родитель',version=1,list='Работа',list_id=LID)
                elif kind=='name':self.native.lists=[dict(id=NEW,name='Работа',account_id=ACCOUNT,group_id=GROUP)]
                elif kind=='group':c['structure']['native_groups']={}
                else:self.native.lists=[dict(id=LID,name='Работа',account_id=ACCOUNT,group_id=GROUP,shared=True)]
                self.config=c;self.save();lists=self.lists_module()
                with self.assertRaises(ValueError):lists.empty_rebind_preview(self.hub,'demo',self.native)
                self.assertEqual(self.native.writes,[])
    def prepare_direct_empty_source(self,source_present=False):
        p=self.prepare();self.apply(p);self.config=self.read()
        self.config['structure']['list_roles'][LID]={'kind':'direct'};self.save()
        if not source_present:self.native.lists=[]
        lists=self.lists_module();permission=lists.permission_preview(self.hub,'Проект')
        lists.permission_apply(permission['plan'],permission['sha256'],True)
        return lists
    def test_empty_rebind_exact_exclusive_direct_source_preserves_origin(self):
        for present in (False,True):
            with self.subTest(source_present=present):
                self.setUp();lists=self.prepare_direct_empty_source(present)
                try:q=lists.empty_rebind_preview(self.hub,'demo',self.native)
                except ValueError as error:self.fail('Доказанный исключительный direct-источник должен приниматься: '+str(error))
                self.assertEqual(lists.empty_rebind_apply(q['plan'],q['sha256'],True,self.native)['phase'],'complete')
                b=self.read()['projects']['demo']
                self.assertEqual((b['list_id'],b['parent_id'],b['account_id'],b['native_group_id']),(NEW,None,ACCOUNT,GROUP))
                self.assertEqual(b['external_retirement_rebind']['previous_binding']['list_id'],LID)
                self.assertEqual(self.read()['structure']['list_roles'].get(LID),{'kind':'direct'} if present else None)
                self.assertNotIn('retired_parent',b);self.assertTrue(self.verify())
                self.assertEqual([tool for tool,args in self.native.writes],['manage_list','manage_list'])
    def test_empty_rebind_direct_source_rejects_another_current_owner(self):
        lists=self.prepare_direct_empty_source();self.config=self.read()
        self.config['projects']['other']=dict(list_id=LID,list_name='Работа',parent_id=NEW,tasks={},history={});self.save()
        with self.assertRaisesRegex(ValueError,'empty_rebind_source_role_conflict'):
            lists.empty_rebind_preview(self.hub,'demo',self.native)
        self.assertEqual(self.native.writes,[])
    def test_empty_rebind_direct_source_rejects_foreign_previous_or_structural_reference(self):
        for kind in ('retired_parent','external_retirement_rebind','structure'):
            with self.subTest(kind=kind):
                self.setUp();lists=self.prepare_direct_empty_source();self.config=self.read()
                if kind=='structure':self.config['structure']['projects']['other']={'list_id':LID,'group':'work'}
                else:
                    b=dict(list_id=ACCOUNT,list_name='Другой',parent_id=NEW,tasks={},history={})
                    b[kind]=({'list_id':LID} if kind=='retired_parent' else {'previous_binding':{'list_id':LID}})
                    self.config['projects']['other']=b
                self.save()
                with self.assertRaisesRegex(ValueError,'empty_rebind_source_role_conflict'):
                    lists.empty_rebind_preview(self.hub,'demo',self.native)
                self.assertEqual(self.native.writes,[])
    def test_empty_rebind_direct_source_rejects_malformed_or_foreign_role(self):
        for role in ({'kind':'direct','project_id':'demo'},{'kind':'project','project_id':'demo'},{'kind':'unknown'}):
            with self.subTest(role=role):
                self.setUp();lists=self.prepare_direct_empty_source();self.config=self.read()
                self.config['structure']['list_roles'][LID]=role;self.save()
                with self.assertRaisesRegex(ValueError,'empty_rebind_source_role_conflict'):
                    lists.empty_rebind_preview(self.hub,'demo',self.native)
                self.assertEqual(self.native.writes,[])

    def test_empty_rebind_exact_known_empty_source_is_allowed(self):
        lists,q=self.prepare_empty(True);lists.empty_rebind_apply(q['plan'],q['sha256'],True,self.native)
        self.assertEqual(self.read()['projects']['demo']['list_id'],NEW);self.assertIn(LID,self.read()['structure']['list_roles'])
    def test_empty_rebind_stops_destination_account_shared_child_and_config_conflicts(self):
        for kind in ('account','shared','child','config'):
            with self.subTest(kind=kind):
                self.setUp();lists,q=self.prepare_empty();original=self.native.call
                def create_change(tool,args):
                    result=original(tool,args)
                    if tool=='manage_list' and args['action']=='create':
                        if kind=='account':self.native.lists[-1]['account_id']=PID
                        elif kind=='shared':self.native.lists[-1]['shared']=True
                        elif kind=='child':self.native.rows[PID]=dict(id=PID,title='Чужая',version=1,list='Проект',list_id=NEW)
                        else:
                            c=self.read();c['neighbor']='external';self.config=c;self.save()
                    return result
                self.native.call=create_change
                with self.assertRaises(ValueError):lists.empty_rebind_apply(q['plan'],q['sha256'],True,self.native)
                self.assertEqual(self.read()['projects']['demo']['list_id'],LID)
                if kind=='config':self.assertEqual(self.read()['neighbor'],'external')
                self.assertEqual(sum(a.get('action')=='create' for t,a in self.native.writes),1)
    def test_canonical_and_config_cas_failures_keep_pending_until_verified_resume(self):
        for point in ('before_pending','after_pending','before_final','after_final'):
            with self.subTest(point=point):
                self.setUp();p=self.prepare();original=m.cancel.durable_json;hit=False
                def crash(path,value):
                    nonlocal hit
                    pending=Path(path)==self.hub/'ai/reminders-sync.json' and bool(value.get('external_retirements_pending'))
                    final=Path(path)==self.hub/'ai/reminders-sync.json' and bool(value.get('external_retirements_completed'))
                    target=(pending if 'pending' in point else final)
                    if target and not hit:
                        hit=True
                        if point.startswith('after'):original(path,value)
                        raise TimeoutError(point)
                    return original(path,value)
                with patch.object(m.cancel,'durable_json',side_effect=crash):
                    with self.assertRaises(TimeoutError):self.apply(p)
                self.assertTrue(hit);self.assertIn('demo',m.pending_projects(self.hub,self.read()))
                self.assertEqual(self.apply(p)['phase'],'complete');self.assertTrue(self.verify());self.assertEqual(self.native.writes,[])
    def test_full_scope_metadata_501_and_errors_cannot_be_absence(self):
        for kind in ('500','501','error','metadata_race','other_list_active'):
            with self.subTest(kind=kind):
                self.setUp();original=self.native.call;count=0
                def response(tool,args):
                    nonlocal count
                    value=original(tool,args)
                    if tool=='find_reminders':
                        if kind in ('500','501'):value={'reminders':[dict(id=str(uuid.UUID(int=100+i)),title='Сосед',version=1,list='Работа',list_id=LID) for i in range(int(kind))]}
                        elif kind=='error':value={'reminders':[],'error':'not authorized'}
                        elif kind=='other_list_active' and args['list']==NEW:value={'reminders':[dict(id=RID,title='Активна',version=1,list='Другое',list_id=NEW)]}
                    if tool=='list_lists':
                        count+=1
                        if kind=='metadata_race' and count>1:value['lists'][0]['account_id']=PID
                    return value
                if kind=='other_list_active':
                    self.allow.write_text(json.dumps({'names':['Работа','Другое']}));self.native.lists.append(dict(id=NEW,name='Другое',account_id=ACCOUNT,group_id=GROUP))
                self.native.call=response
                with self.assertRaises(ValueError):self.prepare()
                self.assertEqual(self.native.writes,[])
    def test_active_mismatch_task_is_not_retired_or_silently_modified(self):
        self.paths['future'].write_text(self.paths['future'].read_text()+'\n### TASK-demo-20261027-002 — Другая\nStatus: ready\n')
        self.config['projects']['demo']['tasks']['TASK-demo-20261027-002']={'reminder_id':NEW};self.save()
        p=self.prepare();self.apply(p);c=self.read()
        self.assertEqual(c['projects']['demo']['tasks']['TASK-demo-20261027-002'],{'reminder_id':NEW})
        self.assertEqual(m.sync.HubProject(self.hub,'demo').rows()['TASK-demo-20261027-002']['status'],'ready')
        self.native.rows[PID]=dict(id=PID,title='Проект',version=1,list='Работа',list_id=LID,parent_id=None,completed=False)
        result=m.sync.sync(self.hub,c,False,project='demo',native=self.native)
        self.assertFalse(result['ok']);self.assertIn('missing_remote_task',str(result));self.assertEqual(self.native.writes,[])


    def test_external_receipt_survives_ordinary_migration_as_separate_proof(self):
        p=self.prepare();self.apply(p)
        self.native.rows[PID]=dict(id=PID,title='Проект',version=1,list='Работа',list_id=LID,parent_id=None,completed=False)
        live=str(uuid.UUID(int=7));tid='TASK-demo-20261027-002'
        self.paths['future'].write_text(self.paths['future'].read_text()+'\n### '+tid+' — Сосед\nStatus: ready\n')
        self.native.rows[live]=dict(id=live,title='Сосед',version=1,list='Работа',list_id=LID,parent_id=PID,completed=False,notes='Контекст соседа')
        c=self.read();c['projects']['demo']['tasks'][tid]={'reminder_id':live};c['unrelated']='preserved';self.config=c;self.save()
        lists=self.lists_module();permission=lists.permission_preview(self.hub,'Проект');lists.permission_apply(permission['plan'],permission['sha256'],True)
        q=lists.preview(self.hub,'demo','Проект',GROUP,self.native);plan=json.loads(Path(q['plan']).read_text())
        self.assertEqual(set(plan['external_retirements']),{RID});self.assertFalse(plan.get('historical'));self.assertEqual(plan['children'],[live])
        try:lists.apply(q['plan'],q['sha256'],True,self.native)
        except ValueError as error:self.fail('Обычный перенос должен сохранить отдельное доказательство: '+str(error))
        self.assertEqual(self.read()['projects']['demo']['list_id'],NEW);self.assertTrue(self.verify())
        self.assertEqual(self.native.rows[live]['list_id'],NEW);self.assertIsNone(self.native.rows[live]['parent_id']);self.assertEqual(self.native.rows[live]['notes'],'Контекст соседа');self.assertEqual(self.read()['unrelated'],'preserved')
    def test_notes_sync_rejects_active_external_return_before_unrelated_note_write(self):
        p=self.prepare();self.apply(p)
        self.native.rows[RID]=dict(id=RID,title='Вернулась',version=1,list='Работа',list_id=LID,parent_id=PID,completed=False)
        result=m.sync.sync_notes(self.hub,self.read(),True,project='demo',native=self.native)
        self.assertFalse(result['ok']);self.assertIn('uuid_active',str(result));self.assertEqual(self.native.writes,[])


    def test_current_and_paused_partial_archive_resume_preserves_source_context(self):
        for kind in ('current','paused'):
            with self.subTest(kind=kind):
                self.setUp();self.paths['future'].write_text('# Будущие задачи\n')
                text=(f'# Текущая задача\nTask ID: {TID}\nStatus: active\nDue: 2026-12-31\n\n## Goal\nЗадача\n\n## Context\nКонтекст.\n' if kind=='current' else f'# Пауза\n\n### 2026-10-27 — Задача\nTask ID: {TID}\nStatus: paused\nDue: 2026-12-31\n\nКонтекст.\n')
                self.paths[kind].write_text(text);p=self.prepare();original=m.cancel.subprocess.run;hit=False
                def crash(*args,**kw):
                    nonlocal hit
                    result=original(*args,**kw)
                    if not hit:hit=True;raise TimeoutError('after_first_canonical_write')
                    return result
                with patch.object(m.cancel.subprocess,'run',side_effect=crash):
                    with self.assertRaises(TimeoutError):self.apply(p)
                self.assertIn('Status: dropped',self.paths['future'].read_text());self.assertEqual(self.paths[kind].read_text(),text)
                self.assertEqual(self.apply(p)['phase'],'complete');self.assertTrue(self.verify());self.assertIn('Контекст.',self.paths['future'].read_text())
    def test_resume_after_canonical_receipt_stops_reverted_task_without_replaying(self):
        p=self.prepare();before=self.paths['future'].read_text();original=m.cancel.durable_json
        def crash(path,value):
            original(path,value)
            if Path(path).name=='state.json' and value.get('phase')=='canonical':raise TimeoutError('after_canonical_receipt')
        with patch.object(m.cancel,'durable_json',side_effect=crash):
            with self.assertRaises(TimeoutError):self.apply(p)
        self.paths['future'].write_text(before)
        with self.assertRaisesRegex(ValueError,'canonical|snapshot|reverted'):self.apply(p)
        self.assertEqual(self.paths['future'].read_text(),before);self.assertIn('demo',m.pending_projects(self.hub,self.read()))
    def test_config_cas_detects_edit_between_wal_and_pending_write(self):
        p=self.prepare();original=m.cancel.durable_json
        def edit(path,value):
            original(path,value)
            if Path(path).name=='state.json' and value.get('phase')=='intent':
                c=self.read();c['neighbor']='human';self.config=c;self.save()
        with patch.object(m.cancel,'durable_json',side_effect=edit):
            with self.assertRaisesRegex(ValueError,'cas_conflict'):self.apply(p)
        self.assertEqual(self.read()['neighbor'],'human');self.assertIn('Status: ready',self.paths['future'].read_text())


    def test_target_retirement_preserves_unrelated_recurrence_history(self):
        self.config['projects']['demo']['history']={NEW:{'task_id':'TASK-demo-previous','project_id':'demo','original_id':PID}}
        self.save();history=copy.deepcopy(self.config['projects']['demo']['history'])
        try:p=self.prepare();self.apply(p)
        except ValueError as error:self.fail('Исключение одной задачи не меняет чужую историю: '+str(error))
        self.assertEqual(self.read()['projects']['demo']['history'],history);self.assertTrue(self.verify())


    def test_config_byte_cas_rejects_equivalent_reformatting(self):
        p=self.prepare();path=self.hub/'ai/reminders-sync.json';path.write_text(json.dumps(self.read(),ensure_ascii=False,indent=2));before=path.read_bytes()
        with self.assertRaisesRegex(ValueError,'cas_conflict'):self.apply(p)
        self.assertEqual(path.read_bytes(),before);self.assertIn('Status: ready',self.paths['future'].read_text())

if __name__=='__main__': unittest.main()
