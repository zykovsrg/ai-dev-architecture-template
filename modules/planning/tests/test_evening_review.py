import importlib.util
import unittest
import tempfile
import subprocess
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/evening_review.py'


def event(title, start='2026-10-02T10:00:00+03:00', ident=None, cal='normal', all_day=False):
    return dict(id=ident or title, calendar_id=cal, title=title, start=start,
                end=(datetime.fromisoformat(start) + timedelta(hours=1)).isoformat(), all_day=all_day)


def response(events, complete=True):
    return dict(source='Apple Calendar / EventKit', timezone='Europe/Kirov',
                availability_complete=complete, unavailable_calendar_ids=[] if complete else ['urgent'], events=events)


class EveningReviewTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.exists(), 'guided evening review helper is missing')
        spec = importlib.util.spec_from_file_location('evening_review', SCRIPT)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)
        self.meta = dict(source='Apple Calendar / EventKit', calendars=[
            dict(id='urgent', name='Важно и срочно', timezone='Europe/Kirov'),
            dict(id='normal', name='Важно, но несрочно', timezone='Europe/Kirov')])

    def prepare(self, events=(), future=(), tasks=(), **kwargs):
        return self.mod.prepare_review(self.meta, response(list(events)), response(list(future)),
                                       {'p'}, list(tasks), '2026-10-02', **kwargs)

    def test_only_exact_urgent_calendar_and_local_day(self):
        a = event('важное без проекта', '2026-10-03T08:00:00+03:00', cal='urgent')
        b = event('дела/p/обычное', '2026-10-03T07:00:00+03:00')
        c = event('позже', '2026-10-04T08:00:00+03:00', ident='later', cal='urgent')
        self.assertEqual(self.prepare(future=[a,b,c])['urgent'], [a])

    def test_queue_skips_projectless_unregistered_and_inactive(self):
        events = [event('дела/сон'), event('дела/несуществующий/задача'),
                  event('дела/p/работа', ident='good'), event('дела/встреча/808')]
        result = self.prepare(events)
        self.assertEqual([r['event']['id'] for r in result['queue']], ['good'])
        self.assertEqual(result['skipped'], 3)

    def test_all_day_and_chronological_order_preserve_titles(self):
        later = event('хадасса/p/позже', '2026-10-02T15:00:00+03:00', ident='later')
        day = event('хадасса/p/весь день', '2026-10-02T00:00:00+03:00', ident='day', all_day=True)
        day['end'] = '2026-10-03T00:00:00+03:00'
        result = self.prepare([later,day])
        self.assertEqual([r['event'] for r in result['queue']], [day,later])

    def test_same_task_blocks_share_key_but_distinct_tasks_do_not(self):
        a = event('дела/p/текст', ident='a')
        b = event('дела/p/текст', '2026-10-02T13:00:00+03:00', ident='b')
        c = event('дела/p/позвонить', '2026-10-02T15:00:00+03:00', ident='c')
        result = self.prepare([a,b,c])
        self.assertEqual(result['queue'][0]['review_key'], result['queue'][1]['review_key'])
        self.assertNotEqual(result['queue'][0]['review_key'], result['queue'][2]['review_key'])
        consumed = [result['queue'][0]['review_key']]
        self.assertEqual([r['event']['id'] for r in self.prepare([a,b,c], consumed=consumed)['queue']], ['c'])

    def test_unique_legacy_link_maps_project_without_title_convention(self):
        ev = event('Старая встреча', ident='e')
        task = dict(project_id='p', task_id='T', title='Встреча', event_link=dict(calendar_id='normal',event_id='e'))
        result = self.prepare([ev], tasks=[task])
        self.assertEqual(result['queue'][0]['project_id'], 'p')
        self.assertEqual(result['queue'][0]['task_id'], 'T')

    def test_conflicting_legacy_links_skip_ambiguous_event(self):
        task = dict(project_id='p',task_id='T',title='one',event_link=dict(calendar_id='normal',event_id='e'))
        other = dict(task, task_id='U')
        self.assertEqual(self.prepare([event('legacy',ident='e')],tasks=[task,other])['queue'], [])

    def test_partial_is_reported_not_empty_or_complete(self):
        result = self.mod.prepare_review(self.meta, response([]), response([],False), {'p'}, [], '2026-10-02')
        self.assertFalse(result['tomorrow_complete'])
        self.assertEqual(result['unavailable_calendar_ids'], ['urgent'])

    def test_missing_and_duplicate_urgent_calendar_are_unavailable(self):
        self.meta['calendars'][0]['name'] = 'Важно и срочно другое'
        self.assertEqual(self.prepare()['urgent_status'], 'unavailable')
        self.meta['calendars'][0]['name'] = 'Важно и срочно'
        self.meta['calendars'].append(dict(id='other', name='Важно и срочно'))
        self.assertEqual(self.prepare()['urgent_status'], 'ambiguous')

    def test_invalid_date_and_unallowlisted_event_rejected(self):
        with self.assertRaises(ValueError):
            self.mod.prepare_review(self.meta,response([]),response([]),{'p'},[],'2026-02-30')
        with self.assertRaises(ValueError):
            self.prepare([event('дела/p/задача',cal='forbidden')])

    def test_cli_reads_discovered_canonical_record_and_reports_heading_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            hub = Path(directory) / 'hub'
            hub.mkdir()
            # The sync step loads sibling task scripts, so run the staged (installed-layout) copy.
            stage = Path(directory) / 'stage'
            subprocess.run(['bash', str(SCRIPT.parents[1] / 'tests/stage-scripts.sh'), str(stage)], check=True)
            script = stage / 'evening_review.py'
            (hub / 'ai').mkdir()
            project = hub / 'projects/p'
            (project / 'ai').mkdir(parents=True)
            (hub / 'ai/project-registry.md').write_text(f'## p\nStatus: active\nPath: {project}\n')
            (project / 'ai/current-task.md').write_text('Status: empty\n')
            (project / 'ai/future-tasks.md').write_text('### TASK-p-20261002-001 — текст\nStatus: ready\n\n### Legacy task\n')
            (project / 'ai/paused-tasks.md').write_text('# Paused Tasks\n')
            payload = dict(metadata=self.meta,today=response([event('дела/p/текст')]),tomorrow=response([]),
                           sync_window=dict(start='2026-09-02T00:00:00+03:00',end='2026-11-02T00:00:00+03:00',response=response([])))
            result = subprocess.run([sys.executable,str(script),'--hub',str(hub),'--day','2026-10-02'],
                                    input=json.dumps(payload),text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['queue'][0]['task_id'],'TASK-p-20261002-001')
            self.assertIn('WARNING: unrecognized task heading skipped', result.stderr)
            # Registered paths outside the one allowed projects root fail closed.
            (hub / 'ai/project-registry.md').write_text(f'## p\nStatus: active\nPath: {hub}\n')
            result = subprocess.run([sys.executable,str(script),'--hub',str(hub),'--day','2026-10-02'],
                                    input=json.dumps(payload),text=True,capture_output=True)
            self.assertEqual(result.returncode,2)
            self.assertEqual(result.stdout,'')


if __name__ == '__main__':
    unittest.main()
