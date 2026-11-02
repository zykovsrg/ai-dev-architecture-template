"""Отмена закрытой записи и ограниченная сериализация; искусственные данные."""
import unittest,json,copy
from pathlib import Path
import test_reminders_project_list_cancellation as base
m=base.m;RID=base.RID;TID=base.TID
class FixesTests(unittest.TestCase):
 def setUp(self):
  self.f=base.ProjectListCancellationTests('test_root_cycle');self.f.setUp();self.addCleanup(self.f.doCleanups);self.f.config['projects']['demo']['tasks'][TID].pop('repeating',None);self.f.save()
 def test_completed_roundtrip_no_uncheck(self):
  self.f.native.data[RID]['completed']=True;before=copy.deepcopy(self.f.native.data[RID]);p=self.f.prepare();self.f.apply(p)
  self.assertEqual(self.f.row()['status'],'dropped');self.assertTrue(self.f.native.data[RID]['completed']);self.assertIn('не подтверждение успешного выполнения',self.f.paths['future'].read_text())
  rp=m.restore_preview(self.f.hub,p['path'],p['sha256'],self.f.config,self.f.native);self.f.restore(p,rp['sha256']);self.assertTrue(self.f.native.data[RID]['completed']);self.assertEqual(self.f.native.data[RID]['notes'],before['notes'])
 def test_completed_repeat_rejected(self):
  self.f.native.data[RID].update(completed=True,repeat=dict(frequency='daily'))
  with self.assertRaisesRegex(ValueError,'completed_series_requires_review'):self.f.prepare()
 def test_completed_link_repeat_rejected(self):
  self.f.native.data[RID]['completed']=True;self.f.config['projects']['demo']['tasks'][TID]['repeating']=True;self.f.save()
  with self.assertRaisesRegex(ValueError,'completed_series_requires_review'):self.f.prepare()
 def test_completed_concurrent_change_rejected(self):
  self.f.native.data[RID]['completed']=True;p=self.f.prepare();self.f.native.data[RID]['version']+='foreign'
  with self.assertRaisesRegex(ValueError,'remote_version_changed'):self.f.apply(p)
  self.assertEqual(self.f.row()['status'],'ready');self.assertNotIn(RID,self.f.native.deleted)
 def test_large_pretty_lossless_compact(self):
  value={'rows':[{'id':i,'value':'я'*100}for i in range(7900)]};pretty=json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
  # Force whitespace overhead rather than oversized payload.
  value={'rows':[dict(a=1,b=2,c=3,d=4,e=5)for _ in range(30000)]}
  self.assertGreater(len((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()),2097152)
  target=self.f.hub/'ai/compact.json';m.durable_json(target,value)
  self.assertLessEqual(target.stat().st_size,2097152);self.assertEqual(json.loads(m.document_bytes(target)),value)
 def test_utf8_limit_no_replace(self):
  target=self.f.hub/'ai/keep.json';target.write_text('{"keep":true}')
  with self.assertRaisesRegex(ValueError,'file_too_large'):m.durable_json(target,{'x':'я'*1048576})
  self.assertEqual(target.read_text(),'{"keep":true}')
 def test_oversize_preview_not_published(self):
  self.f.paths['future'].write_text(self.f.paths['future'].read_text()+'\n'+'я'*1100000+'\n')
  with self.assertRaisesRegex(ValueError,'file_too_large'):self.f.prepare()
  root=self.f.hub/'ai/reminders-cancellations';self.assertFalse([p for p in root.iterdir()if not p.name.startswith('.draft-')]);self.assertEqual(m.pending_projects(self.f.hub,self.f.config),set())
 def test_legacy_pretty_plan_raw_hash(self):
  p=self.f.prepare();path=Path(p['path']);value=json.loads(path.read_text());raw=json.dumps(value,ensure_ascii=False,sort_keys=True,indent=4)+'\n';path.write_text(raw);sha=m.digest(raw)
  state=json.loads(path.with_name('state.json').read_text());state['plan_sha256']=sha;path.with_name('state.json').write_text(json.dumps(state))
  self.assertEqual(m.read_plan(self.f.hub,path,sha)[1],value)

 def test_completed_unknown_delete_resume(self):
  self.f.native.data[RID]['completed']=True;p=self.f.prepare();self.f.native.fail_after='hub_cancel_reminder'
  with self.assertRaises(TimeoutError):self.f.apply(p)
  self.f.apply(p);self.assertTrue(self.f.native.data[RID]['completed']);self.assertEqual(self.f.row()['status'],'dropped')
 def test_large_plan_restore_token_roundtrip(self):
  self.f.config['padding']=[dict(a=1,b=2,c=3,d=4,e=5)for _ in range(16000)];self.f.save()
  self.f.paths['future'].write_text(self.f.paths['future'].read_text()+'\n'+'x'*600000+'\n')
  before=self.f.texts();p=self.f.prepare();self.assertLessEqual(Path(p['path']).stat().st_size,2097152);self.f.apply(p)
  rp=m.restore_preview(self.f.hub,p['path'],p['sha256'],self.f.config,self.f.native);self.assertEqual(m.digest(Path(rp['path']).read_bytes()),rp['sha256']);self.f.restore(p,rp['sha256']);self.assertEqual(self.f.texts(),before)
