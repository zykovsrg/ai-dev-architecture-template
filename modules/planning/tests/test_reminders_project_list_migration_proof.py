"""Точная terminal-стыковка принятого свидетельства и миграции."""
import copy,json,types,unittest
from unittest.mock import patch
from pathlib import Path
import test_reminders_project_list_migration as old
import test_reminders_cancel as cancellation
class MigrationProofTests(old.MigrationTests):
    def setUp(self):
        super().setUp()
        # Mutation runs select the same copied migration source as the cancellation coordinator.
        import importlib.util
        path=Path(cancellation.m.__file__).with_name('reminders_project_lists.py');spec=importlib.util.spec_from_file_location('migration_proof_subject',path);self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
    def completed_pin(self):
        p=self.prepare();self.apply(p);cfg=self.hub/'ai/reminders-sync.json';value=json.loads(cfg.read_text());value['project_list_verification_sha256']='a'*64;cfg.write_text(self.m.encoded(value));return p,cfg,value
    def verifier(self,reject=False):
        sync=self.m.load_sync();cancel=sync.cancellation_module()
        def accepted(*args):
            if reject:raise ValueError('verification_evidence_rejected')
            return dict(list_id='new',account_id='account',group_id='group')
        cancel.verification_module=lambda:types.SimpleNamespace(accepted=accepted);sync.cancellation_module=lambda:cancel
        return patch.object(self.m,'load_sync',lambda:sync)
    def test_final_account_persisted(self):
        p=self.prepare();self.apply(p);value=json.loads((self.hub/'ai/reminders-sync.json').read_text());self.assertEqual(value['projects']['demo']['account_id'],'account')
    def test_terminal_exact_pin_no_native_writes(self):
        p,cfg,value=self.completed_pin();before=cfg.read_bytes();writes=len(self.native.writes)
        with self.verifier():self.apply(p)
        self.assertEqual(cfg.read_bytes(),before);self.assertEqual(len(self.native.writes),writes)
    def test_terminal_unrelated_field_rejected(self):
        p,cfg,value=self.completed_pin();value['extra']='bad';cfg.write_text(self.m.encoded(value))
        with self.verifier(),self.assertRaisesRegex(ValueError,'config_changed'):self.apply(p)
    def test_terminal_unaccepted_proof_rejected(self):
        p,cfg,value=self.completed_pin()
        with self.verifier(True),self.assertRaisesRegex(ValueError,'evidence'):self.apply(p)
    def test_pending_pin_still_rejected(self):
        p=self.prepare();self.m.apply(p['plan'],p['sha256'],True,self.native,prepare_only=True);cfg=self.hub/'ai/reminders-sync.json';value=json.loads(cfg.read_text());value['project_list_verification_sha256']='a'*64;cfg.write_text(self.m.encoded(value))
        with self.verifier(),self.assertRaisesRegex(ValueError,'config_changed'):self.m.apply(p['plan'],p['sha256'],True,self.native,prepare_only=True)
for name in dir(old.MigrationTests):
    if name.startswith('test_') and name not in MigrationProofTests.__dict__:setattr(MigrationProofTests,name,None)
