"""Настоящие Python-журналы в искусственном Хабе; никаких реальных напоминаний."""
import copy,json,unittest,uuid,os
from pathlib import Path
import test_reminders_cancel as base
import test_reminders_project_list_migration as migration

AID,GID,NEW,CHILD=[str(uuid.UUID(int=i)) for i in (10,11,12,13)]
RID,PID,LID,TID=base.RID,base.PID,base.LID,base.TID

class Native(base.Native):
    def __init__(self):
        super().__init__();self.data[PID].pop('parent_id',None);self.data[RID]['notes']='Кириллица https://example.test/a/b\nСтрока';self.writes=[];self.lists=[dict(id=LID,name='Работа',account_id=AID,group_id=GID,shared=False)];self.groups=[dict(id=GID,name='Группа',account_id=AID)]
        self.data[CHILD]=dict(id=CHILD,list_id=LID,list='Работа',parent_id=PID,title='Сосед',version='c1',completed=False,notes='Кириллица https://example.test/a/b\nСтрока')
    def get(self,rid,lid,parent=None):return self.call('get_reminder',dict(id=rid))
    def call(self,tool,args):
        if tool=='hub_cancel_capabilities':return dict(protocol=1,atomic_version_check=True,same_uuid_restore_verified=True,optimistic_version_check=True,requires_no_concurrent_edits=True)
        if tool=='list_lists':return dict(lists=copy.deepcopy(self.lists),groups=copy.deepcopy(self.groups),guarded_list_creation=True)
        if tool=='find_reminders':
            rows=[self.call('get_reminder',dict(id=rid)) for rid,row in self.data.items() if rid not in self.deleted and row['list_id']==args['list']]
            return dict(reminders=rows,count=len(rows))
        if tool=='get_reminder':
            if args['id'] in self.deleted:raise ValueError('deleted')
            row=copy.deepcopy(self.data[args['id']]);children=[dict(id=rid) for rid,r in self.data.items() if rid not in self.deleted and r.get('parent_id')==row['id']]
            if children:row['subtasks']=children
            return row
        if tool=='manage_list':
            self.writes.append((tool,copy.deepcopy(args)))
            if args['action']=='create':self.lists.append(dict(id=NEW,name=args['list'],account_id=AID,group_id=None,shared=False))
            else:self.lists[-1]['group_id']=args['group']
            return copy.deepcopy(self.lists[-1])
        if tool=='update_reminder':
            self.writes.append((tool,copy.deepcopy(args)));row=self.data[args['id']];assert row['version']==args['version']
            row.update(list_id=args['list'],list='Проект',version=row['version']+'m');row.pop('parent_id',None)
            if self.fail_after==tool:self.fail_after=None;raise TimeoutError('unknown move')
            return copy.deepcopy(row)
        result=super().call(tool,args)
        if tool=='hub_cancel_status' and result.get('state')=='deleted':result['projected_binding']=True
        return result

