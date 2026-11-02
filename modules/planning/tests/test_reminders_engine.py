"""Полный искусственный снимок, свежесть, восстановление и проекция без приложения."""
import contextlib, copy, importlib.util, json, pathlib, sys, unittest
from unittest.mock import patch, Mock
ROOT=pathlib.Path(__file__).resolve().parents[3]
SCRIPTS=ROOT/'modules/planning/scripts'
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
class EngineTests(unittest.TestCase):
 def setUp(self):
  self.assertTrue((SCRIPTS/'reminders_engine.py').exists(),'Нет нового координатора')
  self.e=load('engine_subject',SCRIPTS/'reminders_engine.py')
  self.reads=load('engine_test_reads',SCRIPTS/'reminders_reads.py')
  self.snapshot={'metadata':{'lists':[{'id':'l','name':'Лист','account_id':'a','group_id':None}],'groups':[]},'lists':{'l':[{'id':'r','list_id':'l','list':'Лист','title':'До','version':'v1'}]},'scope':{'names':['Лист'],'original_sha256':'x'},'complete':True}
  self.base=Mock();self.base.call.return_value={'fresh':True};self.base.get.return_value={'id':'r','list_id':'l','title':'Свежее','version':'v2'}
 def context(self):return self.e.ContextNative(self.base,self.snapshot,self.reads)
 def test_context_reuses_full_reads_and_returns_independent_rows(self):
  c=self.context();value=c.call('find_reminders',{'list':'l','include_completed':True,'limit':500});value['reminders'][0]['title']='Испортить'
  self.assertEqual(c.get('r','l')['title'],'До');self.assertEqual(c.children({'list_id':'l','parent_id':None})[0]['title'],'До');self.base.call.assert_not_called()
 def test_refresh_expires_context_before_next_read(self):
  c=self.context();self.reads.refresh();self.assertEqual(c.get('r','l')['title'],'Свежее');self.base.get.assert_called_once()
 def test_write_failure_also_expires_context(self):
  c=self.context();self.base.call.side_effect=RuntimeError('unknown outcome')
  with self.assertRaises(RuntimeError):c.call('update_reminder',{'id':'r'})
  self.assertEqual(c.get('r','l')['title'],'Свежее')
 def test_context_refuses_missing_binding_and_unknown_list(self):
  c=self.context()
  with self.assertRaisesRegex(ValueError,'binding'):c.get('r','other')
  with self.assertRaisesRegex(ValueError,'list'):c.call('find_reminders',{'list':'other','include_completed':True,'limit':500})
 def test_export_full_snapshot_is_independent_and_explicit(self):
  value=self.e.export_snapshot(self.snapshot);self.assertTrue(value['complete']);self.assertEqual(value['reminders'][0]['id'],'r');self.assertEqual(value['scope'],self.snapshot['scope']);self.assertIn('captured_at',value)
  value['reminders'][0]['title']='Изменено';self.assertEqual(self.snapshot['lists']['l'][0]['title'],'До')
 def test_pending_delegates_before_capture_and_never_replans(self):
  m=Mock();m.authority_module.return_value.locked.return_value=contextlib.nullcontext();m._legacy_sync.return_value={'ok':False,'items':[{'error':'recovery'}]}
  with patch.object(self.e,'pending',return_value=True),patch.object(self.e,'capture',side_effect=AssertionError('capture before recovery')) as captured,patch.object(self.e,'LocalInputs',side_effect=AssertionError('planning before recovery')) as planned:
   result=self.e.run(m,pathlib.Path('/tmp'),{},native=self.base)
  self.assertFalse(result['ok']);m._legacy_sync.assert_called_once();captured.assert_not_called();planned.assert_not_called()

 def test_changed_permission_bytes_expire_context_and_native_cache(self):
  import tempfile
  with tempfile.TemporaryDirectory() as folder:
   path=pathlib.Path(folder).resolve()/'permissions.json';path.write_bytes(b'one');self.snapshot['_scope_files']={str(path):b'one'}
   c=self.context();self.assertEqual(c.get('r','l')['title'],'До');epoch=self.reads.generation();path.write_bytes(b'two')
   self.assertEqual(c.get('r','l')['title'],'Свежее');self.assertGreater(self.reads.generation(),epoch)

