"""Настоящий снимок структуры и ограниченная проверка пути проекта; без приложения."""
import copy
import importlib.util
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[3]
SCRIPTS=Path(os.environ.get('INTEGRATION_FIX_SCRIPTS',ROOT/'modules/planning/scripts'))

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

with patch.dict(os.environ,AUTHORITY_CORE_SCRIPTS=str(SCRIPTS)):
    core=load('integration_fix_fixture',ROOT/'modules/planning/tests/test_reminders_authority_core.py')

class IntegrationFixTests(unittest.TestCase):
    def setUp(self):
        self.f=core.AuthorityCoreTests('runTest');self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.sync=core.sync;self.structure=load('integration_fix_structure',SCRIPTS/'reminders_structure.py')
    def policy(self):
        authority=self.f.authority();return authority,self.f.helper
    def resolver(self):
        self.assertTrue(hasattr(self.sync,'task_project_path'),'Нужен выбор одного проверенного пути')
        return self.sync.task_project_path
    def archived(self):
        f,path,historical=self.f.real_archived_fixture()
        return f,path,historical
    def test_detailed_structure_snapshot_verifies_real_adopted_archive(self):
        f,path,historical=self.archived();config=f.current()
        snap=self.structure.snapshot(f.native,{f.lid:{}},{'Демо'},detailed=True,include_groups=True)
        self.assertEqual(snap['groups'][f.native.groups[-1]['id']]['account_id'],f.account)
        archive=self.sync.archive_module(config)
        self.assertTrue(archive.verify_archived(f.h,config,'demo',snap));self.assertEqual(path.read_bytes(),historical)
        snap['groups']=list(snap['groups'].values());self.assertTrue(archive.verify_archived(f.h,config,'demo',snap))
    def test_wrong_group_account_in_structure_snapshot_still_rejected(self):
        f,path,historical=self.archived();config=f.current();f.native.groups[-1]['account_id']=core.ACCOUNT
        snap=self.structure.snapshot(f.native,{f.lid:{}},{'Демо'},detailed=True,include_groups=True)
        self.assertEqual(snap['groups'][f.native.groups[-1]['id']]['account_id'],core.ACCOUNT)
        with self.assertRaisesRegex(ValueError,'archive_native_group_changed'):
            self.sync.archive_module(config).verify_archived(f.h,config,'demo',snap)
    def test_legacy_group_without_account_keeps_original_shape(self):
        f=self.f;f.native.groups[0].pop('account_id')
        native=types.SimpleNamespace(call=lambda tool,args:core.Native.call(f.native,tool,args) if tool!='get_reminder' else copy.deepcopy(f.native.rows[args['id']]))
        detailed=self.structure.snapshot(native,{core.LID:{}},{'Работа'},detailed=True)
        self.assertEqual(detailed['groups'][core.GROUP],dict(id=core.GROUP,name='Группа'))
        shallow=self.structure.snapshot(native,{core.LID:{}},{'Работа'})
        self.assertNotIn('groups',shallow)
        selected=self.structure.snapshot(native,{core.LID:{}},{'Работа'},include_groups=True)
        self.assertEqual(selected['groups'][core.GROUP],dict(id=core.GROUP,name='Группа'))
    def test_legacy_detailed_snapshot_preserves_frozen_attestation_with_known_account(self):
        f=self.f
        native=types.SimpleNamespace(call=lambda tool,args:core.Native.call(f.native,tool,args) if tool!='get_reminder' else copy.deepcopy(f.native.rows[args['id']]))
        actual=self.structure.snapshot(native,{core.LID:{}},{'Работа'},detailed=True)
        frozen=dict(lists={core.LID:dict(id=core.LID,name='Работа',group_id=core.GROUP,account_id=core.ACCOUNT)},reminders=copy.deepcopy(f.native.rows),groups={core.GROUP:dict(id=core.GROUP,name='Группа')})
        bidirectional=load('integration_fix_bidirectional',SCRIPTS/'reminders_bidirectional.py')
        self.assertEqual(actual,frozen)
        self.assertEqual(bidirectional.attestation({'test':'legacy'},{'file':'original'},actual),bidirectional.attestation({'test':'legacy'},{'file':'original'},frozen))
    def test_authoritative_fast_structure_pass_never_falls_back_to_details(self):
        f,path,historical=self.archived();config=f.current()
        (f.h/'ai/archiprojects.md').write_text('## hadassah-promo\n```yaml\nid: hadassah-promo\nkind: group\nname: Хадасса\nstatus: active\nparent:\n```\n')
        config['structure'].update(bidirectional=True,journal_file='ai/structure-sync.json',list_roles={f.lid:{'kind':'project'}},projects={'demo':dict(list_id=f.lid,group='hadassah-promo')},native_groups={f.gid:'hadassah-promo'},subgroups={})
        f.savec(config);f.native.calls.clear()
        result=self.structure.reconcile_structure(f.h,config,apply=False,native=f.native)
        self.assertTrue(result['ok'],result);self.assertFalse(result['blocked_projects']);self.assertEqual(path.read_bytes(),historical)
        self.assertFalse(any(name=='get_reminder' for name,args in f.native.calls),f.native.calls)
    def test_group_adapter_rejects_bad_shapes_and_mismatched_keys(self):
        f,path,historical=self.archived();config=f.current();archive=self.sync.archive_module(config)
        snap=self.structure.snapshot(f.native,{f.lid:{}},{'Демо'},detailed=True,include_groups=True)
        group=copy.deepcopy(f.native.groups[-1])
        for value in ({'wrong-key':group},[group,group],['not-a-group'],[dict(group,id=['bad'])],None):
            with self.subTest(shape=value):
                snap['groups']=value
                with self.assertRaisesRegex(ValueError,'archive_native_group'):
                    archive.verify_archived(f.h,config,'demo',snap)
    def test_active_hub_project_never_checks_unrelated_archive(self):
        a,helper=self.policy();self.f.config['projects']['other']={'archive':{'journal':'unrelated'}};self.f.save()
        helper.project_path=Mock(side_effect=ValueError('unrelated_archive_should_not_be_read'))
        hp=self.sync.HubProject(self.f.hub,'demo')
        self.assertEqual(hp.project,self.f.project);helper.project_path.assert_not_called()
    def test_archive_resolver_checks_only_selected_archive(self):
        a,helper=self.policy();self.f.config['projects']['demo']['archive']={'journal':'selected'}
        self.f.config['projects']['other']={'archive':{'journal':'unrelated'}}
        helper.project_path=Mock(side_effect=lambda hub,config,pid:self.f.project if pid=='demo' else (_ for _ in ()).throw(ValueError('unrelated_archive')))
        result=self.resolver()(self.f.hub,'demo',self.f.config)
        self.assertEqual(result,self.f.project);self.assertEqual([call.args[2] for call in helper.project_path.call_args_list],['demo'])
    def test_new_resolver_rejects_active_project_without_binding(self):
        self.policy();self.f.config['projects'].clear()
        with self.assertRaisesRegex(ValueError,'unbound_project'):
            self.resolver()(self.f.hub,'demo',self.f.config)
    def test_selected_archive_damage_remains_an_error(self):
        a,helper=self.policy();self.f.config['projects']['demo']['archive']={'journal':'selected'};helper.project_path=Mock(side_effect=ValueError('archive_authority_anchor_invalid'))
        with self.assertRaisesRegex(ValueError,'archive_authority_anchor_invalid'):
            self.resolver()(self.f.hub,'demo',self.f.config)
        self.assertEqual(helper.project_path.call_count,1)
    def test_full_sync_initial_pass_still_checks_all_archive_paths(self):
        a,helper=self.policy();seen=[]
        helper.archive_group=lambda *args:core.GROUP
        for pid in ('archive-one','archive-two'):
            project=self.f.hub/'projects'/pid;(project/'ai').mkdir(parents=True)
            for kind,name in self.sync.NAMES.items():(project/'ai'/name).write_text('# Текущая задача\nStatus: empty\n' if kind=='current' else '# Задачи\n')
            lid=str(core.uuid.uuid4())
            self.f.native.lists.append(dict(id=lid,name=pid,account_id=core.ACCOUNT,group_id=core.GROUP))
            self.f.config['projects'][pid]=dict(layout='project_list',list_id=lid,list_name=pid,account_id=core.ACCOUNT,parent_id=None,tasks={},history={},archive={'journal':pid})
        self.f.allow.write_text(core.json.dumps({'names':['Работа','archive-one','archive-two']}))
        self.f.save()
        def selected(hub,config,pid):seen.append(pid);return self.f.hub/'projects'/pid
        helper.project_path=selected
        prepared=dict(config=self.f.config,items=[],stop=False)
        with patch.object(a,'prepare_pull',return_value=prepared):
            result=self.sync.sync(self.f.hub,self.f.config,False,native=self.f.native,reconcile=False)
        self.assertTrue(result['ok'],result);self.assertEqual(set(seen),{'archive-one','archive-two'})

if __name__=='__main__':unittest.main()
