"""Проверки полного чтения, подтверждённого применения и точечного повтора."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import session_collect as collect
import session_rules as rules


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.hub = self.root / 'hub'
        (self.hub / 'ai').mkdir(parents=True)
        (self.hub / 'ai/project-registry.md').write_text('')
        self.ledger = collect.empty_ledger()
        self.ledger['cutover'] = '2026-10-01'
        self.catalog = rules.empty_catalog()
        (self.hub / 'ai/rules.json').write_text('[]')
        self.source = self.root / 'source.jsonl'
        self.source.write_text('source')
        self.session = collect.Session('codex', 's', str(self.hub), '2026-10-18', self.source,
                                       [('user', 'Начало ' + 'я' * 70000 + ' середина ' + 'б' * 70000 + ' конец')])

    def batch(self, session=None):
        collect.save_json(self.hub / collect.LEDGER, self.ledger)
        return collect.write_batch(self.hub, [session or self.session], self.root / 'batch')[0]

    def reply(self, batch, cases=None):
        return {'format': 2, 'parts': [dict(part_id=e['part_id'], sha256=e['sha256'],
                    read_complete=True, chars_read=e['chars'], empty_reason='Нет новых наблюдений.',
                    cases=copy.deepcopy(cases or [])) for e in batch['sessions']], 'tasks': []}

    def apply(self, batch, reply):
        return rules.apply_batch(self.catalog, self.ledger, batch, reply, set(), date(2026, 10, 19), 'now')

    def case(self):
        return dict(rule='new', text='Показывать сначала результат проверки.', kind='preference',
                    effect='explicit', scope='global', tool='codex', session='s', note='Пользователь попросил менять порядок ответа.')

    def test_service_sources_are_excluded(self):
        for source in ({'subagent': {'other': 'guardian'}}, {'subagent': 'thread_spawn'}, 'vscode'):
            self.source.write_text(json.dumps({'type': 'session_meta', 'payload': {
                'id': 's', 'cwd': str(self.hub), 'timestamp': '2026-10-18', 'source': source}}) + '\n')
            parsed = collect.parse_codex(self.source)
            self.assertEqual(parsed is None, source != 'vscode')

    def test_parts_preserve_every_character_of_long_user_turn(self):
        collected = []
        for _ in range(20):
            batch = self.batch()
            if not batch['sessions']:
                break
            collected.extend(Path(e['file']).read_text().split('\n\n', 1)[1] for e in batch['sessions'])
            self.apply(batch, self.reply(batch))
        self.assertEqual(''.join(collected), 'USER: ' + self.session.turns[0][1])
        self.assertIn('s', self.ledger['processed']['codex'])

    def test_legacy_reply_cannot_complete_new_batch(self):
        batch = self.batch()
        before = copy.deepcopy(self.ledger)
        with self.assertRaisesRegex(ValueError, 'coverage|protocol|format'):
            self.apply(batch, [])
        self.assertEqual(self.ledger, before)

    def test_incomplete_or_empty_unconfirmed_part_is_rejected(self):
        batch = self.batch()
        reply = self.reply(batch)
        for field, value in [('read_complete', False), ('chars_read', 1), ('empty_reason', '')]:
            bad = copy.deepcopy(reply)
            bad['parts'][0][field] = value
            with self.assertRaises(ValueError, msg=field):
                self.apply(batch, bad)
        for parts in ([], reply['parts'] + reply['parts']):
            with self.assertRaises(ValueError):
                self.apply(batch, dict(reply, parts=parts))
        self.assertEqual(self.ledger['processed']['codex'], [])

    def test_changed_or_missing_source_and_part_stop_apply(self):
        batch = self.batch()
        reply = self.reply(batch)
        self.source.write_text('changed')
        with self.assertRaises(ValueError):
            self.apply(batch, reply)
        self.source.unlink()
        with self.assertRaises(ValueError):
            self.apply(batch, reply)
        self.source.write_text('source')
        part = Path(batch['sessions'][0]['file'])
        body = part.read_text()
        part.write_text(body + 'changed')
        with self.assertRaises(ValueError):
            self.apply(batch, reply)
        part.unlink()
        with self.assertRaises(ValueError):
            self.apply(batch, reply)
        self.assertEqual(self.catalog['rules'], [])

    def test_partial_progress_and_idempotent_resume(self):
        batch = self.batch()
        reply = self.reply(batch, [self.case()])
        self.apply(batch, reply)
        self.assertNotIn('s', self.ledger['processed']['codex'])
        self.apply(batch, reply)
        self.assertEqual(len(self.catalog['rules']), 1)
        self.assertEqual(len(self.catalog['rules'][0]['cases']), 1)
        later = self.batch()
        self.assertNotEqual(later['sessions'][0]['part_id'], batch['sessions'][0]['part_id'])
        self.apply(later, self.reply(later, [self.case()]))
        self.assertEqual(len(self.catalog['rules'][0]['cases']), 1)

    def test_replay_selects_only_named_processed_source_once(self):
        codex = self.root / 'codex'
        codex.mkdir()
        self.source = codex / 's.jsonl'
        self.source.write_text(json.dumps({'type': 'session_meta', 'payload': {
            'id': 's', 'cwd': str(self.hub), 'timestamp': '2026-10-18', 'source': 'vscode'}}) + '\n' +
            json.dumps({'type': 'response_item', 'payload': {'type': 'message', 'role': 'user',
                'content': [{'text': 'Предпочтение.'}]}}) + '\n')
        os.utime(self.source, (1, 1))
        self.ledger['processed']['codex'] = ['s', 'other']
        self.assertEqual(collect.pending(self.hub, self.ledger, datetime.now(timezone.utc), self.root/'claude', codex), [])
        self.assertIn('replay', __import__('inspect').signature(collect.pending).parameters)
        try:
            selected = collect.pending(self.hub, self.ledger, datetime.now(timezone.utc), self.root/'claude', codex,
                                       replay={('codex', 's')})
        except ValueError as error:
            self.fail('valid processed source must remain available to replay: ' + str(error))
        self.assertEqual([s.id for s in selected], ['s'])
        batch = self.batch(selected[0])
        self.apply(batch, self.reply(batch))
        self.assertEqual(collect.pending(self.hub, self.ledger, datetime.now(timezone.utc), self.root/'claude', codex,
                                        replay={('codex', 's')}), [])
        self.assertEqual(self.ledger['processed']['codex'], ['s', 'other'])

    def test_replay_does_not_duplicate_old_catalog_case(self):
        old_batch = {'sessions': [dict(tool='codex', id='s', project='hub', date='2026-10-18')]}
        self.apply(old_batch, [self.case()])
        self.session.turns = [('user', 'Предпочтение.')]
        batch = self.batch()
        self.apply(batch, self.reply(batch, [self.case()]))
        self.assertEqual(len(self.catalog['rules']), 1)
        self.assertEqual(len(self.catalog['rules'][0]['cases']), 1)

    def test_budget_change_keeps_continuation_boundaries(self):
        collect.save_json(self.hub / collect.LEDGER, self.ledger)
        batch = collect.write_batch(self.hub, [self.session], self.root/'batch', max_chars=8000)[0]
        first = Path(batch['sessions'][0]['file']).read_text().split('\n\n', 1)[1]
        self.apply(batch, self.reply(batch))
        later = self.batch()
        second = Path(later['sessions'][0]['file']).read_text().split('\n\n', 1)[1]
        self.assertEqual(first + second, ('USER: ' + self.session.turns[0][1])[:len(first)+len(second)])
        self.assertNotEqual(first, second)

    def test_malformed_transcript_cannot_become_successful_empty_read(self):
        self.source.write_text(json.dumps({'type': 'session_meta', 'payload': {
            'id': 's', 'source': 'vscode'}}) + '\n{broken json\n')
        with self.assertRaises(ValueError):
            collect.parse_codex(self.source)

    def test_user_xml_message_is_not_mistaken_for_environment(self):
        text = '<request>Всегда показывай результат первым.</request>'
        self.source.write_text(json.dumps({'type': 'session_meta', 'payload': {
            'id': 's', 'source': 'vscode'}}) + '\n' + json.dumps({'type': 'response_item', 'payload': {
            'type': 'message', 'role': 'user', 'content': [{'text': text}]}}) + '\n')
        self.assertIn(('user', text), collect.parse_codex(self.source).turns)

    def test_installed_contract_uses_verified_external_reply(self):
        root = SCRIPTS.parent
        skill = (root/'skills/hub-session-scan/SKILL.md').read_text()
        scanner = (root/'skills/hub-session-scan/resources/scanner.md').read_text()
        manifest = (root/'module.md').read_text()
        self.assertIn('session_scan_run.py', skill)
        self.assertIn('session_scan_run.py -> scripts/session_scan_run.py', manifest)
        self.assertIn('read_complete', scanner)
        self.assertIn('chars_read', scanner)
        self.assertNotIn('передайте ошибку сканеру', skill)
        self.assertNotIn('записанный по переданному пути', scanner)

    def test_new_turns_in_completed_session_become_pending(self):
        codex = self.root/'codex'
        codex.mkdir()
        self.source = codex/'s.jsonl'
        header = json.dumps({'type': 'session_meta', 'payload': {'id': 's', 'cwd': str(self.hub),
                            'timestamp': '2026-10-18', 'source': 'vscode'}}) + '\n'
        def turn(text):
            return json.dumps({'type': 'response_item', 'payload': {'type': 'message', 'role': 'user',
                              'content': [{'text': text}]}}) + '\n'
        self.source.write_text(header + turn('Первое предпочтение.'))
        os.utime(self.source, (1, 1))
        def pending():
            return collect.pending(self.hub, self.ledger, datetime.now(timezone.utc), self.root/'claude', codex)
        initial = self.batch(pending()[0])
        self.apply(initial, self.reply(initial, [self.case()]))
        self.assertEqual(pending(), [])
        self.source.write_text(self.source.read_text() + turn('Новое предпочтение.'))
        os.utime(self.source, (1, 1))
        resumed = pending()
        self.assertEqual([s.id for s in resumed], ['s'])
        batch = self.batch(resumed[0])
        self.apply(batch, self.reply(batch, [self.case()]))
        self.assertEqual(len(self.catalog['rules'][0]['cases']), 1)
        self.assertEqual(pending(), [])

    def test_continuation_identifies_user_role_at_start(self):
        batch = self.batch()
        self.apply(batch, self.reply(batch))
        later = self.batch()
        header = Path(later['sessions'][0]['file']).read_text().split('\n\n', 1)[0]
        self.assertIn('Role at part start: USER', header)

    def test_same_session_can_confirm_rule_for_two_projects(self):
        batch = self.batch()
        cases = [dict(self.case(), project=pid) for pid in ('first', 'second')]
        rules.apply_batch(self.catalog, self.ledger, batch, self.reply(batch, cases), {'first', 'second'},
                          date(2026, 10, 19), 'now')
        self.assertEqual({c['project'] for c in self.catalog['rules'][0]['cases']}, {'first', 'second'})

    def test_replay_does_not_duplicate_moved_rule_leak(self):
        old = {'sessions': [dict(tool='codex', id='older', project='hub', date='2026-10-18')]}
        self.apply(old, [dict(self.case(), session='older')])
        rules.retire(self.catalog, 'R-1', date(2026, 10, 19), 'moved to ai/skills/example.md')
        batch = self.batch()
        self.apply(batch, self.reply(batch, [self.case()]))
        self.ledger.pop('parts')  # Simulate catalog saved before a crash prevented ledger persistence.
        self.apply(batch, self.reply(batch, [self.case()]))
        self.assertEqual(len([c for c in self.catalog['rules'][0]['cases'] if c['effect'] == 'leak']), 1)

    def test_duplicate_case_still_requires_valid_scope(self):
        batch = self.batch()
        self.apply(batch, self.reply(batch, [self.case()]))
        self.ledger.pop('parts')
        with self.assertRaisesRegex(ValueError, 'scope'):
            self.apply(batch, self.reply(batch, [dict(self.case(), scope='invalid')]))

    def test_cli_refuses_downgraded_and_unverifiable_legacy_batch(self):
        batch = self.batch()
        batch_path = self.root/'batch/index.json'
        cases_path = self.root/'reply.json'
        cases_path.write_text('[]')
        for broken in (dict(sessions=batch['sessions']), {'sessions': [
                       dict(tool='codex', id='s', project='hub', date='2026-10-18')]}):
            batch_path.write_text(json.dumps(broken))
            done = subprocess.run([sys.executable, str(SCRIPTS/'session_rules.py'), '--hub', str(self.hub),
                                   'apply', '--batch', str(batch_path), '--cases', str(cases_path)],
                                   capture_output=True, text=True)
            self.assertEqual(done.returncode, 1)
            self.assertIn('rebuild', done.stderr)
            self.assertNotIn('s', collect.load_ledger(self.hub)['processed']['codex'])
        with self.assertRaisesRegex(ValueError, 'protocol|format|rebuild'):
            self.apply(dict(sessions=batch['sessions']), [])

    def test_replay_does_not_read_unselected_transcript_body(self):
        codex = self.root/'codex'
        codex.mkdir()
        target = codex/'s.jsonl'
        target.write_text(json.dumps({'type': 'session_meta', 'payload': {'id': 's', 'cwd': str(self.hub),
                          'timestamp': '2026-10-18', 'source': 'vscode'}}) + '\n')
        unrelated = codex/'z.jsonl'
        unrelated.write_text('{broken')
        for path in (target, unrelated):
            os.utime(path, (1, 1))
        original = Path.read_bytes
        full_reads = []
        def tracked(path):
            full_reads.append(path)
            return original(path)
        try:
            with patch.object(Path, 'read_bytes', tracked):
                selected = collect.pending(self.hub, self.ledger, datetime.now(timezone.utc),
                                           self.root/'claude', codex, replay={('codex', 's')})
        except ValueError as error:
            self.fail('unrelated transcript blocked replay: ' + str(error))
        self.assertEqual([s.id for s in selected], ['s'])
        self.assertNotIn(unrelated, full_reads)

    def test_source_digest_remains_bound_to_parsed_snapshot(self):
        codex = self.root/'codex'
        codex.mkdir()
        target = codex/'s.jsonl'
        target.write_text(json.dumps({'type': 'session_meta', 'payload': {'id': 's', 'cwd': str(self.hub),
                          'timestamp': '2026-10-18', 'source': 'vscode'}}) + '\n')
        os.utime(target, (1, 1))
        original = collect.source_hash
        appended = []
        def grow(session):
            if not appended:
                with target.open('a') as handle:
                    handle.write(json.dumps({'type': 'response_item', 'payload': {'type': 'message', 'role': 'user',
                                 'content': [{'text': 'Новое предпочтение после чтения.'}]}}) + '\n')
                appended.append(True)
            return original(session)
        with patch.object(collect, 'source_hash', side_effect=grow):
            selected = collect.pending(self.hub, self.ledger, datetime.now(timezone.utc), self.root/'claude', codex)
            with self.assertRaisesRegex(ValueError, 'source changed'):
                self.batch(selected[0])
        self.assertEqual(self.ledger['processed']['codex'], [])

    def test_codex_only_replay_does_not_read_extra_sources(self):
        journal = self.hub/'ai/workflow-observations.md'
        journal.write_text('- 2026-10-18 | test | friction | Наблюдение.\n')
        original = Path.read_text
        original_raw = Path.read_bytes
        def guarded_raw(path):
            if path == journal:
                self.fail('codex-only replay read journal bytes')
            return original_raw(path)
        def guarded(path, *args, **kwargs):
            if path == journal:
                self.fail('codex-only replay read the journal')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', guarded), patch.object(Path, 'read_bytes', guarded_raw):
            self.assertEqual(collect.extra_sources(self.hub, self.ledger, replay={('codex', 's')}), [])

    def test_observation_replay_does_not_read_unselected_reviews(self):
        journal = self.hub/'ai/workflow-observations.md'
        journal.write_text('- 2026-10-18 | test | friction | Наблюдение.\n')
        project = self.hub/'projects/demo'
        review = project/'ai/session-reviews/2026-10-18-test.md'
        review.parent.mkdir(parents=True)
        review.write_text('## Findings\nНевыбранный текст.\n')
        (self.hub/'ai/project-registry.md').write_text(f'## demo\nStatus: active\nPath: {project}\n')
        original = Path.read_text
        original_raw = Path.read_bytes
        def guarded_raw(path):
            if path == review:
                self.fail('observation replay read unselected review bytes')
            return original_raw(path)
        def guarded(path, *args, **kwargs):
            if path == review:
                self.fail('observation replay read an unselected review')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', guarded), patch.object(Path, 'read_bytes', guarded_raw):
            selected = collect.extra_sources(self.hub, self.ledger, replay={('codex', 's'), ('claude', 'obs-1')})
        self.assertEqual([s.id for s in selected], ['obs-1'])
        # Selecting a review still works and must not read the unselected journal.
        def review_only_raw(path):
            if path == journal:
                self.fail('review-only replay read journal bytes')
            return original_raw(path)
        def review_only(path, *args, **kwargs):
            if path == journal:
                self.fail('review-only replay read the journal')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', review_only), patch.object(Path, 'read_bytes', review_only_raw):
            selected = collect.extra_sources(self.hub, self.ledger, replay={('claude', 'review-demo-2026-10-18-test')})
        self.assertEqual([s.id for s in selected], ['review-demo-2026-10-18-test'])

    def snapshot_race(self, source, replacement, selected):
        original_text, original_bytes = Path.read_text, Path.read_bytes
        changed = []
        def change_after_read(path, body):
            if path == source and not changed:
                source.write_text(replacement)
                changed.append(True)
            return body
        def text(path, *args, **kwargs):
            return change_after_read(path, original_text(path, *args, **kwargs))
        def raw(path):
            return change_after_read(path, original_bytes(path))
        with patch.object(Path, 'read_text', text), patch.object(Path, 'read_bytes', raw):
            with self.assertRaisesRegex(ValueError, 'source changed'):
                sessions = collect.extra_sources(self.hub, self.ledger, replay=selected)
                self.batch(sessions[0])
        self.assertEqual(self.ledger['processed']['claude'], [])

    def test_observation_digest_matches_the_read_snapshot(self):
        journal = self.hub/'ai/workflow-observations.md'
        journal.write_text('- 2026-10-18 | test | friction | OLD\n')
        self.snapshot_race(journal, '- 2026-10-18 | test | friction | NEW\n', {('claude', 'obs-1')})

    def test_review_digest_matches_the_read_snapshot(self):
        project = self.hub/'projects/demo'
        review = project/'ai/session-reviews/2026-10-18-test.md'
        review.parent.mkdir(parents=True)
        review.write_text('## Findings\nOLD\n')
        (self.hub/'ai/project-registry.md').write_text(f'## demo\nStatus: active\nPath: {project}\n')
        self.snapshot_race(review, '## Findings\nNEW\n', {('claude', 'review-demo-2026-10-18-test')})

    def test_replay_cli_never_reports_missing_corrupt_or_active_source_as_done(self):
        codex = self.root/'codex'
        codex.mkdir()
        target = codex/'s.jsonl'
        collect.save_json(self.hub/collect.LEDGER, self.ledger)
        command = [sys.executable, str(SCRIPTS/'session_collect.py'), '--hub', str(self.hub),
                   '--claude-root', str(self.root/'claude'), '--codex-root', str(codex),
                   'batch', '--out-dir', str(self.root/'batch'), '--replay', 'codex:s']
        def check_rejected(reason):
            done = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(done.returncode, 1, done.stdout)
            self.assertNotIn('"written": 0', done.stdout)
            self.assertIn('ERROR:', done.stderr)
            self.assertIn(reason, done.stderr)
        check_rejected('unavailable')  # Missing file.
        target.write_text('{broken')
        os.utime(target, (1, 1))
        check_rejected('unavailable')  # Corrupt header.
        target.write_text(json.dumps({'type': 'session_meta', 'payload': {'id': 's', 'cwd': str(self.hub),
                          'timestamp': '2026-10-18', 'source': 'vscode'}}) + '\n')
        check_rejected('active')  # The selected file is still active.
        os.utime(target, (1, 1))
        (self.hub/'ai/workflow-observations.md').write_text('- 2026-10-18 | test | friction | Наблюдение.\n')
        done = subprocess.run(command + ['--replay', 'claude:obs-1'], text=True, capture_output=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout)['written'], 2)

    def test_replay_missing_extra_key_is_not_silently_completed(self):
        journal = self.hub/'ai/workflow-observations.md'
        journal.write_text('- 2026-10-18 | test | friction | Наблюдение.\n')
        for selected in ({('claude', 'obs-99')}, {('claude', 'review-demo-missing')},
                         {('claude', 'obs-1'), ('claude', 'obs-99'), ('codex', 's')}):
            with self.assertRaisesRegex(ValueError, 'replay|source|selected'):
                collect.extra_sources(self.hub, self.ledger, replay=selected)

    def runner(self):
        path = SCRIPTS / 'session_scan_run.py'
        self.assertTrue(path.exists(), 'нужен исполняемый проверяющий запуск')
        spec = importlib.util.spec_from_file_location('session_scan_run', path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_runner_preserves_invalid_answer_without_semantic_retry(self):
        mod = self.runner()
        batch = self.batch()
        called = []
        def fake(command, **kwargs):
            called.append(command)
            Path(command[command.index('-o')+1]).write_text('Найдено правило\n[]')
            return subprocess.CompletedProcess(command, 0, '', '')
        with patch.object(mod.subprocess, 'run', side_effect=fake):
            with self.assertRaises(ValueError):
                mod.run_scan(self.hub, self.root/'batch/index.json', self.hub/'ai/rules.json', codex='codex')
        self.assertEqual(len(called), 1)
        raw = Path(called[0][called[0].index('-o')+1])
        self.assertFalse(collect._inside(raw, self.hub))
        self.assertEqual(raw.read_text(), 'Найдено правило\n[]')

    def test_runner_uses_readonly_luna_and_checks_success(self):
        mod = self.runner()
        batch = self.batch()
        commands = []
        def fake(command, **kwargs):
            commands.append(command)
            Path(command[command.index('-o')+1]).write_text(json.dumps(self.reply(batch)))
            return subprocess.CompletedProcess(command, 0, '', '')
        with patch.object(mod.subprocess, 'run', side_effect=fake):
            result = mod.run_scan(self.hub, self.root/'batch/index.json', self.hub/'ai/rules.json', codex='codex')
        self.assertTrue(Path(result).is_file())
        command = commands[0]
        self.assertEqual(command[command.index('-m')+1], 'gpt-6-luna')
        self.assertEqual(command[command.index('-s')+1], 'read-only')
        self.assertIn('model_reasoning_effort=low', command)
        self.assertIn('--ephemeral', command)

    def test_runner_passes_full_inputs_via_stdin(self):
        mod = self.runner()
        batch = self.batch()
        calls = []
        def fake(command, **kwargs):
            calls.append((command, kwargs))
            Path(command[command.index('-o')+1]).write_text(json.dumps(self.reply(batch)))
            return subprocess.CompletedProcess(command, 0, '', '')
        with patch.object(mod.subprocess, 'run', side_effect=fake):
            mod.run_scan(self.hub, self.root/'batch/index.json', self.hub/'ai/rules.json', codex='codex')
        command, kwargs = calls[0]
        self.assertIn('input', kwargs)
        for entry in batch['sessions']:
            self.assertIn(json.dumps(Path(entry['file']).read_text(), ensure_ascii=False), kwargs['input'])
        self.assertNotIn(self.session.turns[0][1][:1000], ' '.join(command))
        self.assertFalse(collect._inside(Path(command[command.index('-C')+1]), self.hub))

    def test_runner_constrains_reply_shape_without_forcing_read_success(self):
        mod = self.runner()
        batch = self.batch()
        schemas = []
        def fake(command, **kwargs):
            self.assertIn('--output-schema', command)
            schema_path = Path(command[command.index('--output-schema') + 1])
            self.assertFalse(collect._inside(schema_path, self.hub))
            schema = json.loads(schema_path.read_text())
            schemas.append(schema)
            self.assertFalse(schema['additionalProperties'])
            parts = schema['properties']['parts']
            self.assertEqual(parts['minItems'], len(batch['sessions']))
            self.assertEqual(parts['maxItems'], len(batch['sessions']))
            fields = parts['items']['properties']
            self.assertEqual(fields['part_id']['enum'], [e['part_id'] for e in batch['sessions']])
            self.assertEqual(fields['read_complete'], {'type': 'boolean'})
            self.assertEqual(fields['chars_read'], {'type': 'integer'})
            self.assertEqual(fields['cases']['type'], 'array')
            Path(command[command.index('-o')+1]).write_text(json.dumps(self.reply(batch)))
            return subprocess.CompletedProcess(command, 0)
        with patch.object(mod.subprocess, 'run', side_effect=fake):
            mod.run_scan(self.hub, self.root/'batch/index.json', self.hub/'ai/rules.json', codex='codex')
        self.assertEqual(len(schemas), 1)

    def test_runner_failed_process_never_returns_success(self):
        mod = self.runner()
        self.batch()
        with patch.object(mod.subprocess, 'run', return_value=subprocess.CompletedProcess([], 7)):
            with self.assertRaisesRegex(ValueError, 'model failed'):
                mod.run_scan(self.hub, self.root/'batch/index.json', self.hub/'ai/rules.json', codex='codex')

    def test_invalid_later_case_does_not_commit_part_progress(self):
        batch = self.batch()
        reply = self.reply(batch, [dict(self.case(), rule='R-missing')])
        before = copy.deepcopy(self.ledger)
        with self.assertRaisesRegex(ValueError, 'unknown rule'):
            self.apply(batch, reply)
        self.assertEqual(self.ledger, before)
        self.assertEqual(self.catalog['rules'], [])


if __name__ == '__main__':
    unittest.main()
