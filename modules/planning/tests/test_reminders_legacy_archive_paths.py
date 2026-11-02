"""Исторические пути берутся только из того же неизменяемого плана архива."""
import copy
import json
import unittest
import test_reminders_authority_final_gate as fixture


class LegacyArchivePathTests(unittest.TestCase):
    def setUp(self):
        self.base=fixture.FinalAuthorityGateTests('runTest');self.base.setUp();self.addCleanup(self.base.doCleanups)
        self.f=self.base.f;self.helper=self.base.helper
        self.path,sha=self.f.plan();self.f.run_apply(self.path,sha)
        self.modern=json.loads(self.path.read_text())
        self.legacy=copy.deepcopy(self.modern)
        self.legacy.pop('group_ids_path');self.legacy.pop('group_permissions_path')
        self.assertIsInstance(self.legacy['config_before'],str)

    def install(self,plan):
        # Только синтетическая квитанция: новый старый формат запечатывается до проверки.
        self.path.write_text(json.dumps(plan,ensure_ascii=False))
        config=self.f.current();config['projects']['demo']['archive']['token']=self.base.a.digest(self.path.read_bytes())
        self.f.savec(config)
        return config

    def local(self,plan):
        config=self.install(plan)
        historical=self.helper._historical(self.f.h,config,'demo')
        return self.helper._local(self.f.h,config,'demo',*historical,True)

    def test_legacy_snapshot_paths_allow_preview_without_rewriting_receipt(self):
        config=self.install(self.legacy);before=self.path.read_bytes();token=config['projects']['demo']['archive']['token']
        result=self.helper.preview(self.f.h,'Принять архив с прежними доказанными путями.',self.f.native)
        self.assertIn('demo',result['archives'])
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(self.f.current()['projects']['demo']['archive']['token'],token)
        self.assertEqual(self.local(self.legacy),self.f.h/'projects/demo')

    def test_missing_wrong_or_malformed_snapshot_paths_are_unverified(self):
        before=json.loads(self.legacy['config_before'])
        for key in ('group_ids_allowlist_file','groups_allowlist_file'):
            for value in (None,27,'relative.json',str(self.f.h/'ai/foreign-path.json')):
                changed=copy.deepcopy(before);changed['structure'][key]=value
                plan=dict(self.legacy,config_before=json.dumps(changed))
                with self.subTest(key=key,value=value),self.assertRaisesRegex(ValueError,'unverified|pin_path_changed'):self.local(plan)
            changed=copy.deepcopy(before);changed['structure'].pop(key)
            with self.subTest(missing=key),self.assertRaisesRegex(ValueError,'unverified'):self.local(dict(self.legacy,config_before=json.dumps(changed)))
        for value in (None,{},'not json','[]','null','{"structure":null}'):
            with self.subTest(snapshot=value),self.assertRaisesRegex(ValueError,'unverified'):self.local(dict(self.legacy,config_before=value))

    def test_present_invalid_top_level_path_never_uses_valid_snapshot(self):
        for key in ('group_permissions_path','group_ids_path'):
            for value in (None,12,'relative.json',str(self.f.h/'ai/foreign-path.json')):
                with self.subTest(key=key,value=value),self.assertRaisesRegex(ValueError,'unverified|pin_path_changed'):
                    self.local(dict(self.legacy,**{key:value}))
        # Современные явные пути не требуют разбора старого снимка.
        self.assertEqual(self.local(dict(self.modern,config_before='not json')),self.f.h/'projects/demo')


if __name__=='__main__':unittest.main()
