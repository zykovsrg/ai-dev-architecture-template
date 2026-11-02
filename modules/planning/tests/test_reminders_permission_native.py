"""Проверка реального нативного валидатора без доступа к приложению."""
import os, subprocess, unittest, tempfile
from pathlib import Path
from test_reminders_project_list_cancellation import ProjectListCancellationTests
class NativePermissionTests(ProjectListCancellationTests):
    fixture_dir = str(Path(__file__).resolve().parent)
    def setUp(self):
        super().setUp();self.config["cancellation_policy"]="no_concurrent_edits";self.save()
        call=self.native.call
        def optimistic(tool,args):
            result=call(tool,args)
            if tool=='hub_cancel_capabilities':result.update(optimistic_version_check=True,requires_no_concurrent_edits=True)
            return result
        self.native.call=optimistic
    @classmethod
    def setUpClass(cls):
        cls.build=tempfile.TemporaryDirectory(prefix='native-scope-');cls.addClassCleanup(cls.build.cleanup)
        cls.binary=os.environ.get('NATIVE_SCOPE_CHECK',str(Path(cls.build.name)/'check'))
        if 'NATIVE_SCOPE_CHECK' not in os.environ:
            base=Path(__file__).resolve().parents[1]
            source=os.environ.get('NATIVE_SCOPE_SOURCE',str(base/'native-reminders/Sources/AppleRemindersMCP/Tools/HubCancellationPlan.swift'))
            subprocess.run(['swiftc','-module-cache-path',str(Path(cls.build.name)/'cache'),source,str(base/'tests/native_scope/main.swift'),'-o',cls.binary],check=True,capture_output=True)
    def native_scope(self, plan, mutation=False):
        return subprocess.run([self.binary,str(self.hub),str(plan['path']),plan['sha256'],self.config['projects']['demo']['tasks'][next(iter(self.config['projects']['demo']['tasks']))]['reminder_id'],'mutation' if mutation else 'read'],capture_output=True,text=True,env=dict(os.environ,HUB_REMINDERS_ALLOWED_LISTS_FILE=str(self.standard)))
    def test_native_approved_chain_read(self):
        p=self.prepare();self.apply(p);self.permission_receipt(['Работа','Новый']);self.permission_receipt(['Работа','Новый','Ещё'])
        result=self.native_scope(p);self.assertEqual(result.returncode,0,result.stderr)
    def test_native_extension_cannot_authorize_mutation(self):
        p=self.prepare();self.apply(p);self.permission_receipt(['Работа','Новый'])
        result=self.native_scope(p,True);self.assertNotEqual(result.returncode,0);self.assertIn('allowlist_checksum_mismatch',result.stderr)
    def test_native_unapproved_extension_rejected(self):
        p=self.prepare();self.apply(p);self.permission_receipt(['Работа','Новый'],approved=False)
        result=self.native_scope(p);self.assertNotEqual(result.returncode,0);self.assertIn('allowlist_checksum_mismatch',result.stderr)
for name in dir(ProjectListCancellationTests):
    if name.startswith('test_') and name not in NativePermissionTests.__dict__:setattr(NativePermissionTests,name,None)
del ProjectListCancellationTests