class HistoricalTests(unittest.TestCase):
    def setUp(self):
        self.f=base.CancellationTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.c=base.m;migration.SCRIPT=base.SOURCE.with_name('reminders_project_lists.py');self.m=migration.module();self.hub=self.f.hub;self.config=self.f.config;self.native=Native()
        self.config['cancellation_policy']=getattr(self,'policy','strict')
        self.config['cancellation_binary']=str(self.hub/'executor');(self.hub/'executor').write_bytes(b'synthetic')
        self.config['structure']=dict(list_roles={LID:dict(kind='group',group_id='canonical')},projects={'demo':dict(list_id=LID,group='canonical')})
        self.save();self.cancel=self.c.preview(self.hub,self.config,[('demo',TID)],self.native)
        self.c.execute(self.hub,self.cancel['path'],self.cancel['sha256'],self.config,self.native)
        self.original={name:Path(self.cancel['path']).with_name(name).read_bytes() for name in ('plan.json','state.json')}
        self.link=copy.deepcopy(self.config['projects']['demo']['tasks'][TID])
    def save(self):(self.hub/'ai/reminders-sync.json').write_text(json.dumps(self.config,ensure_ascii=False))
    def prepare(self):
        p=self.m.permission_preview(self.hub,'Проект');self.m.permission_apply(p['plan'],p['sha256'],True)
        return self.m.preview(self.hub,'demo','Проект',GID,self.native)
    def succeeds(self,fn,*args,**kwargs):
        try:return fn(*args,**kwargs)
        except (ValueError,RuntimeError) as error:self.fail('Valid fixture rejected: '+str(error))
    def migrate(self):
        p=self.succeeds(self.prepare);self.succeeds(self.m.apply,p['plan'],p['sha256'],True,self.native)
        self.config=json.loads((self.hub/'ai/reminders-sync.json').read_text());return p
    def verify(self):
        row=self.c.sync.HubProject(self.hub,'demo').rows()[TID]
        return self.c.verify_cancelled_link(self.hub,row,self.link,self.config['projects']['demo'],self.native)
    def test_migration_excludes_only_deleted_and_preserves_journals(self):
        p=self.migrate();plan=json.loads(Path(p['plan']).read_text())
        self.assertEqual(plan['children'],[CHILD]);self.assertEqual(set(plan['historical']),{RID})
        self.assertEqual(self.native.deleted,{RID});self.assertEqual(self.native.data[RID]['list_id'],LID)
        self.assertEqual(self.original,{n:Path(self.cancel['path']).with_name(n).read_bytes() for n in self.original})
        self.assertEqual(self.config['projects']['demo']['tasks'][TID],self.link);self.assertTrue(self.verify())
    def test_invalid_history_rejects_before_writes(self):
        self.native.deleted.remove(RID)
        with self.assertRaises(ValueError):self.prepare()
        self.assertEqual(self.native.writes,[])
    def test_pinned_receipt_and_current_guards(self):
        self.migrate();binding=self.config['projects']['demo'];reference=binding['historical_binding_migration'];path=Path(reference['path']);raw=path.read_bytes()
        for key in ('sha256','list_id','native_group_id','account_id','parent_id'):
            original=copy.deepcopy(self.config)
            if key=='sha256':reference[key]='0'*64
            else:binding[key]=str(uuid.uuid4())
            self.save()
            with self.subTest(key=key),self.assertRaises(ValueError):self.verify()
            self.config=original;binding=self.config['projects']['demo'];reference=binding['historical_binding_migration'];self.save()
        path.write_bytes(raw+b' ')
        with self.assertRaises(ValueError):self.verify()
    def test_future_restore_composes_old_undelete_and_active_move(self):
        self.migrate();rp=self.c.restore_preview(self.hub,self.cancel['path'],self.cancel['sha256'],self.config,self.native)
        self.c.execute(self.hub,self.cancel['path'],self.cancel['sha256'],self.config,self.native,True,rp['sha256'])
        self.assertNotIn(RID,self.native.deleted);self.assertEqual(self.native.data[RID]['list_id'],NEW)
        self.assertIsNone(self.native.data[RID].get('parent_id'));self.assertNotIn('cancellation',self.config['projects']['demo']['tasks'][TID])
        self.assertEqual(self.c.sync.HubProject(self.hub,'demo').rows()[TID]['status'],'ready')
    def restore_token(self):
        self.migrate();return self.c.restore_preview(self.hub,self.cancel['path'],self.cancel['sha256'],self.config,self.native)['sha256']
    def execute_restore(self,token):return self.c.execute(self.hub,self.cancel['path'],self.cancel['sha256'],self.config,self.native,True,token)
    def test_unknown_restore_and_move_resume_once(self):
        for boundary in ('hub_restore_reminder','update_reminder'):
            with self.subTest(boundary=boundary):
                self.setUp();token=self.restore_token();self.native.fail_after=boundary
                with self.assertRaises(TimeoutError):self.execute_restore(token)
                self.assertIn('demo',self.c.pending_projects(self.hub,self.config))
                self.succeeds(self.execute_restore,token)
                self.assertEqual(sum(t=='hub_restore_reminder' for t,a in self.native.calls),1)
                self.assertEqual(sum(t=='update_reminder' and a['id']==RID for t,a in self.native.writes),1)
                self.assertEqual(self.c.status(self.hub,self.cancel['path'],self.cancel['sha256'],self.config,self.native)['items'][0]['state'],'active')
    def test_unknown_move_foreign_edit_stops_without_redelete(self):
        token=self.restore_token();self.native.fail_after='update_reminder'
        with self.assertRaises(TimeoutError):self.execute_restore(token)
        self.native.data[RID]['notes']='Сторонняя правка';before=copy.deepcopy(self.native.data);writes=len(self.native.writes)
        with self.assertRaises(ValueError):self.execute_restore(token)
        self.assertEqual(self.native.data,before);self.assertEqual(len(self.native.writes),writes);self.assertNotIn(RID,self.native.deleted)
    def test_destination_conflict_stops_before_undelete(self):
        token=self.restore_token();self.native.lists[-1]['account_id']=LID
        with self.assertRaises(ValueError):self.execute_restore(token)
        self.assertIn(RID,self.native.deleted);self.assertEqual(sum(t=='hub_restore_reminder' for t,a in self.native.calls),0)
    def test_neighbor_and_canonical_changes_block_stale_token(self):
        token=self.restore_token();path=self.f.paths['future'];path.write_text(path.read_text()+'\nНовая соседняя заметка.\n')
        with self.assertRaises(ValueError):self.execute_restore(token)
        self.assertIn(RID,self.native.deleted);self.assertIn('Новая соседняя заметка.',path.read_text())
    def test_canonical_write_failure_resumes_after_move(self):
        from unittest.mock import patch
        token=self.restore_token()
        with patch.object(self.c,'write_texts',side_effect=OSError('local interrupted')):
            with self.assertRaises(OSError):self.execute_restore(token)
        self.assertEqual(self.native.data[RID]['list_id'],NEW);self.assertIn('demo',self.c.pending_projects(self.hub,self.config))
        self.succeeds(self.execute_restore,token);self.assertEqual(sum(t=='hub_restore_reminder' for t,a in self.native.calls),1)
        self.assertEqual(sum(t=='update_reminder' and a['id']==RID for t,a in self.native.writes),1)
        self.assertEqual(self.c.sync.HubProject(self.hub,'demo').rows()[TID]['status'],'ready')
    def test_unrelated_new_task_preserved_by_fresh_restore(self):
        self.migrate();path=self.f.paths['future'];text=path.read_text()+'\n### TASK-demo-20261027-002 — Новая задача\nStatus: ready\n\nСоседний контекст.\n';path.write_text(text)
        self.config['projects']['demo']['tasks']['new-task']={'reminder_id':str(uuid.UUID(int=20))};self.save()
        token=self.c.restore_preview(self.hub,self.cancel['path'],self.cancel['sha256'],self.config,self.native)['sha256'];self.succeeds(self.execute_restore,token)
        self.assertIn('Соседний контекст.',path.read_text());self.assertIn('new-task',self.config['projects']['demo']['tasks'])
    def test_migration_publication_interrupt_recovers(self):
        from unittest.mock import patch
        p=self.prepare();original=self.m.durable;fired=False
        def write(path,data,*args):
            nonlocal fired
            if Path(path)==self.hub/'ai/reminders-sync.json' and 'historical_binding_migration' in data and not fired:
                fired=True;raise OSError('before final config')
            return original(path,data,*args)
        with patch.object(self.m,'durable',write):
            with self.assertRaises(OSError):self.m.apply(p['plan'],p['sha256'],True,self.native)
        current=json.loads((self.hub/'ai/reminders-sync.json').read_text());self.assertIn('demo',self.m.pending_projects(self.hub,current))
        self.m.apply(p['plan'],p['sha256'],True,self.native);self.config=json.loads((self.hub/'ai/reminders-sync.json').read_text())
        self.assertTrue(self.verify());self.assertEqual(self.original,{n:Path(self.cancel['path']).with_name(n).read_bytes() for n in self.original})
    def test_current_v2_cancel_after_historical_migration(self):
        self.migrate();tid='TASK-demo-20261027-003';path=self.f.paths['future'];path.write_text(path.read_text()+'\n### '+tid+' — Сосед\nStatus: ready\n')
        self.config['projects']['demo']['tasks'][tid]={'reminder_id':CHILD};self.save();old=self.native.call
        def call(tool,args):
            if tool=='hub_cancel_capabilities':return dict(protocol=1,supported_versions=[1,2],same_uuid_restore_verified=True,project_list_same_uuid_restore_verified=True,project_list_verified_scope=dict(family='same_os_executor_account',account_id=AID),atomic_version_check=True)
            return old(tool,args)
        self.native.call=call;p=self.c.preview(self.hub,self.config,[('demo',tid)],self.native);self.succeeds(self.c.execute,self.hub,p['path'],p['sha256'],self.config,self.native)
        self.assertEqual(p['plan']['version'],2);self.assertIn(CHILD,self.native.deleted);self.assertTrue(self.verify())

    def test_multiitem_operation_restores_unmigrated_and_migrated_members(self):
        token=self.c.restore_preview(self.hub,self.cancel['path'],self.cancel['sha256'],self.config,self.native)['sha256']
        self.c.execute(self.hub,self.cancel['path'],self.cancel['sha256'],self.config,self.native,True,token)
        other=self.hub/'projects/other';(other/'ai').mkdir(parents=True)
        tid2=TID.replace('demo','other')
        for kind,path in self.f.paths.items():(other/'ai'/path.name).write_text(path.read_text().replace(TID,tid2))
        registry=self.hub/'ai/project-registry.md';registry.write_text(registry.read_text()+'## other\nStatus: active\nPath: '+str(other)+'\n')
        parent2,rid2=[str(uuid.UUID(int=n)) for n in (30,31)]
        self.native.data[parent2]=dict(self.native.data[PID],id=parent2,title='Другой проект')
        self.native.data[rid2]=dict(self.native.data[RID],id=rid2,parent_id=parent2,title='Другая задача')
        self.config['projects']['other']=dict(list_id=LID,list_name='Работа',parent_id=parent2,tasks={tid2:dict(reminder_id=rid2,repeating=True)})
        self.config['structure']['projects']['other']=dict(list_id=LID,group='canonical');self.save()
        self.cancel=self.c.preview(self.hub,self.config,[('other',tid2),('demo',TID)],self.native)
        self.c.execute(self.hub,self.cancel['path'],self.cancel['sha256'],self.config,self.native)
        self.link=copy.deepcopy(self.config['projects']['demo']['tasks'][TID]);self.migrate()
        token=self.c.restore_preview(self.hub,self.cancel['path'],self.cancel['sha256'],self.config,self.native)['sha256'];self.succeeds(self.execute_restore,token)
        self.assertEqual(self.native.data[RID]['list_id'],NEW);self.assertEqual(self.native.data[rid2]['list_id'],LID)
        self.assertNotIn(RID,self.native.deleted);self.assertNotIn(rid2,self.native.deleted)

    def test_archived_neighbor_does_not_block_historical_read(self):
        token=self.c.restore_preview(self.hub,self.cancel['path'],self.cancel['sha256'],self.config,self.native)['sha256']
        self.c.execute(self.hub,self.cancel['path'],self.cancel['sha256'],self.config,self.native,True,token)
        other=self.hub/'projects/other';(other/'ai').mkdir(parents=True)
        tid2=TID.replace('demo','other')
        for kind,path in self.f.paths.items():(other/'ai'/path.name).write_text(path.read_text().replace(TID,tid2))
        registry=self.hub/'ai/project-registry.md';registry.write_text(registry.read_text()+'## other\nStatus: active\nPath: '+str(other)+'\n')
        parent2,rid2=[str(uuid.UUID(int=n)) for n in (30,31)]
        self.native.data[parent2]=dict(self.native.data[PID],id=parent2,title='Другой проект')
        self.native.data[rid2]=dict(self.native.data[RID],id=rid2,parent_id=parent2,title='Другая задача')
        self.config['projects']['other']=dict(list_id=LID,list_name='Работа',parent_id=parent2,tasks={tid2:dict(reminder_id=rid2,repeating=True)})
        self.config['structure']['projects']['other']=dict(list_id=LID,group='canonical');self.save()
        self.cancel=self.c.preview(self.hub,self.config,[('other',tid2),('demo',TID)],self.native)
        self.c.execute(self.hub,self.cancel['path'],self.cancel['sha256'],self.config,self.native)
        self.link=copy.deepcopy(self.config['projects']['demo']['tasks'][TID]);self.migrate()
        registry.write_text(registry.read_text().replace('## other\nStatus: active','## other\nStatus: archived'))
        self.assertTrue(self.verify())
        with self.assertRaisesRegex(ValueError,'project_path_changed'):
            self.c.restore_preview(self.hub,self.cancel['path'],self.cancel['sha256'],self.config,self.native)
