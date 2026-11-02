"""Проверки источников ревью и сохранения границы только после разбора."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/review_reminders.py'
spec = importlib.util.spec_from_file_location('review_reminders', SCRIPT)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)

NOW = '2026-10-28T21:00:00+03:00'
PREVIOUS = '2026-10-26T20:00:00+03:00'


def row(rid, **fields):
    return dict(id=rid, list_id='L', list='Разрешённый', title=rid, **fields)


def prepared(rows=()):
    return review.prepare(list(rows), '2026-10-28', NOW, PREVIOUS)


def merged(rows=()):
    calendar = dict(queue=[], today_complete=True, tomorrow_complete=True)
    return review.merge(calendar, prepared(rows), {'projects': {}}, [])


class ReviewReminders(unittest.TestCase):
    def test_missing_list_returns_available_queue_and_clarification(self):
        from test_evening_review_sync import make_hub, payload
        with tempfile.TemporaryDirectory() as tmp:
            hub = make_hub(Path(tmp).resolve())
            native = hub / 'native'
            native.write_text('#!' + sys.executable + '\nimport json,sys\n'
                              'print(json.dumps({"lists":[{"id":"L","name":"Разрешённый"}]} '
                              'if sys.argv[2]=="list_lists" else '
                              '{"detail":True,"count":1,"reminders":[{"id":"R","list_id":"L",'
                              '"list":"Разрешённый","title":"Доступная задача","due":"2026-10-03"}]}))\n')
            native.chmod(0o700)
            allow = hub / 'ai/allow.json'
            allow.write_text(json.dumps({'names': ['Разрешённый', 'Пропавший']}))
            config = dict(enabled=True, binary=str(native), allowlist_file=str(allow),
                          projects={'demo': dict(list_id='M', list_name='Пропавший', tasks={})})
            (hub / 'ai/reminders-sync.json').write_text(json.dumps(config))
            result = subprocess.run([sys.executable, str(SCRIPT.with_name('evening_review.py')),
                                     '--hub', str(hub), '--day', '2026-10-03', '--reminders',
                                     '--now', '2026-10-03T21:00:00+03:00'],
                                    input=json.dumps({k: v for k, v in payload().items() if k != 'tomorrow'}), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual([r['sources'] for r in data['queue']], [['calendar'], ['today']])
            self.assertEqual(data['missing_lists'], [dict(list_id='M', list_name='Пропавший', project_ids=['demo'])])
            self.assertIn('Пропавший', data['clarification_question'])
            self.assertIn('удал', data['clarification_question'])
            self.assertFalse(data['complete'])
            self.assertTrue(data['warnings'])
            self.assertFalse((hub / STATE_PATH).exists())

    def test_finish_rejects_missing_lists_even_if_marked_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp).resolve(); (hub / 'ai').mkdir()
            data = merged()
            data.update(previous=None, consumed=[], calendar_reviewed=True,
                        missing_lists=[dict(list_id='M', list_name='Пропавший', project_ids=['demo'])])
            with self.assertRaises(ValueError):
                review.finish(hub, data, '2026-10-28T22:00:00+03:00')
            self.assertFalse((hub / STATE_PATH).exists())

    def test_command_combines_sources_without_calendar_sync_and_finish_persists(self):
        from test_evening_review_sync import make_hub, payload
        with tempfile.TemporaryDirectory() as tmp:
            hub = make_hub(Path(tmp).resolve())
            native = hub / 'native'
            native.write_text('#!' + sys.executable + '\nimport json,sys\n'
                              'print(json.dumps({"lists":[{"id":"L","name":"Разрешённый"}]} '
                              'if sys.argv[2]=="list_lists" else '
                              '{"detail":True,"count":1,"reminders":[{"id":"R","list_id":"L",'
                              '"list":"Разрешённый","title":"Задача сегодня","due":"2026-10-03"}]}))\n')
            native.chmod(0o700)
            allow = hub / 'ai/allow.json'; allow.write_text(json.dumps({'names': ['Разрешённый']}))
            (hub / 'ai/reminders-sync.json').write_text(json.dumps(dict(enabled=True, binary=str(native),
                                                                       allowlist_file=str(allow), projects={})))
            result = subprocess.run([sys.executable, str(SCRIPT.with_name('evening_review.py')),
                                     '--hub', str(hub), '--day', '2026-10-03', '--reminders',
                                     '--now', '2026-10-03T21:00:00+03:00'],
                                    input=json.dumps({k: v for k, v in payload().items() if k != 'tomorrow'}), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual([r['sources'] for r in data['queue']], [['calendar'], ['today']])
            self.assertEqual(data['sync']['status'], 'reminders-mode-no-calendar-task-sync')
            self.assertFalse((hub / STATE_PATH).exists())
            data.update(consumed=data['review_keys'], calendar_reviewed=True, sync_complete=True)
            result = subprocess.run([sys.executable, str(SCRIPT), 'finish', '--hub', str(hub),
                                     '--now', '2026-10-03T22:00:00+03:00'], input=json.dumps(data),
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads((hub / STATE_PATH).read_text())['last_reviewed_through'],
                             '2026-10-03T21:00:00+03:00')

    def test_completed_uses_completion_time_not_due(self):
        rows = [row('old-due', completed=True, due='2026-01-01', completed_at='2026-10-27T12:00:00+03:00'),
                row('no-due', completed=True, completed_at='2026-10-28T10:00:00+03:00'),
                row('old-completion', completed=True, due='2026-10-28', completed_at='2026-10-25T10:00:00+03:00')]
        self.assertEqual([r['id'] for r in prepared(rows)['completed']], ['old-due', 'no-due'])

    def test_exact_window_boundaries(self):
        rows = [row('lower', completed=True, completed_at=PREVIOUS),
                row('upper', completed=True, completed_at=NOW),
                row('later', completed=True, completed_at='2026-10-28T22:00:00+03:00')]
        self.assertEqual([r['id'] for r in prepared(rows)['completed']], ['upper'])

    def test_today_includes_all_open_and_excludes_completed(self):
        rows = [row('overdue', due='2026-10-01'), row('today', due='2026-10-28T23:00:00'),
                row('future', due='2026-10-29'), row('no-date'),
                row('done', due='2026-10-28', completed=True, completed_at=NOW)]
        self.assertEqual([r['id'] for r in prepared(rows)['today']], ['overdue', 'today', 'future', 'no-date'])

    def test_first_review_is_explicit_and_timezone_aware(self):
        result = review.prepare([row('utc', due='2026-10-28T22:00:00Z')], '2026-10-28', NOW, None)
        self.assertTrue(result['first_review'])
        self.assertEqual(result['since'], '2026-10-28T00:00:00+03:00')
        self.assertEqual([r['id'] for r in result['today']], ['utc'])

    def test_missing_completion_time_is_incomplete(self):
        result = prepared([row('unknown', completed=True)])
        self.assertFalse(result['complete'])
        self.assertEqual(result['completed'], [])
        self.assertTrue(result['warnings'])

    def test_calendar_and_known_reminder_merge_by_task_identity(self):
        key = json.dumps(['demo', 'TASK-demo-1'], ensure_ascii=False)
        event = dict(review_key=key, project_id='demo', task_id='TASK-demo-1', event={'title': 'встреча'})
        config = {'projects': {'demo': {'list_id': 'L', 'tasks': {'TASK-demo-1': {'reminder_id': 'R'}}}}}
        result = review.merge(dict(queue=[event, event], today_complete=True, tomorrow_complete=True),
                              prepared([row('R', due='2026-10-28')]), config,
                              [dict(project_id='demo', task_id='TASK-demo-1', source_path='/canonical')])
        self.assertEqual(len(result['queue']), 1)
        self.assertEqual(set(result['queue'][0]['sources']), {'calendar', 'today'})
        self.assertEqual(result['queue'][0]['reminder']['id'], 'R')

    def test_unknown_same_title_does_not_merge_or_invent_owner(self):
        rows = [row('a', title_override='x'), row('b', title_override='x')]
        for r in rows:
            r['title'] = r.pop('title_override')
            r['due'] = '2026-10-28'
        result = merged(rows)
        self.assertEqual(len(result['queue']), 2)
        self.assertTrue(all(r['project_id'] is None for r in result['queue']))

    def test_consumed_keys_keep_full_completion_checklist(self):
        full = merged([row('a', due='2026-10-28')])
        result = review.merge(dict(queue=[], today_complete=True, tomorrow_complete=True),
                              prepared([row('a', due='2026-10-28')]), {'projects': {}}, [], full['review_keys'])
        self.assertEqual(result['queue'], [])
        self.assertEqual(result['review_keys'], full['review_keys'])

    def test_known_repeat_history_keeps_completion_and_next_occurrence(self):
        config = {'projects': {'demo': {'list_id': 'L', 'tasks': {'T': {'reminder_id': 'live'}},
                                       'history': {'history': {'task_id': 'T', 'project_id': 'demo', 'original_id': 'live'}}}}}
        reminders = prepared([row('history', completed=True, completed_at=NOW), row('live', due='2026-10-28')])
        result = review.merge(dict(queue=[], today_complete=True, tomorrow_complete=True), reminders,
                              config, [dict(project_id='demo', task_id='T', source_path='/canonical')])
        self.assertEqual(len(result['queue']), 1)
        item = result['queue'][0]
        self.assertEqual(item['project_id'], 'demo')
        self.assertEqual(item['sources'], ['completed', 'today'])
        self.assertEqual([(r['id'], r['completed']) for r in item['reminders']], [('history', True), ('live', False)])

    def test_invalid_repeat_history_is_not_assigned_to_project(self):
        config = {'projects': {'demo': {'list_id': 'L', 'tasks': {'T': {'reminder_id': 'live'}},
                                       'history': {'history': {'task_id': 'T', 'project_id': 'foreign', 'original_id': 'live'}}}}}
        with self.assertRaises(ValueError):
            review.merge(dict(queue=[], today_complete=True, tomorrow_complete=True),
                         prepared([row('history', completed=True, completed_at=NOW)]), config,
                         [dict(project_id='demo', task_id='T', source_path='/canonical')])

    def test_collector_reads_every_allowed_list_with_details(self):
        class Native:
            def __init__(self): self.calls = []
            def call(self, tool, args):
                self.calls.append((tool, args))
                if tool == 'list_lists':
                    return {'lists': [{'id': 'L', 'name': 'Разрешённый'}, {'id': 'X', 'name': 'Посторонний'}]}
                return dict(detail=True, count=1, reminders=[row('a')])
        native = Native()
        self.assertEqual(len(review.collect(native, {'Разрешённый'})), 1)
        self.assertEqual(native.calls[1], ('find_reminders', dict(list='L', include_completed=True, detail=True, limit=500)))
        self.assertEqual(len(native.calls), 2)

    def test_collector_rejects_truncation_and_foreign_rows(self):
        class Native:
            def call(self, tool, args):
                if tool == 'list_lists': return {'lists': [{'id': 'L', 'name': 'Разрешённый'}]}
                return self.snapshot
        native = Native()
        for snapshot in [dict(detail=True, count=1, more=2, reminders=[row('a')]),
                         dict(detail=True, count=1, reminders=[dict(row('a'), list_id='X')])]:
            native.snapshot = snapshot
            with self.subTest(snapshot=snapshot), self.assertRaises(ValueError):
                review.collect(native, {'Разрешённый'})

    def test_collector_requires_known_lists_and_complete_metadata(self):
        class Native:
            def call(self, tool, args): return self.snapshot
        native = Native()
        for snapshot in [dict(lists=[]), dict(lists=[{'id': 'L', 'name': 'Разрешённый'}], more=1)]:
            native.snapshot = snapshot
            with self.subTest(snapshot=snapshot), self.assertRaises(ValueError):
                review.collect(native, {'Разрешённый'}, {'L'})

    def test_finish_requires_complete_sources_and_all_answers(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp).resolve(); (hub / 'ai').mkdir()
            base = merged([row('a', due='2026-10-28')])
            base['previous'] = None
            for changes in [dict(consumed=[]), dict(complete=False), dict(today_complete=False),
                            dict(tomorrow_complete=False), dict(calendar_reviewed=False)]:
                data = dict(base, consumed=base['review_keys'], calendar_reviewed=True, **{})
                data.update(changes)
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    review.finish(hub, data, '2026-10-28T22:00:00+03:00')
            self.assertFalse((hub / 'ai/evening-review-state.json').exists())

    def test_finish_saves_snapshot_boundary_and_checks_concurrent_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp).resolve(); (hub / 'ai').mkdir()
            data = merged(); data.update(previous=None, consumed=[], calendar_reviewed=True)
            review.finish(hub, data, '2026-10-28T22:00:00+03:00')
            state = json.loads((hub / 'ai/evening-review-state.json').read_text())
            self.assertEqual(state['last_reviewed_through'], NOW)
            self.assertEqual(state['finished_at'], '2026-10-28T22:00:00+03:00')
            self.assertNotIn('queue', state)
            with self.assertRaises(ValueError):
                review.finish(hub, data, '2026-10-28T23:00:00+03:00')

    def test_duplicate_reminder_and_unsafe_state_rejected(self):
        with self.assertRaises(ValueError): prepared([row('a'), row('a')])
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp).resolve(); (hub / 'ai').mkdir()
            (hub / 'outside').write_text('{}')
            (hub / 'ai/evening-review-state.json').symlink_to(hub / 'outside')
            with self.assertRaises(ValueError): review.read_state(hub)


STATE_PATH = 'ai/evening-review-state.json'

if __name__ == '__main__': unittest.main()
