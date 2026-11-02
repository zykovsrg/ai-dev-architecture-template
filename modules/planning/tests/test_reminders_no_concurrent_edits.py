"""Проверки явно выбранного режима без одновременных правок."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import test_reminders_cancel as legacy

m = legacy.m
RID, TID = legacy.RID, legacy.TID


class OptimisticNative(legacy.Native):
    def call(self, tool, args):
        if tool == 'hub_cancel_capabilities':
            self.calls.append((tool, copy.deepcopy(args)))
            return dict(protocol=1, atomic_version_check=False,
                        optimistic_version_check=True,
                        requires_no_concurrent_edits=True,
                        same_uuid_restore_verified=True)
        return super().call(tool, args)


class NoConcurrentEditsTests(unittest.TestCase):
    def setUp(self):
        self.f = legacy.CancellationTests('test_status_reads_without_mutation')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.f.native = OptimisticNative()
        self.f.config['cancellation_policy'] = 'no_concurrent_edits'
        self.f.config_path.write_text(json.dumps(self.f.config))

    def test_explicit_policy_and_default_are_saved_with_condition(self):
        f = self.f
        f.config.pop('cancellation_policy')
        f.config_path.write_text(json.dumps(f.config))
        strict = m.preview(f.hub, f.config, [('demo', TID)], f.native)
        self.assertEqual(strict['plan']['concurrency_policy'], 'strict')
        chosen = m.preview(f.hub, f.config, [('demo', TID)], f.native,
                           concurrency_policy='no_concurrent_edits')
        self.assertEqual(chosen['plan']['concurrency_policy'], 'no_concurrent_edits')
        self.assertIn('не менять', chosen['plan']['changes'].lower())

    def test_policy_capabilities_reject_missing_flags_and_keep_strict(self):
        native = self.f.native
        m.capabilities(native, 'no_concurrent_edits')
        with self.assertRaisesRegex(ValueError, 'capabilit'):
            m.capabilities(native, 'strict')
        for field in ('optimistic_version_check', 'requires_no_concurrent_edits', 'same_uuid_restore_verified'):
            original = native.call
            def missing(tool, args, field=field):
                value = original(tool, args)
                if tool == 'hub_cancel_capabilities':
                    value[field] = False
                return value
            with patch.object(native, 'call', side_effect=missing):
                with self.assertRaisesRegex(ValueError, 'capabilit'):
                    m.capabilities(native, 'no_concurrent_edits')

    def test_legacy_plan_without_policy_stays_strict(self):
        f = self.f
        plan = f.prepare()
        path = Path(plan['path'])
        value = json.loads(path.read_text())
        del value['concurrency_policy']
        del value['changes']
        path.write_text(m.encoded(value))
        sha = m.digest(path.read_bytes())
        state_path = path.with_name('state.json')
        state = json.loads(state_path.read_text())
        state['plan_sha256'] = sha
        state_path.write_text(m.encoded(state))
        with self.assertRaisesRegex(ValueError, 'capabilit'):
            m.execute(f.hub, path, sha, f.config, f.native)
        self.assertNotIn(RID, f.native.deleted)

    def test_explicit_strict_overrides_default_noedit(self):
        f = self.f
        plan = m.preview(f.hub, f.config, [('demo', TID)], f.native,
                         concurrency_policy='strict')
        self.assertEqual(plan['plan']['concurrency_policy'], 'strict')
        with self.assertRaisesRegex(ValueError, 'capabilit'):
            f.apply(plan)
        self.assertNotIn(RID, f.native.deleted)

    def test_invalid_policy_rejected_before_native_call(self):
        f = self.f
        with self.assertRaisesRegex(ValueError, 'policy'):
            m.preview(f.hub, f.config, [('demo', TID)], f.native,
                      concurrency_policy='unknown')
        self.assertEqual(f.native.calls, [])

    def test_plan_policy_controls_execution_and_tamper_fails_hash(self):
        f = self.f
        plan = f.prepare()
        f.config['cancellation_policy'] = 'strict'
        f.config_path.write_text(json.dumps(f.config))
        with self.assertRaisesRegex(ValueError, 'config'):
            f.apply(plan)
        f.config['cancellation_policy'] = 'no_concurrent_edits'
        f.config_path.write_text(json.dumps(f.config))
        f.apply(plan)
        self.assertEqual(f.row()['status'], 'dropped')
        path = Path(plan['path'])
        content = path.read_text().replace('no_concurrent_edits', 'strict')
        path.write_text(content)
        with self.assertRaisesRegex(ValueError, 'checksum'):
            f.apply(plan)

    def test_version_change_before_cancel_stops_without_hub_write(self):
        f = self.f
        plan = f.prepare()
        f.native.data[RID]['version'] = 'new'
        with self.assertRaisesRegex(ValueError, 'remote'):
            f.apply(plan)
        self.assertEqual(f.row()['status'], 'ready')
        self.assertNotIn(RID, f.native.deleted)

    def test_partial_rollback_preserves_fresh_native_notes(self):
        f = self.f
        plan = f.prepare()
        original = f.native.call
        def fresh_after_delete(tool, args):
            value = original(tool, args)
            if tool == 'hub_cancel_reminder':
                f.native.data[RID]['notes'] = 'Свежие заметки'
                f.native.data[RID]['version'] += 'fresh'
            return value
        with patch.object(f.native, 'call', side_effect=fresh_after_delete):
            with self.assertRaisesRegex(ValueError, 'readback'):
                f.apply(plan)
        self.assertEqual(f.row()['status'], 'ready')
        rp = m.restore_preview(f.hub, plan['path'], plan['sha256'], f.config, f.native)
        saved = json.loads(Path(rp['path']).read_text())
        self.assertEqual(saved['items'][RID]['remote']['snapshot']['notes'], 'Свежие заметки')
        self.assertIn('текущие поля', saved['changes'])
        f.restore(plan, rp['sha256'])
        self.assertEqual(f.native.data[RID]['notes'], 'Свежие заметки')
        self.assertEqual(f.row()['status'], 'ready')

    def test_committed_remote_change_still_requires_review(self):
        f = self.f
        plan = f.prepare()
        f.apply(plan)
        f.native.data[RID]['notes'] = 'Свежие заметки'
        f.native.data[RID]['version'] += 'fresh'
        with self.assertRaisesRegex(ValueError, 'restore_remote_conflict'):
            m.restore_preview(f.hub, plan['path'], plan['sha256'], f.config, f.native)
        self.assertIn(RID, f.native.deleted)

    def test_routing_only_four_commands_and_rejects_unsafe_binary(self):
        f = self.f
        normal = str(f.hub / 'normal')
        cancel = str(f.hub / 'cancel')
        f.config['binary'] = normal
        f.config['cancellation_binary'] = cancel
        f.config_path.write_text(json.dumps(f.config))
        loaded = m.sync.load_config(f.hub)
        native = m.sync.Native(loaded)
        calls = []
        def run(argv, **kwargs):
            calls.append(argv)
            return type('Result', (), {'returncode': 0, 'stdout': '{}', 'stderr': ''})()
        with patch.object(m.sync.subprocess, 'run', side_effect=run):
            for tool in ('hub_cancel_capabilities', 'hub_cancel_status', 'hub_cancel_reminder', 'hub_restore_reminder'):
                native.call(tool, {})
            for tool in ('get_reminder', 'find_reminders'):
                native.call(tool, {})
        self.assertEqual([x[0] for x in calls], [cancel] * 4 + [normal] * 2)
        f.config['cancellation_binary'] = 'relative'
        f.config_path.write_text(json.dumps(f.config))
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            m.sync.load_config(f.hub)
        f.config['cancellation_binary'] = str(f.hub / 'nested' / '..' / 'cancel')
        f.config_path.write_text(json.dumps(f.config))
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            m.sync.load_config(f.hub)


if __name__ == '__main__':
    unittest.main()
