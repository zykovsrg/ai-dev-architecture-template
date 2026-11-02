"""Изолированные проверки: приложение и рабочие задачи не используются."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[3] / 'modules/planning/scripts/reminders_sync.py'
spec = importlib.util.spec_from_file_location('sync_subject', SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
REAL_HUB = Path(__file__).resolve().parents[5]

class Native:
    def __init__(self):
        self.data = {'p': dict(id='p', list_id='l', title='Проект', version=1, completed=False)}
        self.calls = []
    def get(self, rid, lid, parent=None):
        row = self.data[rid]
        if row['list_id'] != lid or (parent and row.get('parent_id') != parent):
            raise ValueError('wrong_binding')
        return dict(row)
    def children(self, binding):
        return [dict(r) for r in self.data.values() if r.get('parent_id') == binding['parent_id']]
    def call(self, tool, args):
        self.calls.append((tool, args))
        if tool != 'create_reminder': raise AssertionError(tool)
        rid = 'r' + str(len(self.data))
        self.data[rid] = dict(args, id=rid, list_id=args['list'], version=1, completed=False)
        return dict(self.data[rid])
    def update(self, row, changes):
        self.calls.append(('update', changes))
        self.data[row['id']].update(changes)
        self.data[row['id']]['version'] += 1

class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hub-sync-')
        self.addCleanup(self.temp.cleanup)
        self.hub = Path(self.temp.name).resolve()
        (self.hub / 'ai').mkdir()
        (self.hub / 'scripts').mkdir()
        # Писатель использует только свою папку и реальную проверенную реализацию.
        shutil.copy(REAL_HUB / 'scripts/task_records.py', self.hub / 'scripts/task_records.py')
        self.project = self.hub / 'projects/demo'
        (self.project / 'ai').mkdir(parents=True)
        (self.hub / 'ai/project-registry.md').write_text(f'## demo\nStatus: active\nPath: {self.project}\n')
        self.files = {k: self.project / 'ai' / name for k, name in m.NAMES.items()}
        self.files['current'].write_text('# Текущая задача\n\nStatus: empty\n')
        self.files['future'].write_text('# Будущие задачи\n\n### TASK-demo-20261024-001 — Сделать страницу\nStatus: ready\nDue: 2026-12-31\nЗапланировано: 2026-10-25.\n\nПолный контекст задачи.\n')
        self.files['paused'].write_text('# Пауза\n')
        allowlist = self.hub / 'ai/allowed.json'
        allowlist.write_text(json.dumps({'names': ['Работа']}))
        self.config = dict(version=1, binary='/tmp/test-binary', allowlist_file=str(allowlist), projects={'demo': dict(list_id='l', list_name='Работа', parent_id='p', tasks={})})
        self.native = Native()
    def run_sync(self, apply=True):
        return m.sync(self.hub, self.config, apply, native=self.native)
    def publish(self):
        self.assertTrue(self.run_sync()['ok'])
        link = self.config['projects']['demo']['tasks']['TASK-demo-20261024-001']
        return self.native.data[link['reminder_id']]
    def test_compact_migration_preserves_notes_deadline_and_native_fields(self):
        row = self.publish()
        canonical = m.HubProject(self.hub, 'demo').rows()['TASK-demo-20261024-001']
        legacy = ('--- Hub metadata ---\nHub Task ID: ' + canonical['task_id'] +
                  '\nHub project: demo\nКрайний срок: 2026-12-31\n--- /Hub metadata ---')
        row.update(repeat={'frequency': 'daily'}, notes='  Моя заметка\n\n' + legacy + '\nХвост  ')
        before = {k: v for k, v in row.items() if k not in {'notes', 'version'}}
        self.assertTrue(self.run_sync()['ok'])
        code = m.compact_code('demo', canonical['task_id'])
        self.assertEqual(code, 'd5176c1c6b76')
        self.assertEqual(row['notes'], 'demo\n  Моя заметка\n\nХаб: ' + code + '\nХвост  ')
        self.assertEqual(before, {k: v for k, v in row.items() if k not in {'notes', 'version'}})
        calls = len(self.native.calls)
        self.assertTrue(self.run_sync()['ok'])
        self.assertEqual(len(self.native.calls), calls)
    def test_compact_completed_copy_recognized_with_legacy_history(self):
        row = self.publish()
        canonical = m.HubProject(self.hub, 'demo').rows()['TASK-demo-20261024-001']
        row.update(repeat={'frequency': 'daily'}, notes=m.notes_for(canonical))
        self.native.data['oldcopy'] = dict(row, id='oldcopy', completed=True)
        self.assertTrue(self.run_sync()['ok'])
        self.assertIn('Хаб: ', row['notes'])
        self.native.data['newcopy'] = dict(row, id='newcopy', completed=True)
        self.assertTrue(self.run_sync()['ok'])
        self.assertEqual(set(self.config['projects']['demo']['history']), {'oldcopy', 'newcopy'})
        self.assertEqual(len(m.inventory(self.hub)), 1)
        self.assertTrue(self.run_sync()['ok'])
    def test_compact_rejects_malformed_duplicate_mixed_unknown_and_foreign(self):
        row = self.publish()
        canonical = m.HubProject(self.hub, 'demo').rows()['TASK-demo-20261024-001']
        valid = 'Хаб: ' + m.compact_code('demo', canonical['task_id'])
        samples = ['Хаб: wrong', valid + '\n' + valid, valid + '\n' + m.notes_for(canonical), 'Хаб: 000000000000', 'Хаб: ' + m.compact_code('other', canonical['task_id']), '  ' + valid]
        for notes in samples:
            with self.subTest(notes=notes):
                row.update(repeat={'frequency': 'daily'}, notes=notes)
                before = dict(row)
                self.assertFalse(self.run_sync()['ok'])
                self.assertEqual(row, before)
    def test_compact_unknown_child_code_fails_before_import(self):
        self.publish()
        self.native.data['unknown'] = dict(id='unknown', title='Чужая', list_id='l', parent_id='p', version=1, completed=True, notes='Хаб: 000000000000')
        before = self.files['future'].read_text()
        self.assertFalse(self.run_sync()['ok'])
        self.assertEqual(before, self.files['future'].read_text())
    def test_compact_collision_blocks_all_native_access(self):
        self.publish()
        self.config['projects']['other'] = dict(list_id='q', list_name='Другое', parent_id='q', tasks={'TASK-other-1': {'reminder_id': 'z'}})
        original = m.compact_code
        m.compact_code = lambda pid, tid: '0' * 12
        self.addCleanup(setattr, m, 'compact_code', original)
        self.native.children = lambda binding: self.fail('native access before collision check')
        with self.assertRaisesRegex(ValueError, 'compact_code_collision'):
            self.run_sync()
    def test_compact_deadline_update_and_cancel_preserve_user_text(self):
        row = self.publish()
        row['repeat'] = {'frequency': 'daily'}
        self.assertTrue(self.run_sync()['ok'])
        self.assertIn('Хаб: ', row['notes'])
        row['notes'] = 'Моё\n' + row['notes'] + '\nКонец'
        self.files['future'].write_text(self.files['future'].read_text().replace('Due: 2026-12-31', 'Due: 2027-01-02'))
        self.assertTrue(self.run_sync()['ok'])
        self.assertTrue(row['notes'].startswith('demo\nМоё\n'))
        self.assertNotIn('Крайний срок: 2027-01-02', row['notes'])
        self.assertNotIn('2026-12-31', row['notes'])
        row.pop('repeat')
        self.assertTrue(self.run_sync()['ok'])
        self.assertNotIn('Хаб:', row['notes'])
        self.assertTrue(row['notes'].startswith('demo\nМоё\n'))
        self.assertTrue(row['notes'].endswith('\nКонец'))
    def test_publish_dry_run_idempotent_and_deadline(self):
        before = self.files['future'].read_text()
        self.assertTrue(self.run_sync(False)['ok'])
        self.assertEqual(self.native.calls, [])
        row = self.publish()
        self.assertEqual(row['due'], '2026-10-25')
        created = next(args for tool, args in self.native.calls if tool == 'create_reminder')
        self.assertEqual(created['due'], '2026-10-25')
        self.assertEqual(row['notes'], 'demo')
        self.assertTrue(self.run_sync()['ok'])
        self.assertEqual(len([c for c in self.native.calls if c[0] == 'create_reminder']), 1)
        self.assertEqual(self.files['future'].read_text(), before)
    def test_remote_day_title_completion_preserves_due_and_body(self):
        row = self.publish()
        row.update(due='2026-10-27', title='Готовая страница', completed=True)
        self.assertTrue(self.run_sync()['ok'])
        body = self.files['future'].read_text()
        self.assertIn('Запланировано: 2026-10-27.', body)
        self.assertIn('— Готовая страница', body)
        self.assertIn('Status: done', body)
        self.assertIn('Due: 2026-12-31', body)
        self.assertIn('Полный контекст задачи.', body)
    def test_two_sided_conflict_does_not_overwrite(self):
        row = self.publish()
        row['due'] = '2026-10-28'
        self.files['future'].write_text(self.files['future'].read_text().replace('2026-10-25.', '2026-10-29.'))
        result = self.run_sync()
        self.assertFalse(result['ok'])
        self.assertIn('two_sided_conflict', str(result))
        self.assertEqual(row['due'], '2026-10-28')
        self.assertIn('2026-10-29.', self.files['future'].read_text())
    def test_parent_cascade_and_paused_body(self):
        self.files['paused'].write_text('# Пауза\n\n### 2026-10-24 — Отложенная работа\nTask ID: TASK-demo-20261024-002\nStatus: paused\nDue: 2026-12-30\n\nПолный контекст паузы.\n')
        self.publish()
        self.native.data['p']['completed'] = True
        self.assertTrue(self.run_sync()['ok'])
        self.assertTrue(all(r['completed'] for r in self.native.data.values()))
        self.assertIn('Полный контекст паузы.', self.files['future'].read_text())
        self.assertIn('Due: 2026-12-30', self.files['future'].read_text())
        self.assertNotIn('TASK-demo-20261024-002', self.files['paused'].read_text())
    def test_import_and_missing_binding_no_delete(self):
        self.publish()
        self.native.data['external'] = dict(id='external', title='Внешняя задача', list_id='l', parent_id='p', version=1, completed=False, due='2026-10-28', notes='Status: done\nDue: 1900-01-01')
        self.assertTrue(self.run_sync()['ok'])
        body = self.files['future'].read_text()
        self.assertIn('Внешняя задача', body)
        self.assertIn('> Status: done', body)
        self.assertTrue(self.run_sync()['ok'])
        self.assertEqual(self.files['future'].read_text().count('— Внешняя задача'), 1)
        del self.native.data['external']
        self.assertFalse(self.run_sync()['ok'])
        self.assertEqual(self.files['future'].read_text(), body)
    def test_unknown_create_outcome_recovers_without_duplicate(self):
        real = self.native.call
        def failed(tool, args):
            real(tool, args)
            raise RuntimeError('lost_reply')
        self.native.call = failed
        self.assertFalse(self.run_sync()['ok'])
        self.native.call = real
        self.assertTrue(self.run_sync()['ok'])
        self.assertEqual(len(self.native.data), 2)
    def test_recurring_completion_does_not_close_series(self):
        row = self.publish()
        self.config['projects']['demo']['tasks']['TASK-demo-20261024-001']['repeating'] = True
        row.update(due='2026-10-26', completed=True)
        self.assertTrue(self.run_sync()['ok'])
        self.assertIn('Status: ready', self.files['future'].read_text())
        self.assertIn('Запланировано: 2026-10-26.', self.files['future'].read_text())
    def test_local_change_push_and_date_clear(self):
        row = self.publish()
        self.files['future'].write_text(self.files['future'].read_text().replace('Сделать страницу', 'Новое название').replace('Запланировано: 2026-10-25.\n', ''))
        self.assertTrue(self.run_sync()['ok'])
        self.assertEqual(self.native.data[row['id']]['title'], 'Новое название')
        self.assertIsNone(self.native.data[row['id']]['due'])
    def test_recover_pending_import(self):
        self.publish()
        remote = dict(id='external', title='Внешняя', list_id='l', parent_id='p', version=1, completed=False)
        self.native.data['external'] = remote
        self.config['projects']['demo']['tasks']['TASK-demo-20261024-002'] = dict(reminder_id='external', pending_import=True)
        self.assertTrue(self.run_sync()['ok'])
        self.assertEqual(self.files['future'].read_text().count('— Внешняя'), 1)
    def test_recover_partial_paused_save(self):
        self.files['paused'].write_text('# Пауза\n\n### 2026-10-24 — Отложенная\nTask ID: TASK-demo-20261024-002\nStatus: paused\nDue: 2026-12-30\n\nТело паузы.\n')
        self.publish()
        self.native.data['p']['completed'] = True
        real = m.subprocess.run
        def failed(args, **kwargs):
            if '--kind' in args and args[args.index('--kind') + 1] == 'paused':
                return m.subprocess.CompletedProcess(args, 1, '', 'forced_partial')
            return real(args, **kwargs)
        m.subprocess.run = failed
        try:
            self.assertFalse(self.run_sync()['ok'])
        finally:
            m.subprocess.run = real
        self.assertTrue(self.run_sync()['ok'])
        self.assertEqual(self.files['future'].read_text().count('— Отложенная'), 1)
        self.assertNotIn('TASK-demo-20261024-002', self.files['paused'].read_text())
    def test_recurring_cascade_conflict(self):
        row = self.publish()
        row['repeat'] = {'frequency': 'daily'}
        self.native.data['p']['completed'] = True
        result = self.run_sync()
        self.assertFalse(result['ok'])
        self.assertIn('cascade_repeating_requires_explicit_cancel', str(result))
        self.assertIn('Status: ready', self.files['future'].read_text())
    def test_current_promoted_duplicate_uses_current_record(self):
        self.files['current'].write_text('# Текущая\n\nTask ID: TASK-demo-20261024-001\nStatus: active\nDue: 2026-12-31\n\n## Goal\n\nТекущая работа\n\n## Context\n\nСохранённый контекст.\n')
        self.files['future'].write_text(self.files['future'].read_text().replace('Status: ready', 'Status: promoted'))
        row = self.publish()
        self.assertEqual(row['title'], 'Текущая работа')
        self.assertEqual(len(m.inventory(self.hub)), 1)
        row['title'] = 'Новое имя текущей'
        self.assertTrue(self.run_sync()['ok'])
        body = self.files['current'].read_text()
        self.assertIn('Новое имя текущей', body)
        self.assertIn('Сохранённый контекст.', body)
        self.assertIn('Status: promoted', self.files['future'].read_text())
    def test_deadline_notes_updates_without_erasing_user_notes(self):
        row = self.publish()
        row['notes'] = 'Моя заметка перед.\n' + row['notes'] + '\nМоя заметка после. Крайний срок: помнить.'
        self.files['future'].write_text(self.files['future'].read_text().replace('Due: 2026-12-31', 'Due: 2026-12-20'))
        self.assertTrue(self.run_sync()['ok'])
        notes = self.native.data[row['id']]['notes']
        self.assertTrue(notes.startswith('demo\nМоя заметка перед.\n'))
        self.assertNotIn('Крайний срок: 2026-12-20', notes)
        self.assertNotIn('Крайний срок: 2026-12-31', notes)
        self.assertTrue(notes.startswith('demo\nМоя заметка перед.\n'))
        self.assertTrue(notes.endswith('Моя заметка после. Крайний срок: помнить.'))
        self.assertEqual(self.native.data[row['id']]['due'], '2026-10-25')
        self.files['future'].write_text(self.files['future'].read_text().replace('Due: 2026-12-20\n', ''))
        self.assertTrue(self.run_sync()['ok'])
        self.assertNotIn('Крайний срок: 2026-12-20', self.native.data[row['id']]['notes'])
    def test_cascade_fresh_child_before_parent_blocks_completion(self):
        self.publish()
        self.config['projects']['demo']['complete_requested'] = True
        real = self.native.update
        def changed(row, changes):
            real(row, changes)
            if row['id'] != 'p' and changes.get('completed'):
                self.native.data['late'] = dict(id='late', list_id='l', parent_id='p', title='Поздняя', version=1, completed=False)
        self.native.update = changed
        result = self.run_sync()
        self.assertFalse(result['ok'])
        self.assertIn('cascade_children_changed_or_incomplete', str(result))
        self.assertFalse(self.native.data['p']['completed'])
    def test_cascade_fresh_child_after_parent_reports_failure(self):
        self.publish()
        self.config['projects']['demo']['complete_requested'] = True
        real = self.native.update
        def changed(row, changes):
            real(row, changes)
            if row['id'] == 'p' and changes.get('completed'):
                self.native.data['late'] = dict(id='late', list_id='l', parent_id='p', title='Поздняя', version=1, completed=False)
        self.native.update = changed
        result = self.run_sync()
        self.assertFalse(result['ok'])
        self.assertIn('cascade_children_changed_or_incomplete', str(result))
        self.assertTrue(self.config['projects']['demo']['complete_requested'])
    def test_completed_recurring_copy_does_not_import_new_task(self):
        row = self.publish()
        link = self.config['projects']['demo']['tasks']['TASK-demo-20261024-001']
        link['repeating'] = True
        clone = dict(row, id='completed-copy', completed=True, notes=m.notes_for(m.HubProject(self.hub, 'demo').rows()['TASK-demo-20261024-001']))
        self.native.data['completed-copy'] = clone
        self.assertTrue(self.run_sync()['ok'])
        self.assertEqual(len(m.inventory(self.hub)), 1)
        self.assertEqual(len(self.config['projects']['demo']['tasks']), 1)
    def test_cascade_fresh_hub_before_parent_blocks_completion(self):
        self.publish()
        self.config['projects']['demo']['complete_requested'] = True
        real = self.native.children
        calls = [0]
        def changed(binding):
            calls[0] += 1
            if calls[0] == 2:
                self.files['future'].write_text(self.files['future'].read_text() + '\n### TASK-demo-20261024-009 — Поздняя задача Хаба\nStatus: ready\n')
            return real(binding)
        self.native.children = changed
        result = self.run_sync()
        self.assertFalse(result['ok'])
        self.assertIn('cascade_hub_changed_or_incomplete', str(result))
        self.assertFalse(self.native.data['p']['completed'])
    def test_cascade_reopened_hub_after_parent_reports_failure(self):
        self.publish()
        self.config['projects']['demo']['complete_requested'] = True
        real = self.native.update
        def changed(row, changes):
            real(row, changes)
            if row['id'] == 'p' and changes.get('completed'):
                self.files['future'].write_text(self.files['future'].read_text().replace('Status: done', 'Status: ready'))
        self.native.update = changed
        result = self.run_sync()
        self.assertFalse(result['ok'])
        self.assertIn('cascade_hub_changed_or_incomplete', str(result))
        self.assertTrue(self.config['projects']['demo']['complete_requested'])
    def test_pending_create_rejects_foreign_identity(self):
        self.config['projects']['demo']['tasks']['TASK-demo-20261024-001'] = {'pending_create': True}
        self.native.data['wrong'] = dict(id='wrong', list_id='l', parent_id='p', title='Чужая', version=1, completed=False, notes='--- Hub metadata ---\nHub Task ID: TASK-demo-20261024-001\nHub project: foreign\n--- /Hub metadata ---')
        result = self.run_sync()
        self.assertFalse(result['ok'])
        self.assertIn('creation_identity_mismatch', str(result))
        self.assertNotIn('reminder_id', self.config['projects']['demo']['tasks']['TASK-demo-20261024-001'])
    def test_creation_identity_rejects_multiple_task_markers(self):
        remote = {'notes': '--- Hub metadata ---\nHub Task ID: TASK-demo-20261024-001\nHub Task ID: TASK-demo-20261024-002\nHub project: demo\n--- /Hub metadata ---'}
        with self.assertRaisesRegex(ValueError, 'ambiguous_creation_identity'):
            m.creation_identity(remote, m.compact_identities(self.config))
    def test_global_unique_id_guard_before_checkpoint(self):
        real = self.native.call
        def duplicate(tool, args):
            value = real(tool, args)
            value['id'] = 'p'
            return value
        self.native.call = duplicate
        self.assertFalse(self.run_sync()['ok'])
        saved = json.loads((self.hub / 'ai/reminders-sync.json').read_text())
        self.assertNotIn('reminder_id', saved['projects']['demo']['tasks']['TASK-demo-20261024-001'])
    def test_recurring_history_requires_exact_project_identity(self):
        row = self.publish()
        self.config['projects']['demo']['tasks']['TASK-demo-20261024-001']['repeating'] = True
        self.native.data['completed-copy'] = dict(row, id='completed-copy', completed=True, notes=m.notes_for(m.HubProject(self.hub, 'demo').rows()['TASK-demo-20261024-001']).replace('Hub project: demo', 'Hub project: foreign'))
        result = self.run_sync()
        self.assertFalse(result['ok'])
        self.assertIn('recurrence_history_identity_mismatch', str(result))
    def test_terminal_current_future_duplicate_not_published(self):
        self.files['current'].write_text('# Текущая\nTask ID: TASK-demo-20261024-001\nStatus: done\n\n## Goal\n\nЗавершённая текущая\n')
        self.files['future'].write_text(self.files['future'].read_text().replace('Status: ready', 'Status: done'))
        before = {k: p.read_text() for k, p in self.files.items()}
        self.assertTrue(self.run_sync()['ok'])
        self.assertEqual(self.native.calls, [])
        self.assertEqual(len(m.inventory(self.hub)), 1)
        self.assertEqual({k: p.read_text() for k, p in self.files.items()}, before)
    def test_promoted_future_duplicate_selects_paused(self):
        self.files['future'].write_text(self.files['future'].read_text().replace('Status: ready', 'Status: promoted'))
        self.files['paused'].write_text('# Пауза\n\n### 2026-10-24 — Реальная задача на паузе\nTask ID: TASK-demo-20261024-001\nStatus: paused\nDue: 2026-12-30\n')
        before = {k: p.read_text() for k, p in self.files.items()}
        rows = m.inventory(self.hub)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['kind'], 'paused')
        row = self.publish()
        self.assertEqual(row['title'], 'Реальная задача на паузе')
        self.assertEqual({k: p.read_text() for k, p in self.files.items()}, before)
    def test_two_active_duplicates_are_conflict(self):
        self.files['current'].write_text('# Текущая\nTask ID: TASK-demo-20261024-001\nStatus: active\n\n## Goal\n\nАктивная текущая\n')
        result = self.run_sync()
        self.assertFalse(result['ok'])
        self.assertIn('duplicate_task_id', str(result))
        self.assertEqual(self.native.calls, [])
    def test_paused_completion_replaces_promoted_preserves_context(self):
        self.files['future'].write_text(self.files['future'].read_text().replace('Status: ready', 'Status: promoted'))
        self.files['paused'].write_text('# Пауза\n\n### 2026-10-24 — Работа с паузы\nTask ID: TASK-demo-20261024-001\nStatus: paused\nDue: 2026-12-30\n\nСохранённое тело паузы.\n')
        self.publish()
        self.native.data['p']['completed'] = True
        real = m.subprocess.run
        def failed(args, **kwargs):
            if '--kind' in args and args[args.index('--kind') + 1] == 'paused':
                return m.subprocess.CompletedProcess(args, 1, '', 'forced_partial')
            return real(args, **kwargs)
        m.subprocess.run = failed
        try:
            self.assertFalse(self.run_sync()['ok'])
        finally:
            m.subprocess.run = real
        self.assertTrue(self.run_sync()['ok'])
        body = self.files['future'].read_text()
        self.assertIn('Сохранённое тело паузы.', body)
        self.assertIn('> Полный контекст задачи.', body)
        self.assertEqual(len(m.inventory(self.hub)), 1)
        self.assertEqual(m.inventory(self.hub)[0]['status'], 'done')
        self.assertNotIn('TASK-demo-20261024-001', self.files['paused'].read_text())
    def test_explicit_missing_project_binding_fails_without_native(self):
        result = m.sync(self.hub, self.config, True, project='missing', native=self.native)
        self.assertFalse(result['ok'])
        self.assertEqual(result['items'], [{'project': 'missing', 'error': 'missing_project_binding'}])
        self.assertEqual(self.native.calls, [])
    def test_global_unbound_open_project_reports_and_bound_continues(self):
        other = self.hub / 'projects/other'
        (other / 'ai').mkdir(parents=True)
        registry = self.hub / 'ai/project-registry.md'
        registry.write_text(registry.read_text() + f'\n## other\nStatus: active\nPath: {other}\n')
        for kind, name in m.NAMES.items():
            value = self.files[kind].read_text().replace('TASK-demo-', 'TASK-other-')
            (other / 'ai' / name).write_text(value)
        result = self.run_sync()
        self.assertFalse(result['ok'])
        self.assertIn({'project': 'other', 'error': 'missing_project_binding'}, result['items'])
        self.assertEqual(len([c for c in self.native.calls if c[0] == 'create_reminder']), 1)
        self.assertEqual(len(self.native.data), 2)
        self.assertNotIn('other', self.config['projects'])
    def native_snapshot(self, rows, **extra):
        client = m.Native(self.config)
        calls = []
        def call(tool, args):
            calls.append((tool, args))
            if tool != 'find_reminders':
                raise AssertionError('unexpected detail call')
            return dict(reminders=rows, **extra)
        client.call = call
        return client, calls
    def snapshot_row(self, **changes):
        return dict(dict(id='r1', list='Работа', parent_id='p', version='v1', title='Работа', notes='Заметка', due='2026-10-25', repeat={'frequency': 'daily'}), **changes)
    def test_native_children_uses_one_fresh_scoped_find_without_get(self):
        client, calls = self.native_snapshot([self.snapshot_row(), self.snapshot_row(id='other', parent_id='other-parent')])
        rows = client.children(self.config['projects']['demo'])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['list_id'], 'l')
        self.assertEqual(rows[0]['notes'], 'Заметка')
        self.assertEqual(rows[0]['repeat'], {'frequency': 'daily'})
        self.assertEqual(calls, [('find_reminders', {'list': 'l', 'include_completed': True, 'limit': 500})])
        client.children(self.config['projects']['demo'])
        self.assertEqual(len(calls), 2)
    def test_native_snapshot_rejects_foreign_list(self):
        client, calls = self.native_snapshot([self.snapshot_row(list='Чужой список')])
        with self.assertRaisesRegex(ValueError, 'foreign_list_in_snapshot'):
            client.children(self.config['projects']['demo'])
        self.assertEqual(len(calls), 1)
    def test_native_snapshot_rejects_duplicate_ids(self):
        client, calls = self.native_snapshot([self.snapshot_row(), self.snapshot_row()])
        with self.assertRaisesRegex(ValueError, 'duplicate_reminder_in_snapshot'):
            client.children(self.config['projects']['demo'])
        self.assertEqual(len(calls), 1)
    def test_native_snapshot_rejects_truncation(self):
        client, calls = self.native_snapshot([self.snapshot_row()], more=1)
        with self.assertRaisesRegex(ValueError, 'incomplete_reminder_snapshot'):
            client.children(self.config['projects']['demo'])
        self.assertEqual(len(calls), 1)
    def test_cleanup_legacy_preserves_exact_user_notes_and_deadline(self):
        row = m.HubProject(self.hub, 'demo').rows()['TASK-demo-20261024-001']
        legacy = ('--- Hub metadata ---\nHub Task ID: ' + row['task_id'] +
                  '\nHub project: demo\nКрайний срок: 2026-12-31\n--- /Hub metadata ---')
        notes = 'Перед\n\n' + legacy + '\nПосле  '
        clean, owner = m.managed_notes(notes, row, {})
        self.assertEqual(clean, 'demo\nПеред\n\n\nПосле  ')
        self.assertIsNotNone(owner)
        again, again_owner = m.managed_notes(clean, row, {'notes_owner': owner})
        self.assertEqual((again, again_owner), (clean, owner))
    def test_cleanup_rejects_wrong_legacy_project(self):
        row = m.HubProject(self.hub, 'demo').rows()['TASK-demo-20261024-001']
        notes = m.notes_for(row).replace('Hub project: demo', 'Hub project: foreign')
        with self.assertRaisesRegex(ValueError, 'foreign_managed_notes'):
            m.managed_notes(notes, row, {})
    def test_cleanup_deadline_does_not_own_identical_user_line(self):
        row = self.publish()
        remote = self.native.data[row['id']]
        self.assertNotIn('Hub metadata', remote['notes'])
        self.assertNotIn('Hub Task ID', remote['notes'])
        remote['notes'] = 'Крайний срок: 2026-12-31\nМоя строка'
        link = self.config['projects']['demo']['tasks']['TASK-demo-20261024-001']
        link.pop('notes_owner', None)
        self.assertTrue(self.run_sync()['ok'])
        self.files['future'].write_text(self.files['future'].read_text().replace('Due: 2026-12-31', 'Due: 2026-12-20'))
        self.assertTrue(self.run_sync()['ok'])
        self.assertTrue(remote['notes'].startswith('demo\nКрайний срок: 2026-12-31\nМоя строка'))
        self.assertNotIn('Крайний срок: 2026-12-20', remote['notes'])
    def test_cleanup_pending_notes_recovers_after_unknown_update(self):
        row = self.publish()
        self.config['projects']['demo']['project_label'] = 'Новая подпись'
        real = self.native.update
        def failed(remote, changes):
            real(remote, changes)
            if 'notes' in changes:
                raise RuntimeError('lost_notes_reply')
        self.native.update = failed
        self.assertFalse(self.run_sync()['ok'])
        persisted = json.loads((self.hub / 'ai/reminders-sync.json').read_text())
        self.assertIn('pending_notes', persisted['projects']['demo']['tasks']['TASK-demo-20261024-001'])
        self.config = persisted
        self.native.update = real
        self.assertTrue(self.run_sync()['ok'])
        self.assertEqual(self.native.data[row['id']]['notes'], 'Новая подпись')
        self.assertNotIn('pending_notes', self.config['projects']['demo']['tasks']['TASK-demo-20261024-001'])
    def test_cleanup_transient_creation_marker_removed_after_id_checkpoint(self):
        self.publish()
        saved = json.loads((self.hub / 'ai/reminders-sync.json').read_text())
        link = saved['projects']['demo']['tasks']['TASK-demo-20261024-001']
        self.assertTrue(link['reminder_id'])
        self.assertNotIn('Hub metadata', self.native.data[link['reminder_id']]['notes'])
        self.assertTrue(self.run_sync()['ok'])
        self.assertNotIn('Hub metadata', self.native.data[link['reminder_id']]['notes'])
    def test_cleanup_empty_notes_omitted_by_native_readback(self):
        self.files['future'].write_text(self.files['future'].read_text().replace('Due: 2026-12-31\n', ''))
        real = self.native.get
        def omitted(rid, lid, parent=None):
            value = real(rid, lid, parent)
            if not value.get('notes'):
                value.pop('notes', None)
            return value
        self.native.get = omitted
        self.assertTrue(self.run_sync()['ok'])
        self.assertTrue(self.run_sync()['ok'])
        self.assertEqual(self.native.data['r1']['notes'], 'demo')
    def test_cleanup_changed_user_notes_never_delete_lookalike(self):
        row = self.publish()
        self.native.data[row['id']]['notes'] += '\nКрайний срок: 2026-12-31\nЧужой добавленный текст'
        self.files['future'].write_text(self.files['future'].read_text().replace('Due: 2026-12-31', 'Due: 2026-12-20'))
        before = self.native.data[row['id']]['notes']
        result = self.run_sync()
        self.assertTrue(result['ok'])
        self.assertEqual(self.native.data[row['id']]['notes'], before)
    def test_cleanup_ambiguous_notes_with_unchanged_deadline_allows_other_sync(self):
        row = self.publish()
        notes = self.native.data[row['id']]['notes'] + '\nКрайний срок: 2026-12-31\nПользовательский текст'
        self.native.data[row['id']].update(notes=notes, due='2026-10-28')
        self.assertTrue(self.run_sync()['ok'])
        self.assertEqual(self.native.data[row['id']]['notes'], notes)
        self.assertIn('Запланировано: 2026-10-28.', self.files['future'].read_text())
    def test_cleanup_import_user_notes_exact_without_marker(self):
        notes = '  Пользовательский текст\nКрайний срок: просто заметка\n'
        self.native.data['external'] = dict(id='external', list_id='l', parent_id='p', title='Новая', version=1, completed=False, notes=notes)
        self.assertTrue(self.run_sync()['ok'])
        self.assertEqual(self.native.data['external']['notes'], 'demo\n' + notes)
        self.assertTrue(self.run_sync()['ok'])
        self.assertEqual(self.native.data['external']['notes'], 'demo\n' + notes)
    def test_cleanup_no_deadline_preserves_surrounding_whitespace(self):
        row = m.HubProject(self.hub, 'demo').rows()['TASK-demo-20261024-001']
        row['deadline'] = None
        original = ('  Перед\n\n--- Hub metadata ---\nHub Task ID: ' + row['task_id'] +
                    '\nHub project: demo\n--- /Hub metadata ---\nПосле  ')
        notes, owner = m.managed_notes(original, row, {})
        self.assertEqual(notes, 'demo\n  Перед\n\n\nПосле  ')
        self.assertEqual(owner['label'], 'demo')
    def test_cleanup_conditional_ordinary_clean_repeating_marker_preserved(self):
        self.files['future'].write_text(self.files['future'].read_text() + '\n### TASK-demo-20261024-002 — Повторяющаяся\nStatus: ready\nDue: 2026-12-30\n')
        row = self.publish()
        binding = self.config['projects']['demo']
        repeat_id = binding['tasks']['TASK-demo-20261024-002']['reminder_id']
        repeating = self.native.data[repeat_id]
        canonical = m.HubProject(self.hub, 'demo').rows()['TASK-demo-20261024-002']
        repeating.update(repeat={'frequency': 'daily'}, notes=m.notes_for(canonical))
        binding['tasks']['TASK-demo-20261024-002']['notes_owner'] = None
        before = repeating['notes']
        self.assertTrue(self.run_sync()['ok'])
        self.assertNotIn('Hub metadata', self.native.data[row['id']]['notes'])
        self.assertNotEqual(repeating['notes'], before)
        self.assertEqual(m.creation_identity(repeating, m.compact_identities(self.config)), ('demo', 'TASK-demo-20261024-002'))
    def test_cleanup_transition_to_repeat_removes_only_owned_plain_deadline(self):
        row = self.publish()
        remote = self.native.data[row['id']]
        remote.update(repeat={'frequency': 'daily'})
        self.assertTrue(self.run_sync()['ok'])
        self.assertEqual(remote['notes'].count('Крайний срок: 2026-12-31'), 0)
        self.assertEqual(m.creation_identity(remote, m.compact_identities(self.config)), ('demo', 'TASK-demo-20261024-001'))
        self.assertIsNotNone(self.config['projects']['demo']['tasks']['TASK-demo-20261024-001']['notes_owner'])
        self.assertTrue(self.run_sync()['ok'])
        self.assertEqual(remote['notes'].count('Хаб:'), 1)
    def test_cleanup_repeating_marker_rejects_foreign_project(self):
        row = self.publish()
        remote = self.native.data[row['id']]
        canonical = m.HubProject(self.hub, 'demo').rows()['TASK-demo-20261024-001']
        remote.update(repeat={'frequency': 'daily'}, notes=m.notes_for(canonical).replace('Hub project: demo', 'Hub project: foreign'))
        before = dict(remote)
        self.assertFalse(self.run_sync()['ok'])
        self.assertEqual(remote, before)
    def test_cleanup_unknown_completed_without_marker_with_repeat_requires_review(self):
        row = self.publish()
        row['repeat'] = {'frequency': 'daily'}
        self.native.data['unknown'] = dict(id='unknown', list_id='l', parent_id='p', version=1, title='Любое название', completed=True, notes='Пользовательский текст')
        before = self.files['future'].read_text()
        result = self.run_sync()
        self.assertFalse(result['ok'])
        self.assertIn('unidentified_completed_task_requires_review', str(result))
        self.assertEqual(self.files['future'].read_text(), before)
        self.assertEqual(len(self.config['projects']['demo']['tasks']), 1)
    def test_cleanup_unknown_active_with_repeat_still_imports(self):
        row = self.publish()
        row['repeat'] = {'frequency': 'daily'}
        self.native.data['unknown'] = dict(id='unknown', list_id='l', parent_id='p', version=1, title='Новая активная', completed=False, notes='Моя заметка')
        self.assertTrue(self.run_sync()['ok'])
        self.assertIn('— Новая активная', self.files['future'].read_text())
        self.assertEqual(self.native.data['unknown']['notes'], 'demo\nМоя заметка')
    def test_cleanup_unknown_completed_without_repeat_still_imports(self):
        self.publish()
        self.native.data['unknown'] = dict(id='unknown', list_id='l', parent_id='p', version=1, title='Выполненная обычная', completed=True, notes='Моя заметка')
        self.assertTrue(self.run_sync()['ok'])
        row = next(r for r in m.inventory(self.hub) if r['title'] == 'Выполненная обычная')
        self.assertEqual(row['status'], 'done')
        self.assertEqual(self.native.data['unknown']['notes'], 'demo\nМоя заметка')
    def test_cleanup_legacy_history_survives_cancel_then_project_cascade(self):
        row = self.publish()
        row['repeat'] = {'frequency': 'daily'}
        self.assertTrue(self.run_sync()['ok'])
        self.native.data['copy'] = dict(row, id='copy', completed=True)
        self.native.data['copy'].pop('repeat')
        row['due'] = '2026-10-26'
        self.assertTrue(self.run_sync()['ok'])
        self.assertIn('copy', self.config['projects']['demo']['history'])
        self.assertEqual(len(m.inventory(self.hub)), 1)
        copy_notes = self.native.data['copy']['notes']
        row.pop('repeat')
        self.config['projects']['demo']['tasks']['TASK-demo-20261024-001'].pop('repeating', None)
        self.native.data['new'] = dict(id='new', title='Новая работа', list_id='l', parent_id='p', version=1, completed=False)
        self.assertTrue(self.run_sync()['ok'])
        self.config['projects']['demo']['complete_requested'] = True
        self.assertTrue(self.run_sync()['ok'])
        self.assertTrue(all(r['completed'] for r in self.native.data.values()))
        self.assertEqual(self.native.data['copy']['notes'], copy_notes)
        self.assertTrue(all(r['status'] == 'done' for r in m.inventory(self.hub)))
    def test_cleanup_known_history_requires_unchanged_exact_identity(self):
        row = self.publish()
        row['repeat'] = {'frequency': 'daily'}
        self.assertTrue(self.run_sync()['ok'])
        self.native.data['copy'] = dict(row, id='copy', completed=True)
        self.native.data['copy'].pop('repeat')
        self.assertTrue(self.run_sync()['ok'])
        self.native.data['copy']['notes'] = self.native.data['copy']['notes'].replace('Хаб: ', 'Хаб: 0')
        before = self.files['future'].read_text()
        result = self.run_sync()
        self.assertFalse(result['ok'])
        self.assertRegex(str(result), 'invalid_recurrence_history|ambiguous_creation_identity')
        self.assertEqual(self.files['future'].read_text(), before)
    def test_native_timed_due_syncs_day_without_rewriting_hour(self):
        row = self.publish()
        row['due'] = '2026-10-26T15:00'
        self.native.calls = []
        self.assertTrue(self.run_sync()['ok'])
        self.assertIn('Запланировано: 2026-10-26.', self.files['future'].read_text())
        self.assertEqual(self.native.data[row['id']]['due'], '2026-10-26T15:00')
        self.assertFalse(any('due' in args for tool, args in self.native.calls if tool == 'update'))
    def test_hub_day_move_preserves_remote_time_and_clear_removes_all(self):
        row = self.publish()
        row['due'] = '2026-10-26T15:00:30+03:00'
        self.assertTrue(self.run_sync()['ok'])
        self.files['future'].write_text(self.files['future'].read_text().replace('Запланировано: 2026-10-26.', 'Запланировано: 2026-10-28.'))
        self.assertTrue(self.run_sync()['ok'])
        self.assertEqual(self.native.data[row['id']]['due'], '2026-10-28T15:00:30+03:00')
        self.files['future'].write_text(self.files['future'].read_text().replace('Запланировано: 2026-10-28.\n', ''))
        self.assertTrue(self.run_sync()['ok'])
        self.assertIsNone(self.native.data[row['id']]['due'])
    def test_remote_day_rejects_invalid_datetime_strings(self):
        for value in ['2026-10-26T25:00', '2026-02-30T15:00', '2026-10-26garbage', '2026-10-26T15:00junk']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.remote_day({'due': value})
    def test_inventory_rejects_symlink(self):
        target = self.files['future']
        moved = self.project / 'ai/copy.md'
        target.rename(moved)
        target.symlink_to(moved)
        with self.assertRaisesRegex(ValueError, 'unsafe_path'):
            m.inventory(self.hub)

if __name__ == '__main__':
    unittest.main()
