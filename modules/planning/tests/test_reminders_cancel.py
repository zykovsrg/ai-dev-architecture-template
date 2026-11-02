"""Изолированное исполнение; настоящее приложение никогда не запускается."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import uuid

SOURCE = Path(os.environ.get('CANCEL_TEST_SOURCE', str(Path(__file__).resolve().parents[1] / 'scripts/reminders_cancel.py')))
spec = importlib.util.spec_from_file_location('cancel_subject', SOURCE)
m = importlib.util.module_from_spec(spec) if SOURCE.exists() else None
if m:
    spec.loader.exec_module(m)
REAL_HUB = Path(__file__).resolve().parents[3]
TID = 'TASK-demo-20261026-001'
RID, PID, LID = [str(uuid.UUID(int=i)) for i in (1, 2, 3)]


class Native:
    """Двойник с атомарной проверкой; не доказательство гарантий приложения."""
    def __init__(self):
        self.data = {
            PID: dict(id=PID, list_id=LID, list='Работа', parent_id=None, title='Проект', version='p1', completed=False),
            RID: dict(id=RID, list_id=LID, list='Работа', parent_id=PID, title='Задача', version='r1', completed=False,
                      notes='Контекст', due='2026-11-01T10:30:00+03:00', repeat={'frequency': 'daily'})}
        self.deleted = set()
        self.calls = []
        self.capable = True
        self.fail_after = None
        self.race = False
    def get(self, rid, lid, parent=None):
        row = self.data[rid]
        if rid in self.deleted or row['list_id'] != lid or (parent and row.get('parent_id') != parent):
            raise ValueError('wrong_binding')
        return copy.deepcopy(row)
    def call(self, tool, args):
        self.calls.append((tool, copy.deepcopy(args)))
        if tool == 'hub_cancel_capabilities':
            return dict(protocol=1, atomic_version_check=self.capable, same_uuid_restore_verified=self.capable)
        if tool == 'find_reminders':
            return dict(reminders=[copy.deepcopy(r) for i, r in self.data.items() if i not in self.deleted])
        rid = args['id']
        row = self.data[rid]
        if tool == 'hub_cancel_status':
            return dict(state='deleted' if rid in self.deleted else 'active', version=row['version'], snapshot=copy.deepcopy(row))
        if tool not in {'hub_cancel_reminder', 'hub_restore_reminder'}:
            raise AssertionError(tool)
        if self.race:
            row['version'] += 'x'
            row['notes'] = 'Свежая правка'
        if args['version'] != row['version']:
            raise ValueError('stale_version')
        if tool == 'hub_cancel_reminder':
            self.deleted.add(rid)
        else:
            self.deleted.discard(rid)
        row['version'] += 'x'
        if self.fail_after == tool:
            self.fail_after = None
            raise TimeoutError('unknown_result')
        return self.call('hub_cancel_status', args)


class CancellationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(m, 'Отсутствует исполнитель отмены')
        self.temp = tempfile.TemporaryDirectory(prefix='hub-cancellation-', dir=getattr(self, 'fixture_dir', None))
        self.addCleanup(self.temp.cleanup)
        self.hub = Path(self.temp.name).resolve()
        (self.hub / 'ai').mkdir()
        (self.hub / 'scripts').mkdir()
        shutil.copy(REAL_HUB / 'modules/tasks/scripts/task_records.py', self.hub / 'scripts/task_records.py')
        self.project = self.hub / 'projects/demo'
        (self.project / 'ai').mkdir(parents=True)
        (self.hub / 'ai/project-registry.md').write_text(f'## demo\nStatus: active\nPath: {self.project}\n')
        self.paths = {k: self.project / 'ai' / n for k, n in m.sync.NAMES.items()}
        self.paths['current'].write_text('# Текущая задача\n\nStatus: empty\n')
        self.paths['paused'].write_text('# Пауза\n')
        self.paths['future'].write_text(f'# Будущие задачи\n\n### {TID} — Задача\nStatus: ready\nDue: 2026-12-31\nЗапланировано: 2026-10-27.\n\nПолный контекст.\n')
        self.allow = self.hub / 'ai/reminders-allowlist.json'
        self.allow.write_text(json.dumps({'names': ['Работа']}))
        self.config = dict(version=1, binary='/tmp/never-run', allowlist_file=str(self.allow), projects={'demo': dict(list_id=LID, list_name='Работа', parent_id=PID, tasks={TID: {'reminder_id': RID, 'repeating': True}})})
        self.config_path = self.hub / 'ai/reminders-sync.json'
        self.config_path.write_text(json.dumps(self.config))
        self.native = Native()
    def prepare(self):
        return m.preview(self.hub, self.config, [('demo', TID)], self.native)
    def apply(self, plan):
        return m.execute(self.hub, plan['path'], plan['sha256'], self.config, self.native)
    def restore(self, plan, token):
        return m.execute(self.hub, plan['path'], plan['sha256'], self.config, self.native, restore=True, restore_token=token)
    def texts(self):
        return {k: p.read_text() for k, p in self.paths.items()}
    def row(self):
        return m.sync.HubProject(self.hub, 'demo').rows()[TID]
    def test_cancel_is_dropped_not_done_and_retains_series(self):
        before = copy.deepcopy(self.native.data[RID])
        plan = self.prepare()
        self.assertEqual(plan['plan']['items'][0]['scope'], 'entire_series')
        self.apply(plan)
        self.assertEqual(self.row()['status'], 'dropped')
        self.assertIn(RID, self.native.deleted)
        self.assertFalse(self.native.data[RID]['completed'])
        self.assertEqual(before['repeat'], self.native.data[RID]['repeat'])
        self.assertEqual(before['notes'], self.native.data[RID]['notes'])
        self.assertEqual(before['due'], self.native.data[RID]['due'])
        self.assertEqual(m.pending_projects(self.hub, self.config), set())
    def test_current_and_paused_archive_then_restore_exactly(self):
        for kind in ('current', 'paused'):
            with self.subTest(kind=kind):
                self.paths['future'].write_text('# Будущие задачи\n')
                if kind == 'current':
                    text = f'# Текущая задача\nTask ID: {TID}\nStatus: active\nDue: 2026-12-31\n\n## Goal\nЗадача\n\n## Context\nПолный контекст.\n'
                else:
                    text = f'# Пауза\n\n### 2026-10-26 — Задача\nTask ID: {TID}\nStatus: paused\nDue: 2026-12-31\n\nПолный контекст.\n'
                self.paths[kind].write_text(text)
                before = self.texts()
                plan = self.prepare()
                self.apply(plan)
                self.assertEqual(self.row()['kind'], 'future')
                self.assertEqual(self.row()['status'], 'dropped')
                self.assertIn('Полный контекст.', self.paths['future'].read_text())
                rp = m.restore_preview(self.hub, plan['path'], plan['sha256'], self.config, self.native)
                self.restore(plan, rp['sha256'])
                self.assertEqual(self.texts(), before)
                self.paths[kind].write_text('# Пауза\n' if kind == 'paused' else '# Текущая задача\nStatus: empty\n')
    def test_restore_keeps_uuid_and_stable_token_after_timeout(self):
        before = self.texts()
        plan = self.prepare()
        self.apply(plan)
        rp = m.restore_preview(self.hub, plan['path'], plan['sha256'], self.config, self.native)
        self.native.fail_after = 'hub_restore_reminder'
        with self.assertRaises(TimeoutError):
            self.restore(plan, rp['sha256'])
        self.restore(plan, rp['sha256'])
        self.restore(plan, rp['sha256'])
        self.assertEqual(self.texts(), before)
        self.assertNotIn(RID, self.native.deleted)
        self.assertEqual(sum(t == 'hub_restore_reminder' for t, _ in self.native.calls), 1)
    def test_capability_refusal_precedes_execution_wal(self):
        plan = self.prepare()
        state = Path(plan['path']).with_name('state.json').read_bytes()
        self.native.capable = False
        with self.assertRaisesRegex(ValueError, 'capabilit'):
            self.apply(plan)
        self.assertEqual(Path(plan['path']).with_name('state.json').read_bytes(), state)
        self.assertNotIn(RID, self.native.deleted)
    def test_allowlist_rejected_before_native(self):
        self.allow.write_text(json.dumps({'names': ['Чужой']}))
        with self.assertRaisesRegex(ValueError, 'allowlist'):
            self.prepare()
        self.assertEqual(self.native.calls, [])
    def test_changed_plan_rejected(self):
        plan = self.prepare()
        path = Path(plan['path'])
        path.write_text(path.read_text() + ' ')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            self.apply(plan)
        self.assertNotIn(RID, self.native.deleted)
    def test_changed_config_and_allowlist_rejected(self):
        plan = self.prepare()
        before = self.config_path.read_text()
        self.config_path.write_text(before + ' ')
        with self.assertRaises(ValueError):
            self.apply(plan)
        self.config_path.write_text(before)
        self.allow.write_text(self.allow.read_text() + ' ')
        with self.assertRaisesRegex(ValueError, 'allowlist'):
            self.apply(plan)
        self.assertNotIn(RID, self.native.deleted)
    def test_changed_hub_rejected_before_delete(self):
        plan = self.prepare()
        self.paths['future'].write_text(self.paths['future'].read_text() + '\nСвежая правка\n')
        with self.assertRaisesRegex(ValueError, 'hub'):
            self.apply(plan)
        self.assertNotIn(RID, self.native.deleted)
    def test_changed_parent_and_remote_rejected(self):
        plan = self.prepare()
        self.native.data[PID]['version'] = 'p2'
        with self.assertRaisesRegex(ValueError, 'parent'):
            self.apply(plan)
        self.native.data[PID]['version'] = 'p1'
        self.native.data[RID]['version'] = 'r2'
        with self.assertRaisesRegex(ValueError, 'remote'):
            self.apply(plan)
        self.assertNotIn(RID, self.native.deleted)
    def test_children_rejected_in_full_list(self):
        self.native.data[str(uuid.UUID(int=4))] = dict(id=str(uuid.UUID(int=4)), parent_id=RID, list_id=LID, list='Работа', title='Ребёнок', version='1')
        with self.assertRaisesRegex(ValueError, 'children'):
            self.prepare()
        self.assertNotIn(RID, self.native.deleted)
    def test_duplicate_and_uuid_rejected(self):
        self.config['projects']['demo']['tasks']['TASK-demo-20261026-002'] = {'reminder_id': RID}
        self.config_path.write_text(json.dumps(self.config))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.prepare()
        del self.config['projects']['demo']['tasks']['TASK-demo-20261026-002']
        self.config['projects']['demo']['tasks'][TID]['reminder_id'] = '../bad'
        self.config_path.write_text(json.dumps(self.config))
        with self.assertRaisesRegex(ValueError, 'uuid'):
            self.prepare()
    def test_same_project_batch_rejected_before_native(self):
        with self.assertRaisesRegex(ValueError, 'one_target_per_project'):
            m.preview(self.hub, self.config, [('demo', TID), ('demo', TID)], self.native)
        self.assertEqual(self.native.calls, [])
    def test_unknown_delete_result_resumes_once(self):
        plan = self.prepare()
        self.native.fail_after = 'hub_cancel_reminder'
        with self.assertRaises(TimeoutError):
            self.apply(plan)
        self.assertEqual(m.pending_projects(self.hub, self.config), {'demo'})
        self.apply(plan)
        self.apply(plan)
        self.assertEqual(sum(t == 'hub_cancel_reminder' for t, _ in self.native.calls), 1)
        self.assertEqual(self.row()['status'], 'dropped')
    def test_archive_write_failure_keeps_source_and_resumes(self):
        self.paths['current'].write_text(f'# Текущая задача\nTask ID: {TID}\nStatus: active\n\n## Goal\nЗадача\n\nКонтекст\n')
        self.paths['future'].write_text('# Будущие задачи\n')
        before = self.paths['current'].read_text()
        plan = self.prepare()
        with patch.object(m.subprocess, 'run', side_effect=RuntimeError('write_failure')):
            with self.assertRaisesRegex(RuntimeError, 'write_failure'):
                self.apply(plan)
        self.assertEqual(self.paths['current'].read_text(), before)
        self.apply(plan)
        self.assertEqual(self.row()['status'], 'dropped')
    def test_restore_conflict_preserves_new_current(self):
        plan = self.prepare()
        self.apply(plan)
        rp = m.restore_preview(self.hub, plan['path'], plan['sha256'], self.config, self.native)
        self.paths['current'].write_text('# Текущая задача\nStatus: empty\nСвежий контекст\n')
        with self.assertRaisesRegex(ValueError, 'hub'):
            self.restore(plan, rp['sha256'])
        self.assertIn(RID, self.native.deleted)
    def test_mutation_race_is_atomically_rejected(self):
        plan = self.prepare()
        self.native.race = True
        with self.assertRaisesRegex(ValueError, 'stale_version'):
            self.apply(plan)
        self.assertNotIn(RID, self.native.deleted)
        self.assertEqual(self.native.data[RID]['notes'], 'Свежая правка')
    def test_corrupt_journal_fails_closed(self):
        plan = self.prepare()
        Path(plan['path']).with_name('state.json').write_text('{}')
        with self.assertRaises(ValueError):
            m.pending_projects(self.hub, self.config)
    def test_completed_cancelled_link_requires_deleted_remote(self):
        plan = self.prepare()
        self.apply(plan)
        binding = self.config['projects']['demo']
        link = binding['tasks'][TID]
        self.assertTrue(m.verify_cancelled_link(self.hub, self.row(), link, binding, self.native))
        self.native.deleted.clear()
        with self.assertRaisesRegex(ValueError, 'external_restore'):
            m.verify_cancelled_link(self.hub, self.row(), link, binding, self.native)
    def test_old_refused_restore_future_status_uses_uuid_after_old_list_cleanup(self):
        plan = self.prepare(); self.apply(plan)
        fixture = Path(__file__).with_name('test_reminders_old_list_cleanup.py')
        fs = __import__('importlib.util').util.spec_from_file_location('cleanup_fixture_for_cancel', fixture)
        fm = __import__('importlib.util').util.module_from_spec(fs); fs.loader.exec_module(fm)
        reference, parent_id, old_blocked = fm.OldListCleanupContractTests.completed_receipt(self.hub)
        folder = Path(reference['path']).parent
        plan_path = folder / 'plan.json'; plan_data = json.loads(plan_path.read_text())
        plan_data['restore_refusal_ids'] = [RID] + plan_data['restore_refusal_ids'][1:]
        plan_data['restoration_forfeit_consent']['reminder_ids'] = plan_data['restore_refusal_ids']
        cancel_item = plan['plan']['items'][0]
        cancel_status = m.native_status(self.native, Path(plan['path']), plan['sha256'], cancel_item)
        plan_data['restore_refusal_proofs'].pop(old_blocked)
        plan_data['restore_refusal_proofs'][RID] = {'project_id': 'demo', 'task_id': TID,
            'reminder_id': RID, 'operation_id': plan['plan']['operation_id'],
            'plan_sha256': plan['sha256'], 'native_status': cancel_status}
        plan_raw = json.dumps(plan_data, sort_keys=True, indent=2).encode() + b'\n'
        plan_path.write_bytes(plan_raw)
        receipt_path = Path(reference['path']); receipt = json.loads(receipt_path.read_text())
        import hashlib
        receipt['plan_sha256'] = hashlib.sha256(plan_raw).hexdigest()
        receipt['restore_refusal_ids'] = plan_data['restore_refusal_ids']
        receipt['restore_refusal_proofs'] = plan_data['restore_refusal_proofs']
        receipt['restoration_forfeit_consent'] = plan_data['restoration_forfeit_consent']
        receipt_raw = json.dumps(receipt, sort_keys=True, indent=2).encode() + b'\n'
        receipt_path.write_bytes(receipt_raw)
        receipt_sha = hashlib.sha256(receipt_raw).hexdigest()
        (folder / 'state.json').write_text(json.dumps({'protocol': 1, 'phase': 'complete',
            'plan_sha256': hashlib.sha256(plan_raw).hexdigest(), 'receipt_sha256': receipt_sha}))
        reference.update(sha256=receipt_sha, restore_refusal_ids=plan_data['restore_refusal_ids'])
        binding = self.config['projects']['demo']
        binding['retired_parent'] = {'id': parent_id, 'list_id': LID,
            'snapshot': {'id': parent_id, 'list_id': LID, 'parent_id': None, 'subtasks': []}}
        binding['retired_parent_cleanup'] = reference
        reference['restore_refusal_ids'] = [RID]
        binding['restoration_forfeit_state'] = {'state': 'restoration_forfeited', 'reminder_ids': [RID]}
        cleanup_plan = json.loads(plan_path.read_text())
        account = '60000000-0000-4000-8000-000000000001'
        active_ids = cleanup_plan['protected_list_ids']
        project_bindings = {f'project-{i}': {
            'layout': 'project_list', 'parent_id': None, 'list_id': lid,
            'list_name': cleanup_plan['inventory']['lists'][lid]['name'], 'account_id': account,
            'tasks': {}, 'history': {}}
            for i, lid in enumerate(active_ids)}
        project_bindings['demo'] = binding
        list_roles = {lid: {'kind': 'project', 'project_id': f'project-{i}'}
                      for i, lid in enumerate(active_ids)}
        list_roles[LID] = {'kind': 'group', 'group_id': 'legacy'}
        self.config['projects'] = project_bindings
        self.config['structure'] = {
            'list_roles': list_roles,
            'projects': {f'project-{i}': {'list_id': lid, 'group': 'current'}
                         for i, lid in enumerate(active_ids)},
        }
        self.config_path.write_text(json.dumps(self.config))
        link = binding['tasks'][TID]
        class FaithfulAfterCleanup:
            def __init__(self):
                self.calls=[]; self.fail_active_scan=False; self.incomplete_active_scan=False
                self.active_lists = [dict(row) for lid, row in cleanup_plan['inventory']['lists'].items()
                                     if lid in cleanup_plan['protected_list_ids']]
                self.active_rows = [dict(row) for row in cleanup_plan['inventory']['reminders'].values()]
                self.active_lists.append({'id': LID, 'name': 'Работа', 'account_id': account,
                                          'group_id': None, 'open': 0, 'total': 0, 'shared': False})
                self.refresh_counts()
                self.active_groups = []
            def refresh_counts(inner):
                for list_row in inner.active_lists:
                    count = sum(row['list_id'] == list_row['id'] for row in inner.active_rows)
                    list_row['total'] = count; list_row['open'] = count
            def cancellation_status(inner, args):
                inner.calls.append(('hub_cancel_status', args))
                raise RuntimeError('Cancellation list identity changed.')
            def call(inner, tool, args):
                inner.calls.append(tool)
                if tool == 'list_lists':
                    if inner.fail_active_scan: raise RuntimeError('Native active list read failed')
                    return {'lists': inner.active_lists, 'groups': inner.active_groups}
                if tool == 'find_reminders':
                    if inner.fail_active_scan: raise RuntimeError('Native active list read failed')
                    rows = [dict(row) for row in inner.active_rows if row['list_id'] == args['list']]
                    return {'reminders': rows, 'count': len(rows),
                            **({'more': True} if inner.incomplete_active_scan else {})}
                if tool == 'get_reminder': return dict(cleanup_plan['inventory']['reminders'][args['id']])
                raise AssertionError(tool)
        faithful = FaithfulAfterCleanup()
        self.assertTrue(m.verify_cancelled_link(self.hub, self.row(), link, binding, faithful))
        self.assertNotIn('hub_cancel_status', faithful.calls)
        structure = m.sync.structure_module()
        self.assertEqual(structure.verified_cancelled_ids(self.hub, 'demo', binding,
                         self.config, faithful), {RID})
        self.assertNotIn('hub_cancel_status', faithful.calls)

        # Post-cleanup consumer allows current work to change and ordinary tasks to be created,
        # cancelled, and restored while scanning the complete current summary.
        ordinary = next(row for row in faithful.active_rows if row['id'] != RID)
        ordinary['title'] = 'Новый заголовок обычной задачи'
        ordinary['notes'] = 'Текущая заметка после очистки'
        created_id = '90000000-0000-4000-8000-000000000001'
        faithful.active_rows.append(dict(id=created_id, list_id=ordinary['list_id'], list=ordinary['list'], title='Новая задача'))
        faithful.refresh_counts()
        self.assertTrue(fm.cleanup.restoration_forfeited_for_binding(self.hub, binding, RID, faithful))
        faithful.active_rows.remove(ordinary)  # ordinary cancellation
        faithful.refresh_counts()
        self.assertTrue(fm.cleanup.restoration_forfeited_for_binding(self.hub, binding, RID, faithful))
        faithful.active_rows.append(ordinary)  # ordinary restoration
        faithful.refresh_counts()
        self.assertTrue(fm.cleanup.restoration_forfeited_for_binding(self.hub, binding, RID, faithful))

        refused_id = next(rid for rid in receipt['restore_refusal_ids'] if rid != RID)
        faithful.active_rows.append(dict(id=refused_id, list_id=ordinary['list_id'], list=ordinary['list'], title='forged active refusal'))
        faithful.refresh_counts()
        with self.assertRaisesRegex(ValueError, 'cleanup_forfeited_reminder_active'):
            fm.cleanup.restoration_forfeited_for_binding(self.hub, binding, RID, faithful)
        faithful.active_rows.pop()
        faithful.refresh_counts()

        faithful.incomplete_active_scan = True
        with self.assertRaisesRegex(ValueError, 'cleanup_forfeiture_current_list_rows_incomplete'):
            fm.cleanup.restoration_forfeited_for_binding(self.hub, binding, RID, faithful)
        faithful.incomplete_active_scan = False

        original_account = faithful.active_lists[0]['account_id']
        faithful.active_lists[0]['account_id'] = 'foreign-account'
        with self.assertRaisesRegex(ValueError, 'cleanup_forfeiture_active_list_identity_invalid'):
            fm.cleanup.restoration_forfeited_for_binding(self.hub, binding, RID, faithful)
        faithful.active_lists[0]['account_id'] = original_account

        faithful.fail_active_scan=True
        with self.assertRaisesRegex(RuntimeError,'Native active list read failed'):
            m.verify_cancelled_link(self.hub, self.row(), link, binding, faithful)
    def test_symlink_plan_and_traversal_rejected(self):
        plan = self.prepare()
        alias = self.hub / 'ai/alias.json'
        alias.symlink_to(plan['path'])
        with self.assertRaises(ValueError):
            m.execute(self.hub, alias, plan['sha256'], self.config, self.native)
        with self.assertRaises(ValueError):
            m.execute(self.hub, Path(plan['path']).parent / '../plan.json', plan['sha256'], self.config, self.native)
    def test_shared_sync_lock_refuses_parallel_execution(self):
        plan = self.prepare()
        import fcntl
        with open(self.hub / 'ai/.reminders-sync.lock', 'a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                self.apply(plan)
    def test_wal_failure_prevents_native_mutation(self):
        plan = self.prepare()
        with patch.object(m, 'durable_json', side_effect=OSError('disk_full')):
            with self.assertRaisesRegex(OSError, 'disk_full'):
                self.apply(plan)
        self.assertNotIn(RID, self.native.deleted)
    def test_cancel_resumes_after_each_durable_boundary(self):
        for boundary in range(1, 7):
            with self.subTest(boundary=boundary):
                self.setUp()
                plan = self.prepare()
                original = m.durable_json
                calls = [0]
                def crash(path, value):
                    original(path, value)
                    calls[0] += 1
                    if calls[0] == boundary:
                        raise OSError('crash_after_write')
                with patch.object(m, 'durable_json', side_effect=crash):
                    with self.assertRaises(OSError):
                        self.apply(plan)
                self.config = json.loads(self.config_path.read_text())
                self.apply(plan)
                self.assertEqual(self.row()['status'], 'dropped')
                self.assertEqual(sum(t == 'hub_cancel_reminder' for t, _ in self.native.calls), 1)
                self.assertEqual(m.pending_projects(self.hub, self.config), set())
    def test_restore_resumes_after_each_durable_boundary(self):
        for boundary in range(1, 7):
            with self.subTest(boundary=boundary):
                self.setUp()
                before = self.texts()
                plan = self.prepare()
                self.apply(plan)
                rp = m.restore_preview(self.hub, plan['path'], plan['sha256'], self.config, self.native)
                original = m.durable_json
                calls = [0]
                def crash(path, value):
                    original(path, value)
                    calls[0] += 1
                    if calls[0] == boundary:
                        raise OSError('crash_after_write')
                with patch.object(m, 'durable_json', side_effect=crash):
                    with self.assertRaises(OSError):
                        self.restore(plan, rp['sha256'])
                self.config = json.loads(self.config_path.read_text())
                self.restore(plan, rp['sha256'])
                self.assertEqual(self.texts(), before)
                self.assertEqual(sum(t == 'hub_restore_reminder' for t, _ in self.native.calls), 1)
    def test_archive_partial_write_resumes_before_source_clear(self):
        self.paths['current'].write_text(f'# Текущая задача\nTask ID: {TID}\nStatus: active\n\n## Goal\nЗадача\n\nКонтекст\n')
        self.paths['future'].write_text('# Будущие задачи\n')
        plan = self.prepare()
        original = m.subprocess.run
        def crash(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError('after_archive')
        with patch.object(m.subprocess, 'run', side_effect=crash):
            with self.assertRaises(OSError):
                self.apply(plan)
        self.assertIn('Task ID: ' + TID, self.paths['current'].read_text())
        self.assertIn('Status: dropped', self.paths['future'].read_text())
        self.apply(plan)
        self.assertEqual(self.row()['status'], 'dropped')
    def test_cancelled_verification_allows_unrelated_task_edit(self):
        plan = self.prepare()
        self.apply(plan)
        self.paths['future'].write_text(self.paths['future'].read_text() + '\n### TASK-demo-20261026-002 — Другая\nStatus: ready\n')
        binding = self.config['projects']['demo']
        self.assertTrue(m.verify_cancelled_link(self.hub, self.row(), binding['tasks'][TID], binding, self.native))
    def test_expected_uuid_is_explicit_and_exact(self):
        with self.assertRaisesRegex(ValueError, 'expected_uuid'):
            m.preview(self.hub, self.config, [('demo', TID)], self.native, expected_uuid=str(uuid.UUID(int=9)))
        self.assertNotIn(RID, self.native.deleted)
    def test_batch_checks_all_projects_before_any_mutation(self):
        other = self.hub / 'projects/other'
        (other / 'ai').mkdir(parents=True)
        with (self.hub / 'ai/project-registry.md').open('a') as stream:
            stream.write(f'\n## other\nStatus: active\nPath: {other}\n')
        other_tid = 'TASK-other-20261026-001'
        other_parent, other_rid = [str(uuid.UUID(int=i)) for i in (20, 21)]
        for kind, path in self.paths.items():
            (other / 'ai' / path.name).write_text(path.read_text().replace(TID, other_tid))
        self.config['projects']['other'] = dict(list_id=LID, list_name='Работа', parent_id=other_parent, tasks={other_tid: {'reminder_id': other_rid}})
        self.config_path.write_text(json.dumps(self.config))
        self.native.data[other_parent] = dict(self.native.data[PID], id=other_parent)
        self.native.data[other_rid] = dict(self.native.data[RID], id=other_rid, parent_id=other_parent)
        plan = m.preview(self.hub, self.config, [('demo', TID), ('other', other_tid)], self.native)
        self.native.data[other_rid]['version'] += 'changed'
        with self.assertRaisesRegex(ValueError, 'remote'):
            self.apply(plan)
        self.assertEqual(self.native.deleted, set())
    def test_restore_token_is_required_and_saved_plan_is_immutable(self):
        plan = self.prepare()
        self.apply(plan)
        rp = m.restore_preview(self.hub, plan['path'], plan['sha256'], self.config, self.native)
        same = m.restore_preview(self.hub, plan['path'], plan['sha256'], self.config, self.native)
        self.assertEqual(rp, same)
        with self.assertRaisesRegex(ValueError, 'restore_token'):
            self.restore(plan, None)
        Path(rp['path']).write_text(Path(rp['path']).read_text() + ' ')
        with self.assertRaisesRegex(ValueError, 'restore_checksum'):
            self.restore(plan, rp['sha256'])
        self.assertIn(RID, self.native.deleted)
    def test_unknown_uuid_never_counts_as_deleted(self):
        plan = self.prepare()
        del self.native.data[RID]
        with self.assertRaises(KeyError):
            self.apply(plan)
        self.assertEqual(self.row()['status'], 'ready')
    def test_directory_fsync_is_required_before_native_mutation(self):
        plan = self.prepare()
        with patch.object(m, 'fsync_dir', side_effect=OSError('fsync_failed')):
            with self.assertRaisesRegex(OSError, 'fsync_failed'):
                self.apply(plan)
        self.assertNotIn(RID, self.native.deleted)
    def test_committed_phase_without_receipt_fails_closed(self):
        plan = self.prepare()
        path = Path(plan['path']).with_name('state.json')
        state = json.loads(path.read_text())
        state['approved'] = True
        state['items'][RID]['phase'] = 'committed'
        path.write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError, 'journal'):
            m.pending_projects(self.hub, self.config)
    def test_native_uppercase_uuid_and_scoped_list_without_ids(self):
        upper = 'ABCDEFAB-1234-5678-9ABC-ABCDEFABCDEF'
        self.config['projects']['demo']['tasks'][TID]['reminder_id'] = upper
        self.config_path.write_text(json.dumps(self.config))
        self.native.data[upper] = dict(self.native.data.pop(RID), id=upper)
        original = self.native.call
        def realistic(tool, args):
            value = original(tool, args)
            if tool == 'find_reminders':
                for row in value['reminders']:
                    row.pop('list_id', None)
            return value
        self.native.call = realistic
        plan = self.prepare()
        self.apply(plan)
        self.assertIn(upper, self.native.deleted)
    def test_unapproved_preview_does_not_block_sync(self):
        self.prepare()
        self.assertEqual(m.pending_projects(self.hub, self.config), set())
    def test_restore_preview_preserves_new_unrelated_tasks(self):
        plan = self.prepare()
        self.apply(plan)
        addition = '\n### TASK-demo-20261026-002 — Новая задача\nStatus: ready\n\nНовый контекст.\n'
        self.paths['future'].write_text(self.paths['future'].read_text() + addition)
        rp = m.restore_preview(self.hub, plan['path'], plan['sha256'], self.config, self.native)
        self.restore(plan, rp['sha256'])
        self.assertEqual(self.row()['status'], 'ready')
        self.assertIn(addition, self.paths['future'].read_text())
    def test_new_restore_plan_after_unapplied_preview(self):
        plan = self.prepare()
        self.apply(plan)
        rp = m.restore_preview(self.hub, plan['path'], plan['sha256'], self.config, self.native)
        self.paths['future'].write_text(self.paths['future'].read_text() + '\n### TASK-demo-20261026-002 — Новая задача\nStatus: ready\n')
        newer = m.restore_preview(self.hub, plan['path'], plan['sha256'], self.config, self.native)
        self.assertNotEqual(rp['sha256'], newer['sha256'])
        self.assertTrue(Path(rp['path']).is_file())
        self.restore(plan, newer['sha256'])
        self.assertIn('Новая задача', self.paths['future'].read_text())
    def test_apply_allowlist_guard_precedes_any_native_call(self):
        plan = self.prepare()
        self.native.calls.clear()
        self.allow.write_text(json.dumps({'names': ['Чужая']}))
        with self.assertRaisesRegex(ValueError, 'allowlist'):
            self.apply(plan)
        self.assertEqual(self.native.calls, [])
    def test_config_reformatting_invalidates_original_approval(self):
        plan = self.prepare()
        self.config_path.write_text(m.encoded(self.config))
        with self.assertRaisesRegex(ValueError, 'config_checksum'):
            self.apply(plan)
        self.assertNotIn(RID, self.native.deleted)
    def test_parent_subtasks_own_change_allows_retry_and_restore(self):
        child = dict(id=RID, title='Задача', completed=False)
        self.native.data[PID]['subtasks'] = [child]
        original = self.native.call
        def realistic(tool, args):
            value = original(tool, args)
            if tool == 'hub_cancel_reminder':
                self.native.data[PID].pop('subtasks', None)
            elif tool == 'hub_restore_reminder':
                self.native.data[PID]['subtasks'] = [child]
            return value
        self.native.call = realistic
        plan = self.prepare()
        self.apply(plan)
        self.apply(plan)
        rp = m.restore_preview(self.hub, plan['path'], plan['sha256'], self.config, self.native)
        self.restore(plan, rp['sha256'])
        self.assertEqual(self.native.data[PID]['subtasks'], [child])
    def test_partial_cancel_can_roll_back_after_hub_write_failure(self):
        before = self.texts()
        plan = self.prepare()
        with patch.object(m.subprocess, 'run', side_effect=RuntimeError('write_failure')):
            with self.assertRaises(RuntimeError):
                self.apply(plan)
        self.assertIn(RID, self.native.deleted)
        self.assertEqual(self.row()['status'], 'ready')
        rp = m.restore_preview(self.hub, plan['path'], plan['sha256'], self.config, self.native)
        self.restore(plan, rp['sha256'])
        self.assertEqual(self.texts(), before)
        self.assertNotIn(RID, self.native.deleted)
        self.assertEqual(m.pending_projects(self.hub, self.config), set())
    def test_partial_cancel_rollback_when_remote_action_never_happened(self):
        plan = self.prepare()
        original = m.durable_json
        def crash(path, value):
            original(path, value)
            if value.get('items', {}).get(RID, {}).get('phase') == 'deleting':
                raise OSError('before_native')
        with patch.object(m, 'durable_json', side_effect=crash):
            with self.assertRaises(OSError):
                self.apply(plan)
        rp = m.restore_preview(self.hub, plan['path'], plan['sha256'], self.config, self.native)
        self.restore(plan, rp['sha256'])
        self.assertNotIn(RID, self.native.deleted)
        self.assertEqual(self.row()['status'], 'ready')
        self.assertFalse(any(t == 'hub_restore_reminder' for t, _ in self.native.calls))
    def test_incomplete_preview_never_publishes_blocking_journal(self):
        original = m.durable_json
        def crash(path, value):
            if Path(path).name == 'state.json':
                raise OSError('state_write_failed')
            original(path, value)
        with patch.object(m, 'durable_json', side_effect=crash):
            with self.assertRaises(OSError):
                self.prepare()
        self.assertEqual(m.pending_projects(self.hub, self.config), set())
        root = self.hub / 'ai/reminders-cancellations'
        self.assertFalse(any(not path.name.startswith('.') for path in root.iterdir()))
    def test_historical_journal_does_not_require_active_project(self):
        plan = self.prepare()
        self.apply(plan)
        registry = self.hub / 'ai/project-registry.md'
        registry.write_text(registry.read_text().replace('Status: active', 'Status: archived'))
        self.assertEqual(m.pending_projects(self.hub, self.config), set())
    def test_restore_rejects_fresh_source_duplicate_without_touching_it(self):
        self.paths['future'].write_text('# Будущие задачи\n')
        original = f'# Пауза\n\n### 2026-10-26 — Задача\nTask ID: {TID}\nStatus: paused\n\nИсходный контекст.\n'
        self.paths['paused'].write_text(original)
        plan = self.prepare()
        self.apply(plan)
        fresh = f'\n### 2026-10-27 — Пользовательская запись\nTask ID: {TID}\nStatus: paused\n\nСвежий контекст пользователя.\n'
        self.paths['paused'].write_text(self.paths['paused'].read_text() + fresh)
        before = self.texts()
        with self.assertRaisesRegex(ValueError, 'duplicate_task_id'):
            m.restore_preview(self.hub, plan['path'], plan['sha256'], self.config, self.native)
        self.assertEqual(self.texts(), before)
        self.assertIn(RID, self.native.deleted)
        self.assertFalse(any(t == 'hub_restore_reminder' for t, _ in self.native.calls))
    def test_receipt_of_active_project_ignores_archived_batch_neighbor(self):
        other = self.hub / 'projects/other'
        (other / 'ai').mkdir(parents=True)
        with (self.hub / 'ai/project-registry.md').open('a') as stream:
            stream.write(f'\n## other\nStatus: active\nPath: {other}\n')
        other_tid = 'TASK-other-20261026-001'
        other_parent, other_rid = [str(uuid.UUID(int=i)) for i in (20, 21)]
        for kind, path in self.paths.items():
            (other / 'ai' / path.name).write_text(path.read_text().replace(TID, other_tid))
        self.config['projects']['other'] = dict(list_id=LID, list_name='Работа', parent_id=other_parent, tasks={other_tid: {'reminder_id': other_rid}})
        self.config_path.write_text(json.dumps(self.config))
        self.native.data[other_parent] = dict(self.native.data[PID], id=other_parent)
        self.native.data[other_rid] = dict(self.native.data[RID], id=other_rid, parent_id=other_parent)
        plan = m.preview(self.hub, self.config, [('demo', TID), ('other', other_tid)], self.native)
        self.apply(plan)
        registry = self.hub / 'ai/project-registry.md'
        registry.write_text(registry.read_text().replace('## other\nStatus: active', '## other\nStatus: archived'))
        binding = self.config['projects']['demo']
        self.assertTrue(m.verify_cancelled_link(self.hub, self.row(), binding['tasks'][TID], binding, self.native))
    def test_status_reads_without_mutation(self):
        plan = self.prepare()
        before = self.texts()
        result = m.status(self.hub, plan['path'], plan['sha256'], self.config, self.native)
        self.assertEqual(result['items'][0]['state'], 'active')
        self.assertEqual(self.texts(), before)
        self.assertFalse(any(t in {'hub_cancel_reminder', 'hub_restore_reminder'} for t, _ in self.native.calls))

if __name__ == '__main__':
    unittest.main()