class IntegrationTests(unittest.TestCase):
 def setUp(self):
  self.assertTrue((SCRIPTS/'reminders_engine.py').exists(),'Нет нового координатора')
  self.core=load('engine_core_fixture',ROOT/'modules/planning/tests/test_reminders_authority_core.py')
  self.f=self.core.AuthorityCoreTests('runTest');self.f.setUp();self.addCleanup(self.f.doCleanups);self.f.authority()
  self.m=self.core.sync;self.e=self.m.engine_module()
  # Старый искусственный исполнитель разделяет get() и call().
  self.calls=[];original=self.f.native.call
  def call(tool,args):self.calls.append(tool);return original(tool,args)
  self.f.native.call=call
 def test_full_incoming_projection_final_snapshot_and_second_noop(self):
  result=self.m.sync(self.f.hub,self.f.config,True,native=self.f.native,reconcile=False,return_snapshot=True)
  self.assertTrue(result['ok'],result);self.assertEqual(self.f.row()['title'],'Из приложения');self.assertTrue(result['final_snapshot']['complete']);self.assertEqual(len(result['final_snapshot']['reminders']),2);self.assertEqual(self.f.native.writes,[])
  again=self.m.sync(self.f.hub,self.f.config,True,native=self.f.native,reconcile=False)
  self.assertTrue(again['ok'],again);self.assertNotIn('final_snapshot',again);self.assertFalse(any(i.get('action')=='sync' for i in again['items']))
 def test_final_remote_race_is_visible_and_never_reports_success(self):
  original=self.e.capture;calls=0
  def racing(*args,**kwargs):
   nonlocal calls
   calls+=1
   if calls==2:self.f.native.rows[self.core.RID]['title']='Изменилось во время записи'
   return original(*args,**kwargs)
  with patch.object(self.e,'capture',side_effect=racing):result=self.m.sync(self.f.hub,self.f.config,True,native=self.f.native,reconcile=False,return_snapshot=True)
  self.assertFalse(result['ok'],result);self.assertTrue(result['final_snapshot']['complete']);self.assertTrue(any('final' in i.get('error','') for i in result['items']))

 def test_batch_capture_avoids_individual_get_and_covers_both_boundaries(self):
  original=self.f.native.call
  for row in self.f.native.rows.values():row['version']=str(row['version'])
  self.f.native.rows[self.core.PID]['subtasks']=[{'id':self.core.RID,'title':'Из приложения','completed':False}]
  def batch(tool,args):
   value=original(tool,args)
   if tool=='list_lists':value['detailed_reminder_snapshot']=True
   if tool=='find_reminders' and args.get('detail'):value['detail']=True
   return value
  self.f.native.call=batch
  with patch.object(self.f.native,'get',side_effect=AssertionError('individual get forbidden')):
   result=self.m.sync(self.f.hub,self.f.config,True,native=self.f.native,reconcile=False,return_snapshot=True)
  self.assertTrue(result['ok'],result);self.assertEqual(self.f.row()['title'],'Из приложения');self.assertTrue(result['final_snapshot']['complete']);self.assertEqual(self.calls.count('find_reminders'),4)

 def test_final_read_failure_has_no_invented_empty_success_snapshot(self):
  original=self.e.capture;calls=0
  def failing(*args,**kwargs):
   nonlocal calls
   calls+=1
   if calls==2:raise ValueError('read failed')
   return original(*args,**kwargs)
  with patch.object(self.e,'capture',side_effect=failing):result=self.m.sync(self.f.hub,self.f.config,True,native=self.f.native,reconcile=False,return_snapshot=True)
  self.assertFalse(result['ok']);self.assertFalse(result['final_snapshot']['complete']);self.assertIsNone(result['final_snapshot']['metadata']);self.assertTrue(result['final_snapshot']['limitations'])
 def test_capture_timestamp_precedes_first_native_read_and_names_keep_missing_lists(self):
  import datetime
  allow=json.loads(self.f.allow.read_text());allow['names'].append('Несуществующий список');self.f.allow.write_text(json.dumps(allow));first=[];original=self.f.native.call
  def call(tool,args):
   if not first:first.append(datetime.datetime.now(datetime.timezone.utc))
   return original(tool,args)
  self.f.native.call=call
  observation=self.e.capture(self.m,self.f.hub,self.f.config,self.f.native)
  self.assertLessEqual(datetime.datetime.fromisoformat(observation['captured_at']),first[0]);self.assertIn('Несуществующий список',observation['scope']['names']);self.assertEqual(observation['lists'][self.core.LID][0]['list'],'Работа')
 def test_incomplete_scope_preserves_errors_and_never_claims_complete(self):
  self.f.native.incomplete=True
  result=self.m.sync(self.f.hub,self.f.config,True,native=self.f.native,reconcile=False,return_snapshot=True)
  self.assertFalse(result['ok'],result);self.assertFalse(result['final_snapshot']['complete']);self.assertFalse(result.get('complete',True));self.assertEqual(self.f.native.writes,[])
 def test_real_structure_move_and_task_projection_reload_committed_configuration(self):
  f=self.f;c=self.core;gid='00000000-0000-0000-0000-000000000099'
  f.native.rows.pop(c.PID);f.native.rows[c.RID].pop('parent_id');f.config['projects']['demo'].update(layout='project_list',parent_id=None)
  f.native.groups.append(dict(id=gid,name='Другая группа',account_id=c.ACCOUNT))
  (f.hub/'ai/project-cards').mkdir();(f.hub/'ai/project-cards/demo.md').write_text('Project ID: demo\nStatus: active\nprimary_archiproject: b\n')
  (f.hub/'ai/project-registry.md').write_text((f.hub/'ai/project-registry.md').read_text()+'Card: ai/project-cards/demo.md\n')
  (f.hub/'ai/archiprojects.md').write_text(''.join(f'## {g}\n```yaml\nid: {g}\nname: {g}\nstatus: active\nkind: group\n```\n' for g in ('a','b')))
  groups=f.hub/'ai/groups.json';groups.write_text(json.dumps({'names':['Группа','Другая группа']}));pins=f.hub/'ai/pins.json';pins.write_text(json.dumps({'groups':{c.GROUP:'Группа',gid:'Другая группа'}}))
  f.config['structure']=dict(enabled=True,bidirectional=True,groups_allowlist_file=str(groups),group_ids_allowlist_file=str(pins),native_groups={c.GROUP:'a',gid:'b'},list_roles={c.LID:{'kind':'project','project_id':'demo'}},projects={'demo':{'group':'a','list_id':c.LID}},subgroups={},journal_file='ai/structure.json')
  f.save();original=f.native.call
  def mover(tool,args):
   if tool=='manage_list':
    self.assertEqual(args['expected_group_id'],f.native.lists[0]['group_id']);f.native.lists[0]['group_id']=args['group'];return copy.deepcopy(f.native.lists[0])
   if tool=='get_reminder':return f.native.get(args['id'],c.LID)
   return original(tool,args)
  f.native.call=mover
  result=self.m.sync(f.hub,f.config,True,native=f.native,return_snapshot=True)
  self.assertTrue(result['ok'],result);self.assertEqual(f.row()['title'],'Из приложения');self.assertEqual(result['final_snapshot']['metadata']['lists'][0]['group_id'],gid);self.assertEqual(f.config['projects']['demo']['native_group_id'],gid);self.assertEqual(self.m.load_config(f.hub)['projects']['demo']['native_group_id'],gid)
 def test_converged_task_does_not_rewrite_configuration(self):
  first=self.m.sync(self.f.hub,self.f.config,True,native=self.f.native,reconcile=False);self.assertTrue(first['ok'],first)
  before=(self.f.hub/'ai/reminders-sync.json').read_bytes()
  with patch.object(self.m,'atomic_json',wraps=self.m.atomic_json) as writer:
   second=self.m.sync(self.f.hub,self.f.config,True,native=self.f.native,reconcile=False)
  self.assertTrue(second['ok'],second);writer.assert_not_called();self.assertEqual((self.f.hub/'ai/reminders-sync.json').read_bytes(),before)

 def test_complete_noop_uses_one_capture_and_does_not_repeat_global_verification(self):
  first=self.m.sync(self.f.hub,self.f.config,True,native=self.f.native,reconcile=False);self.assertTrue(first['ok'],first)
  with patch.object(self.e,'capture',wraps=self.e.capture) as capture:
   second=self.m.sync(self.f.hub,self.f.config,True,native=self.f.native,reconcile=False,return_snapshot=True)
  self.assertTrue(second['ok'],second);self.assertTrue(second['final_snapshot']['complete']);self.assertEqual(capture.call_count,1)

 def test_noop_cannot_skip_final_capture_when_local_inputs_changed(self):
  first=self.m.sync(self.f.hub,self.f.config,True,native=self.f.native,reconcile=False);self.assertTrue(first['ok'],first)
  with patch.object(self.e.LocalInputs,'unchanged',return_value=False),patch.object(self.e,'capture',wraps=self.e.capture) as capture:
   second=self.m.sync(self.f.hub,self.f.config,True,native=self.f.native,reconcile=False,return_snapshot=True)
  self.assertTrue(second['ok'],second);self.assertEqual(capture.call_count,2)
 def test_advertised_invalid_batch_never_falls_back_to_writing_from_summaries(self):
  original=self.f.native.call;before=self.f.files['future'].read_bytes()
  def broken(tool,args):
   value=original(tool,args)
   if tool=='list_lists':value['detailed_reminder_snapshot']=True
   if tool=='find_reminders' and args.get('detail'):value.update(detail=True,count=len(value['reminders'])+1)
   return value
  self.f.native.call=broken
  result=self.m.sync(self.f.hub,self.f.config,True,native=self.f.native,reconcile=False,return_snapshot=True)
  self.assertFalse(result['ok'],result);self.assertEqual(self.f.files['future'].read_bytes(),before);self.assertFalse(result['final_snapshot']['complete']);self.assertEqual(self.f.native.writes,[])
 def test_unexpected_capture_error_refuses_without_legacy_apply(self):
  before=self.f.files['future'].read_bytes()
  with patch.object(self.e,'capture',side_effect=RuntimeError('unexpected read error')),patch.object(self.m,'_legacy_sync',side_effect=AssertionError('legacy apply forbidden')) as legacy:
   result=self.m.sync(self.f.hub,self.f.config,True,native=self.f.native,reconcile=False,return_snapshot=True)
  self.assertFalse(result['ok']);self.assertEqual(self.f.files['future'].read_bytes(),before);self.assertFalse(result['final_snapshot']['complete']);legacy.assert_not_called()

 def test_partial_scope_pulls_only_verified_project_and_rejects_malformed_details(self):
  self.f.add_second_project()
  self.f.native.lists=[r for r in self.f.native.lists if r['id']!=self.core.LID]
  self.f.native.rows.pop(self.core.RID)
  result=self.m.sync(self.f.hub,self.f.config,True,native=self.f.native,reconcile=False,return_snapshot=True)
  self.assertFalse(result['ok']);self.assertFalse(result['complete']);self.assertFalse(result['final_snapshot']['complete'])
  self.assertEqual(self.m.HubProject(self.f.hub,'other').rows()['TASK-other-20261027-001']['planned_day'],'2026-11-02')
  self.assertEqual(self.f.native.writes,[]);self.assertTrue(any('expected_list' in i.get('error','') for i in result['items']))
  before=(self.f.hub/'projects/other/ai/future-tasks.md').read_bytes()
  original=self.f.native.call
  def broken(tool,args):
   value=original(tool,args)
   if tool=='list_lists':value['detailed_reminder_snapshot']=True
   if tool=='find_reminders' and args.get('detail'):value.update(detail=True,count=999)
   return value
  self.f.native.call=broken
  result=self.m.sync(self.f.hub,self.f.config,True,native=self.f.native,reconcile=False,return_snapshot=True)
  self.assertFalse(result['ok']);self.assertFalse(result['final_snapshot']['complete'])
  self.assertTrue(any('engine_snapshot_read_failed' in i.get('error','') for i in result['items']))
  self.assertEqual((self.f.hub/'projects/other/ai/future-tasks.md').read_bytes(),before);self.assertEqual(self.f.native.writes,[])
