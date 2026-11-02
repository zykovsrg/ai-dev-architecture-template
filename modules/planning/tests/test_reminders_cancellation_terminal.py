"""Все пять завершённых отмен; посторонняя конфигурация не отменяет точные guards."""
import copy,json,shutil,unittest,uuid
from pathlib import Path
import test_reminders_cancel as legacy
m=legacy.m
class TerminalCompatibilityTests(legacy.CancellationTests):
    def prepare_five(self):
        targets=[('demo',legacy.TID)]
        for n in range(1,5):
            pid='other-'+str(n);tid=legacy.TID.replace('demo',pid);project=self.hub/'projects'/pid;shutil.copytree(self.project,project)
            for path in (project/'ai').iterdir():path.write_text(path.read_text().replace(legacy.TID,tid))
            with (self.hub/'ai/project-registry.md').open('a') as f:f.write(f'\n## {pid}\nStatus: active\nPath: {project}\n')
            rid=str(uuid.UUID(int=100+n));parent=str(uuid.UUID(int=200+n));binding=copy.deepcopy(self.config['projects']['demo']);binding['parent_id']=parent;binding['tasks']={tid:{'reminder_id':rid,'repeating':True}};self.config['projects'][pid]=binding
            self.native.data[parent]=dict(self.native.data[legacy.PID],id=parent);self.native.data[rid]=dict(self.native.data[legacy.RID],id=rid,parent_id=parent);targets.append((pid,tid))
        self.config_path.write_text(json.dumps(self.config));p=m.preview(self.hub,self.config,targets,self.native);self.apply(p);return p
    def change_unrelated(self):self.config['standard_allowlist_file']=str(self.hub/'ai/reminders-standard-allowlist.json');self.config['unrelated']='new';self.config_path.write_text(json.dumps(self.config))
    def test_five_terminal_status_and_execute_no_writes(self):
        p=self.prepare_five();self.change_unrelated();before={x:x.read_bytes() for x in self.hub.rglob('*') if x.is_file()};calls=len(self.native.calls)
        result=m.status(self.hub,p['path'],p['sha256'],self.config,self.native);self.assertEqual([x['state'] for x in result['items']],['deleted']*5);self.apply(p)
        self.assertEqual({x:x.read_bytes() for x in before},before);self.assertFalse(any(t in {'hub_cancel_reminder','hub_restore_reminder'} for t,a in self.native.calls[calls:]))
    def test_target_binding_still_rejected(self):
        p=self.prepare_five();self.change_unrelated();self.config['projects']['demo']['label']='changed';self.config_path.write_text(json.dumps(self.config))
        with self.assertRaisesRegex(ValueError,'binding'):m.status(self.hub,p['path'],p['sha256'],self.config,self.native)
    def test_target_receipt_still_rejected(self):
        p=self.prepare_five();self.change_unrelated();self.config['projects']['demo']['tasks'][legacy.TID].pop('cancellation');self.config_path.write_text(json.dumps(self.config))
        with self.assertRaisesRegex(ValueError,'receipt'):m.status(self.hub,p['path'],p['sha256'],self.config,self.native)
    def test_policy_still_rejected(self):
        p=self.prepare_five();self.change_unrelated();self.config['cancellation_policy']='no_concurrent_edits';self.config_path.write_text(json.dumps(self.config))
        with self.assertRaisesRegex(ValueError,'policy'):m.status(self.hub,p['path'],p['sha256'],self.config,self.native)
    def test_allowlist_still_rejected(self):
        p=self.prepare_five();self.change_unrelated();self.allow.write_text(self.allow.read_text()+' ')
        with self.assertRaisesRegex(ValueError,'allowlist'):m.status(self.hub,p['path'],p['sha256'],self.config,self.native)
    def test_registry_still_rejected(self):
        p=self.prepare_five();self.change_unrelated();reg=self.hub/'ai/project-registry.md';reg.write_text(reg.read_text().replace('Status: active','Status: paused',1))
        with self.assertRaisesRegex(ValueError,'project'):m.status(self.hub,p['path'],p['sha256'],self.config,self.native)
    def test_four_terminal_one_intermediate_strict(self):
        p=self.prepare_five();state=Path(p['path']).with_name('state.json');data=json.loads(state.read_text());data['items'][legacy.RID]['phase']='hub_cancelled';state.write_text(m.encoded(data));self.change_unrelated()
        with self.assertRaisesRegex(ValueError,'config_checksum'):m.status(self.hub,p['path'],p['sha256'],self.config,self.native)
    def test_restored_status_allows_unrelated(self):
        p=self.prepare();self.apply(p);rp=m.restore_preview(self.hub,p['path'],p['sha256'],self.config,self.native);self.restore(p,rp['sha256']);self.change_unrelated();self.assertEqual(m.status(self.hub,p['path'],p['sha256'],self.config,self.native)['items'][0]['state'],'active');self.apply(p)
    def test_restore_token_stays_strict(self):
        p=self.prepare();self.apply(p);rp=m.restore_preview(self.hub,p['path'],p['sha256'],self.config,self.native);self.change_unrelated()
        with self.assertRaisesRegex(ValueError,'config_checksum'):self.restore(p,rp['sha256'])
        self.assertFalse(any(t=='hub_restore_reminder' for t,a in self.native.calls))
    def test_v1_null_parent_rejected(self):
        self.config['projects']['demo']['parent_id']=None;self.config_path.write_text(json.dumps(self.config))
        with self.assertRaisesRegex(ValueError,'invalid_uuid'):self.prepare()
        self.assertFalse(self.native.calls)
    def test_terminal_execute_preserves_hub_guard(self):
        p=self.prepare();self.apply(p);self.paths['future'].write_text(self.paths['future'].read_text()+'\nИзменённая запись.\n');self.change_unrelated()
        with self.assertRaisesRegex(ValueError,'hub'):self.apply(p)
for name in dir(legacy.CancellationTests):
    if name.startswith('test_') and name not in TerminalCompatibilityTests.__dict__:setattr(TerminalCompatibilityTests,name,None)
