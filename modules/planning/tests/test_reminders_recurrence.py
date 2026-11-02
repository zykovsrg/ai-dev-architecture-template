"""Изолированные доказательства истории повторений; приложение не вызывается."""
import copy
import importlib.util
import json
import os
import shutil
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
import uuid

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
SOURCE = Path(os.environ.get('RECURRENCE_SOURCE', SCRIPTS / 'reminders_recurrence.py'))
if SOURCE.exists():
    spec = importlib.util.spec_from_file_location('recurrence_subject', SOURCE)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
else:
    m = None
LIVE, OLD, LID, ACCOUNT, GROUP = [str(uuid.UUID(int=i)) for i in range(1, 6)]
TID = 'TASK-demo-20261031-001'


class Native:
    def __init__(self):
        self.lists = [dict(id=LID, name='Работа', account_id=ACCOUNT, group_id=GROUP)]
        self.groups = [dict(id=GROUP, name='Группа', account_id=ACCOUNT)]
        self.rows = {
            LIVE: dict(id=LIVE, title='Корм', version=4, completed=False, repeat={'frequency': 'daily'}, list='Работа', list_id=LID, parent_id=None, notes='Хаб: pending'),
            OLD: dict(id=OLD, title='Корм', version=2, completed=True, list='Работа', list_id=LID, parent_id=None, notes='Личная заметка'),
        }
        self.incomplete = False
        self.writes = []
    def call(self, tool, args):
        if tool == 'list_lists':
            return dict(lists=copy.deepcopy(self.lists), groups=copy.deepcopy(self.groups))
        if tool == 'find_reminders':
            listing = next(item for item in self.lists if item['id'] == args['list'])
            rows = [copy.deepcopy(r) for r in self.rows.values() if r.get('list_id') == args['list'] or ('list_id' not in r and r.get('list') == listing['name'])]
            return dict(reminders=rows, count=len(rows), has_more=self.incomplete)
        self.writes.append((tool, args)); raise AssertionError('native write forbidden')


class RecurrenceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(m, 'Нет исполнителя подтверждённой истории повторений')
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.hub = Path(self.tmp.name).resolve(); (self.hub / 'ai').mkdir()
        project = self.hub / 'projects/demo'; project.mkdir(parents=True)
        (self.hub / 'ai/project-registry.md').write_text(f'## demo\nName: Демо\nStatus: active\nPath: {project}\n')
        allow = self.hub / 'ai/reminders-allowlist.json'; allow.write_text(json.dumps({'names': ['Работа']}))
        self.config = dict(version=1, binary='/private/tmp/never-run', allowlist_file=str(allow), projects={
            'demo': dict(layout='project_list', list_id=LID, list_name='Работа', parent_id=None, account_id=ACCOUNT, native_group_id=GROUP,
                         tasks={TID: dict(reminder_id=LIVE, repeating=True)}, history={})},
            task_authority=dict(mode='reminders', deletions='cancel', journal='ai/reminders-authority/' + str(uuid.uuid4()), sha256='a' * 64))
        self.native = Native()
        self.native.rows[LIVE]['notes'] = 'Хаб: ' + m.sync.compact_code('demo', TID)
        self.authority = m.sync.authority_module()
        self.addCleanup(patch.stopall)
        patch.object(self.authority, 'archive_module', return_value=types.SimpleNamespace(validate_activation=lambda h,c: {'snapshot': {'groups': self.native.groups}}, archive_group=lambda h,c,p: GROUP)).start()
        self.save()
        self.target = dict(project_id='demo', task_id=TID, live_id=LIVE, completed_id=OLD)
        self.intent = dict(confirmed=True, statement='Это завершённый повтор этой серии.', target=copy.deepcopy(self.target))
    def save(self):
        (self.hub / 'ai/reminders-sync.json').write_text(json.dumps(self.config, ensure_ascii=False))
    def read(self):
        return json.loads((self.hub / 'ai/reminders-sync.json').read_text())
    def preview(self):
        return m.preview(self.hub, self.target, self.intent, self.native)
    def apply(self, plan):
        return m.apply(plan['plan'], plan['sha256'], native=self.native)
    def observe(self):
        return m.sync.external_retirement_module().observe(self.hub, self.config, self.native, partial=True)
    def missing(self, apply=True, observation=None):
        return m.prepare_missing(m.sync, self.hub, self.config, observation or self.observe(), apply=apply, native=self.native)
    def historical(self):
        self.config['projects']['demo']['history'][OLD] = dict(original_id=LIVE, task_id=TID, project_id='demo', arbitrary={'kept': True})
        self.native.rows.pop(OLD); self.save()
    def verified(self, observation=None):
        config = self.read()
        return m.verified_missing(m.sync, self.hub, config, 'demo', config['projects']['demo'], self.native, observation=observation)
    def canonical_task(self):
        scripts = self.hub / 'scripts'; scripts.mkdir(exist_ok=True)
        for source in SCRIPTS.glob('*.py'): shutil.copyfile(source, scripts / source.name)
        shutil.copyfile(SCRIPTS.parents[2] / 'modules/tasks/scripts/task_records.py', scripts / 'task_records.py')
        ai = self.hub / 'projects/demo/ai'; ai.mkdir(exist_ok=True)
        (ai / 'current-task.md').write_text('# Текущая задача\nStatus: empty\n')
        (ai / 'paused-tasks.md').write_text('# Пауза\n')
        (ai / 'future-tasks.md').write_text(f'# Будущие задачи\n\n### {TID} — Серия\nStatus: ready\n\nКонтекст.\n')
    def retire_series(self):
        self.canonical_task(); self.config = self.read(); self.native.rows.pop(LIVE, None)
        external = m.sync.external_retirement_module()
        targets = [dict(project_id='demo', task_id=TID, reminder_id=LIVE)]
        intent = dict(confirmed=True, statement='Отменить именно эту серию с сохранением истории.', targets=copy.deepcopy(targets))
        plan = external.preview(self.hub, targets, intent, self.native)
        external.apply(plan['plan'], plan['sha256'], True, self.native)
        self.config = self.read(); return plan
    def receipt_prefix_context(self):
        extra = str(uuid.UUID(int=48)); self.native.lists.append(dict(id=extra, name='Личное', account_id=ACCOUNT, group_id=GROUP))
        allow = self.hub / 'ai/reminders-allowlist.json'; allow.write_text(json.dumps({'names': ['Работа', 'Личное']}))
        other = copy.deepcopy(self.config['projects']['demo']); other.update(list_id=extra, list_name='Личное', tasks={}, history={}); self.config['projects']['other'] = other
        path = self.hub / 'projects/other'; path.mkdir()
        with (self.hub / 'ai/project-registry.md').open('a') as file: file.write(f'\n## other\nName: Другой\nStatus: active\nPath: {path}\n')
        self.historical(); self.retire_series(); self.missing(); self.native.lists[1]['group_id'] = None
        proof = self.read(); proof['projects']['other']['native_group_id'] = None
        external = m.sync.external_retirement_module(); fresh = external.observe(self.hub, proof, self.native, partial=True)
        self.assertTrue(fresh['complete']); return proof, fresh, external
    def test_absence_prefix_reuses_validated_snapshot_for_current_retirement_proof(self):
        proof, fresh, external = self.receipt_prefix_context(); seen = []
        def strict(hub, row, link, binding, native, observation=None):
            self.assertIsNotNone(observation, 'Штатному валидатору нужен уже проверенный полный снимок')
            self.assertEqual(observation, fresh); seen.append(observation)
            return external.verify_link(hub, row, link, binding, native, observation=observation)
        facade = types.SimpleNamespace(permissions=external.permissions, observe=external.observe, verify_link=strict)
        with patch.object(m.sync, 'external_retirement_module', return_value=facade):
            result = m.verified_missing(m.sync, self.hub, proof, 'demo', proof['projects']['demo'], self.native, observation=fresh)
        self.assertEqual(result, {OLD}); self.assertEqual(len(seen), 1); self.assertEqual(self.native.writes, [])
        self.assertEqual(self.read()['projects']['other']['native_group_id'], GROUP)
    def test_absence_prefix_wrong_subject_group_stops_before_snapshot_forwarding(self):
        proof, fresh, external = self.receipt_prefix_context(); wrong = copy.deepcopy(fresh)
        next(row for row in wrong['metadata']['lists'] if row['id'] == LID)['group_id'] = None
        def forbidden(*args, **kwargs): raise AssertionError('Непроверенный снимок передан штатному валидатору')
        facade = types.SimpleNamespace(permissions=external.permissions, observe=external.observe, verify_link=forbidden)
        with patch.object(m.sync, 'external_retirement_module', return_value=facade):
            with self.assertRaisesRegex(ValueError, 'group'):
                m.verified_missing(m.sync, self.hub, proof, 'demo', proof['projects']['demo'], self.native, observation=wrong)
        moved = copy.deepcopy(proof); moved['projects']['demo']['native_group_id'] = None
        with self.assertRaises(ValueError):
            m.verified_missing(m.sync, self.hub, moved, 'demo', moved['projects']['demo'], self.native, observation=wrong)
    def test_absence_prefix_tampered_snapshot_stops_before_forwarding(self):
        proof, fresh, external = self.receipt_prefix_context(); wrong = copy.deepcopy(fresh)
        wrong['lists'][LID].append(dict(id=str(uuid.UUID(int=49)), version=1, title='Чужая строка', list='Неверный список', list_id=LID))
        def forbidden(*args, **kwargs): raise AssertionError('Повреждённый снимок передан штатному валидатору')
        facade = types.SimpleNamespace(permissions=external.permissions, observe=external.observe, verify_link=forbidden)
        with patch.object(m.sync, 'external_retirement_module', return_value=facade):
            with self.assertRaisesRegex(ValueError, 'snapshot'):
                m.verified_missing(m.sync, self.hub, proof, 'demo', proof['projects']['demo'], self.native, observation=wrong)
    def test_absence_apply_validates_target_once_per_project_for_multiple_histories(self):
        self.historical(); other = str(uuid.UUID(int=27))
        self.config['projects']['demo']['history'][other] = copy.deepcopy(self.config['projects']['demo']['history'][OLD]); self.save()
        before = copy.deepcopy(self.config)
        with patch.object(self.authority, 'validate_target', wraps=self.authority.validate_target) as validator:
            result = self.missing()
        self.assertEqual(validator.call_count, 1); self.assertEqual(validator.call_args.args[3], 'demo')
        after = copy.deepcopy(result['config']); refs = []
        for rid in (OLD, other): refs.append(after['projects']['demo']['history'][rid].pop('absence_receipt'))
        self.assertEqual(after, before); self.assertEqual(refs[0], refs[1])
        state = json.loads((self.hub / refs[0]['plan']).with_name('state.json').read_text())
        self.assertEqual(state['phase'], 'complete'); self.assertEqual(state['before_config'], before); self.assertEqual(state['after_config'], result['config'])
        self.assertEqual(self.native.writes, [])
    def test_stopped_series_missing_history_accepts_verified_current_retirement(self):
        self.historical(); self.retire_series(); before = copy.deepcopy(self.config)
        result = self.missing(); self.assertEqual(self.verified(), {OLD})
        actual = copy.deepcopy(result['config']); actual['projects']['demo']['history'][OLD].pop('absence_receipt')
        self.assertEqual(actual, before); self.assertEqual(self.native.writes, [])
        row = m.sync.HubProject(self.hub, 'demo').rows()[TID]; self.assertEqual(row['status'], 'dropped')
    def test_stopped_series_forged_receipt_rejects_without_absence_writes(self):
        self.historical(); self.retire_series()
        self.config['projects']['demo']['tasks'][TID]['external_retirement']['plan_sha256'] = '0' * 64; self.save()
        before = (self.hub / 'ai/reminders-sync.json').read_bytes()
        with self.assertRaises(ValueError): self.missing()
        self.assertEqual((self.hub / 'ai/reminders-sync.json').read_bytes(), before)
        self.assertFalse((self.hub / 'ai/reminders-recurrence').exists()); self.assertEqual(self.native.writes, [])
    def test_later_verified_series_retirement_preserves_prior_absence(self):
        self.historical(); self.missing(); receipt = copy.deepcopy(self.read()['projects']['demo']['history'][OLD])
        self.retire_series(); self.assertEqual(self.verified(), {OLD})
        self.assertEqual(self.read()['projects']['demo']['history'][OLD], receipt); self.assertEqual(self.native.writes, [])
        self.config = self.read(); self.config['projects']['demo']['tasks'][TID]['external_retirement']['plan_sha256'] = '0' * 64; self.save()
        with self.assertRaises(ValueError): self.verified()
    def test_cancelled_series_history_requires_current_cancellation_verifier_true(self):
        self.historical(); self.canonical_task(); self.config['projects']['demo']['tasks'][TID]['cancellation'] = {'proof': 'test'}; self.save()
        verifier = types.SimpleNamespace(verify_cancelled_link=lambda h,r,l,b,n: True)
        with patch.object(m.sync, 'cancellation_module', return_value=verifier):
            self.missing(); self.assertEqual(self.verified(), {OLD})
        verifier.verify_cancelled_link = lambda h,r,l,b,n: False
        with patch.object(m.sync, 'cancellation_module', return_value=verifier):
            with self.assertRaises(ValueError): self.verified()
    def test_confirmation_changes_only_history_and_has_durable_receipt(self):
        before = copy.deepcopy(self.config); plan = self.preview(); self.assertEqual(self.read(), before)
        self.apply(plan); after = self.read(); history = after['projects']['demo']['history'].pop(OLD)
        self.assertEqual(after, before); self.assertEqual(history['original_id'], LIVE)
        self.assertEqual(history['task_id'], TID); self.assertEqual(history['project_id'], 'demo')
        current = self.read(); binding = current['projects']['demo']
        self.assertTrue(m.validate_confirmed(self.hub, self.native.rows[OLD], binding, binding['history'][OLD]))
        state = json.loads(Path(plan['plan']).with_name('state.json').read_text())
        self.assertEqual(state['phase'], 'complete'); self.assertEqual(state['before_config'], before)
        self.assertEqual(state['after_config'], current); self.assertEqual(self.native.writes, [])
    def test_confirmed_raw_snapshot_without_list_id_accepts_normalized_child(self):
        for row in self.native.rows.values(): row.pop('list_id')
        plan = self.preview(); self.apply(plan); binding = self.read()['projects']['demo']
        child = dict(self.native.rows[OLD], list_id=LID)
        self.assertTrue(m.validate_confirmed(self.hub, child, binding, binding['history'][OLD]))
        child['list_id'] = GROUP
        with self.assertRaises(ValueError): m.validate_confirmed(self.hub, child, binding, binding['history'][OLD])
    def test_existing_live_binding_without_notes_uses_exact_config_identity(self):
        self.native.rows[LIVE]['notes'] = ''
        plan = self.preview(); self.apply(plan)
        binding = self.read()['projects']['demo']
        self.assertEqual(binding['history'][OLD]['original_id'], LIVE)
        self.assertEqual(binding['tasks'][TID]['reminder_id'], LIVE)
        self.assertEqual(self.native.writes, [])
    def test_existing_open_live_allows_omitted_or_none_completed(self):
        self.native.rows[LIVE].pop('completed')
        plan = self.preview(); self.apply(plan)
        self.assertEqual(self.read()['projects']['demo']['history'][OLD]['original_id'], LIVE)
        self.config = self.read(); self.config['projects']['demo']['history'].clear(); self.save()
        self.native.rows[LIVE]['completed'] = None
        plan = self.preview(); self.apply(plan)
        self.assertEqual(self.read()['projects']['demo']['history'][OLD]['original_id'], LIVE)
    def test_live_uuid_defensively_rejects_other_task_parent_or_history_binding(self):
        original = copy.deepcopy(self.config); observation = self.observe()
        for kind in ('task', 'parent', 'history'):
            with self.subTest(kind=kind):
                config = copy.deepcopy(original)
                if kind == 'task': config['projects']['demo']['tasks']['other'] = {'reminder_id': LIVE}
                elif kind == 'parent': config['projects']['foreign'] = {'parent_id': LIVE, 'list_id': GROUP}
                else: config['projects']['demo']['history'][LIVE] = dict(project_id='demo', task_id=TID, original_id=LIVE)
                with self.assertRaisesRegex(ValueError, 'live_uuid'):
                    m._target(m.sync, self.hub, config, self.target, observation)
    def test_uppercase_uuid_preserves_exact_identity_for_confirmation_and_absence(self):
        identities = {old: str(uuid.UUID(int=0xABC000 + index)).upper() for index, old in enumerate((LIVE, OLD, LID, ACCOUNT, GROUP), 1)}
        def changed(value):
            if isinstance(value, dict): return {identities.get(key, key): changed(item) for key, item in value.items()}
            if isinstance(value, list): return [changed(item) for item in value]
            return identities.get(value, value) if isinstance(value, str) else value
        self.config = changed(self.config); self.native.rows = changed(self.native.rows); self.native.lists = changed(self.native.lists); self.native.groups = changed(self.native.groups)
        self.target = changed(self.target); self.intent['target'] = copy.deepcopy(self.target); self.save()
        plan = self.preview(); self.apply(plan); self.config = self.read()
        completed = identities[OLD]; live = identities[LIVE]; binding = self.config['projects']['demo']
        self.assertIn(completed, binding['history']); self.assertEqual(binding['history'][completed]['original_id'], live)
        self.assertTrue(m.validate_confirmed(self.hub, self.native.rows[completed], binding, binding['history'][completed]))
        self.native.rows.pop(completed)
        result = m.prepare_missing(m.sync, self.hub, self.config, self.observe(), apply=True, native=self.native)
        self.assertEqual(m.verified_missing(m.sync, self.hub, result['config'], 'demo', result['config']['projects']['demo'], self.native), {completed})
        for invalid in ('{' + completed + '}', completed.replace('-', ''), 'urn:uuid:' + completed):
            with self.assertRaises(ValueError): m._uuid(invalid)
    def test_confirmation_refuses_intent_markers_duplicates_and_wrong_series(self):
        original = copy.deepcopy(self.config); rows = copy.deepcopy(self.native.rows); intent = copy.deepcopy(self.intent)
        for kind in ('intent', 'target', 'marker', 'live_marker', 'quoted_live_marker', 'completed', 'repeat', 'duplicate', 'archive', 'parent'):
            with self.subTest(kind=kind):
                self.config = copy.deepcopy(original); self.native.rows = copy.deepcopy(rows); self.intent = copy.deepcopy(intent)
                if kind == 'intent': self.intent['confirmed'] = False
                elif kind == 'target': self.intent['target']['live_id'] = OLD
                elif kind == 'marker': self.native.rows[OLD]['notes'] = '> Хаб: чужой код'
                elif kind == 'live_marker': self.native.rows[LIVE]['notes'] = 'Хаб: ' + m.sync.compact_code('foreign', 'other')
                elif kind == 'quoted_live_marker': self.native.rows[LIVE]['notes'] = '> ' + self.native.rows[LIVE]['notes']
                elif kind == 'completed': self.native.rows[OLD]['completed'] = False
                elif kind == 'repeat': self.native.rows[LIVE]['repeat'] = None
                elif kind == 'duplicate': self.config['projects']['demo']['tasks']['other'] = {'reminder_id': OLD}
                elif kind == 'archive': self.config['projects']['demo']['archive'] = {'journal': 'historic'}
                else: self.native.rows[OLD]['parent_id'] = LIVE
                self.save(); before = (self.hub / 'ai/reminders-sync.json').read_bytes()
                with self.assertRaises(ValueError): self.preview()
                self.assertEqual((self.hub / 'ai/reminders-sync.json').read_bytes(), before)
    def test_confirmation_apply_checks_config_versions_and_complete_snapshot(self):
        plan = self.preview(); self.native.rows[OLD]['version'] += 1
        with self.assertRaisesRegex(ValueError, 'snapshot'): self.apply(plan)
        self.native.rows[OLD]['version'] -= 1; self.native.incomplete = True
        with self.assertRaises(ValueError): self.apply(plan)
        self.native.incomplete = False; self.config['unrelated'] = 'changed'; self.save()
        with self.assertRaisesRegex(ValueError, 'config'): self.apply(plan)
    def test_confirmation_receipt_guards_state_plan_remote_and_live_link(self):
        plan = self.preview(); self.apply(plan); current = self.read(); b = current['projects']['demo']; h = b['history'][OLD]
        for field, value in (('completed', False), ('id', LIVE), ('list_id', GROUP), ('parent_id', LIVE)):
            row = copy.deepcopy(self.native.rows[OLD]); row[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): m.validate_confirmed(self.hub, row, b, h)
        other = copy.deepcopy(b); other['tasks'][TID]['reminder_id'] = OLD
        with self.assertRaises(ValueError): m.validate_confirmed(self.hub, self.native.rows[OLD], other, h)
        state_path = Path(plan['plan']).with_name('state.json'); state_path.write_text(state_path.read_text() + ' ')
        with self.assertRaises(ValueError): m.validate_confirmed(self.hub, self.native.rows[OLD], b, h)
    def test_confirmation_resumes_prepared_after_config_write_and_rejects_foreign_config(self):
        plan = self.preview(); original = m._write_state
        def fail_complete(path, state):
            if state['phase'] == 'complete': raise TimeoutError('after_config')
            return original(path, state)
        with patch.object(m, '_write_state', side_effect=fail_complete):
            with self.assertRaises(TimeoutError): self.apply(plan)
        self.assertIn(OLD, self.read()['projects']['demo']['history']); self.apply(plan)
        self.assertEqual(json.loads(Path(plan['plan']).with_name('state.json').read_text())['phase'], 'complete')
        self.config = self.read(); self.config['foreign'] = True; self.save()
        with self.assertRaises(ValueError): self.apply(plan)
    def test_missing_preview_is_read_only_and_apply_preserves_exact_history(self):
        self.historical(); prior = copy.deepcopy(self.config); raw = (self.hub / 'ai/reminders-sync.json').read_bytes()
        preview = self.missing(False); self.assertEqual(preview['items'][0]['action'], 'recurrence_history_missing')
        self.assertEqual((self.hub / 'ai/reminders-sync.json').read_bytes(), raw)
        self.assertFalse((self.hub / 'ai/reminders-recurrence').exists())
        result = self.missing(); row = result['config']['projects']['demo']['history'][OLD]
        row.pop('absence_receipt'); self.assertEqual(row, prior['projects']['demo']['history'][OLD])
        self.assertEqual(self.verified(), {OLD}); self.assertEqual(self.native.writes, [])
    def test_missing_refuses_incomplete_observation_and_reappearing_uuid(self):
        self.historical(); incomplete = self.observe(); incomplete['complete'] = False
        with self.assertRaises(ValueError): self.missing(observation=incomplete)
        self.missing(); self.native.rows[OLD] = dict(id=OLD, title='Вернулась', version=9, completed=True, list='Работа', list_id=LID)
        with self.assertRaisesRegex(ValueError, 'returned'): self.verified()
    def test_missing_receipt_requires_unchanged_scope_metadata_and_prior_history(self):
        self.historical(); self.missing(); saved = self.read()
        self.native.lists[0]['account_id'] = LIVE
        with self.assertRaises(ValueError): self.verified()
        self.native.lists[0]['account_id'] = ACCOUNT
        self.native.lists[0]['group_id'] = None
        with self.assertRaises(ValueError): self.verified()
        self.native.lists[0]['group_id'] = GROUP
        allow = self.hub / 'ai/reminders-allowlist.json'; allow.write_text(json.dumps({'names': []}))
        with self.assertRaises(ValueError): self.verified()
        allow.write_text(json.dumps({'names': ['Работа']})); self.config = saved
        self.config['projects']['demo']['history'][OLD]['arbitrary'] = 'altered'; self.save()
        with self.assertRaises(ValueError): self.verified()
    def test_missing_receipt_requires_exact_plan_and_state(self):
        self.historical(); self.missing(); ref = self.read()['projects']['demo']['history'][OLD]['absence_receipt']
        path = self.hub / ref['plan']; original = path.read_bytes(); path.write_bytes(original + b' ')
        with self.assertRaisesRegex(ValueError, 'checksum'): self.verified()
        path.write_bytes(original); state = path.with_name('state.json'); value = json.loads(state.read_text()); value['phase'] = 'prepared'; state.write_text(json.dumps(value))
        with self.assertRaises(ValueError): self.verified()
    def test_missing_apply_rechecks_snapshot_before_writing(self):
        self.historical(); observation = self.observe(); self.native.rows[LIVE]['version'] += 1
        with self.assertRaisesRegex(ValueError, 'snapshot'): self.missing(observation=observation)
        self.assertNotIn('absence_receipt', self.read()['projects']['demo']['history'][OLD])
    def test_missing_never_touches_archive_and_requires_receipt(self):
        self.historical(); self.config['projects']['demo']['archive'] = {'journal': 'historic'}; self.save()
        self.assertEqual(self.missing()['items'], []); self.assertEqual(self.verified(self.observe()), set())
        self.config['projects']['demo'].pop('archive'); self.save()
        with self.assertRaisesRegex(ValueError, 'receipt'): self.verified()
    def test_missing_allows_unrelated_group_move_but_guards_its_account_and_list(self):
        extra = str(uuid.UUID(int=9)); self.native.lists.append(dict(id=extra, name='Личное', account_id=ACCOUNT, group_id=GROUP))
        allow = self.hub / 'ai/reminders-allowlist.json'; allow.write_text(json.dumps({'names': ['Работа', 'Личное']}))
        self.historical(); self.missing(); self.native.lists[1]['group_id'] = None
        self.assertEqual(self.verified(), {OLD})
        self.native.lists[1]['account_id'] = LIVE
        with self.assertRaisesRegex(ValueError, 'metadata'): self.verified()
        self.native.lists.pop()
        with self.assertRaisesRegex(ValueError, 'metadata'): self.verified()
    def test_missing_project_filter_preserves_other_project_history(self):
        extra, live2, old2 = [str(uuid.UUID(int=i)) for i in (10, 11, 12)]
        self.native.lists.append(dict(id=extra, name='Личное', account_id=ACCOUNT, group_id=GROUP))
        self.native.rows[live2] = dict(id=live2, title='Серия 2', version=1, completed=False, repeat={'frequency': 'daily'}, list='Личное', list_id=extra)
        allow = self.hub / 'ai/reminders-allowlist.json'; allow.write_text(json.dumps({'names': ['Работа', 'Личное']}))
        other = copy.deepcopy(self.config['projects']['demo']); other.update(list_id=extra, list_name='Личное', tasks={'task2': {'reminder_id': live2}}, history={old2: dict(original_id=live2, task_id='task2', project_id='other')})
        self.config['projects']['other'] = other
        path = self.hub / 'projects/other'; path.mkdir()
        with (self.hub / 'ai/project-registry.md').open('a') as file: file.write(f'\n## other\nName: Другой\nStatus: active\nPath: {path}\n')
        self.historical(); before = copy.deepcopy(self.config['projects']['other'])
        result = m.prepare_missing(m.sync, self.hub, self.config, self.observe(), apply=True, native=self.native, project='demo')
        self.assertEqual(result['config']['projects']['other'], before)
        self.assertEqual({r['project'] for r in result['items']}, {'demo'})
        self.assertIn('absence_receipt', result['config']['projects']['demo']['history'][OLD])
    def test_missing_complete_snapshot_stores_all_lists_and_hashes(self):
        self.historical(); self.missing(); ref = self.read()['projects']['demo']['history'][OLD]['absence_receipt']
        plan = json.loads((self.hub / ref['plan']).read_text())
        self.assertEqual(set(plan['observation']['lists']), {LID})
        self.assertEqual(plan['snapshot_sha256'][LID], m._sha(m._encoded(plan['observation']['lists'][LID])))
        self.assertEqual(plan['items'][0]['prior_history'], self.config['projects']['demo']['history'][OLD])
        self.assertEqual(self.verified(self.observe()), {OLD})


if __name__ == '__main__': unittest.main()
