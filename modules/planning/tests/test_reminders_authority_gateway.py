"""Изолированные проверки явных поручений; настоящее приложение не вызывается."""
import contextlib
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(os.environ.get('GATEWAY_TEST_SOURCE', ROOT / 'modules/planning/scripts/reminders_task_gateway.py'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


class GatewayTests(unittest.TestCase):
    def setUp(self):
        # Отсутствующая функция даёт осмысленное красное состояние до реализации.
        self.assertTrue(SOURCE.is_file(), 'gateway implementation missing')
        # Другие fixtures загружают эти имена из своих удаляемых копий scripts/.
        # Только gateway-кэш ограничен временем теста; singleton authority сохраняется.
        module_scope=patch.dict(sys.modules)
        module_scope.start(); self.addCleanup(module_scope.stop)
        sys.modules.pop('hub_reminders_gateway_sync',None)
        self.m = load('hub_reminders_task_gateway', SOURCE)
        self.temp = tempfile.TemporaryDirectory(prefix='gateway-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.hub = Path(self.temp.name).resolve()
        (self.hub / 'ai').mkdir()
        (self.hub / 'scripts').mkdir()
        for source in (ROOT / 'modules/planning/scripts').glob('*.py'):
            shutil.copy(source, self.hub / 'scripts' / source.name)
        shutil.copy(Path(os.environ.get('GATEWAY_TEST_TASK_SOURCE', ROOT / 'modules/tasks/scripts/task_records.py')), self.hub / 'scripts/task_records.py')
        self.parser = load('gateway_parser', self.hub / 'scripts/task_records.py')
        self.project = self.hub / 'projects/demo'
        (self.project / 'ai').mkdir(parents=True)
        (self.hub / 'ai/project-registry.md').write_text(f'## demo\nStatus: active\nPath: {self.project}\n')
        self.tid = 'TASK-demo-20261030-001'
        self.text = f'# Задачи\n\n### {self.tid} — Старое название\nStatus: ready\nЗапланировано: 2026-10-30.\nDue: 2026-12-31\n\nКонтекст.\n'
        self.target = self.project / 'ai/future-tasks.md'
        self.target.write_text(self.text)
        (self.project / 'ai/current-task.md').write_text('Status: empty\n')
        (self.project / 'ai/paused-tasks.md').write_text('# Пауза\n')
        allow = self.hub / 'ai/allow.json'; allow.write_text('{"names":["Работа"]}')
        pins=self.hub/'ai/pins.json';pins.write_text('{"groups":{"g":"Группа"}}')
        self.config = dict(version=1, binary='/private/tmp/unused', allowlist_file=str(allow),
                           task_authority={'mode':'reminders','deletions':'cancel','journal':'ai/reminders-authority/00000000-0000-0000-0000-000000000001','sha256':'a'*64},
                           structure={'group_ids_allowlist_file':str(pins)}, projects={'demo':dict(list_id='l',list_name='Работа',parent_id=None,account_id='account',native_group_id='g',
                           layout='project_list',tasks={self.tid:{'reminder_id':'r'}})})
        self.config_path = self.hub / 'ai/reminders-sync.json'
        self.config_path.write_text(json.dumps(self.config))
        self.sync = self.m.sync_module()
        real_authority=self.sync.authority_module()
        authority = type('Authority', (), {'enabled':staticmethod(real_authority.enabled),
            'validate_policy':staticmethod(lambda h,c: None), 'locked':staticmethod(lambda h: contextlib.nullcontext(h)),
            'validate_target':staticmethod(real_authority.validate_target),
            'bound_projects':staticmethod(lambda h,c: {'demo':self.project})})()
        self.patch = patch.object(self.sync, 'authority_module', return_value=authority)
        self.patch.start(); self.addCleanup(self.patch.stop)
        self.native = FakeNative()

    def write(self, text=None, sha=None):
        return self.m.write_from_text(self.parser, self.hub, 'demo', 'future',
            sha or hashlib.sha256(self.text.encode()).hexdigest(), text if text is not None else self.text,
            native=self.native)

    def test_unbound_completed_history_does_not_block_new_task(self):
        history = 'Status: done\nTask ID: TASK-demo-20260828-001\n\n## Goal\nСтарая завершённая работа\n'
        current = self.project / 'ai/current-task.md'
        current.write_text(history)
        requested = self.text + '\n### TASK-demo-20261031-001 — Новая задача\nStatus: ready\n'
        self.write(requested)
        self.assertEqual(current.read_text(), history)
        self.assertEqual(self.native.creates, 1)
        self.assertIn('Новая задача', self.target.read_text())
        self.assertNotIn('TASK-demo-20260828-001', json.loads(self.config_path.read_text())['projects']['demo']['tasks'])

    def test_unbound_history_cannot_be_changed_or_active(self):
        for status, changed in [('done', True), ('ready', False)]:
            with self.subTest(status=status, changed=changed):
                self.text = self.text.replace('Status: ready', 'Status: '+status)
                self.target.write_text(self.text)
                self.config['projects']['demo']['tasks'] = {}
                self.config_path.write_text(json.dumps(self.config))
                requested = self.text.replace('Контекст.', 'Изменённый контекст.') if changed else self.text
                with self.assertRaisesRegex(ValueError, 'unbound_existing_task'):
                    self.write(requested)
                self.assertEqual(self.native.creates, 0)
                self.assertEqual(self.target.read_text(), self.text)
                self.text = self.text.replace('Status: done', 'Status: ready')

    def test_title_patch_uses_fresh_day_completion_and_context(self):
        self.native.data['r'].pop('repeat')
        self.native.data['r']['completed'] = True
        self.write(self.text.replace('Старое название', 'Новое название'))
        self.assertEqual(self.native.writes, [{'title':'Новое название'}])
        actual = self.target.read_text()
        self.assertIn('2026-11-02', actual)
        self.assertIn('Status: done', actual)
        self.assertIn('Due: 2026-12-31', actual)
        self.assertIn('Контекст.', actual)

    def test_library_resolver_rejects_project_outside_bound_projects(self):
        authority=self.sync.authority_module()
        with patch.object(self.parser,'gateway_module',return_value=self.m), patch.object(authority,'bound_projects',return_value={}):
            with self.assertRaisesRegex(ValueError,'unbound_project'):
                self.parser.write_task_file(self.hub,'demo','future',hashlib.sha256(self.text.encode()).hexdigest(),
                                            self.text.replace('Старое название','Недопустимая правка'))
        self.assertEqual(self.target.read_text(),self.text)
        self.assertEqual(self.native.writes,[])

    def test_completed_recurring_title_patch_keeps_series_open_for_next_pull(self):
        self.native.data['r']['completed']=True
        self.write(self.text.replace('Старое название','Новое название серии'))
        self.assertEqual(self.native.writes,[{'title':'Новое название серии'}])
        self.assertIn('Status: ready',self.target.read_text())
        config=self.sync.load_config(self.hub)
        self.assertFalse(config['projects']['demo']['tasks'][self.tid]['last_completed'])
        result=self.sync._sync(self.hub,config,apply=True,project='demo',native=self.native,reconcile=False)
        self.assertTrue(result['ok'],result)
        self.assertEqual(self.native.writes,[{'title':'Новое название серии'}])
        self.assertIn('Status: ready',self.target.read_text())

    def test_explicit_day_preserves_time_repeat_and_notes(self):
        original = copy.deepcopy(self.native.data['r'])
        self.write(self.text.replace('2026-10-30.', '2026-11-03.'))
        self.assertEqual(self.native.writes, [{'due':'2026-11-03T14:30:00+03:00'}])
        self.assertEqual(self.native.data['r']['repeat'], original['repeat'])
        self.assertEqual(self.native.data['r']['notes'], original['notes'])

    def test_unknown_update_resumes_without_second_write(self):
        self.native.fail_update = True
        requested = self.text.replace('Старое название', 'Новое название')
        with self.assertRaises(TimeoutError): self.write(requested)
        self.write(requested)
        self.assertEqual(len(self.native.writes), 1)
        self.assertIn('Новое название', self.target.read_text())

    def test_unknown_create_recovers_exact_marker_without_duplicate(self):
        tid = 'TASK-demo-20261030-002'
        requested = self.text + f'\n### {tid} — Новая задача\nStatus: ready\n'
        self.native.fail_create = True
        with self.assertRaises(TimeoutError): self.write(requested)
        self.write(requested)
        self.assertEqual(self.native.creates, 1)
        self.assertEqual(json.loads(self.config_path.read_text())['projects']['demo']['tasks'][tid]['reminder_id'], 'new')

    def test_unknown_create_without_marker_never_retries(self):
        self.native.fail_create = True
        requested = self.text + '\n### TASK-demo-20261030-002 — Новая задача\nStatus: ready\n'
        with self.assertRaises(TimeoutError): self.write(requested)
        self.native.data.pop('new')
        with self.assertRaisesRegex(ValueError, 'uncertain_creation'): self.write(requested)
        self.assertEqual(self.native.creates, 1)

    def test_new_creation_requires_readback_of_requested_fields(self):
        requested=self.text+'\n### TASK-demo-20261030-002 — Новая задача\nStatus: ready\n'
        original_get=self.native.get
        def changed(rid,*a):
            value=original_get(rid,*a)
            if rid=='new': value['title']='Исполнитель потерял название'
            return value
        self.native.get=changed
        with self.assertRaisesRegex(ValueError,'creation_readback_failed'): self.write(requested)
        self.assertEqual(self.target.read_text(),self.text)

    def test_verified_write_recovery_accepts_later_app_edit(self):
        requested=self.text.replace('Старое название','Новое название')
        with patch.object(self.parser,'write_task_file',side_effect=OSError('projection failed')):
            with self.assertRaises(OSError): self.write(requested)
        self.native.data['r']['title']='Более поздняя правка приложения'
        self.write(requested)
        self.assertEqual(len(self.native.writes),1)
        self.assertIn('Более поздняя правка приложения',self.target.read_text())

    def test_preflight_move_and_invalid_text_do_not_write(self):
        with self.assertRaisesRegex(ValueError, 'task_move_requires_batch'): self.write('# Задачи\n')
        with self.assertRaises(ValueError): self.write(self.text.replace('Status: ready', 'Status: invalid'))
        self.assertEqual(self.native.writes, [])
        self.assertEqual(self.target.read_text(), self.text)

    def test_cas_and_version_guard_prevent_overwrite(self):
        with self.assertRaisesRegex(ValueError, 'task_file_changed'): self.write(sha='0'*64)
        self.native.version_conflict = True
        with self.assertRaisesRegex(ValueError, 'version_conflict'):
            self.write(self.text.replace('Старое название', 'Новое название'))
        self.assertEqual(self.target.read_text(), self.text)

    def test_projection_failure_resumes_without_app_write(self):
        requested = self.text.replace('Старое название', 'Новое название')
        with patch.object(self.parser, 'write_task_file', side_effect=OSError('projection failed')):
            with self.assertRaises(OSError): self.write(requested)
        self.write(requested)
        self.assertEqual(len(self.native.writes), 1)
        self.assertIn('2026-11-02', self.target.read_text())

    def test_cancel_uses_existing_protocol(self):
        cancellation = type('Cancel', (), {})()
        cancellation.preview = lambda *a,**kw: {'path':'/synthetic/plan.json', 'sha256':'a'*64}
        calls = []
        cancellation.execute = lambda *a,**kw: calls.append(a) or {'ok':True}
        with patch.object(self.sync, 'cancellation_module', return_value=cancellation):
            self.write(self.text.replace('Status: ready', 'Status: dropped'))
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.native.writes, [])

    def test_cancel_recovery_delegates_progress_to_own_verified_protocol(self):
        calls=[]
        cancellation=type('Cancel',(),{})()
        cancellation.preview=lambda *a,**kw: {'path':'/synthetic/plan.json','sha256':'a'*64}
        requested=self.text.replace('Status: ready','Status: dropped')
        def execute(*a,**kw):
            calls.append(a)
            if len(calls)==1:
                config=json.loads(self.config_path.read_text())
                config['projects']['demo']['tasks'][self.tid]['cancellation']={'receipt':'synthetic'}
                self.config_path.write_text(json.dumps(config))
                self.target.write_text(requested+'\nКвитанция отмены.\n')
                raise OSError('interrupted after cancel commit')
            return {'ok':True}
        cancellation.execute=execute
        with patch.object(self.sync,'cancellation_module',return_value=cancellation):
            with self.assertRaises(OSError): self.write(requested)
            self.write(requested)
        self.assertEqual(len(calls),2)
        self.assertEqual(self.native.writes,[])

    def test_external_cli_routes_and_library_stays_internal(self):
        calls = []
        fake = type('Gateway', (), {'write_from_text':staticmethod(lambda *a,**k: calls.append(a) or {'result':'routed'}),
                                   'sync_module':staticmethod(lambda:self.sync)})()
        with patch.object(self.parser, 'gateway_module', return_value=fake), patch('sys.argv', ['task_records.py','write','--hub',str(self.hub),
                '--project-id','demo','--kind','future','--expected-sha256',hashlib.sha256(self.text.encode()).hexdigest()]), patch('sys.stdin', __import__('io').StringIO(self.text)):
            self.assertEqual(self.parser.main(), 0)
        self.assertEqual(len(calls), 1)
        self.parser.write_task_file(self.hub,'demo','future',hashlib.sha256(self.text.encode()).hexdigest(),self.text)
        self.assertEqual(len(calls), 1)
        requested=self.text.replace('Старое название','Правка через команду')
        with patch.object(self.parser,'gateway_module',return_value=self.m), patch.object(self.sync,'Native',return_value=self.native), \
                patch('sys.argv',['task_records.py','write','--hub',str(self.hub),'--project-id','demo','--kind','future',
                    '--expected-sha256',hashlib.sha256(self.text.encode()).hexdigest()]), \
                patch('sys.stdin',__import__('io').StringIO(requested)), patch('sys.stdout',__import__('io').StringIO()):
            self.assertEqual(self.parser.main(),0)
        self.assertEqual(self.native.writes,[{'title':'Правка через команду'}])
        self.assertIn('Правка через команду',self.target.read_text())
        self.assertIn('2026-11-02',self.target.read_text())

    def test_batch_move_keeps_id_and_recovers_partial_projection(self):
        texts = {'future':'# Задачи\n', 'current':f'Task ID: {self.tid}\nStatus: active\nЗапланировано: 2026-10-30.\n\n## Goal\n\nСтарое название\n\nКонтекст.\n'}
        expected = {k:hashlib.sha256((self.project / 'ai' / self.parser.TASK_FILES[k]).read_bytes()).hexdigest() for k in texts}
        writer = self.parser.write_task_file
        writes = []
        def interrupt(*a,**kw):
            writes.append(a[2])
            if len(writes)==2: raise OSError('interrupted projection')
            return writer(*a,**kw)
        with patch.object(self.parser,'write_task_file',side_effect=interrupt):
            with self.assertRaises(OSError):
                self.m.write_batch_from_texts(self.parser,self.hub,'demo',expected,texts,native=self.native)
        with patch.object(self.parser,'gateway_module',return_value=self.m), patch.object(self.sync,'Native',return_value=self.native), \
                patch('sys.argv',['task_records.py','write-batch','--hub',str(self.hub),'--project-id','demo']), \
                patch('sys.stdin',__import__('io').StringIO(json.dumps({'expected_sha256':expected,'texts':texts}))), \
                patch('sys.stdout',__import__('io').StringIO()):
            self.assertEqual(self.parser.main(),0)
        self.assertIn(self.tid,(self.project / 'ai/current-task.md').read_text())
        self.assertNotIn(self.tid,self.target.read_text())
        self.assertEqual(self.native.writes, [])


class FakeNative:
    def __init__(self):
        self.data = {'r':dict(id='r',list_id='l',list='Работа',version='v1',title='Удалённое название',due='2026-11-02T14:30:00+03:00',
                             completed=False,repeat={'frequency':'daily'},notes='Личная заметка')}
        self.writes=[]; self.creates=0; self.fail_update=False; self.fail_create=False; self.version_conflict=False
    def get(self,rid,lid,parent=None):
        row=copy.deepcopy(self.data[rid]); assert row['list_id']==lid and row.get('parent_id')==parent
        return row
    def children(self,b): return [copy.deepcopy(r) for r in self.data.values()]
    def update(self,row,changes):
        if self.version_conflict: raise ValueError('version_conflict')
        assert row['version']==self.data[row['id']]['version']
        self.writes.append(copy.deepcopy(changes)); self.data[row['id']].update(changes,version='v2')
        if self.fail_update: self.fail_update=False; raise TimeoutError('unknown_update')
    def call(self,tool,args):
        if tool=='list_lists':
            return {'lists':[{'id':'l','name':'Работа','account_id':'account','group_id':'g'}],
                    'groups':[{'id':'g','name':'Группа','account_id':'account'}]}
        assert tool=='create_reminder'
        self.creates+=1; self.data['new']=dict(args,id='new',list_id=args['list'],version='v1',completed=False)
        if self.fail_create: self.fail_create=False; raise TimeoutError('unknown_create')
        return copy.deepcopy(self.data['new'])


if __name__=='__main__': unittest.main()
