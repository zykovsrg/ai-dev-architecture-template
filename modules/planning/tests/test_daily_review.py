"""Полный ежедневный список и явное завершение просмотра."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from test_review_reminders import review, prepared, row, merged
from test_evening_review_sync import payload, event, response

spec = importlib.util.spec_from_file_location('daily_evening', Path(__file__).resolve().parents[1] / 'scripts/evening_review.py')
evening = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evening)


class DailyReview(unittest.TestCase):
    def test_all_open_reminders_include_future_and_undated(self):
        data = prepared([row('future', due='2027-01-01'), row('undated'), row('past', due='2020-01-01')])
        self.assertEqual({r['id'] for r in data['today']}, {'future', 'undated', 'past'})
        self.assertEqual(data['open'], data['today'])

    def test_daily_calendar_keeps_unlinked_all_day_and_repeated_blocks(self):
        data = payload()
        data['today'] = response([event('2026-10-03T00:00:00+03:00', '2026-10-04T00:00:00+03:00', 'day', 'Личное'),
                                  event('2026-10-03T12:00:00+03:00', '2026-10-03T13:00:00+03:00', 'one'),
                                  event('2026-10-03T14:00:00+03:00', '2026-10-03T15:00:00+03:00', 'two')])
        data['today']['events'][0]['all_day'] = True
        result = evening.prepare_daily_calendar(data['metadata'], data['today'], '2026-10-03')
        result = review.merge(result, prepared(), {'projects': {}}, [])
        self.assertEqual([i['event']['id'] for i in result['queue']], ['day', 'one', 'two'])
        self.assertEqual(len(set(result['review_keys'])), 3)
        self.assertTrue(result['calendar_events'][0]['all_day'])

    def test_explicit_finish_skips_uncommented_without_completing_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp).resolve(); (hub / 'ai').mkdir()
            data = merged([row('a', due='2026-10-28'), row('b', due='2026-10-28')])
            data.update(previous=None, consumed=[], calendar_reviewed=True, list_reviewed=True, sync_complete=True)
            state = review.finish(hub, data, '2026-10-28T22:00:00+03:00')
            self.assertEqual(state['last_reviewed_through'], data['through'])
            self.assertEqual(data['consumed'], [])
            self.assertTrue(all(not i['reminder']['completed'] for i in data['queue']))

    def test_explicit_finish_requires_successful_sync_and_complete_read(self):
        for changes in [dict(sync_complete=False), dict(complete=False), dict(today_complete=False), dict(list_reviewed=False)]:
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as tmp:
                hub = Path(tmp).resolve(); (hub / 'ai').mkdir()
                data = merged([row('a', due='2026-10-28')])
                data.update(previous=None, consumed=[], calendar_reviewed=True, list_reviewed=True, sync_complete=True)
                data.update(changes)
                with self.assertRaises(ValueError):
                    review.finish(hub, data, '2026-10-28T22:00:00+03:00')
                self.assertFalse((hub / review.STATE).exists())

    def test_fast_payload_cannot_bypass_sync_with_all_consumed(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp).resolve(); (hub / 'ai').mkdir()
            data = merged()
            data.update(previous=None, consumed=data['review_keys'], calendar_reviewed=True, daily_review=True)
            with self.assertRaises(ValueError):
                review.finish(hub, data, '2026-10-28T22:00:00+03:00')
