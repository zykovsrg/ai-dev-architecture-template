"""Входящая сверка сохраняет исчезнувшие повторения."""
import copy
import unittest
import test_reminders_authority_core as core
sync, TID, RID = core.sync, core.TID, core.RID

OLD = '00000000-0000-0000-0000-000000000099'

class RecoveryIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = core.AuthorityCoreTests('test_repeating_live_instance_stays_open_without_native_write')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.authority = self.fixture.authority()
        self.fixture.activation['snapshot'] = {'groups':copy.deepcopy(self.fixture.native.groups)}
        self.binding = self.fixture.config['projects']['demo']
        self.binding['history'] = {OLD:dict(original_id=RID, task_id=TID, project_id='demo')}
        self.fixture.native.rows[RID]['repeat'] = {'frequency':'daily'}
        self.fixture.save()

    def test_full_pull_preserves_missing_history_and_open_series(self):
        prior = copy.deepcopy(self.binding['history'][OLD])
        result = self.fixture.pull()
        self.assertTrue(result['ok'], result)
        saved = self.fixture.config['projects']['demo']['history'][OLD]
        self.assertEqual({key:saved[key] for key in prior}, prior)
        self.assertIn('absence_receipt', saved)
        self.assertEqual(self.fixture.row()['status'], 'ready')
        self.assertEqual(self.fixture.native.writes, [])
        repeated = self.fixture.pull()
        self.assertTrue(repeated['ok'], repeated)
        self.assertEqual(self.fixture.config['projects']['demo']['history'][OLD], saved)

    def test_preview_reports_history_absence_without_changing_config(self):
        path = self.fixture.hub/'ai/reminders-sync.json'
        before = path.read_bytes()
        result = self.authority.prepare_pull(sync,self.fixture.hub,self.fixture.config,native=self.fixture.native)
        self.assertTrue(result['stop'], result)
        self.assertTrue(any(item.get('action')=='recurrence_history_missing' for item in result['items']), result)
        self.assertEqual(path.read_bytes(), before)
        self.assertNotIn('absence_receipt', self.binding['history'][OLD])
        self.assertEqual(self.fixture.native.writes, [])

    def test_unrelated_unmarked_completed_task_is_imported_separately(self):
        self.binding['history'] = {}
        self.fixture.native.rows[OLD] = dict(self.fixture.native.rows[RID], id=OLD,
            title='Заказать роллы', completed=True, repeat=None, notes=None)
        self.fixture.save()
        result = self.fixture.pull()
        self.assertTrue(result['ok'], result)
        rows = sync.HubProject(self.fixture.hub, 'demo').rows()
        imported = [row for row in rows.values() if row['title'] == 'Заказать роллы']
        self.assertEqual(len(imported), 1)
        self.assertEqual(imported[0]['status'], 'done')
        self.assertEqual(rows[TID]['status'], 'ready')
        self.assertEqual(self.fixture.config['projects']['demo']['history'], {})
        self.assertEqual(self.fixture.native.writes, [])

    def test_possible_unmarked_repeat_still_requires_confirmation(self):
        self.binding['history'] = {}
        self.fixture.native.rows[OLD] = dict(self.fixture.native.rows[RID], id=OLD,
            completed=True, repeat=None, notes=None)
        self.fixture.save()
        result = self.fixture.pull()
        self.assertFalse(result['ok'], result)
        self.assertIn('unidentified_completed_task_requires_review', str(result))
        self.assertEqual(set(self.fixture.config['projects']['demo']['tasks']), {TID})
        self.assertEqual(self.fixture.native.writes, [])

    def test_confirmed_native_format_history_is_accepted_by_full_pull(self):
        f = self.fixture
        self.binding.update(layout='project_list', parent_id=None, history={})
        f.native.rows.pop(core.PID)
        f.native.rows[RID].update(parent_id=None, notes=None)
        f.native.rows[RID].pop('completed')
        f.native.rows[OLD] = dict(f.native.rows[RID], id=OLD, completed=True, repeat=None)
        original_call = f.native.call
        def native_format(tool, args):
            result = original_call(tool, args)
            if tool == 'find_reminders':
                for row in result['reminders']:
                    row.pop('list_id', None)
            return result
        f.native.call = native_format
        f.save()
        target = dict(project_id='demo', task_id=TID, live_id=RID, completed_id=OLD)
        intent = dict(confirmed=True, statement='Да, это повторение этой задачи.', target=target)
        recovery = sync.recurrence_module()
        plan = recovery.preview(f.hub, target, intent, native=f.native, sync_module=sync)
        f.config = recovery.apply(plan['plan'], plan['sha256'], native=f.native, sync_module=sync)['config']
        result = f.pull()
        self.assertTrue(result['ok'], result)
        self.assertEqual(set(f.config['projects']['demo']['tasks']), {TID})
        self.assertIn('confirmation_receipt', f.config['projects']['demo']['history'][OLD])
        self.assertEqual(f.row()['status'], 'ready')
        self.assertEqual(f.native.writes, [])

if __name__ == '__main__': unittest.main()
