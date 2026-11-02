"""Планы внешней отмены: размер, точные байты и атомарная публикация."""
import json
from pathlib import Path
from unittest.mock import patch
import unittest

import test_reminders_external_retirement as base

m = base.m


class PlanV2Tests(base.ExternalRetirementTests):
    def large_config(self, size=1_100_000):
        self.config['unrelated_padding'] = 'x' * size
        self.save()
        return (self.hub / 'ai/reminders-sync.json').read_bytes()

    def journals(self):
        root = self.hub / 'ai/reminders-external-retirements'
        return list(root.iterdir()) if root.exists() else []

    def test_large_plan_keeps_one_config_and_roundtrips(self):
        original = self.large_config()
        p = self.prepare()
        raw = Path(p['plan']).read_bytes()
        disk = json.loads(raw)
        self.assertLessEqual(len(raw), 2_097_152)
        self.assertNotIn('config', disk)
        self.assertEqual(disk['config_raw'].encode(), original)
        self.assertGreater(len(raw) + len(json.dumps(self.config).encode()), 2_097_152)
        self.assertEqual(m.read(p['plan'], p['sha256'])[1]['config'], self.config)
        self.apply(p)
        self.assertTrue(self.verify())
        self.assertEqual(self.native.writes, [])

    def test_oversize_preview_leaves_no_active_journal(self):
        original = self.large_config(1_700_000)
        self.native.rows[base.NEW] = dict(id=base.NEW, title='Сосед', version=1,
            list='Работа', list_id=base.LID, notes='y' * 2_100_000)
        before = self.paths['future'].read_bytes()
        with self.assertRaisesRegex(ValueError, 'file_too_large'):
            self.prepare()
        self.assertEqual(self.journals(), [])
        self.assertEqual(m.pending_projects(self.hub, self.read()), set())
        self.assertEqual((self.hub / 'ai/reminders-sync.json').read_bytes(), original)
        self.assertEqual(self.paths['future'].read_bytes(), before)
        self.assertEqual(self.native.writes, [])

    def test_state_write_failure_never_exposes_partial_journal(self):
        stage = m.stage_bytes
        def fail_state(path, payload):
            self.assertEqual(self.journals(), [])
            if Path(path).name == 'state.json':
                raise OSError('state unavailable')
            stage(path, payload)
        with patch.object(m, 'stage_bytes', side_effect=fail_state):
            with self.assertRaisesRegex(OSError, 'state unavailable'):
                self.prepare()
        self.assertEqual(self.journals(), [])
        self.assertEqual(list((self.hub / 'ai').glob('.retirement-preview-*')), [])
        self.assertEqual(m.pending_projects(self.hub, self.read()), set())
        p = self.prepare()
        self.apply(p)
        self.assertTrue(self.verify())

    def test_rename_failure_is_reported_and_retry_is_safe(self):
        with patch.object(m.os, 'rename', side_effect=OSError('publish unavailable')):
            with self.assertRaisesRegex(OSError, 'publish unavailable'):
                self.prepare()
        self.assertEqual(self.journals(), [])
        self.assertEqual(list((self.hub / 'ai').glob('.retirement-preview-*')), [])
        self.assertEqual(self.native.writes, [])
        p = self.prepare()
        self.apply(p)
        self.assertTrue(self.verify())

    def test_legacy_v1_plan_and_receipt_remain_supported(self):
        p = self.prepare()
        path = Path(p['plan'])
        legacy = json.loads(path.read_bytes())
        legacy.update(version=1, config=json.loads(legacy['config_raw']))
        m.cancel.durable_json(path, legacy)
        digest = m.cancel.digest(path.read_bytes())
        state = json.loads(path.with_name('state.json').read_bytes())
        state['sha256'] = digest
        m.cancel.durable_json(path.with_name('state.json'), state)
        self.apply(dict(plan=str(path), sha256=digest))
        self.assertTrue(self.verify())
        self.assertEqual(self.native.writes, [])

    def test_large_plan_rejects_equivalent_config_reformat(self):
        self.large_config()
        p = self.prepare()
        path = self.hub / 'ai/reminders-sync.json'
        path.write_text(json.dumps(self.read(), ensure_ascii=False, indent=2))
        edited = path.read_bytes()
        before = self.paths['future'].read_bytes()
        with self.assertRaisesRegex(ValueError, 'cas_conflict'):
            self.apply(p)
        self.assertEqual(path.read_bytes(), edited)
        self.assertEqual(self.paths['future'].read_bytes(), before)
        self.assertEqual(self.native.writes, [])

    def test_large_partial_apply_resumes_with_history(self):
        self.large_config()
        p = self.prepare()
        write = m.cancel.write_texts
        def fail_after_write(hp, project):
            write(hp, project)
            raise OSError('after canonical')
        with patch.object(m.cancel, 'write_texts', side_effect=fail_after_write):
            with self.assertRaisesRegex(OSError, 'after canonical'):
                self.apply(p)
        self.assertEqual(m.pending_projects(self.hub, self.read()), {'demo'})
        self.apply(p)
        self.assertTrue(self.verify())
        self.assertEqual(m.pending_projects(self.hub, self.read()), set())
        self.assertEqual(self.native.writes, [])
        self.assertIn('Контекст.', self.paths['future'].read_text())

    def test_v2_rejects_non_object_config(self):
        p = self.prepare()
        path = Path(p['plan'])
        value = json.loads(path.read_bytes())
        value['config_raw'] = '[]'
        m.cancel.durable_json(path, value)
        digest = m.cancel.digest(path.read_bytes())
        state = json.loads(path.with_name('state.json').read_bytes())
        state['sha256'] = digest
        m.cancel.durable_json(path.with_name('state.json'), state)
        with self.assertRaisesRegex(ValueError, 'invalid_retirement_config'):
            m.read(path, digest)


if __name__ == '__main__':
    unittest.main()
