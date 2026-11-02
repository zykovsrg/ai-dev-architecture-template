"""Маршрутизация разрешений, не запуск приложения."""
import json,types,unittest
from unittest.mock import patch
from pathlib import Path
import test_reminders_project_list_cancellation as root
class CancellationClientTests(root.ProjectListCancellationTests):
    def test_v2_standard_allowlist_and_groups(self):
        group=self.hub/'ai/groups.json';group.write_text('{"names":["Group"]}');self.config['structure']={'groups_allowlist_file':str(group)};plan=self.hub/'plan.json';plan.write_text('{"version":2}');native=root.m.sync.Native(self.config)
        with patch.object(root.m.sync.subprocess,'run',return_value=types.SimpleNamespace(returncode=0,stdout='{}',stderr='')) as call:native.call('hub_cancel_status',{'plan':str(plan),'plan_sha256':root.m.digest(plan.read_bytes())})
        env=call.call_args.kwargs['env'];self.assertEqual(env['HUB_REMINDERS_ALLOWED_LISTS_FILE'],str(self.standard));self.assertEqual(env['HUB_REMINDERS_ALLOWED_GROUPS_FILE'],str(group))
    def test_v1_keeps_original_allowlist(self):
        plan=self.hub/'plan.json';plan.write_text('{"version":1}');native=root.m.sync.Native(self.config)
        with patch.object(root.m.sync.subprocess,'run',return_value=types.SimpleNamespace(returncode=0,stdout='{}',stderr='')) as call:native.call('hub_cancel_status',{'plan':str(plan),'plan_sha256':root.m.digest(plan.read_bytes())})
        self.assertEqual(call.call_args.kwargs['env']['HUB_REMINDERS_ALLOWED_LISTS_FILE'],str(self.allow))
    def test_client_changed_plan_sha(self):
        plan=self.hub/'plan.json';plan.write_text('{"version":2}');native=root.m.sync.Native(self.config)
        with patch.object(root.m.sync.subprocess,'run') as call,self.assertRaisesRegex(ValueError,'checksum'):native.call('hub_cancel_status',{'plan':str(plan),'plan_sha256':'0'*64})
        call.assert_not_called()
    def test_plan_size_limit(self):
        p=self.prepare();path=Path(p['path']);path.write_bytes(path.read_bytes()+b' '*(2_097_153));sha=root.m.digest(path.read_bytes())
        with self.assertRaisesRegex(ValueError,'file_too_large'):root.m.read_plan(self.hub,path,sha)
    def test_status_runtime_never_routes_writes_or_legacy(self):
        self.config.update(cancellation_binary='/old-runtime',cancellation_status_binary='/status-runtime')
        plan=self.hub/'plan.json';native=root.m.sync.Native(self.config)
        for version,purpose,tool,expected in [(2,'task_cancellation','hub_cancel_status','/status-runtime'),(2,'task_cancellation','hub_cancel_reminder','/old-runtime'),(2,'task_cancellation','hub_restore_reminder','/old-runtime'),(1,'task_cancellation','hub_cancel_status','/old-runtime'),(2,'project_list_verification','hub_cancel_status','/old-runtime')]:
            with self.subTest(version=version,purpose=purpose,tool=tool):
                plan.write_text(json.dumps(dict(version=version,purpose=purpose)))
                with patch.object(root.m.sync.subprocess,'run',return_value=types.SimpleNamespace(returncode=0,stdout='{}',stderr='')) as call:
                    native.call(tool,dict(plan=str(plan),plan_sha256=root.m.digest(plan.read_bytes())))
                self.assertEqual(call.call_args.args[0][0],expected)
for name in dir(root.ProjectListCancellationTests):
    if name.startswith('test_') and name not in CancellationClientTests.__dict__:setattr(CancellationClientTests,name,None)
