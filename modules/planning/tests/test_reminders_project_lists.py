"""Синтетические проверки режима проекта-списка; приложения не вызываются."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

m = load('project_lists_sync', Path(os.environ.get('CANCEL_TEST_SOURCE', str(ROOT / 'modules/planning/scripts/reminders_cancel.py'))).with_name('reminders_sync.py'))
legacy = load('project_lists_fixture', Path(__file__).with_name('legacy_reminders_sync_fixture.py'))
legacy.m = m
TID = 'TASK-demo-20261024-001'

class Native(m.Native):
    def __init__(self):
        self.data = {}
        self.calls = []
        self.fail_after = False
    def call(self, tool, args):
        self.calls.append((tool, copy.deepcopy(args)))
        if tool == 'get_reminder':
            return copy.deepcopy(self.data[args['id']])
        if tool == 'find_reminders':
            rows = [copy.deepcopy(row) for row in self.data.values() if row['list_id'] == args['list']]
            return dict(reminders=rows, count=len(rows))
        if tool == 'create_reminder':
            rid = 'r' + str(len(self.data))
            self.data[rid] = dict(args, id=rid, list='Работа', list_id=args['list'], version=1, completed=False)
            return copy.deepcopy(self.data[rid])
        if tool == 'update_reminder':
            changes = {key:value for key,value in args.items() if key not in {'id','version'}}
            row = self.data[args['id']]
            assert row['version'] == args['version']
            row.update(changes)
            row['version'] += 1
            if self.fail_after:
                self.fail_after = False
                raise TimeoutError('unknown_result')
            return copy.deepcopy(row)
        raise AssertionError(tool)

class ProjectListsTests(unittest.TestCase):
    def setUp(self):
        self.fixture = legacy.SyncTests('test_publish_dry_run_idempotent_and_deadline')
        self.fixture.setUp()
        self.addCleanup(self.fixture.temp.cleanup)
        self.hub = self.fixture.hub
        self.config = self.fixture.config
        self.config['binary'] = '/private/tmp/never-run'
        self.binding = self.config['projects']['demo']
        self.binding.update(layout='project_list', parent_id=None, native_group_id='g')
        self.native = Native()
    def run_sync(self, apply=True):
        return m.sync(self.hub, self.config, apply=apply, native=self.native)
    def publish(self):
        report = self.run_sync()
        self.assertTrue(report['ok'], report)
        return self.native.data[self.binding['tasks'][TID]['reminder_id']]
    def test_config_project_list_optional_parent_and_legacy(self):
        self.binding.pop('parent_id')
        path = self.hub / 'ai/reminders-sync.json'
        path.write_text(json.dumps(self.config))
        try:
            loaded = m.load_config(self.hub)
        except ValueError as exc:
            self.fail(str(exc))
        self.assertEqual(loaded['projects']['demo']['layout'], 'project_list')
        self.binding.pop('layout'); self.binding['parent_id'] = 'p'
        path.write_text(json.dumps(self.config))
        self.assertEqual(m.load_config(self.hub)['projects']['demo']['parent_id'], 'p')
    def test_config_unknown_layout_and_exclusive_list(self):
        self.binding['layout'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'unknown_project_layout'):
            m.validate_binding_ids(self.config)
        self.binding['layout'] = 'project_list'
        self.config['projects']['other'] = dict(list_id='l', list_name='Работа', parent_id='other')
        with self.assertRaisesRegex(ValueError, 'exclusive_project_list'):
            m.validate_binding_ids(self.config)
    def test_config_duplicate_history_and_null_parents(self):
        self.config['projects']['other'] = dict(layout='project_list', list_id='other', list_name='Другое', parent_id=None)
        try:
            m.validate_binding_ids(self.config)
        except ValueError as exc:
            self.fail(str(exc))
        self.binding['history'] = {'same': {}}
        self.config['projects']['other']['tasks'] = {'x': {'reminder_id':'same'}}
        with self.assertRaisesRegex(ValueError, 'duplicate_reminder_binding'):
            m.validate_binding_ids(self.config)
    def test_get_explicit_root_and_legacy_list_only(self):
        self.native.data['child'] = dict(id='child', list_id='l', parent_id='p')
        self.assertEqual(self.native.get('child', 'l')['id'], 'child')
        with self.assertRaisesRegex(ValueError, 'reminder_binding_mismatch'):
            self.native.get('child', 'l', None)
    def test_children_missing_parent_filters_nested(self):
        self.binding.pop('parent_id')
        self.native.data = {rid:dict(id=rid, list_id='l', list='Работа', title=rid, version=1, parent_id=parent)
                            for rid,parent in [('root',None),('nested','root')]}
        try:
            rows = self.native.children(self.binding)
        except KeyError as exc:
            self.fail(str(exc))
        self.assertEqual([row['id'] for row in rows], ['root'])
    def test_incomplete_count_blocks_children(self):
        self.native.call = lambda tool,args: dict(reminders=[], count=1)
        with self.assertRaisesRegex(ValueError, 'incomplete_reminder_snapshot'):
            self.native.children(self.binding)

    def test_publish_sync_and_nested_preserved(self):
        row = self.publish()
        created = next(args for tool,args in self.native.calls if tool == 'create_reminder')
        self.assertNotIn('parent_id', created)
        self.native.data['nested'] = dict(row, id='nested', parent_id=row['id'], title='Вложенная')
        before = copy.deepcopy(self.native.data['nested'])
        row.update(title='Новое название', due='2026-10-27')
        self.assertTrue(self.run_sync()['ok'])
        self.assertEqual(self.native.data['nested'], before)
        self.assertEqual(len(self.binding['tasks']), 1)
        self.assertIn('Новое название', self.fixture.files['future'].read_text())
    def test_notes_retry_preserves_protected_fields(self):
        row = self.publish()
        row['notes'] += '\nМоя заметка'
        self.binding['project_label'] = 'Подпись'
        protected = {key:row.get(key) for key in m.PROTECTED_REMINDER_FIELDS}
        self.native.fail_after = True
        self.assertFalse(m.sync_notes(self.hub, self.config, True, native=self.native)['ok'])
        self.assertIn('pending_notes', self.binding['tasks'][TID])
        result = m.sync_notes(self.hub, self.config, True, native=self.native)
        self.assertTrue(result['ok'], result)
        self.assertNotIn('pending_notes', self.binding['tasks'][TID])
        self.assertEqual(protected, {key:row.get(key) for key in m.PROTECTED_REMINDER_FIELDS})
        self.assertEqual(row['notes'], 'Подпись\nМоя заметка')
    def test_complete_project_without_parent(self):
        row = self.publish()
        self.binding['complete_requested'] = True
        result = self.run_sync()
        self.assertTrue(result['ok'], result)
        self.assertTrue(row['completed'])
        self.assertTrue(self.binding['last_completed'])
        self.assertNotIn('complete_requested', self.binding)
        self.assertEqual(len(self.native.data), 1)
    def test_history_and_repeating_completion_guard(self):
        row = self.publish()
        row['repeat'] = {'frequency':'daily'}
        self.assertTrue(self.run_sync()['ok'])
        self.native.data['old'] = dict(row, id='old', completed=True)
        self.assertTrue(self.run_sync()['ok'])
        self.assertIn('old', self.binding['history'])
        self.binding['complete_requested'] = True
        result = self.run_sync()
        self.assertFalse(result['ok'])
        self.assertIn('cascade_repeating_requires_explicit_cancel', str(result))
        self.assertFalse(row['completed'])
    def test_sync_foreign_unmarked_uuid_blocks_preview_and_apply(self):
        initial = copy.deepcopy(self.config)
        for kind in ('parent', 'task', 'history'):
            for apply in (False, True):
                with self.subTest(kind=kind, apply=apply):
                    self.config = copy.deepcopy(initial)
                    self.native = Native()
                    other = dict(list_id='other', list_name='Другое', parent_id='other-parent', tasks={}, history={})
                    if kind == 'parent': other['parent_id'] = 'foreign'
                    elif kind == 'task': other['tasks']['other-task'] = {'reminder_id':'foreign'}
                    else: other['history']['foreign'] = {}
                    self.config['projects']['other'] = other
                    self.native.data['foreign'] = dict(id='foreign', list_id='l', list='Работа', title='Чужая', version=1, notes='Обычная подпись')
                    before = copy.deepcopy(self.config)
                    result = m.sync(self.hub, self.config, apply=apply, project='demo', native=self.native)
                    self.assertFalse(result['ok'], result)
                    self.assertIn('foreign_reminder_binding', str(result))
                    self.assertFalse(any(row.get('action') == 'import' for row in result['items']))
                    self.assertEqual(self.config, before)
                    self.assertFalse(any(tool in {'create_reminder','update_reminder'} for tool,args in self.native.calls))

    def test_cancellation_receipt_fails_before_any_native_write(self):
        self.binding['tasks'][TID] = {'reminder_id':'r', 'cancellation':{'receipt':'placeholder'}}
        result = self.run_sync()
        self.assertFalse(result['ok'])
        self.assertIn('invalid_uuid', str(result))
        self.assertEqual(self.native.calls, [])

class ProjectListStructureTests(unittest.TestCase):
    def setUp(self):
        fixture = load('lists_structure_fixture', Path(__file__).with_name('legacy_reminders_structure_fixture.py'))
        self.structure = fixture.m
        self.case = fixture.StructureTests('test_move_dry_run_and_apply')
        self.case.setUp()
        self.addCleanup(self.case.temp.cleanup)
        c = self.case
        (c.hub / 'projects/list-project').mkdir()
        self.card = c.hub / 'ai/project-cards/list-project.md'
        self.card.write_text('Project ID: list-project\nStatus: active\nprimary_archiproject: sub\n')
        registry = c.hub / 'ai/project-registry.md'
        registry.write_text(registry.read_text() + f'## list-project\nStatus: active\nPath: {c.hub}/projects/list-project\nCard: ai/project-cards/list-project.md\n')
        self.binding = dict(layout='project_list', list_id='lp', list_name='Список проекта', native_group_id='n1', tasks={'x':{'reminder_id':'root'}}, history={'old':{}})
        c.config['projects']['list-project'] = self.binding
        c.config['structure']['projects']['list-project'] = dict(group='sub', list_id='lp')
        c.config['structure']['list_roles']['lp'] = dict(kind='project', project_id='list-project')
        c.native.lists.append(dict(id='lp', name='Список проекта', group_id='n1'))
        c.native.rows['lp'] = [dict(id=rid, title=rid, list_id='lp', version=1, parent_id=parent) for rid,parent in [('root',None),('old',None),('nested','root')]]
        (c.hub / 'ai/lists.json').write_text(json.dumps(['l1','l2','lp']))
        c.save_config()
    def run_structure(self, bidirectional=False):
        c = self.case
        c.config['structure']['bidirectional'] = bidirectional
        c.save_config()
        base = c.native
        class Reader:
            def call(self, tool, args):
                if tool == 'get_reminder':
                    return copy.deepcopy(next(row for rows in base.rows.values() for row in rows if row['id'] == args['id']))
                value = base.call(tool,args)
                if tool == 'list_lists':
                    value['groups'] = [dict(id='n1',name='a'),dict(id='n2',name='b')]
                return value
        result = self.structure.reconcile_structure(c.hub,c.config,apply=True,native=Reader())
        c.config = result['config']
        return result
    def test_mixed_structure_keeps_project_list_and_updates_legacy(self):
        for bidirectional in (False,True):
            with self.subTest(bidirectional=bidirectional):
                result = self.run_structure(bidirectional)
                self.assertTrue(result['ok'], result)
                self.assertIn('primary_archiproject: sub', self.card.read_text())
                self.assertEqual(result['config']['projects']['list-project'], self.binding)
                self.assertEqual(result['config']['projects']['demo']['list_id'], 'l2')
                self.case.config = result['config']
    def test_project_list_group_list_and_card_drift_conflict(self):
        c = self.case
        for bidirectional in (False,True):
            for field,value in [('group_id','n2'),('name','Переименован')]:
                with self.subTest(bidirectional=bidirectional,field=field):
                    row = c.native.lists[-1]; old = row[field]; row[field] = value
                    result = self.run_structure(bidirectional)
                    self.assertFalse(result['ok'], result)
                    self.assertIn('list-project', result['blocked_projects'])
                    self.assertIn('primary_archiproject: sub', self.card.read_text())
                    row[field] = old
            self.card.write_text(self.card.read_text().replace(': sub', ': a'))
            result = self.run_structure(bidirectional)
            self.assertFalse(result['ok'], result)
            self.assertIn('project_list_structure_conflict', str(result))
            self.card.write_text(self.card.read_text().replace(': a', ': sub'))
    def test_legacy_tree_cannot_enter_exclusive_project_list(self):
        c = self.case
        c.native.rows['lp'].extend(dict(row,list_id='lp') for row in c.native.rows['l2'])
        c.native.rows['l2'] = []
        for bidirectional in (False,True):
            result = self.run_structure(bidirectional)
            self.assertFalse(result['ok'], result)
            self.assertIn('exclusive_project_list', str(result))
            self.assertEqual(result['config']['projects']['demo']['list_id'], 'l1')

    def test_structure_foreign_unmarked_uuid_blocks_target(self):
        c = self.case
        original = copy.deepcopy(c.config)
        original_rows = copy.deepcopy(c.native.rows)
        for kind in ('parent', 'task', 'history'):
            for parent in (None, 'root'):
                for bidirectional in (False, True):
                    with self.subTest(kind=kind, parent=parent, bidirectional=bidirectional):
                        c.config = copy.deepcopy(original)
                        c.native.rows = copy.deepcopy(original_rows)
                        if kind == 'history':
                            c.config['projects']['demo']['history'] = {'foreign':{}}
                            moved = dict(id='foreign',title='Чужая',version=1)
                        else:
                            rid = 'parent' if kind == 'parent' else 'task'
                            moved = next(row for row in c.native.rows['l2'] if row['id'] == rid)
                            c.native.rows['l2'].remove(moved)
                        moved.update(list_id='lp', parent_id=parent, notes='Обычная подпись')
                        c.native.rows['lp'].append(moved)
                        result = self.run_structure(bidirectional)
                        self.assertIn('list-project', result['blocked_projects'], result)
                        self.assertTrue(any(row.get('project') == 'list-project' and row.get('error') == 'foreign_reminder_binding' for row in result['items']), result)
                        self.assertEqual(result['config']['projects']['list-project'], original['projects']['list-project'])
                        self.assertFalse(any(tool in {'manage_list','update_reminder','create_reminder'} for tool,args in c.native.calls))

    def test_retired_parent_exact_snapshot_only(self):
        c = self.case
        row = dict(id='retired', title='Старый проект', list_id='l1', version=1, notes='Hub project: list-project')
        c.native.rows['l1'].append(row)
        self.binding['retired_parent'] = dict(id='retired', list_id='l1', snapshot=copy.deepcopy(row))
        result = self.run_structure()
        self.assertTrue(result['ok'], result)
        c.config = result['config']
        row['notes'] = 'Hub project: foreign'
        result = self.run_structure()
        self.assertFalse(result['ok'], result)
        self.assertIn('retired_project_parent_changed', str(result))


class RetiredParentSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.fixture = ProjectListStructureTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.case = self.fixture.case
        self.structure = self.fixture.structure
        self.row = dict(id='retired', title='Старый проект', list_id='l1',
                        version='1', notes='Hub project: list-project',
                        images=[dict(id='img', type='image/png', width=10, height=10, bytes=20)],
                        alarms=[dict(id='alarm', date='2026-10-27')],
                        early_alerts=[dict(offset=-60)], urls=['https://example.test/extra'])
        self.case.native.rows['l1'].append(self.row)
        self.fixture.binding['retired_parent'] = dict(
            id='retired', list_id='l1', snapshot=copy.deepcopy(self.row))
        self.calls = []
        self.detail_changes = {}
        owner = self
        class Reader:
            def call(self, tool, args):
                owner.calls.append((tool, copy.deepcopy(args)))
                if tool == 'get_reminder':
                    row = copy.deepcopy(next(row for rows in owner.case.native.rows.values()
                                             for row in rows if row['id'] == args['id']))
                    if args['id'] == 'retired':
                        row.update(owner.detail_changes)
                    return row
                value = owner.case.native.call(tool, args)
                if tool == 'list_lists':
                    value['groups'] = [dict(id='n1', name='a'), dict(id='n2', name='b')]
                elif tool == 'find_reminders':
                    for row in value['reminders']:
                        # Нативный find добавляет smart_lists и сокращает подробные поля get.
                        row['smart_lists'] = ['Today']
                        if 'images' in row:
                            row['images'] = len(row['images'])
                        for key in ('alarms', 'early_alerts', 'urls'):
                            row.pop(key, None)
                return value
        self.reader = Reader()

    def run_structure(self, bidirectional, apply=True):
        if self.case.config['structure'].get('bidirectional') != bidirectional:
            self.case.config['structure']['bidirectional'] = bidirectional
            self.case.save_config()
        result = self.structure.reconcile_structure(
            self.case.hub, self.case.config, apply=apply, native=self.reader)
        self.case.config = result['config']
        return result

    def test_legacy_retired_parent_uses_full_narrow_snapshot(self):
        result = self.run_structure(False)
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['blocked_projects'], [])
        self.assertEqual(result['config']['projects']['demo']['list_id'], 'l2')
        self.assertEqual([args for tool, args in self.calls if tool == 'get_reminder'],
                         [dict(id='retired'), dict(id='retired')])
        journal = json.loads((self.case.hub / 'ai/structure-journal.json').read_text())
        self.assertEqual(journal['snapshot']['reminders']['retired'], self.row)
        self.assertIn('smart_lists', journal['snapshot']['reminders']['task'])

    def test_bidirectional_retired_parent_uses_full_snapshot(self):
        result = self.run_structure(True)
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['blocked_projects'], [])
        self.assertEqual(result['config']['projects']['demo']['list_id'], 'l2')
        journal = json.loads((self.case.hub / 'ai/structure-journal.json').read_text())
        self.assertEqual(journal['snapshot']['reminders']['retired'], self.row)

    def assert_detailed_change_blocks(self, bidirectional):
        original = copy.deepcopy(self.row)
        for field, value in [('images', [dict(original['images'][0], width=11)]),
                             ('alarms', [dict(id='changed')]),
                             ('early_alerts', [dict(offset=-120)]),
                             ('urls', ['https://example.test/changed']),
                             ('notes', 'Чужая заметка')]:
            for apply in (False, True):
                with self.subTest(field=field, apply=apply):
                    self.row.clear(); self.row.update(copy.deepcopy(original))
                    self.row[field] = value
                    self.case.config['structure']['bidirectional'] = bidirectional
                    self.case.save_config()
                    before = {p:p.read_bytes() for p in self.case.hub.rglob('*') if p.is_file()}
                    result = self.structure.reconcile_structure(
                        self.case.hub, self.case.config, apply=apply, native=self.reader)
                    self.assertFalse(result['ok'], result)
                    self.assertIn('retired_project_parent_changed', str(result))
                    self.assertEqual(result['blocked_projects'], ['demo', 'list-project'])
                    self.assertEqual(before, {p:p.read_bytes() for p in self.case.hub.rglob('*') if p.is_file()})
                    self.assertEqual(self.row['version'], original['version'])
                    self.assertEqual(len(self.row['images']), len(original['images']))
        self.row.clear(); self.row.update(original)

    def test_legacy_retired_parent_detailed_change_blocks(self):
        self.assert_detailed_change_blocks(False)

    def test_bidirectional_retired_parent_detailed_change_blocks(self):
        self.assert_detailed_change_blocks(True)

    def test_retired_parent_get_identity_version_and_list_are_guarded(self):
        for mode in (False, True):
            for key, value in [('id', 'other'), ('version', '2'), ('list_id', 'l2')]:
                with self.subTest(bidirectional=mode, field=key):
                    self.detail_changes = {key:value}
                    with self.assertRaisesRegex(ValueError, 'structure_snapshot_changed'):
                        self.structure.snapshot(self.reader,
                            self.case.config['structure']['list_roles'], {'l1', 'l2', 'lp'},
                            detailed=mode, detailed_ids={'retired'})
                    self.assertFalse((self.case.hub / 'ai/structure-journal.json').exists())

    def interrupt_journal(self, bidirectional):
        original = self.structure.atomic_write
        journal = self.case.hub / 'ai/structure-journal.json'
        def crash(path, data):
            original(path, data)
            if path == (self.case.config_path if bidirectional else journal):
                raise OSError('simulated crash after journal')
        with patch.object(self.structure, 'atomic_write', crash):
            result = self.run_structure(bidirectional)
        self.assertFalse(result['ok'], result)
        self.assertIn('simulated crash after journal', str(result))
        pending = json.loads(journal.read_text())
        self.assertEqual(pending['status'], 'pending')
        self.assertEqual(pending['snapshot']['reminders']['retired'], self.row)
        self.case.config = json.loads(self.case.config_path.read_text())
        return journal

    def assert_recovery_comparable(self, bidirectional):
        journal = self.interrupt_journal(bidirectional)
        result = self.run_structure(bidirectional)
        self.assertTrue(result['ok'], result)
        self.assertEqual(json.loads(journal.read_text())['status'], 'complete')
        self.assertEqual(json.loads(journal.read_text())['snapshot']['reminders']['retired'], self.row)
        self.assertEqual(result['config']['projects']['demo']['list_id'], 'l2')
        self.assertIn('primary_archiproject: b', self.case.card.read_text())
        if not bidirectional:
            self.assertEqual({args['id'] for tool,args in self.calls if tool == 'get_reminder'}, {'retired'})

    def test_legacy_journal_recovery_uses_comparable_retired_snapshot(self):
        self.assert_recovery_comparable(False)

    def test_bidirectional_journal_recovery_uses_comparable_retired_snapshot(self):
        self.assert_recovery_comparable(True)

    def assert_recovery_changed(self, bidirectional, version=False):
        journal = self.interrupt_journal(bidirectional)
        if version:
            self.row['version'] = '2'
        else:
            self.row['images'][0]['width'] = 11
        before = {p:p.read_bytes() for p in self.case.hub.rglob('*') if p.is_file()}
        result = self.run_structure(bidirectional)
        self.assertFalse(result['ok'], result)
        self.assertEqual(json.loads(journal.read_text())['status'], 'pending')
        self.assertEqual(before, {p:p.read_bytes() for p in self.case.hub.rglob('*') if p.is_file()})
        self.assertIn('retired_project_parent_changed' if bidirectional else 'structure_snapshot_changed', str(result))

    def test_legacy_journal_recovery_rejects_detailed_change(self):
        self.assert_recovery_changed(False)

    def test_bidirectional_journal_recovery_rejects_detailed_change(self):
        self.assert_recovery_changed(True)

    def test_bidirectional_journal_recovery_rejects_retired_version_change(self):
        self.assert_recovery_changed(True, version=True)

    def test_legacy_native_allows_get_but_keeps_write_prohibition(self):
        config = self.case.config
        native = self.structure.StructureNative(config)
        class Reply:
            returncode = 0
            stdout = json.dumps(self.row)
        with patch.object(self.structure.subprocess, 'run', return_value=Reply()) as run:
            try:
                actual = native.call('get_reminder', dict(id='retired'))
            except ValueError as exc:
                actual = dict(error=str(exc))
            self.assertEqual(actual, self.row)
            self.assertEqual(run.call_args.args[0][1:3], ['call', 'get_reminder'])
            for tool in ('manage_list', 'update_reminder', 'create_reminder', 'delete_reminder'):
                with self.subTest(tool=tool):
                    with self.assertRaisesRegex(ValueError, 'structure_read_only'):
                        native.call(tool, {})
            self.assertEqual(run.call_count, 1)

if __name__ == '__main__':
    unittest.main()
