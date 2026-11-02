"""Изолированные проверки подписей; реальные Напоминания не открываются."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/reminders_sync.py'
spec = importlib.util.spec_from_file_location('labels_subject', SOURCE)
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)
REAL_HUB = Path(__file__).resolve().parents[5]
TID = 'TASK-demo-20261026-001'


class Native:
    def __init__(self):
        self.rows = {
            'parent': dict(id='parent', list_id='list', parent_id=None, title='Проект', version=1, completed=False),
            'task': dict(id='task', list_id='list', parent_id='parent', title='Задача', version=1,
                         completed=False, notes='Моя заметка', due='2026-11-01'),
        }
        self.updates = []
        self.fail_after = False
        self.race = False

    def get(self, rid, lid, parent=None):
        row = self.rows[rid]
        if row['list_id'] != lid or (parent is not None and row['parent_id'] != parent):
            raise ValueError('binding_mismatch')
        return copy.deepcopy(row)

    def update(self, row, changes):
        assert set(changes) == {'notes'}, changes
        if self.race:
            self.rows[row['id']]['notes'] = 'Чужая свежая правка'
            self.rows[row['id']]['version'] += 1
        if self.rows[row['id']]['version'] != row['version']:
            raise ValueError('stale_version')
        self.updates.append(copy.deepcopy(changes))
        self.rows[row['id']].update(changes)
        self.rows[row['id']]['version'] += 1
        if self.fail_after:
            self.fail_after = False
            raise TimeoutError('unknown_result')


class LabelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='labels-')
        self.addCleanup(self.temp.cleanup)
        self.hub = Path(self.temp.name).resolve()
        (self.hub / 'ai').mkdir()
        (self.hub / 'scripts').mkdir()
        shutil.copy(REAL_HUB / 'scripts/task_records.py', self.hub / 'scripts/task_records.py')
        self.project = self.hub / 'projects/demo'
        (self.project / 'ai').mkdir(parents=True)
        (self.hub / 'ai/project-registry.md').write_text(f'## demo\nName: Название проекта\nStatus: active\nPath: {self.project}\n')
        (self.project / 'ai/current-task.md').write_text('# Текущая задача\n\nStatus: empty\n')
        (self.project / 'ai/future-tasks.md').write_text(f'# Будущие задачи\n\n### {TID} — Задача\nStatus: ready\nDue: 2026-12-31\n')
        (self.project / 'ai/paused-tasks.md').write_text('# Пауза\n')
        self.allowlist = self.hub / 'ai/allowed.json'
        self.allowlist.write_text(json.dumps({'names': ['Работа']}))
        self.config = dict(version=1, binary='/tmp/never-run', allowlist_file=str(self.allowlist),
                           projects={'demo': dict(list_id='list', list_name='Работа', parent_id='parent',
                                                  tasks={TID: {'reminder_id': 'task'}})})
        (self.hub / 'ai/reminders-sync.json').write_text(json.dumps(self.config))
        self.native = Native()

    def test_project_label_override_registry_and_fallback(self):
        binding = self.config['projects']['demo']
        self.assertEqual(sync.project_label(self.hub, 'demo', binding), 'Название проекта')
        self.assertEqual(sync.project_label(self.hub, 'demo', dict(binding, project_label='Подпись')), 'Подпись')
        self.assertEqual(sync.project_label(self.hub, 'missing', {}), 'missing')
        with self.assertRaises(ValueError):
            sync.project_label(self.hub, 'demo', dict(binding, project_label='Плохая\nподпись'))
        with self.assertRaises(ValueError):
            sync.project_label(self.hub, 'demo', dict(binding, project_label='Плохая\u202eподпись'))

    def test_managed_notes_first_line_no_deadline_preserves_user_text(self):
        row = dict(project_id='demo', task_id=TID, project_label='Название проекта', deadline='2026-12-31')
        notes, owner = sync.managed_notes('  Моя заметка\nКонец  ', row, {})
        self.assertEqual(notes, 'Название проекта\n  Моя заметка\nКонец  ')
        self.assertNotIn('Крайний срок:', notes)
        self.assertEqual(sync.managed_notes(notes, row, {'notes_owner': owner})[0], notes)

    def test_legacy_block_removes_only_proven_deadline(self):
        row = dict(project_id='demo', task_id=TID, project_label='Название проекта', deadline='2026-12-31')
        old = ('Перед\n' + '--- Hub metadata ---\nHub Task ID: ' + TID +
               '\nHub project: demo\nКрайний срок: 2026-12-31\n--- /Hub metadata ---' +
               '\nПосле\nКрайний срок: пользовательский текст')
        notes, _ = sync.managed_notes(old, row, {})
        self.assertEqual(notes, 'Название проекта\nПеред\n\nПосле\nКрайний срок: пользовательский текст')

    def test_repeating_retains_single_identity_without_deadline(self):
        row = dict(project_id='demo', task_id=TID, project_label='Название проекта', deadline='2026-12-31')
        notes, owner = sync.managed_notes('Моя заметка', row, {}, repeating=True)
        self.assertTrue(notes.startswith('Название проекта\nМоя заметка'))
        self.assertEqual(notes.count('Хаб: '), 1)
        self.assertNotIn('Крайний срок:', notes)
        self.assertEqual(sync.creation_identity({'notes': notes}, {sync.compact_code('demo', TID): ('demo', TID)}), ('demo', TID))
        self.assertEqual(sync.managed_notes(notes, row, {'notes_owner': owner}, repeating=True)[0], notes)

    def test_creation_marker_has_label_then_cleans_to_label(self):
        row = dict(project_id='demo', task_id=TID, project_label='Название проекта', deadline='2026-12-31')
        created = sync.notes_for(row)
        self.assertEqual(created.splitlines()[0], 'Название проекта')
        self.assertEqual(sync.creation_identity({'notes': created}), ('demo', TID))
        self.assertEqual(sync.managed_notes(created, row, {})[0], 'Название проекта')

    def test_creation_marker_with_inserted_text_refuses(self):
        row = dict(project_id='demo', task_id=TID, project_label='Название проекта', deadline=None)
        created = sync.notes_for(row)
        changed = created.replace('Название проекта\n--- Hub metadata ---',
                                  'Название проекта\nПеред\nНазвание проекта\n--- Hub metadata ---')
        with self.assertRaisesRegex(ValueError, 'ambiguous_managed_notes'):
            sync.managed_notes(changed, row, {})

    def test_compact_unowned_deadline_is_ambiguous(self):
        row = dict(project_id='demo', task_id=TID, project_label='Название проекта', deadline='2026-12-31')
        old = 'Хаб: ' + sync.compact_code('demo', TID) + '\nКрайний срок: 2026-12-31'
        with self.assertRaisesRegex(ValueError, 'notes_ownership_conflict'):
            sync.managed_notes(old, row, {}, repeating=True)

    def test_owned_deadline_ambiguity_refuses_without_change(self):
        row = dict(project_id='demo', task_id=TID, project_label='Название проекта', deadline='2026-12-31')
        old = 'Моя заметка\n\nКрайний срок: 2026-12-31'
        owner = {'snapshot': old, 'start': len('Моя заметка'), 'end': len(old),
                 'line': 'Крайний срок: 2026-12-31', 'prefix': '\n\n'}
        with self.assertRaisesRegex(ValueError, 'notes_ownership_conflict'):
            sync.managed_notes(old + '\n' + old, row, {'notes_owner': owner})

    def test_owned_deadline_unique_snapshot_shift_preserves_user_text(self):
        row = dict(project_id='demo', task_id=TID, project_label='Название проекта', deadline='2026-12-31')
        old = 'Моя заметка\n\nКрайний срок: 2026-12-31'
        owner = {'snapshot': old, 'start': len('Моя заметка'), 'end': len(old),
                 'line': 'Крайний срок: 2026-12-31', 'prefix': '\n\n'}
        notes, _ = sync.managed_notes('Перед\n' + old + '\nПосле', row, {'notes_owner': owner})
        self.assertEqual(notes, 'Название проекта\nПеред\nМоя заметка\nПосле')

    def test_owned_deadline_removed_from_plain_notes(self):
        row = dict(project_id='demo', task_id=TID, project_label='Название проекта', deadline='2026-12-31')
        old = 'Моя заметка\n\nКрайний срок: 2026-12-31'
        owner = {'snapshot': old, 'start': len('Моя заметка'), 'end': len(old),
                 'line': 'Крайний срок: 2026-12-31', 'prefix': '\n\n'}
        notes, new_owner = sync.managed_notes(old, row, {'notes_owner': owner})
        self.assertEqual(notes, 'Название проекта\nМоя заметка')
        self.assertEqual(new_owner['label'], 'Название проекта')

    def test_notes_preview_apply_replay_and_native_fields(self):
        before = copy.deepcopy(self.native.rows['task'])
        files = {p.name: p.read_bytes() for p in (self.project / 'ai').iterdir()}
        preview = sync.sync_notes(self.hub, self.config, native=self.native)
        self.assertTrue(preview['ok'])
        self.assertEqual(self.native.rows['task'], before)
        result = sync.sync_notes(self.hub, self.config, apply=True, native=self.native)
        self.assertTrue(result['ok'])
        self.assertEqual(self.native.rows['task']['notes'], 'Название проекта\nМоя заметка')
        self.assertEqual({k: v for k, v in self.native.rows['task'].items() if k not in {'notes', 'version'}},
                         {k: v for k, v in before.items() if k not in {'notes', 'version'}})
        self.assertEqual(len(self.native.updates), 1)
        self.assertEqual(files, {p.name: p.read_bytes() for p in (self.project / 'ai').iterdir()})
        self.assertEqual(set(self.native.rows), {'parent', 'task'})
        self.assertTrue(sync.sync_notes(self.hub, self.config, apply=True, native=self.native)['ok'])
        self.assertEqual(len(self.native.updates), 1)

    def test_notes_preview_includes_uuid_and_version(self):
        report = sync.sync_notes(self.hub, self.config, native=self.native)
        item = next(item for item in report['items'] if item.get('action') == 'notes')
        self.assertEqual(item.get('reminder_id'), 'task')
        self.assertEqual(item.get('version'), 1)
        self.assertEqual(item['before'], 'Моя заметка')
        self.assertEqual(item['after'], 'Название проекта\nМоя заметка')

    def test_notes_timeout_resume_and_race(self):
        self.native.fail_after = True
        self.assertFalse(sync.sync_notes(self.hub, self.config, apply=True, native=self.native)['ok'])
        self.assertIn('pending_notes', json.loads((self.hub / 'ai/reminders-sync.json').read_text())['projects']['demo']['tasks'][TID])
        self.config = json.loads((self.hub / 'ai/reminders-sync.json').read_text())
        self.assertTrue(sync.sync_notes(self.hub, self.config, apply=True, native=self.native)['ok'])
        self.assertEqual(len(self.native.updates), 1)
        self.assertNotIn('pending_notes', self.config['projects']['demo']['tasks'][TID])
        self.config['projects']['demo']['project_label'] = 'Новая подпись'
        self.native.race = True
        self.assertFalse(sync.sync_notes(self.hub, self.config, apply=True, native=self.native)['ok'])
        self.assertEqual(self.native.rows['task']['notes'], 'Чужая свежая правка')

    def test_notes_skips_completed_and_cancelled(self):
        self.native.rows['task']['completed'] = True
        self.assertTrue(sync.sync_notes(self.hub, self.config, apply=True, native=self.native)['ok'])
        self.assertEqual(self.native.updates, [])
        self.native.rows['task']['completed'] = False
        self.config['projects']['demo']['tasks'][TID]['cancellation'] = {'receipt': 'protected'}
        self.assertTrue(sync.sync_notes(self.hub, self.config, apply=True, native=self.native)['ok'])
        self.assertEqual(self.native.updates, [])

    def test_pending_notes_foreign_edit_conflicts(self):
        link = self.config['projects']['demo']['tasks'][TID]
        link['pending_notes'] = {'before': 'Моя заметка', 'after': 'Название проекта\nМоя заметка',
                                 'owner': {'snapshot': 'Название проекта\nМоя заметка', 'label': 'Название проекта'}}
        self.native.rows['task']['notes'] = 'Сторонняя правка'
        result = sync.sync_notes(self.hub, self.config, apply=True, native=self.native)
        self.assertFalse(result['ok'])
        self.assertIn('pending_notes_conflict', str(result))
        self.assertEqual(self.native.rows['task']['notes'], 'Сторонняя правка')
        self.assertEqual(self.native.updates, [])

    def test_pending_after_preview_and_apply_recovers(self):
        link = self.config['projects']['demo']['tasks'][TID]
        old = 'Моя заметка\n\nКрайний срок: 2026-12-31'
        after = 'Название проекта\nМоя заметка'
        link['notes_owner'] = {'snapshot': old, 'start': len('Моя заметка'), 'end': len(old),
                               'line': 'Крайний срок: 2026-12-31', 'prefix': '\n\n'}
        link['pending_notes'] = {'before': old, 'after': after,
                                 'owner': {'snapshot': after, 'label': 'Название проекта'},
                                 'protected': {key: self.native.rows['task'].get(key) for key in
                                               ('id', 'title', 'due', 'completed', 'list', 'list_id', 'parent_id', 'repeat')}}
        self.native.rows['task']['notes'] = after
        self.assertTrue(sync.sync_notes(self.hub, self.config, native=self.native)['ok'])
        self.assertTrue(sync.sync_notes(self.hub, self.config, apply=True, native=self.native)['ok'])
        self.assertNotIn('pending_notes', link)
        self.assertEqual(self.native.updates, [])

    def test_legacy_block_preserves_same_named_user_line(self):
        row = dict(project_id='demo', task_id=TID, project_label='Название проекта', deadline=None)
        legacy = ('Перед\nНазвание проекта\n--- Hub metadata ---\nHub Task ID: ' + TID +
                  '\nHub project: demo\n--- /Hub metadata ---\nПосле')
        notes, owner = sync.managed_notes(legacy, row, {})
        self.assertEqual(notes, 'Название проекта\nПеред\nНазвание проекта\n\nПосле')
        renamed, _ = sync.managed_notes(notes, dict(row, project_label='Новое название'), {'notes_owner': owner})
        self.assertEqual(renamed, 'Новое название\nПеред\nНазвание проекта\n\nПосле')

    def test_unowned_same_first_line_stays_user_text_on_rename(self):
        row = dict(project_id='demo', task_id=TID, project_label='Название проекта', deadline=None)
        notes, owner = sync.managed_notes('Название проекта\nМоя заметка', row, {})
        self.assertEqual(notes, 'Название проекта\nНазвание проекта\nМоя заметка')
        renamed, _ = sync.managed_notes(notes, dict(row, project_label='Новое название'), {'notes_owner': owner})
        self.assertEqual(renamed, 'Новое название\nНазвание проекта\nМоя заметка')

    def test_owned_label_unique_shift_preserves_user_prefix(self):
        row = dict(project_id='demo', task_id=TID, project_label='Название проекта', deadline=None)
        notes, owner = sync.managed_notes('Моя заметка', row, {})
        shifted = 'Перед\n' + notes + '\nПосле'
        moved, _ = sync.managed_notes(shifted, dict(row, project_label='Новое название'), {'notes_owner': owner})
        self.assertEqual(moved, 'Новое название\nПеред\nМоя заметка\nПосле')

    def test_readback_protected_field_change_keeps_pending(self):
        original = self.native.update
        def changed(row, changes):
            original(row, changes)
            self.native.rows[row['id']]['due'] = '2099-01-01'
        self.native.update = changed
        result = sync.sync_notes(self.hub, self.config, apply=True, native=self.native)
        self.assertFalse(result['ok'])
        self.assertIn('remote_protected_fields_changed', str(result))
        self.assertEqual(self.native.rows['task']['due'], '2099-01-01')
        self.assertIn('pending_notes', self.config['projects']['demo']['tasks'][TID])

    def test_pending_after_protected_change_stays_conflict(self):
        link = self.config['projects']['demo']['tasks'][TID]
        after = 'Название проекта\nМоя заметка'
        link['pending_notes'] = {'before': 'Моя заметка', 'after': after,
                                 'owner': {'snapshot': after, 'label': 'Название проекта'},
                                 'protected': {'id': 'task', 'title': 'Задача', 'due': '2026-11-01',
                                               'completed': False, 'list_id': 'list', 'parent_id': 'parent'}}
        self.native.rows['task']['notes'] = after
        self.native.rows['task']['due'] = '2099-01-01'
        result = sync.sync_notes(self.hub, self.config, apply=True, native=self.native)
        self.assertFalse(result['ok'])
        self.assertIn('remote_protected_fields_changed', str(result))
        self.assertIn('pending_notes', link)
        self.assertEqual(self.native.updates, [])

    def test_allowlist_preflight_blocks_all_before_native_access(self):
        other = self.hub / 'projects/other'
        (other / 'ai').mkdir(parents=True)
        (other / 'ai/current-task.md').write_text('# Текущая задача\n\nStatus: empty\n')
        (other / 'ai/future-tasks.md').write_text('# Будущие задачи\n')
        (other / 'ai/paused-tasks.md').write_text('# Пауза\n')
        (self.hub / 'ai/project-registry.md').write_text((self.hub / 'ai/project-registry.md').read_text() +
                                                           f'## other\nName: Другой\nStatus: active\nPath: {other}\n')
        self.config['projects']['other'] = dict(list_id='other-list', list_name='Чужой список', parent_id='other-parent', tasks={})
        self.native.get = lambda *args: self.fail('native access before allowlist preflight')
        result = sync.sync_notes(self.hub, self.config, apply=True, native=self.native)
        self.assertFalse(result['ok'])
        self.assertIn('list_outside_allowlist', str(result))
        self.assertEqual(self.native.updates, [])

    def test_ordinary_sync_rejects_notes_wal_with_foreign_due(self):
        legacy_path = Path(__file__).with_name('legacy_reminders_sync_fixture.py')
        spec = importlib.util.spec_from_file_location('legacy_wal_fixture', legacy_path)
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        fixture.m = sync
        case = fixture.SyncTests('test_publish_dry_run_idempotent_and_deadline')
        case.setUp()
        self.addCleanup(case.temp.cleanup)
        remote = case.publish()
        tid = 'TASK-demo-20261024-001'
        link = case.config['projects']['demo']['tasks'][tid]
        protected = {key: remote.get(key) for key in sync.PROTECTED_REMINDER_FIELDS}
        link['pending_notes'] = {'before': 'Предыдущая заметка', 'after': remote['notes'],
                                 'owner': link['notes_owner'], 'protected': protected}
        before_files = {kind: path.read_bytes() for kind, path in case.files.items()}
        remote['due'] = '2099-01-01'
        result = case.run_sync()
        self.assertFalse(result['ok'])
        self.assertIn('remote_protected_fields_changed', str(result))
        self.assertIn('pending_notes', link)
        self.assertEqual(before_files, {kind: path.read_bytes() for kind, path in case.files.items()})
        self.assertEqual(remote['due'], '2099-01-01')


if __name__ == '__main__':
    unittest.main()
