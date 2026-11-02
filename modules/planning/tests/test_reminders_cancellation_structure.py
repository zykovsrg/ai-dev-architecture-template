"""Отсутствующий UUID исключается из дерева только после проверки квитанции."""
import copy,unittest
from unittest.mock import patch
import test_reminders_project_list_cancellation as root
import test_reminders_project_lists as structure_fixture
c=root.m
class ReceiptStructureTests(root.ProjectListCancellationTests):
    def structure_case(self):
        p=self.prepare();self.apply(p);self.config['structure']={'list_roles':{root.LID:{'kind':'project','project_id':'demo'}},'projects':{'demo':{'list_id':root.LID,'group':'g'}}};self.save()
        m=c.sync.structure_module();binding=self.config['projects']['demo'];snap={'lists':{root.LID:dict(name='Работа',group_id=root.GID,account_id=root.AID)},'reminders':{}}
        return m,binding,snap
    def test_verified_receipt_removes_only_deleted_target(self):
        m,binding,snap=self.structure_case();ids=m.verified_cancelled_ids(self.hub,'demo',binding,self.config,self.native);self.assertEqual(ids,{root.RID});self.assertEqual(m.validate_project_list('demo',binding,snap,self.config,cancelled_ids=ids),root.LID)
    def test_unverified_receipt_is_not_ignored(self):
        m,binding,snap=self.structure_case();binding['tasks'][root.TID]['cancellation']['plan_sha256']='0'*64;self.save()
        with self.assertRaises(ValueError):m.verified_cancelled_ids(self.hub,'demo',binding,self.config,self.native)
    def test_restored_uuid_cannot_hide_in_skip_set(self):
        m,binding,snap=self.structure_case();ids=m.verified_cancelled_ids(self.hub,'demo',binding,self.config,self.native);snap['reminders'][root.RID]=copy.deepcopy(self.native.data[root.RID])
        with self.assertRaisesRegex(ValueError,'reappeared'):m.validate_project_list('demo',binding,snap,self.config,cancelled_ids=ids)
for name in dir(root.ProjectListCancellationTests):
    if name.startswith('test_') and name not in ReceiptStructureTests.__dict__:setattr(ReceiptStructureTests,name,None)
class StructureRoutesTests(unittest.TestCase):
    def route(self,bidirectional,reject):
        f=structure_fixture.ProjectListStructureTests();f.setUp();self.addCleanup(f.doCleanups);f.structure=c.sync.structure_module();f.binding['tasks']['x']['cancellation']={'receipt':'test double; actual receipt tested separately'}
        f.case.native.rows['lp']=[row for row in f.case.native.rows['lp'] if row['id']=='old'];f.case.save_config()
        calls=[]
        def checked(hub,pid,binding,config,native):
            calls.append(pid)
            if pid!='list-project':return set()
            if reject:raise ValueError('verification_refused')
            return {'root'}
        with patch.object(f.structure,'verified_cancelled_ids',checked):result=f.run_structure(bidirectional)
        self.assertIn('list-project',calls)
        if reject:self.assertFalse(result['ok']);self.assertIn('verification_refused',str(result))
        else:self.assertTrue(result['ok'],result)
    def test_readonly_route_accepts_verified(self):self.route(False,False)
    def test_bidirectional_route_accepts_verified(self):self.route(True,False)
    def test_readonly_route_rejects_unverified(self):self.route(False,True)
    def test_bidirectional_route_rejects_unverified(self):self.route(True,True)
