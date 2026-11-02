"""Только искусственные данные; нативное приложение не вызывается."""
import copy,json,unittest,uuid
from pathlib import Path
from unittest.mock import patch
import test_reminders_project_list_migration as base
LID='AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA';AID='BBBBBBBB-BBBB-4BBB-8BBB-BBBBBBBBBBBB';GID='CCCCCCCC-CCCC-4CCC-8CCC-CCCCCCCCCCCC'

class RenameFake(base.Fake):
    def call(self,tool,args):
        if tool=='manage_list' and 'new_name' in args:
            self.writes.append((tool,copy.deepcopy(args)))
            row=self.lists[0]
            assert args==dict(action='update',list=LID,expected_name='Работа',new_name='Работа — прежний список',expected_account_id=AID,expected_group_id=GID)
            row['name']=args['new_name']
            for r in self.rows.values():r['list']=row['name']
            if self.fail=='rename':self.fail=None;raise TimeoutError('unknown rename outcome')
            return copy.deepcopy(row)
        value=super().call(tool,args)
        if tool=='list_lists':value['guarded_list_rename']=True
        return value

class ExtrasTests(unittest.TestCase):
    def setUp(self):
        self.f=base.MigrationTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.m=self.f.m;self.hub=self.f.hub;self.config=self.f.config;self.native=RenameFake()
        self.native.lists[0].update(id=LID,account_id=AID,group_id=GID);self.native.groups[0].update(id=GID,account_id=AID,name='Группа')
        for row in self.native.rows.values():row['list_id']=LID
        self.native.rows['history']['notes']=self.f.native.rows['history']['notes']
        self.config['projects']['demo'].update(list_id=LID,project_label='Проект')
        self.config['standard_allowlist_file']=str(self.hub/'ai/reminders-standard-allowlist.json')
        self.config['structure']['list_roles']={LID:dict(kind='group',group_id='canonical')}
        self.config['structure']['projects']['demo']['list_id']=LID
        self.config['structure'].update(native_groups={GID:'top'},groups_allowlist_file=str(self.hub/'ai/groups.json'))
        (self.hub/'ai/groups.json').write_text(json.dumps(['Группа']))
        (self.hub/'ai/archiprojects.md').write_text('## top\n```yaml\nid: top\nkind: group\nname: Группа\nstatus: active\nparent:\n```\n## canonical\n```yaml\nid: canonical\nkind: group\nname: Подгруппа\nstatus: active\nparent: top\n```\n')
        (self.hub/'ai/project-cards').mkdir();(self.hub/'ai/project-cards/demo.md').write_text('Project ID: demo\nStatus: active\nprimary_archiproject: canonical\n')
        registry=self.hub/'ai/project-registry.md';registry.write_text(registry.read_text()+'Name: Проект\nCard: ai/project-cards/demo.md\n')
        self.f.save()
    def prepare(self):
        self.assertTrue(callable(getattr(self.m,'rename_preview',None)))
        p=self.m.permission_preview(self.hub,'Работа — прежний список');self.m.permission_apply(p['plan'],p['sha256'],True)
        return self.m.rename_preview(self.hub,LID,'Работа','Работа — прежний список',self.native)
    def apply(self,p):return self.m.rename_apply(p['plan'],p['sha256'],True,self.native)
    def test_rename_only_names_and_full_neighbor_snapshot(self):
        p=self.prepare();before=copy.deepcopy(self.config);plan=json.loads(Path(p['plan']).read_text());self.assertEqual(set(plan['source']),set(self.native.rows))
        state=self.apply(p);self.assertEqual(state['phase'],'complete');before['projects']['demo']['list_name']='Работа — прежний список'
        self.assertEqual(json.loads((self.hub/'ai/reminders-sync.json').read_text()),before)
        self.assertEqual(len(self.native.writes),1);self.apply(p);self.assertEqual(len(self.native.writes),1)
    def test_historical_plan_reference_blocks_even_without_current_link(self):
        ids={old:str(uuid.uuid4()) for old in self.native.rows};converted={}
        for old,row in self.native.rows.items():
            row=copy.deepcopy(row);row['id']=ids[old]
            if row.get('parent_id'):row['parent_id']=ids[row['parent_id']]
            converted[row['id']]=row
        self.native.rows=converted;b=self.config['projects']['demo'];b['parent_id']=ids['parent'];b['tasks']['t']['reminder_id']=ids['task']
        history=b['history'].pop('history');history['original_id']=ids['task'];b['history'][ids['history']]=history;self.f.save()
        c=self.m.load_sync().cancellation_module();operation=str(uuid.uuid4());folder=self.hub/'ai/reminders-cancellations'/operation;folder.mkdir(parents=True)
        texts={kind:(self.f.project/'ai'/name).read_text() for kind,name in c.sync.NAMES.items()}
        remote=self.native.call('get_reminder',dict(id=ids['task']))
        item=dict(project_id='demo',task_id='t',project_path=str(self.f.project),reminder_id=ids['task'],parent_id=ids['parent'],list_id=LID,list_name='Работа',
                  source_kind='future',source_path=str(self.f.project/'ai'/c.sync.NAMES['future']),before_texts=texts,after_texts=texts,remote=remote,link=copy.deepcopy(b['tasks']['t']))
        plan=dict(version=1,operation_id=operation,items=[item],concurrency_policy='strict',config=self.config,
                  config_sha256=c.digest((self.hub/'ai/reminders-sync.json').read_bytes()),allowlist_sha256=c.guard_bindings(self.config,[item],self.hub))
        raw=c.encoded(plan);path=folder/'plan.json';path.write_text(raw);digest=c.digest(raw)
        status=dict(state='active',version=remote['version'],snapshot=remote)
        state=dict(plan_sha256=digest,approved=True,items={ids['task']:dict(phase='restored',restored_snapshot=status)})
        (folder/'state.json').write_text(c.encoded(state))
        _,loaded=c.read_plan(self.hub,path,digest,require_active=False)
        self.assertEqual(c.read_state(path,loaded,digest),state)
        self.assertEqual(c.pending_projects(self.hub,self.config),set())
        self.assertNotIn('cancellation',b['tasks']['t'])
        with self.assertRaises(ValueError):self.prepare()
        self.assertEqual(self.native.writes,[])
    def test_rename_names_reject_all_line_separators(self):
        for name in ['x\vy','x\fy','x\x85y','x\u2028y']:
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError,'invalid_rename_arguments'):self.m.rename_preview(self.hub,LID,'Работа',name,self.native)
        self.assertEqual(self.native.writes,[])
    def test_rename_requires_approval_and_exact_sha(self):
        p=self.prepare()
        with self.assertRaisesRegex(ValueError,'approval'):self.m.rename_apply(p['plan'],p['sha256'],False,self.native)
        with self.assertRaisesRegex(ValueError,'sha256'):self.m.rename_apply(p['plan'],'bad',True,self.native)
        self.assertEqual(self.native.writes,[])
    def test_unknown_rename_resume_uses_own_intent(self):
        p=self.prepare();self.native.fail='rename'
        with self.assertRaises(TimeoutError):self.apply(p)
        self.assertEqual(self.m.pending_projects(self.hub,json.loads((self.hub/'ai/reminders-sync.json').read_text())),{'demo'})
        self.assertEqual(self.apply(p)['phase'],'complete');self.assertEqual(len(self.native.writes),1)
    def test_external_rename_without_intent_rejected(self):
        p=self.prepare();self.native.call('manage_list',dict(action='update',list=LID,expected_name='Работа',new_name='Работа — прежний список',expected_account_id=AID,expected_group_id=GID));self.native.writes=[]
        with self.assertRaisesRegex(ValueError,'unattested'):self.apply(p)
        self.assertEqual(self.native.writes,[])
    def test_rename_stale_guards(self):
        for kind in ['config','canonical','permission','remote','group']:
            with self.subTest(kind=kind):
                self.setUp();p=self.prepare()
                if kind=='config':self.config['extra']=True;self.f.save()
                elif kind=='canonical':(self.f.project/'ai/future-tasks.md').write_text('changed')
                elif kind=='permission':(self.hub/'ai/reminders-standard-allowlist.json').write_text('{"names":[]}')
                elif kind=='group':self.native.lists[0]['group_id']=None
                else:self.native.rows['neighbor']['notes']='changed'
                with self.assertRaises(ValueError):self.apply(p)
                self.assertEqual(self.native.writes,[])
    def test_rename_rejects_history_retired_and_pending(self):
        for kind in ['cancel','retired','pending']:
            with self.subTest(kind=kind):
                self.setUp()
                if kind=='cancel':self.config['projects']['demo']['tasks']['t']['cancellation']={}
                elif kind=='retired':self.config['projects']['demo']['retired_parent']={'list_id':LID}
                else:self.config['project_list_migrations_pending']={'demo':'other'}
                self.f.save()
                with self.assertRaises(ValueError):self.prepare()
                self.assertEqual(self.native.writes,[])
    def test_rename_requires_selected_standard_permissions(self):
        self.config.pop('standard_allowlist_file');self.f.save()
        with self.assertRaisesRegex(ValueError,'standard_permission_selection'):self.prepare()
        self.assertEqual(self.native.writes,[])
    def test_rename_requires_approved_permission_receipt(self):
        p=self.prepare()
        for f in (self.hub/'ai/reminders-project-lists').iterdir():
            if json.loads((f/'plan.json').read_text())['kind']=='permission':(f/'state.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'consent'):self.apply(p)
        self.assertEqual(self.native.writes,[])
    def test_rename_wal_and_shared_pending_before_effect(self):
        self.config['projects']['other']=dict(list_id=LID,list_name='Работа',parent_id='neighbor',tasks={},history={})
        project=self.hub/'projects/other';(project/'ai').mkdir(parents=True)
        reg=self.hub/'ai/project-registry.md';reg.write_text(reg.read_text()+'## other\nStatus: active\nPath: '+str(project)+'\n')
        self.config['structure']['projects']['other']=dict(list_id=LID,group='canonical');self.f.save();p=self.prepare();old=self.native.call
        def call(tool,args):
            if tool=='manage_list':
                state=json.loads(Path(p['plan']).with_name('state.json').read_text());self.assertEqual(state['phase'],'renaming');self.assertEqual(state['write_intent'],args)
                c=json.loads((self.hub/'ai/reminders-sync.json').read_text());self.assertEqual(self.m.pending_projects(self.hub,c),{'demo','other'})
            return old(tool,args)
        self.native.call=call;self.apply(p)
        self.assertEqual(json.loads((self.hub/'ai/reminders-sync.json').read_text())['projects']['other']['list_name'],'Работа — прежний список')
    def test_rename_committing_resume_and_tamper(self):
        p=self.prepare();old=self.m.durable
        def write(path,data,*args):
            if Path(path).name=='state.json' and json.loads(data).get('phase')=='complete':raise OSError('lost final receipt')
            return old(path,data,*args)
        with patch.object(self.m,'durable',write):
            with self.assertRaises(OSError):self.apply(p)
        self.assertEqual(self.apply(p)['phase'],'complete');self.assertEqual(len(self.native.writes),1)
        st=Path(p['plan']).with_name('state.json');state=json.loads(st.read_text());state['final_config']='{}';st.write_text(json.dumps(state))
        with self.assertRaises(ValueError):self.apply(p)
    def test_bulk_is_read_only_and_uses_top_ancestor(self):
        self.assertTrue(callable(getattr(self.m,'bulk_candidates',None)))
        before={str(p):p.read_bytes() for p in self.hub.rglob('*') if p.is_file()};r=self.m.bulk_candidates(self.hub,self.native)
        self.assertEqual(len(r['eligible']),1);self.assertEqual(r['eligible'][0]['group_id'],GID);self.assertEqual(r['eligible'][0]['top_group'],'top')
        self.assertEqual(before,{str(p):p.read_bytes() for p in self.hub.rglob('*') if p.is_file()});self.assertEqual(self.native.writes,[])
    def test_bulk_broken_binding_and_cancel_remain_blocked(self):
        self.assertTrue(callable(getattr(self.m,'bulk_candidates',None)))
        for kind in ['missing','cancel','foreign']:
            with self.subTest(kind=kind):
                self.setUp()
                if kind=='missing':self.config['projects']['demo']['tasks']['t']['reminder_id']='missing'
                elif kind=='cancel':self.config['projects']['demo']['tasks']['t']['cancellation']={}
                else:self.native.rows['task']['notes']='Hub project: foreign'
                self.f.save();r=self.m.bulk_candidates(self.hub,self.native);self.assertEqual(r['eligible'],[]);self.assertEqual(len(r['blocked']),1)
    def test_bulk_source_collision_reports_rename(self):
        self.assertTrue(callable(getattr(self.m,'bulk_candidates',None)))
        self.config['projects']['demo']['project_label']='Работа';self.f.save();r=self.m.bulk_candidates(self.hub,self.native)
        self.assertEqual(r['eligible'][0]['rename']['new_name'],'Работа — прежний список')
    def test_bulk_unallowed_group_and_destination_conflict(self):
        self.assertTrue(callable(getattr(self.m,'bulk_candidates',None)))
        for kind in ['permission','duplicate','card']:
            with self.subTest(kind=kind):
                self.setUp()
                if kind=='permission':(self.hub/'ai/groups.json').write_text('[]')
                elif kind=='card':(self.hub/'ai/project-cards/demo.md').write_text('Project ID: demo\nStatus: active\nprimary_archiproject: top\n')
                else:self.native.lists.append(dict(id=str(uuid.uuid4()),name='Проект',account_id=AID,group_id=GID))
                r=self.m.bulk_candidates(self.hub,self.native);self.assertFalse(r['eligible']);self.assertEqual(len(r['blocked']),1)

    def test_existing_project_list_requires_exact_roots(self):
        b=self.config['projects']['demo'];b.update(layout='project_list',parent_id=None,native_group_id=GID,list_name='Проект')
        self.native.lists[0]['name']='Проект'
        for r in self.native.rows.values():r['list']='Проект';r['parent_id']=None
        self.config['structure']['list_roles'][LID]=dict(kind='project',project_id='demo');self.f.save()
        r=self.m.bulk_candidates(self.hub,self.native);self.assertEqual(len(r['existing_project_lists']),1)
        self.native.rows['task']['parent_id']='parent';r=self.m.bulk_candidates(self.hub,self.native)
        self.assertEqual(r['existing_project_lists'],[]);self.assertEqual(len(r['blocked']),1)
    def test_duplicate_registered_target_names_block_both(self):
        self.config['projects']['other']=dict(list_id=LID,list_name='Работа',parent_id='neighbor',project_label='Проект',tasks={},history={})
        project=self.hub/'projects/other';project.mkdir();reg=self.hub/'ai/project-registry.md';reg.write_text(reg.read_text()+'## other\nStatus: active\nPath: '+str(project)+'\nCard: ai/project-cards/other.md\n')
        (self.hub/'ai/project-cards/other.md').write_text('Project ID: other\nStatus: active\nprimary_archiproject: canonical\n')
        self.config['structure']['projects']['other']=dict(group='canonical',list_id=LID);self.f.save()
        r=self.m.bulk_candidates(self.hub,self.native);self.assertEqual(r['eligible'],[]);self.assertEqual(len(r['blocked']),2)
    def test_old_outcome_resume_and_permission_types(self):
        p=self.prepare();old=self.native.call
        def fail(tool,args):
            if tool=='manage_list':raise TimeoutError('before effect')
            return old(tool,args)
        self.native.call=fail
        with self.assertRaises(TimeoutError):self.apply(p)
        self.native.call=old;self.assertEqual(self.apply(p)['phase'],'complete');self.assertEqual(len(self.native.writes),1)
    def test_unknown_outcome_external_neighbor_edit_blocks_resume(self):
        p=self.prepare();self.native.fail='rename'
        with self.assertRaises(TimeoutError):self.apply(p)
        self.native.rows['neighbor']['notes']='external'
        with self.assertRaisesRegex(ValueError,'remote_changed'):self.apply(p)
        self.assertEqual(len(self.native.writes),1)

    def test_migration_advertised_batches_keep_start_and_final_guards(self):
        ids={old:str(uuid.uuid4()) for old in self.native.rows};data={}
        for old,row in self.native.rows.items():
            row=copy.deepcopy(row);row.update(id=ids[old],version='1')
            if row.get('parent_id'):row['parent_id']=ids[row['parent_id']]
            data[row['id']]=row
        binding=self.config['projects']['demo'];binding['parent_id']=ids['parent'];binding['tasks']['t']['reminder_id']=ids['task']
        h=binding['history'].pop('history');h['original_id']=ids['task'];binding['history'][ids['history']]=h;self.f.save()
        m=self.m
        class DetailedMigration(RenameFake):
            def __init__(self,old):self.__dict__=copy.deepcopy(old.__dict__);self.rows=data;self.batch=0
            def detail(self,rid):
                row={k:copy.deepcopy(v) for k,v in self.rows[rid].items() if v is not None};children=[dict(id=r['id'],title=r['title'],**({'completed':True} if r['completed'] else {})) for r in self.rows.values() if r.get('parent_id')==rid]
                if children:row['subtasks']=children
                return row
            def call(self,tool,args):
                if tool=='list_lists':
                    value=super().call(tool,args);value['detailed_reminder_snapshot']=True;return value
                if tool=='get_reminder':return self.detail(args['id'])
                if tool=='find_reminders':
                    values=[self.detail(rid) for rid,r in self.rows.items() if r['list_id']==args['list']]
                    if args.get('detail'):self.batch+=1
                    else:values=[m.summary_projection(r) for r in values]
                    return dict(detail=True,count=len(values),reminders=values)
                self.writes.append((tool,copy.deepcopy(args)))
                if tool=='manage_list':
                    if args['action']=='create':
                        row=dict(id=GID,name=args['list'],account_id=AID,group_id=None);self.lists.append(row)
                    else:row=self.lists[-1];row['group_id']=args['group']
                else:
                    row=self.rows[args['id']];row.update(list_id=args['list'],list='Проект',parent_id=None,version=str(int(row['version'])+1))
                return copy.deepcopy(row)
        native=DetailedMigration(self.native);p=self.m.permission_preview(self.hub,'Проект');self.m.permission_apply(p['plan'],p['sha256'],True)
        p=self.m.preview(self.hub,'demo','Проект',GID,native);native.batch=0
        self.assertEqual(self.m.apply(p['plan'],p['sha256'],True,native)['phase'],'complete')
        self.assertEqual(native.batch,10)
        self.assertEqual(sum(r['list_id']==GID for r in native.rows.values()),3)

    def test_existing_project_list_validates_all_marked_identities(self):
        b=self.config['projects']['demo'];b.update(layout='project_list',parent_id=None,native_group_id=GID,list_name='Проект')
        b['tasks']['other']={'reminder_id':'unbound'};self.native.lists[0]['name']='Проект'
        for row in self.native.rows.values():row.update(list='Проект',parent_id=None)
        self.config['structure']['list_roles'][LID]=dict(kind='project',project_id='demo');self.f.save()
        self.native.rows['task']['notes']='Хаб: '+self.m.load_sync().compact_code('demo','t')
        self.native.rows['neighbor']['notes']='Обычная пользовательская строка'
        self.assertEqual(len(self.m.bulk_candidates(self.hub,self.native)['existing_project_lists']),1)
        original=copy.deepcopy(self.native.rows)
        cases=[('neighbor','--- Hub metadata ---\nHub Task ID: stranger\nHub project: foreign\n--- /Hub metadata ---'),
               ('task','Хаб: '+self.m.load_sync().compact_code('demo','other')),
               ('neighbor','Hub project: demo\nHub project: foreign')]
        for rid,notes in cases:
            with self.subTest(rid=rid,notes=notes):
                self.native.rows=copy.deepcopy(original);self.native.rows[rid]['notes']=notes
                result=self.m.bulk_candidates(self.hub,self.native)
                self.assertEqual(result['existing_project_lists'],[]);self.assertEqual(len(result['blocked']),1)

class DetailFake:
    def __init__(self):
        self.calls=[];self.rows=[dict(id=AID,list_id=LID,list='Работа',title='Row',version='1')];self.bad=None;self.support=True
    def call(self,tool,args):
        self.calls.append((tool,copy.deepcopy(args)))
        if tool=='list_lists':return dict(lists=[dict(id=LID,name='Работа',account_id=AID)],groups=[],detailed_reminder_snapshot=self.support)
        if tool=='get_reminder':return copy.deepcopy(next(r for r in self.rows if r['id']==args['id']))
        rows=copy.deepcopy(self.rows)
        if not args.get('detail'):
            for r in rows:r.pop('list_id',None);r.pop('subtasks',None)
        result=dict(reminders=rows,count=len(rows),detail=True)
        if self.bad:result.update(self.bad)
        return result
class DetailTests(unittest.TestCase):
    def setUp(self):self.m=base.module();self.native=DetailFake()
    def test_boundary_batch_one_process_and_step_cache(self):
        self.m.metadata(self.native);self.m.reset_cache(self.native);self.m.rows(self.native,LID)
        self.assertEqual([x for x in self.native.calls if x[0]=='get_reminder'],[])
        self.assertTrue(self.native.calls[-1][1].get('detail'))
        self.m.rows(self.native,LID);self.assertNotIn('detail',self.native.calls[-1][1]);self.assertEqual(len(self.native.calls),3)
        self.native.rows[0]['version']='2';self.m.rows(self.native,LID);self.assertEqual(self.native.calls[-1][0],'get_reminder')
        self.m.reset_cache(self.native);self.m.rows(self.native,LID);self.assertTrue(self.native.calls[-1][1]['detail'])
    def test_promised_malformed_batch_never_falls_back(self):
        for bad in [dict(detail=False),dict(count=True),dict(reminders={}),dict(more=1),dict(reminders=[{}]),dict(reminders=[dict(id='bad',version='1',list_id=LID,title='x')])]:
            with self.subTest(bad=bad):
                self.setUp();self.m.metadata(self.native);self.native.bad=bad
                with self.assertRaises(ValueError):self.m.rows(self.native,LID)
                self.assertFalse(any(x[0]=='get_reminder' for x in self.native.calls))
    def test_absent_capability_keeps_legacy_get(self):
        self.native.support=False;self.m.metadata(self.native);self.m.rows(self.native,LID)
        self.assertEqual(self.native.calls[-1][0],'get_reminder')
    def test_derived_children_refreshed_despite_same_version(self):
        self.native.rows[0]['subtasks']=[dict(id=GID,title='Child')];self.native.rows.append(dict(id=GID,list_id=LID,list='Работа',title='Child',version='1',parent_id=AID));self.m.metadata(self.native);self.m.rows(self.native,LID)
        self.native.rows[0]['subtasks'][0]['title']='Changed';self.native.rows[1]['title']='Changed';r=self.m.rows(self.native,LID)
        self.assertEqual(r[AID]['subtasks'][0]['title'],'Changed');self.assertTrue(self.native.calls[-1][1].get('detail'))

    def test_detailed_snapshot_duplicate_and_derived_membership_rejected(self):
        for kind in ['duplicate','child','list','version']:
            with self.subTest(kind=kind):
                self.setUp();self.m.metadata(self.native)
                if kind=='duplicate':self.native.rows.append(copy.deepcopy(self.native.rows[0]))
                elif kind=='child':self.native.rows[0]['subtasks']=[dict(id=GID,title='Missing child')]
                elif kind=='list':self.native.rows[0]['list_id']=GID
                else:self.native.rows[0]['version']=1
                with self.assertRaises(ValueError):self.m.rows(self.native,LID)
    def test_empty_parent_cache_refreshes_new_child_without_version_change(self):
        self.m.metadata(self.native);self.m.rows(self.native,LID)
        self.native.rows[0]['subtasks']=[dict(id=GID,title='Child')]
        self.native.rows.append(dict(id=GID,list_id=LID,list='Работа',title='Child',version='1',parent_id=AID))
        result=self.m.rows(self.native,LID);self.assertEqual(result[AID].get('subtasks'),[dict(id=GID,title='Child')])
    def test_detailed_envelope_counter_types_are_strict(self):
        for bad in [dict(more=False),dict(more=-1),dict(has_more=0)]:
            with self.subTest(bad=bad):
                self.setUp();self.m.metadata(self.native);self.native.bad=bad
                with self.assertRaises(ValueError):self.m.rows(self.native,LID)

    def test_advertised_detail_rejects_malformed_known_fields(self):
        cases=[('completed','false'),('parent_id','not-a-uuid'),('images',[9]),('notes',3),
               ('flagged',1),('urgent',None),('shared_list','true'),('tags',[9]),('due',3),
               ('images',[dict(id=AID,type='image/png',width=True,height=2,bytes=3)]),
               ('early_alerts',[dict(before='1',unit='minutes')]),('repeat',dict(frequency='weekly',interval=True)),
               ('location',dict(title='Place',latitude='bad',longitude=1,radius=2,when='arriving')),
               ('when_messaging',dict(phones=['123'],emails=[9])),('urls',[3]),('alarms',[3]),('completed_at',3)]
        for field,value in cases:
            with self.subTest(field=field,value=value):
                self.setUp();self.native.rows[0][field]=value;self.m.metadata(self.native)
                with self.assertRaises(ValueError):self.m.rows(self.native,LID)
                self.assertFalse(any(tool=='get_reminder' for tool,args in self.native.calls))
                self.assertFalse(getattr(self.native,'_migration_detail_cache',{}))
    def test_advertised_child_completion_requires_boolean(self):
        self.native.rows[0]['subtasks']=[dict(id=GID,title='Child',completed=0)]
        self.native.rows.append(dict(id=GID,list_id=LID,list='Работа',title='Child',version='1',parent_id=AID))
        self.m.metadata(self.native)
        with self.assertRaises(ValueError):self.m.rows(self.native,LID)
    def test_advertised_parent_reference_requires_member(self):
        self.native.rows[0]['parent_id']=GID;self.m.metadata(self.native)
        with self.assertRaises(ValueError):self.m.rows(self.native,LID)
    def test_actual_optional_detail_shapes_are_preserved(self):
        row=self.native.rows[0];row.update(completed=True,flagged=True,urgent=True,shared_list=True,notes='Text',
            due='2026-10-26',start='2026-10-26',completed_at='2026-10-26T12:00:00Z',priority='high',section='Section',assigned_to='User',
            tags=['Tag'],url='https://example.test/',urls=['https://example.test/','https://example.test/2'],alarms=['2026-10-26'],
            early_alerts=[dict(before=1,unit='minutes')],images=[dict(id=GID,type='image/png',width=10,height=20,bytes=30)],
            repeat=dict(frequency='weekly',interval=1,days_of_week=['mon'],days_of_month=[1],months=[1],until='2027-01-01',count=3),
            location=dict(title='Place',latitude=1.0,longitude=2.0,radius=3.0,when='arriving',address='Address'),
            when_messaging=dict(phones=['123'],emails=['test@example.test']))
        self.m.metadata(self.native)
        try:result=self.m.rows(self.native,LID)
        except ValueError as exc:self.fail(str(exc))
        self.assertEqual(result[AID],row)
