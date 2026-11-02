"""Граница потребителя полной синхронизации без повторного чтения приложения."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from test_review_reminders import review, row

NOW = '2026-10-28T21:00:00+03:00'


class DailySyncIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.hub = Path(self.tmp.name).resolve(); (self.hub / 'ai').mkdir()
        self.allow = self.hub / 'ai/allow.json'
        self.allow.write_text(json.dumps({'names': ['Разрешённый']}))
        self.config = dict(enabled=True, projects={}, allowlist_file=str(self.allow))
        self.snapshot = dict(complete=True, metadata={'lists': [{'id': 'L', 'name': 'Разрешённый'}], 'groups': []},
                             reminders=[row('open')], captured_at='2026-10-28T18:00:00+00:00',
                             scope={'names': ['Разрешённый'], 'original_sha256': hashlib.sha256(self.allow.read_bytes()).hexdigest()}, limitations=[])
        self.result = dict(ok=True, final_snapshot=self.snapshot, items=[])
        self.calls = []
        self.module = types.SimpleNamespace(
            load_config=self.load_config, standard_allowlist=lambda config: config['allowlist_file'],
            sync_lock=lambda hub: contextlib.nullcontext(), reads_module=lambda: None,
            sync=self.sync, Native=self.native)
        self.mock = patch.dict(sys.modules, {'reminders_sync': self.module}); self.mock.start()
        self.addCleanup(self.mock.stop); self.addCleanup(self.tmp.cleanup)

    def load_config(self, hub):
        self.calls.append('load_config'); return self.config

    def sync(self, hub, config, **kwargs):
        self.calls.append(kwargs); return self.result

    def native(self, config):
        raise AssertionError('Нельзя повторно читать полный пригодный снимок')

    def collect(self):
        return review.load_reminders(self.hub, '2026-10-28', NOW, sync_first=True)[0]

    def test_success_reuses_snapshot_and_validates_config(self):
        result = self.collect()
        self.assertTrue(result['sync_complete'])
        self.assertEqual([r['id'] for r in result['open']], ['open'])
        self.assertIn(dict(apply=True, return_snapshot=True), self.calls)
        self.assertEqual(self.calls.count('load_config'), 2)

    def test_foreign_scope_or_missing_required_list_cannot_report_success(self):
        for change in ['names', 'hash', 'required']:
            with self.subTest(change=change):
                snapshot = json.loads(json.dumps(self.snapshot))
                if change == 'names': snapshot['scope']['names'] = ['Посторонний']
                elif change == 'hash': snapshot['scope']['original_sha256'] = 'wrong'
                else: self.config['projects'] = {'demo': {'list_id': 'missing', 'list_name': 'Пропавший'}}
                self.result['final_snapshot'] = snapshot
                with patch.object(review, 'collect', return_value=[]) as fallback:
                    self.module.Native = lambda config: object()
                    result = self.collect()
                self.assertFalse(result['sync_complete'])
                self.assertTrue(result['sync_errors'])
                fallback.assert_called_once()
                self.config['projects'] = {}

    def test_sync_errors_remain_visible_with_complete_snapshot(self):
        self.result.update(ok=False, items=[{'error': 'conflict', 'project': 'demo'}])
        result = self.collect()
        self.assertFalse(result['sync_complete'])
        self.assertIn('conflict', json.dumps(result['sync_errors']))

    def test_incomplete_snapshot_falls_back_without_success(self):
        self.snapshot['complete'] = False
        self.module.Native = lambda config: object()
        with patch.object(review, 'collect', return_value=[row('available')]) as fallback:
            result = self.collect()
        fallback.assert_called_once()
        self.assertEqual([r['id'] for r in result['open']], ['available'])
        self.assertFalse(result['sync_complete'])

    def test_snapshot_boundary_defers_completion_during_conversation(self):
        self.snapshot['captured_at'] = '2026-10-28T17:59:00+00:00'
        self.snapshot['reminders'] = [row('before', completed=True, completed_at='2026-10-28T20:58:00+03:00'),
                                      row('during', completed=True, completed_at='2026-10-28T20:59:30+03:00')]
        result = self.collect()
        self.assertEqual(result['through'], '2026-10-28T20:59:00+03:00')
        self.assertEqual([r['id'] for r in result['completed']], ['before'])
        self.snapshot['captured_at'] = '2026-10-28T18:02:00+00:00'
        self.assertEqual(self.collect()['through'], NOW)

    def test_evening_sync_requires_reminders_before_any_source_access(self):
        script = Path(review.__file__).with_name('evening_review.py')
        result = subprocess.run([sys.executable, str(script), '--hub', '/unavailable', '--day', '2026-10-28', '--sync'],
                                input='{}', capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--reminders', result.stderr)
        self.assertNotIn('No such file', result.stderr)

    def test_evening_reads_canonical_identity_after_sync_writes(self):
        path = Path(review.__file__).with_name('evening_review.py')
        spec = importlib.util.spec_from_file_location('daily_sync_evening', path)
        evening = importlib.util.module_from_spec(spec); spec.loader.exec_module(evening)
        source = evening.SOURCE
        data = dict(metadata={'source': source, 'calendars': []},
                    today={'source': source, 'timezone': 'Europe/Kirov', 'events': [],
                           'availability_complete': True, 'unavailable_calendar_ids': []})
        def canonical(hub):
            self.calls.append('canonical'); return set(), []
        argv = ['evening_review.py', '--hub', str(self.hub), '--day', '2026-10-28', '--reminders', '--sync', '--now', NOW]
        with patch.dict(sys.modules, {'review_reminders': review}), patch.object(evening, 'canonical_inputs', canonical), \
                patch.object(sys, 'argv', argv), patch.object(sys, 'stdin', io.StringIO(json.dumps(data))), \
                patch.object(sys, 'stdout', io.StringIO()) as output:
            self.assertEqual(evening.main(), 0)
        self.assertLess(self.calls.index(dict(apply=True, return_snapshot=True)), self.calls.index('canonical'))
        self.assertEqual(self.calls.count('canonical'), 1)
        self.assertTrue(json.loads(output.getvalue())['sync_complete'])
