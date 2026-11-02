"""Итоговые барьеры: настоящая активация/архив, полностью поддельное приложение."""
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch
import uuid

ROOT=Path(__file__).resolve().parents[3]
SCRIPTS=Path(os.environ.get('AUTHORITY_FINAL_SCRIPTS',ROOT/'modules/planning/scripts'))
TASK_SOURCE=Path(os.environ.get('AUTHORITY_FINAL_TASK_SOURCE',ROOT/'modules/tasks/scripts/task_records.py'))


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module


class FinalAuthorityGateTests(unittest.TestCase):
    def setUp(self):
        scope=patch.dict(sys.modules);scope.start();self.addCleanup(scope.stop)
        for key in ('hub_reminders_gateway_sync','hub_reminders_authority','hub_reminders_task_gateway'):
            sys.modules.pop(key,None)
        self.gateway=load('hub_reminders_task_gateway',SCRIPTS/'reminders_task_gateway.py')
        self.sync=self.gateway.sync_module()
        with patch.dict(os.environ,ARCHIVE_SOURCE=str(SCRIPTS/'reminders_archive.py')):
            fixture=load('authority_final_archive_fixture',ROOT/'modules/planning/tests/test_reminders_archive.py')
        self.a=fixture.a
        self.f=fixture.ArchiveTests('runTest')
        with patch.object(fixture,'REAL',ROOT/'modules/tasks'):
            self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        for source in SCRIPTS.glob('*.py'):shutil.copyfile(source,self.f.h/'scripts'/source.name)
        shutil.copyfile(TASK_SOURCE,self.f.h/'scripts/task_records.py')
        self.hub=self.f.h;self.native=self.f.native;self.writes=[];self.creates=[]
        original_update=self.native.update;original_call=self.native.call
        def update(row,fields):
            self.writes.append(copy.deepcopy(fields));return original_update(row,fields)
        def call(tool,args):
            if tool=='create_reminder':
                self.creates.append(copy.deepcopy(args));rid=str(uuid.uuid4()).upper()
                row=dict(args,id=rid,list_id=args['list'],list=self.f.c['projects']['demo']['list_name'],version='v1',completed=args.get('completed',False))
                self.native.rows[rid]=row;return copy.deepcopy(row)
            return original_call(tool,args)
        self.native.update=update;self.native.call=call
        self.native.children=lambda binding:[copy.deepcopy(row) for row in self.native.rows.values() if row['list_id']==binding['list_id'] and row.get('parent_id')==binding.get('parent_id')]
        self.helper=self.sync.authority_module().archive_module()
        self.target=self.hub/'projects/demo/ai/future-tasks.md'

    def activate(self,archive=False):
        if archive:
            plan,sha=self.f.plan();self.f.run_apply(plan,sha)
            self.historical=(plan,plan.read_bytes())
        plan=self.helper.preview(self.hub,'Главная копия в приложении; удаление отменяет с историей.',self.native)
        self.helper.apply(plan['plan'],plan['sha256'],True,self.native)
        self.config=self.sync.load_config(self.hub);self.original=self.target.read_text()
        self.writes.clear();self.creates.clear()

    def write(self,text=None,parser=None):
        return self.gateway.write_from_text(parser or self.sync.parser_for(self.hub),self.hub,'demo','future',
            hashlib.sha256(self.original.encode()).hexdigest(),text or self.original.replace('Написать текст','Явная правка'),native=self.native)

    def test_active_target_metadata_account_group_name_and_pins(self):
        self.activate()
        # Сосед присутствует уже до журнала поручения; его список не читается.
        self.config['projects']['other']=dict(self.config['projects']['demo'],list_id=str(uuid.uuid4()).upper(),tasks={})
        self.f.savec(self.config)
        lists=copy.deepcopy(self.native.lists);groups=copy.deepcopy(self.native.groups)
        pin=self.hub/'ai/pins.json';pin_before=pin.read_bytes()
        mutations=[lambda:self.native.lists[self.f.lid].update(group_id=None),
            lambda:self.native.lists[self.f.lid].update(account_id=str(uuid.uuid4()).upper()),
            lambda:self.native.lists[self.f.lid].update(name='Чужой список'),
            lambda:self.native.groups[0].update(name='Чужая группа'),
            lambda:pin.write_text(json.dumps({'groups':{self.f.gid:'Другое закрепление'}}))]
        for mutation in mutations:
            self.native.lists=copy.deepcopy(lists);self.native.groups=copy.deepcopy(groups);pin.write_bytes(pin_before)
            mutation()
            with self.assertRaises(ValueError):self.write()
            self.assertEqual(self.writes,[]);self.assertEqual(self.target.read_text(),self.original)
        self.native.lists=lists;self.native.groups=groups;pin.write_bytes(pin_before)
        # Неподтверждённый сосед не должен отменять проверку безопасного целевого списка.
        self.write();self.assertEqual(self.writes,[{'title':'Явная правка'}])

    def test_real_adopted_archive_uses_receipt_group_before_update(self):
        self.activate(archive=True)
        lists=copy.deepcopy(self.native.lists);groups=copy.deepcopy(self.native.groups)
        self.native.lists[self.f.lid]['group_id']=self.f.gid
        with self.assertRaises(ValueError):self.write()
        self.native.lists=lists;self.native.groups[-1]['account_id']=str(uuid.uuid4()).upper()
        with self.assertRaises(ValueError):self.write()
        self.native.groups=groups;self.native.groups[-1]['name']='Чужое имя архива'
        with self.assertRaises(ValueError):self.write()
        self.assertEqual(self.writes,[]);self.assertEqual(self.target.read_text(),self.original)
        path,before=self.historical;self.assertEqual(path.read_bytes(),before)

    def test_target_metadata_blocks_create_before_native_write(self):
        self.activate();self.native.lists[self.f.lid]['group_id']=None
        request=self.original+'\n### TASK-demo-20261031-002 — Новая задача\nStatus: ready\n'
        with self.assertRaises(ValueError):self.write(request)
        self.assertEqual(self.creates,[]);self.assertEqual(self.writes,[]);self.assertEqual(self.target.read_text(),self.original)

    def test_target_metadata_blocks_cancel_before_protocol(self):
        self.activate();self.native.lists[self.f.lid]['group_id']=None
        with patch.object(self.sync,'cancellation_module',side_effect=AssertionError('cancellation before metadata validation')):
            with self.assertRaises(ValueError):self.write(self.original.replace('Status: ready','Status: dropped'))
        self.assertEqual(self.target.read_text(),self.original)

    def test_pending_projection_rechecks_fresh_target_metadata(self):
        self.activate();parser=self.sync.parser_for(self.hub)
        with patch.object(parser,'write_task_file',side_effect=OSError('projection interrupted')):
            with self.assertRaises(OSError):self.write(parser=parser)
        self.native.lists[self.f.lid]['group_id']=None
        with self.assertRaises(ValueError):self.write()
        self.assertEqual(self.writes,[{'title':'Явная правка'}]);self.assertEqual(self.target.read_text(),self.original)

    def test_incomplete_duplicate_and_error_metadata_refuse_before_write(self):
        self.activate();call=self.native.call
        faults=[lambda v:v.update(more=True),lambda v:v.update(has_more=True),lambda v:v.update(errors=['unavailable']),
            lambda v:v['lists'].append(copy.deepcopy(v['lists'][0])),lambda v:v['groups'].append(copy.deepcopy(v['groups'][0])),
            lambda v:v.pop('groups'),lambda v:v['lists'][0].pop('account_id')]
        for fault in faults:
            def bad(tool,args):
                value=call(tool,args)
                if tool=='list_lists':fault(value)
                return value
            with patch.object(self.native,'call',side_effect=bad):
                with self.assertRaises(ValueError):self.write()
            self.assertEqual(self.writes,[]);self.assertEqual(self.target.read_text(),self.original)
        # Правильный селектор всё равно требует настоящий завершённый журнал с верной суммой.
        config=copy.deepcopy(self.config);config['task_authority']['sha256']='0'*64;self.f.savec(config)
        with patch.object(self.native,'call',side_effect=AssertionError('native before activation verification')):
            with self.assertRaises(ValueError):self.sync.sync(self.hub,config,True,native=self.native,reconcile=False)
        self.assertEqual(self.writes,[])

    def test_present_invalid_selector_refuses_every_entry_before_native(self):
        self.activate();parser=self.sync.parser_for(self.hub)
        selections=[None,'reminders',{'mode':'remidners'},{},dict(self.config['task_authority'],deletions='ignore'),
            dict(self.config['task_authority'],journal=None),dict(self.config['task_authority'],sha256='invalid')]
        for selected in selections:
            config=copy.deepcopy(self.config);config['task_authority']=selected;self.f.savec(config)
            with self.assertRaises(ValueError):self.sync.load_config(self.hub)
            with patch.object(self.native,'call',side_effect=AssertionError('native before config validation')):
                with self.assertRaises(ValueError):self.sync.sync(self.hub,config,True,native=self.native,reconcile=False)
                with self.assertRaises(ValueError):self.a.preview(self.hub,['demo'],self.native)
            with self.assertRaises(ValueError):self.sync.authority_enabled(config)
            with self.assertRaises(ValueError):self.sync.authority_module().enabled(config)
            with self.assertRaises(ValueError):parser.reminders_mode(self.hub)
            with self.assertRaises(ValueError):parser.write_task_file(self.hub,'demo','future',hashlib.sha256(self.original.encode()).hexdigest(),self.original)
            with self.assertRaises(ValueError):self.a.read_receipt(self.hub,config,'demo')
            with self.assertRaises(ValueError):self.helper.archive_adopted(self.hub,config,'demo',{}, {}, {})
            with patch.object(sys,'argv',['task_records.py','write','--hub',str(self.hub),'--project-id','demo','--kind','future',
                    '--expected-sha256',hashlib.sha256(self.original.encode()).hexdigest()]),patch.object(sys,'stdin',io.StringIO(self.original)), \
                    patch.object(sys,'stderr',io.StringIO()):self.assertEqual(parser.main(),2)
            self.assertEqual(self.writes,[]);self.assertEqual(self.target.read_text(),self.original)

    def test_absent_key_keeps_legacy_but_invalid_present_key_cannot_use_missing_helpers(self):
        self.activate();standalone=self.hub/'standalone';standalone.mkdir()
        for name,source in [('reminders_sync.py',SCRIPTS/'reminders_sync.py'),('task_records.py',TASK_SOURCE)]:shutil.copyfile(source,standalone/name)
        sync=load('authority_final_standalone_sync',standalone/'reminders_sync.py')
        parser=load('authority_final_standalone_parser',standalone/'task_records.py')
        legacy=copy.deepcopy(self.config);legacy.pop('task_authority');self.f.savec(legacy)
        self.assertFalse(sync.authority_enabled(legacy));self.assertFalse(parser.reminders_mode(self.hub))
        with patch.dict(sys.modules):
            sys.modules.pop('hub_reminders_authority',None);sys.modules.pop('hub_reminders_task_gateway',None)
            for value in (None,'reminders',{'mode':'remidners'}):
                invalid=dict(legacy,task_authority=value);self.f.savec(invalid)
                with self.assertRaises(ValueError):sync.authority_enabled(invalid)
                with self.assertRaises(ValueError):parser.reminders_mode(self.hub)

    def test_legacy_archive_roundtrip_needs_no_authority_helpers(self):
        self.activate();legacy=copy.deepcopy(self.config);legacy.pop('task_authority');self.f.savec(legacy)
        standalone=self.hub/'old-archive';standalone.mkdir()
        for name,source in [('reminders_sync.py',SCRIPTS/'reminders_sync.py'),('reminders_archive.py',SCRIPTS/'reminders_archive.py')]:shutil.copyfile(source,standalone/name)
        archive=load('authority_final_legacy_archive',standalone/'reminders_archive.py')
        with patch.dict(sys.modules):
            sys.modules.pop('hub_reminders_authority',None)
            plan=archive.preview(self.hub,['demo'],self.native)
            state=archive.apply(Path(plan['plan']),plan['sha256'],True,self.native)
        self.assertEqual(state['phase'],'complete')


if __name__=='__main__':unittest.main()
