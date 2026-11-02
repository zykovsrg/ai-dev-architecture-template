"""Семейство проверенного примитива: текущая область проверяется отдельно."""
import copy,json,unittest
import test_reminders_project_list_verification as base
import test_reminders_cancel as legacy
class FamilyTests(unittest.TestCase):
 def setUp(self):
  self.f=base.VerificationTests();self.f.setUp();self.addCleanup(self.f.doCleanups);self.c=base.c;self.v=base.v
 def proof(self):
  self.f.test_accepted_proof_survives_new_task();return self.f.config
 def test_sealed_witness_survives_permission_extension(self):
  config=self.proof();path=self.f.hub/'ai/reminders-standard-allowlist.json';data=json.loads(path.read_text());data['names'].append('Другой утверждённый проект');path.write_text(self.c.encoded(data))
  try:proof=self.v.accepted(self.c,self.f.hub,config)
  except ValueError as error:self.fail('Valid extension rejected: '+str(error))
  self.assertEqual(proof['account_id'],base.AID)
 def test_family_capability_same_account_other_list_and_group(self):
  scope=dict(family='same_os_executor_account',account_id=base.AID)
  class Native:
   def call(self,*args):return dict(protocol=1,supported_versions=[1,2],project_list_same_uuid_restore_verified=True,project_list_verified_scope=scope,atomic_version_check=True)
  try:self.c.capabilities(Native(),version=2,items=[dict(list_id=base.GID,account_id=base.AID,native_group_id=base.LID)])
  except ValueError as error:self.fail('Valid family rejected: '+str(error))
  with self.assertRaises(ValueError):self.c.capabilities(Native(),version=2,items=[dict(list_id=base.GID,account_id=base.LID,native_group_id=base.AID)])
 def test_family_witness_keeps_runtime_and_permission_guards(self):
  config=self.proof();path=self.f.hub/'executor';path.write_bytes(b'foreign')
  with self.assertRaises(ValueError):self.v.accepted(self.c,self.f.hub,config)
