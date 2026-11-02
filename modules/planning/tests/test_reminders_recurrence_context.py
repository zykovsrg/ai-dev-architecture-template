"""Настоящие квитанции исчезнувших повторений и срок жизни общего снимка."""
import copy
import unittest
from unittest.mock import patch
import test_reminders_engine as fixture

OLD = '00000000-0000-0000-0000-000000000099'


class RecurrenceContextTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.IntegrationTests('runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.f, self.m, self.e = self.fixture.f, self.fixture.m, self.fixture.e
        self.core = self.fixture.core
        self.f.activation['snapshot'] = {'groups': copy.deepcopy(self.f.native.groups)}
        self.f.config['projects']['demo']['history'] = {
            OLD: dict(original_id=self.core.RID, task_id=self.core.TID, project_id='demo')}
        self.f.native.rows[self.core.RID]['repeat'] = {'frequency': 'daily'}
        self.f.save()
        first = self.m.sync(self.f.hub, self.f.config, True, native=self.f.native, reconcile=False)
        self.assertTrue(first['ok'], first)
        self.assertIn('absence_receipt', self.f.config['projects']['demo']['history'][OLD])

    def context(self):
        observation = self.e.capture(self.m, self.f.hub, self.f.config, self.f.native)
        return self.e.ContextNative(self.f.native, observation, self.m.reads_module())

    def restore_history(self):
        self.f.native.rows[OLD] = dict(self.f.native.rows[self.core.RID], id=OLD, completed=True, repeat=None)

    def verify(self, context):
        return self.m.recurrence_module().verified_missing(
            self.m, self.f.hub, self.f.config, 'demo', self.f.config['projects']['demo'],
            context, observation=context.validated_observation())

    def test_existing_absence_receipt_noop_uses_single_capture_without_refresh(self):
        config_before = (self.f.hub / 'ai/reminders-sync.json').read_bytes()
        with patch.object(self.e, 'capture', wraps=self.e.capture) as captured:
            result = self.m.sync(self.f.hub, self.f.config, True, native=self.f.native,
                                 reconcile=False, return_snapshot=True)
        self.assertTrue(result['ok'], result)
        self.assertTrue(result['final_snapshot']['complete'])
        self.assertEqual(captured.call_count, 1)
        self.assertEqual((self.f.hub / 'ai/reminders-sync.json').read_bytes(), config_before)
        self.assertEqual(self.f.native.writes, [])

    def test_refresh_and_failed_write_force_fresh_detection_of_returned_uuid(self):
        for invalidation in ('refresh', 'write'):
            with self.subTest(invalidation=invalidation):
                self.f.native.rows.pop(OLD, None)
                context = self.context()
                self.assertIsNotNone(context.validated_observation())
                self.restore_history()
                if invalidation == 'refresh':
                    self.m.reads_module().refresh()
                else:
                    with patch.object(self.f.native, 'call', side_effect=RuntimeError('unknown write outcome')):
                        with self.assertRaises(RuntimeError):
                            context.call('update_reminder', {'id': self.core.RID})
                self.assertIsNone(context.validated_observation())
                with self.assertRaisesRegex(ValueError, 'recurrence_history_returned'):
                    self.verify(context)

    def test_current_snapshot_with_returned_uuid_still_rejects_absence_receipt(self):
        self.restore_history()
        context = self.context()
        self.assertIsNotNone(context.validated_observation())
        with self.assertRaisesRegex(ValueError, 'recurrence_history_returned'):
            self.verify(context)

    def test_partial_and_changed_permissions_cannot_supply_observation(self):
        context = self.context()
        context.observation['complete'] = False
        self.assertIsNone(context.validated_observation())
        context = self.context()
        self.f.allow.write_text(self.f.allow.read_text() + '\n')
        self.assertIsNone(context.validated_observation())

    def test_legacy_without_context_keeps_fresh_read_boundary(self):
        reads = self.m.reads_module()
        with patch.object(reads, 'refresh', wraps=reads.refresh) as refresh:
            result = self.m._legacy_sync(self.f.hub, self.f.config, True,
                                         native=self.f.native, reconcile=False)
        self.assertTrue(result['ok'], result)
        self.assertGreaterEqual(refresh.call_count, 1)


if __name__ == '__main__':
    unittest.main()
