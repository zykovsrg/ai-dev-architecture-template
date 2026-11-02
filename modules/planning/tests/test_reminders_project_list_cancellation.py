"""Искусственный Хаб и приложение; никаких реальных задач или разрешений."""
import copy,json,unittest
from pathlib import Path
from unittest.mock import patch
from test_reminders_cancel import CancellationTests, Native, m, RID, PID, LID, TID
AID='00000000-0000-0000-0000-000000000004'
GID='00000000-0000-0000-0000-000000000005'
class RootNative(Native):
    def __init__(self):
        super().__init__();del self.data[PID];self.data[RID].pop('parent_id');self.data[RID].pop('repeat');self.verified=True
        self.meta={'lists':[{'id':LID,'name':'Работа','account_id':AID,'group_id':GID,'shared':False}],'groups':[{'id':GID,'name':'Group','account_id':AID}]}
    def call(self,tool,args):
        if tool=='list_lists':return copy.deepcopy(self.meta)
        if tool=='hub_cancel_capabilities':return dict(protocol=1,supported_versions=[1,2],atomic_version_check=True,same_uuid_restore_verified=True,project_list_same_uuid_restore_verified=self.verified,project_list_verified_scope=dict(list_id=LID,account_id=AID,group_id=GID))
        result=super().call(tool,args)
        if tool=='hub_cancel_status' and result.get('state')=='deleted':result['projected_binding']=True
        return result
