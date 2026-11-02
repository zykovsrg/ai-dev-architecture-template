"""Передача проверенных групп из очистки в настоящий архивный валидатор."""
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
SOURCE=Path(os.environ.get('CLEANUP_GROUP_FIX_SOURCE',ROOT/'modules/planning/scripts/reminders_old_list_cleanup.py'))
with patch.dict(os.environ,CLEANUP_ARCHIVE_SOURCE=str(SOURCE)):
 spec=importlib.util.spec_from_file_location('cleanup_group_fixture',ROOT/'modules/planning/tests/test_cleanup_archive_compatibility.py')
 fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)

class CleanupGroupHandoffTests(unittest.TestCase):
 def setUp(self):
  self.base=fixture.Tests('runTest');self.base.setUp();self.addCleanup(self.base.doCleanups);self.f=self.base.f
  self.base.archive()
  helper=fixture.fixture.a.authority_archive()
  operation=helper.preview(self.f.h,'Главная копия в приложении; удаление отменяет с историей.',self.f.native)
  helper.apply(operation['plan'],operation['sha256'],True,self.f.native)
  self.path=self.f.h/self.f.current()['projects']['demo']['archive']['journal']/'plan.json';self.historical=self.path.read_bytes()
  self.f.native.calls.clear()
 def test_adopted_archive_receives_groups_without_extra_metadata_reads(self):
  self.assertEqual(self.base.check(),{self.f.rid})
  self.assertEqual(sum(tool=='list_lists' for tool,args in self.f.native.calls),2)
  self.assertTrue(all(tool in {'list_lists','find_reminders'} for tool,args in self.f.native.calls),self.f.native.calls)
  self.assertEqual(self.path.read_bytes(),self.historical)
 def test_changed_archive_group_name_is_still_rejected(self):
  self.f.native.groups[-1]['name']='Подменённая группа'
  with self.assertRaisesRegex(ValueError,'archive_native_group_changed'):
   self.base.check()
  self.assertEqual(self.path.read_bytes(),self.historical)

if __name__=='__main__':unittest.main()
