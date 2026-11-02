"""Архивная совместимость старой очистки; только синтетические данные."""
import unittest,importlib.util,json,sys,copy,os
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).parent))
import test_reminders_archive as fixture
SOURCE=Path(os.environ.get('CLEANUP_ARCHIVE_SOURCE',str(Path(__file__).resolve().parents[1]/'scripts/reminders_old_list_cleanup.py')))
spec=importlib.util.spec_from_file_location('cleanup_archive_test',SOURCE);cleanup=importlib.util.module_from_spec(spec);spec.loader.exec_module(cleanup)
class Tests(unittest.TestCase):
 def setUp(self):
  self.f=fixture.ArchiveTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
  self.f.c['structure']['list_roles']={self.f.lid:dict(kind='project',project_id='demo')}
  self.f.c['structure']['projects']={'demo':dict(list_id=self.f.lid)}
  self.f.savec(self.f.c)
  self.helper=SimpleNamespace(config_read=lambda h:(self.f.current(),(h/'ai/reminders-sync.json').read_text()),load_sync=lambda:fixture.M,metadata=lambda n:n.call('list_lists',{}))
 def check(self):
  return cleanup._current_active_ids(self.f.h,self.f.native,self.helper,'demo',self.f.current()['projects']['demo'])
 def archive(self):
  p,t=self.f.plan();self.f.run_apply(p,t)
 def test_valid_attested_archive(self):
  self.archive();self.assertEqual(self.check(),{self.f.rid})
 def test_unknown_move_rejected(self):
  self.f.native.groups.append(dict(id='11111111-1111-4111-8111-111111111111',name='Архив',account_id=self.f.account))
  self.f.native.lists[self.f.lid]['group_id']=self.f.native.groups[-1]['id']
  with self.assertRaisesRegex(ValueError,'identity_changed'):self.check()
 def test_tampered_receipt_rejected(self):
  self.archive();c=self.f.current();c['projects']['demo']['archive']['token']='bad';self.f.savec(c)
  with self.assertRaisesRegex(ValueError,'checksum'):self.check()
 def test_changed_archived_content_rejected(self):
  self.archive();self.f.native.rows[self.f.rid]['notes']='new foreign content'
  with self.assertRaisesRegex(ValueError,'content_changed'):self.check()
 def test_unknown_archived_group_rejected(self):
  self.archive();gid='11111111-1111-4111-8111-111111111111';self.f.native.groups.append(dict(id=gid,name='Foreign',account_id=self.f.account));self.f.native.lists[self.f.lid]['group_id']=gid
  with self.assertRaisesRegex(ValueError,'identity_changed'):self.check()