class ProjectListCancellationTests(CancellationTests):
    # Only the tests in this class run: inherited v1 scenarios have separate coverage.
    def setUp(self):
        super().setUp();self.native=RootNative();self.config['projects']['demo'].update(layout='project_list',parent_id=None,account_id=AID,native_group_id=GID)
        self.config['structure']=dict(list_roles={LID:dict(kind='project',project_id='demo')},projects={'demo':dict(list_id=LID)})
        self.standard=self.hub/'ai/reminders-standard-allowlist.json';self.standard.write_text(self.allow.read_text());self.config['standard_allowlist_file']=str(self.standard);self.save()
    def save(self):self.config_path.write_text(json.dumps(self.config))
    def test_root_cycle(self):
        plan=self.prepare();self.assertEqual(plan['plan']['version'],2);self.apply(plan)
        token=m.restore_preview(self.hub,plan['path'],plan['sha256'],self.config,self.native);self.restore(plan,token['sha256']);self.assertNotIn(RID,self.native.deleted);self.assertNotIn('parent_id',self.native.data[RID])
    def test_mixed_before_writes(self):
        self.config['projects']['legacy']=dict(list_id=AID,list_name='Работа',parent_id=PID,tasks={});self.save()
        with self.assertRaisesRegex(ValueError,'mixed'):m.preview(self.hub,self.config,[('demo',TID),('legacy','other')],self.native)
        self.assertFalse((self.hub/'ai/reminders-cancellations').exists());self.assertFalse(self.native.calls)
    def test_wrong_allowlist_path(self):
        self.config['standard_allowlist_file']=str(self.allow);self.save()
        with self.assertRaisesRegex(ValueError,'allowlist'):self.prepare()
    def test_duplicate_list(self):
        self.config['projects']['other']=copy.deepcopy(self.config['projects']['demo']);self.save()
        with self.assertRaisesRegex(ValueError,'exclusive'):self.prepare()
    def test_root_parent(self):
        self.native.data[RID]['parent_id']=PID
        with self.assertRaisesRegex(ValueError,'root'):self.prepare()
    def test_root_null_parent(self):
        self.native.data[RID]['parent_id']=None
        with self.assertRaisesRegex(ValueError,'root'):self.prepare()
    def test_root_children(self):
        self.native.data[PID]=dict(id=PID,list_id=LID,list='Работа',parent_id=RID,version='c1')
        with self.assertRaisesRegex(ValueError,'children'):self.prepare()
    def test_foreign_account(self):
        self.native.meta['lists'][0]['account_id']=GID
        with self.assertRaisesRegex(ValueError,'identity'):self.prepare()
    def test_foreign_group(self):
        self.native.meta['lists'][0]['group_id']=AID
        with self.assertRaisesRegex(ValueError,'identity'):self.prepare()
    def test_shared_list(self):
        self.native.meta['lists'][0]['shared']=True
        with self.assertRaisesRegex(ValueError,'identity'):self.prepare()
    def test_pending_migration(self):
        self.config['project_list_migrations_pending']={'demo':'a'*64};self.save()
        with self.assertRaisesRegex(ValueError,'migration'):self.prepare()
    def test_gate_false(self):
        plan=self.prepare();self.native.verified=False
        with self.assertRaisesRegex(ValueError,'capabilit'):self.apply(plan)
        self.assertNotIn(RID,self.native.deleted)
    def test_allowlist_sha(self):
        plan=self.prepare();self.standard.write_text(self.standard.read_text()+' ')
        with self.assertRaisesRegex(ValueError,'allowlist'):self.apply(plan)
    def test_verify_cancelled_full_config(self):
        plan=self.prepare();self.apply(plan);row=self.row();row['project_id']='demo';binding=self.config['projects']['demo'];link=binding['tasks'][TID]
        self.assertTrue(m.verify_cancelled_link(self.hub,row,link,binding,self.native))
        self.config['projects']['other']=copy.deepcopy(binding);self.save()
        with self.assertRaisesRegex(ValueError,'exclusive'):m.verify_cancelled_link(self.hub,row,link,binding,self.native)
    def test_missing_standard_no_fallback(self):
        self.config.pop('standard_allowlist_file');self.save()
        with self.assertRaises(ValueError):self.prepare()
        self.assertFalse(self.native.calls)
    def test_gate_wrong_scope(self):
        p=self.prepare();original=self.native.call
        def wrong(tool,args):
            value=original(tool,args)
            if tool=='hub_cancel_capabilities':value['project_list_verified_scope']['list_id']=AID
            return value
        self.native.call=wrong
        with self.assertRaisesRegex(ValueError,'capabilit'):self.apply(p)
    def test_v2_gate_independent_of_v1(self):
        p=self.prepare();original=self.native.call
        def caps(tool,args):
            value=original(tool,args)
            if tool=='hub_cancel_capabilities':value['same_uuid_restore_verified']=False
            return value
        self.native.call=caps;self.apply(p);self.assertIn(RID,self.native.deleted)
    def permission_receipt(self, names, approved=True, phase='complete'):
        import uuid
        folder=self.hub/'ai/reminders-project-lists'/str(uuid.uuid4());folder.mkdir(parents=True)
        before=self.standard.read_text();after=m.encoded({'names':names})
        plan=dict(kind='permission',hub=str(self.hub),operation=folder.name,list_name=names[-1],permission=dict(original=self.allow.read_text(),before=before,after=after,added=[n for n in names if n not in json.loads(before)['names']]))
        raw=m.encoded(plan);(folder/'plan.json').write_text(raw)
        (folder/'state.json').write_text(m.encoded(dict(sha256=m.digest(raw),approved=approved,phase=phase)))
        self.standard.write_text(after)
        return folder
    def verify_after_permission(self):
        row=self.row();row['project_id']='demo';binding=self.config['projects']['demo']
        return m.verify_cancelled_link(self.hub,row,binding['tasks'][TID],binding,self.native)
    def test_terminal_accepts_approved_permission_chain(self):
        plan=self.prepare();self.apply(plan)
        original=Path(plan['path']).read_bytes()
        self.permission_receipt(['Работа','Новый']);self.permission_receipt(['Работа','Новый','Ещё'])
        self.assertTrue(self.verify_after_permission())
        self.assertEqual(Path(plan['path']).read_bytes(),original)
        malformed=self.hub/'ai/reminders-project-lists'/'00000000-0000-0000-0000-000000000099';malformed.mkdir()
        (malformed/'plan.json').write_text('[]')
        self.assertTrue(m.terminal_allowlist_matches(self.hub,self.config,plan['plan'],m.digest(self.standard.read_bytes())))
    def test_terminal_rejects_unproved_permission_changes(self):
        plan=self.prepare();self.apply(plan);before=self.standard.read_text()
        for defect in ('unapproved','pending','tampered','gap','shrinking','wrong_hub','original'):
            with self.subTest(defect=defect):
                import shutil
                root=self.hub/'ai/reminders-project-lists'
                if root.exists():shutil.rmtree(root)
                self.standard.write_text(before)
                if defect=='shrinking':
                    self.permission_receipt(['Работа','Новый'])
                    folder=self.permission_receipt(['Работа'])
                else:folder=self.permission_receipt(['Работа','Новый'],approved=defect!='unapproved',phase='preview' if defect=='pending' else 'complete')
                path=folder/'plan.json';value=json.loads(path.read_text())
                if defect=='tampered':path.write_text(path.read_text()+' ')
                if defect in ('gap','wrong_hub','original'):
                    if defect=='gap':value['permission']['before']=m.encoded({'names':['Работа','Чужой']})
                    if defect=='wrong_hub':value['hub']='/tmp/other'
                    if defect=='original':value['permission']['original']=m.encoded({'names':['Иное']})
                    raw=m.encoded(value);path.write_text(raw)
                    state=json.loads((folder/'state.json').read_text());state['sha256']=m.digest(raw);(folder/'state.json').write_text(m.encoded(state))
                with self.assertRaisesRegex(ValueError,'allowlist'):self.verify_after_permission()
    def test_approved_extension_does_not_authorize_pending_delete(self):
        plan=self.prepare();self.permission_receipt(['Работа','Новый'])
        with self.assertRaisesRegex(ValueError,'allowlist'):self.apply(plan)
        self.assertNotIn(RID,self.native.deleted)
# Avoid inherited v1 test duplication with a v2 fixture.
for name in dir(CancellationTests):
    if name.startswith('test_') and name not in ProjectListCancellationTests.__dict__:setattr(ProjectListCancellationTests,name,None)

del CancellationTests
