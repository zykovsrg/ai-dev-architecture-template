"""Проверка bootstrap и журнала целиком на искусственных данных."""
import copy,json,tempfile,unittest,uuid
from pathlib import Path
from unittest.mock import patch
import test_reminders_cancel as legacy
from test_reminders_project_list_cancellation import RootNative,AID,GID
c=legacy.m;v=c.verification_module();RID=legacy.RID;LID=legacy.LID
OP='dd69f50c-9e7b-4842-83cc-8eea5788cccc'
MID='00000000-0000-0000-0000-000000000099'
class VerificationNative(RootNative):
    def __init__(self):
        super().__init__();self.data={};self.meta['lists'][0]['name']='Система контента';self.created=0
    def call(self,tool,args):
        if tool=='create_reminder':
            self.created+=1;self.data[RID]=dict(id=RID,list_id=LID,list='Система контента',title=args['title'],notes=args['notes'],version='one');return copy.deepcopy(self.data[RID])
        return super().call(tool,args)
class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=getattr(self,'fixture_dir',None));self.addCleanup(self.temp.cleanup);self.hub=Path(self.temp.name).resolve();(self.hub/'ai').mkdir()
        project=self.hub/'projects/content-system';(project/'ai').mkdir(parents=True)
        (self.hub/'ai/project-registry.md').write_text(f'## content-system\nStatus: active\nPath: {project}\n')
        old=self.hub/'ai/reminders-allowlist.json';old.write_text('{"names":["Работа"]}')
        standard=self.hub/'ai/reminders-standard-allowlist.json';standard.write_text('{"names":["Работа","Система контента"]}')
        binary=self.hub/'executor';binary.write_bytes(b'artificial-test-executor')
        self.config=dict(binary=str(binary),cancellation_binary=str(binary),allowlist_file=str(old),cancellation_policy='no_concurrent_edits',projects={'content-system':dict(list_id=str(uuid.UUID(int=50)),list_name='Работа',parent_id=str(uuid.UUID(int=51)),tasks={})})
        self.path=self.hub/'ai/reminders-project-lists'/MID/'plan.json';self.path.parent.mkdir(parents=True)
        self.migration=dict(kind='migration',operation=MID,hub=str(self.hub),project='content-system',list_name='Система контента',account_id=AID,group_id=GID,config_raw=c.encoded(self.config),permission={'after':standard.read_text()})
        self.path.write_text(c.encoded(self.migration));self.sha=c.digest(self.path.read_bytes());self.ms=dict(sha256=self.sha,phase='destination_ready',steps={},list_id=LID,group_done=True)
        self.path.with_name('state.json').write_text(c.encoded(self.ms));self.config['project_list_migrations_pending']={'content-system':self.sha}
        self.cfg=self.hub/'ai/reminders-sync.json';self.raw=' '+json.dumps(self.config,ensure_ascii=False)+'\n';self.cfg.write_text(self.raw);self.native=VerificationNative()
    def create(self):return v.bootstrap(c,self.hub,self.config,self.native,OP,str(self.path),self.sha,True)
    def prepare(self):self.create();return v.prepare(c,self.hub,self.config,self.native,OP,True)
    def step(self,p,action,token=None):return v.step(c,self.hub,p['path'],p['sha256'],self.config,self.native,action,True,token)
    def cycle(self):
        p=self.prepare();self.step(p,'delete');token=self.step(p,'restore-preview')['sha256'];self.step(p,'restore',token);self.step(p,'cleanup');return p
    def test_complete_cycle_exact_bytes(self):
        p=self.cycle();self.assertEqual(self.native.created,1);self.assertEqual([t for t,a in self.native.calls if t in {'hub_cancel_reminder','hub_restore_reminder'}],['hub_cancel_reminder','hub_restore_reminder','hub_cancel_reminder'])
        self.assertEqual(list((self.hub/'projects/content-system/ai').iterdir()),[])
        v.close(c,self.hub,p['path'],p['sha256'],self.config,self.native,True);self.assertEqual(self.cfg.read_text(),self.raw);self.assertEqual(c.pending_projects(self.hub,self.config),set())
    def test_no_consent(self):
        with self.assertRaisesRegex(ValueError,'consent'):v.bootstrap(c,self.hub,self.config,self.native,OP,str(self.path),self.sha,False)
        self.assertEqual(self.native.created,0)
    def test_no_second_create(self):
        self.create()
        with self.assertRaises(ValueError):self.create()
        self.assertEqual(self.native.created,1)
    def test_wrong_migration_phase(self):
        self.ms['phase']='moving';self.path.with_name('state.json').write_text(c.encoded(self.ms))
        with self.assertRaisesRegex(ValueError,'destination'):self.create()
        self.assertEqual(self.native.created,0)
    def test_existing_moved_step(self):
        self.ms['steps']={RID:{'status':'done'}};self.path.with_name('state.json').write_text(c.encoded(self.ms))
        with self.assertRaisesRegex(ValueError,'destination'):self.create()
    def test_marker_substitution(self):
        self.create();self.native.data[RID]['title']='Чужая задача '+OP
        with self.assertRaisesRegex(ValueError,'snapshot'):v.prepare(c,self.hub,self.config,self.native,OP,True)
    def test_binding_substitution(self):
        p=self.prepare();self.config['project_list_verifications'][OP]['reminder_id']=AID;self.cfg.write_text(c.encoded(self.config))
        with self.assertRaisesRegex(ValueError,'binding'):self.step(p,'delete')
        self.assertNotIn(RID,self.native.deleted)
    def test_real_binding_collision(self):
        self.config['projects']['content-system']['tasks']['real']={'reminder_id':RID}
        original=copy.deepcopy(self.config);original.pop('project_list_migrations_pending');self.migration['config_raw']=c.encoded(original);self.path.write_text(c.encoded(self.migration));self.sha=c.digest(self.path.read_bytes());self.ms['sha256']=self.sha;self.path.with_name('state.json').write_text(c.encoded(self.ms));self.config['project_list_migrations_pending']['content-system']=self.sha;self.raw=c.encoded(self.config);self.cfg.write_text(self.raw)
        with self.assertRaisesRegex(ValueError,'collision'):self.create()
    def test_cleanup_without_restore(self):
        p=self.prepare();self.step(p,'delete')
        with self.assertRaisesRegex(ValueError,'order'):self.step(p,'cleanup')
    def test_cleanup_not_repeated(self):
        p=self.cycle()
        with self.assertRaisesRegex(ValueError,'already_done'):self.step(p,'cleanup')
        self.assertEqual(sum(t=='hub_cancel_reminder' for t,a in self.native.calls),2)
    def test_stale_restore_token(self):
        p=self.prepare();self.step(p,'delete');token=self.step(p,'restore-preview')['sha256'];self.config['other']='changed';self.cfg.write_text(c.encoded(self.config))
        with self.assertRaises(ValueError):self.step(p,'restore',token)
    def test_close_requires_cleaned(self):
        p=self.prepare()
        with self.assertRaisesRegex(ValueError,'not_cleaned'):v.close(c,self.hub,p['path'],p['sha256'],self.config,self.native,True)
    def test_unknown_delete_recovery(self):
        p=self.prepare();self.native.fail_after='hub_cancel_reminder'
        with self.assertRaises(TimeoutError):self.step(p,'delete')
        self.step(p,'delete');self.assertEqual(sum(t=='hub_cancel_reminder' for t,a in self.native.calls),1)

    def test_witness_requires_review(self):
        p=self.cycle();v.close(c,self.hub,p['path'],p['sha256'],self.config,self.native,True);journal=c.digest(Path(p['path']).with_name('state.json').read_bytes())
        with self.assertRaisesRegex(ValueError,'acceptance'):v.witness(c,self.hub,p['path'],p['sha256'],journal,True,False)
        self.assertFalse((self.hub/'ai/reminders-project-list-verification.json').exists())
    def test_pin_requires_completed_migration(self):
        p=self.cycle();v.close(c,self.hub,p['path'],p['sha256'],self.config,self.native,True);journal=c.digest(Path(p['path']).with_name('state.json').read_bytes());proof=v.witness(c,self.hub,p['path'],p['sha256'],journal,True,True)
        with self.assertRaisesRegex(ValueError,'completed_migration'):v.pin(c,self.hub,c.digest(self.cfg.read_bytes()),proof['sha256'],True)
    def test_accepted_proof_survives_new_task(self):
        p=self.cycle();v.close(c,self.hub,p['path'],p['sha256'],self.config,self.native,True);journal=c.digest(Path(p['path']).with_name('state.json').read_bytes());proof=v.witness(c,self.hub,p['path'],p['sha256'],journal,True,True)
        self.config['projects']['content-system'].update(layout='project_list',parent_id=None,list_id=LID,list_name='Система контента',account_id=AID,native_group_id=GID);self.config['standard_allowlist_file']=str(self.hub/'ai/reminders-standard-allowlist.json');self.config['project_list_migrations_pending'].clear();self.config['project_list_migrations_completed']={'content-system':self.sha};self.ms['phase']='complete';self.path.with_name('state.json').write_text(c.encoded(self.ms));self.cfg.write_text(c.encoded(self.config));v.pin(c,self.hub,c.digest(self.cfg.read_bytes()),proof['sha256'],True)
        self.config=json.loads(self.cfg.read_text());self.config['projects']['content-system']['tasks']['new-task']={'reminder_id':AID};self.config['unrelated']='new';self.cfg.write_text(c.encoded(self.config));self.assertEqual(v.accepted(c,self.hub,self.config)['list_id'],LID)

    def test_prepare_recovery_keeps_immutable_plan(self):
        p=self.prepare();plan=Path(p['path']).read_bytes();state=Path(p['path']).with_name('state.json').read_bytes();again=v.prepare(c,self.hub,self.config,self.native,OP,True);self.assertEqual(again['sha256'],p['sha256']);self.assertEqual(Path(p['path']).read_bytes(),plan);self.assertEqual(Path(p['path']).with_name('state.json').read_bytes(),state)

    def confirmation_recovery(self,stage):
        p=self.prepare();token=None
        if stage!='delete':
            self.step(p,'delete');token=self.step(p,'restore-preview')['sha256']
        if stage=='cleanup':self.step(p,'restore',token)
        original=c.native_status;reads=0
        def interrupted(*args,**kwargs):
            nonlocal reads
            reads+=1
            if reads==3:raise TimeoutError('confirmation read failed')
            return original(*args,**kwargs)
        with patch.object(c,'native_status',side_effect=interrupted):
            with self.assertRaisesRegex(TimeoutError,'confirmation'):self.step(p,stage,token)
        statepath=Path(p['path']).with_name('state.json');state=json.loads(statepath.read_text())
        self.assertIn('after_'+stage,[e['stage'] for e in state['events']]);self.assertNotIn('confirmed_'+stage,[e['stage'] for e in state['events']])
        effects=[t for t,a in self.native.calls if t in {'hub_cancel_reminder','hub_restore_reminder'}]
        self.step(p,stage,token)
        self.assertEqual([t for t,a in self.native.calls if t in {'hub_cancel_reminder','hub_restore_reminder'}],effects)
        events=json.loads(statepath.read_text())['events'];self.assertEqual(sum(e['stage']=='confirmed_'+stage for e in events),1)
        if stage=='delete':token=self.step(p,'restore-preview')['sha256'];self.step(p,'restore',token)
        if stage!='cleanup':self.step(p,'cleanup')
        with self.assertRaisesRegex(ValueError,'already_done'):self.step(p,'cleanup')
        self.assertEqual(self.native.created,1);self.assertEqual([t for t,a in self.native.calls if t in {'hub_cancel_reminder','hub_restore_reminder'}],['hub_cancel_reminder','hub_restore_reminder','hub_cancel_reminder'])
        v.close(c,self.hub,p['path'],p['sha256'],self.config,self.native,True);self.assertEqual(self.cfg.read_bytes(),self.raw.encode())
        proof=v.witness(c,self.hub,p['path'],p['sha256'],c.digest(statepath.read_bytes()),True,True);self.assertTrue(Path(proof['path']).exists())
    def test_delete_confirmation_recovery(self):self.confirmation_recovery('delete')
    def test_restore_confirmation_recovery(self):self.confirmation_recovery('restore')
    def test_cleanup_confirmation_recovery(self):self.confirmation_recovery('cleanup')

    def incomplete_confirmation(self):
        p=self.prepare();self.step(p,'delete');statepath=Path(p['path']).with_name('state.json');state=json.loads(statepath.read_text());state['events']=[e for e in state['events'] if e['stage']!='confirmed_delete'];statepath.write_text(c.encoded(state));return p,statepath,state
    def test_confirmation_requires_exact_saved_result(self):
        p,path,state=self.incomplete_confirmation()
        for event in state['events']:
            if event['stage']=='after_delete':event['remote']['version']='foreign'
        path.write_text(c.encoded(state));before=path.read_bytes();effects=list(self.native.calls)
        with self.assertRaisesRegex(ValueError,'confirmation_proof_missing'):self.step(p,'delete')
        self.assertEqual(path.read_bytes(),before);self.assertEqual(sum(t=='hub_cancel_reminder' for t,a in self.native.calls),1)
    def test_confirmation_requires_fresh_exact_result(self):
        p,path,state=self.incomplete_confirmation();before=path.read_bytes();self.native.data[RID]['version']='foreign'
        with self.assertRaisesRegex(ValueError,'completed_readback_changed'):self.step(p,'delete')
        self.assertEqual(path.read_bytes(),before);self.assertEqual(sum(t=='hub_cancel_reminder' for t,a in self.native.calls),1)

    def test_close_requires_cleanup_confirmation(self):
        p=self.cycle();path=Path(p['path']).with_name('state.json');state=json.loads(path.read_text());state['events']=[e for e in state['events'] if e['stage']!='confirmed_cleanup'];path.write_text(c.encoded(state));before=self.cfg.read_bytes()
        with self.assertRaisesRegex(ValueError,'cleanup_not_confirmed'):v.close(c,self.hub,p['path'],p['sha256'],self.config,self.native,True)
        self.assertEqual(self.cfg.read_bytes(),before)
        self.step(p,'cleanup');v.close(c,self.hub,p['path'],p['sha256'],self.config,self.native,True);self.assertEqual(self.cfg.read_bytes(),self.raw.encode())
