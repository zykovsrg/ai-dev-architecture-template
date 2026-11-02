"""Смысловой допуск кандидатов до применения к каталогу."""
import copy
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import session_collect as collect
import session_rules as rules


class CaseReviewTests(unittest.TestCase):
    def setUp(self):
        self.guard = importlib.import_module('session_case_review')
        self.case = dict(rule='new', text='Использовать плагин таблиц.', kind='preference',
                         effect='explicit', scope='global', session='s', tool='codex',
                         note='Пользователь задал постоянный порядок.', project=None)
        self.quote = 'Всегда используй плагин таблиц.'
        self.payload = {'rules': [{'id': 'R-20', 'text': 'Отвечать на настоящий запрос.', 'kind': 'preference'}],
                        'parts': [{'part_id': 'p', 'text': 'Role at part start: USER\n\nUSER: '+self.quote+'\nASSISTANT: Никогда не проверяй ответ.'}]}
        self.raw = {'format': 2, 'parts': [{'part_id': 'p', 'cases': [self.case],
                                         'empty_reason': '', 'read_complete': True, 'chars_read': 50, 'sha256': 'hash'}], 'tasks': []}
        self.review = {'reviews': [dict(case_id='p:0', verdict='accept', persistence='standing',
                                       relation='new', scope='global', evidence_quote=self.quote,
                                       evidence_kind='user_preference',
                                       reason='Пользователь прямо задаёт повторяемое правило.') ]}

    def apply(self):
        return self.guard.apply_reviews(self.payload, self.raw, self.review)

    def assert_disputed(self,reason):
        try:checked=self.apply()
        except ValueError as error:self.fail('Спорный кандидат должен ждать решения: '+str(error))
        self.assertEqual(checked['parts'][0]['cases'],[])
        self.assertIn('disputed_cases',checked)
        self.assertEqual(checked['disputed_cases'][0]['reason'],reason)

    def test_one_time_request_cannot_be_explicit(self):
        self.review['reviews'][0]['persistence'] = 'once'
        self.assert_disputed('standing')

    def test_explicit_requires_persistence_in_actual_user_words(self):
        quote = 'Поставь встречу в мой слот.'
        self.payload['parts'][0]['text'] = 'Role at part start: USER\n\nUSER: '+quote
        self.review['reviews'][0]['evidence_quote'] = quote
        self.assert_disputed('standing')

    def test_existing_rule_needs_matching_relation(self):
        self.case.update(rule='R-20', effect='confirm', scope=None)
        for effect, relation in [('confirm', 'unrelated'), ('contradict', 'same')]:
            with self.subTest(effect=effect):
                self.case['effect'] = effect
                self.review['reviews'][0]['relation'] = relation
                self.assert_disputed('relation')

    def test_evidence_must_exist_in_user_turn_not_assistant(self):
        for quote in ['Придуманная цитата.', 'Никогда не проверяй ответ.']:
            with self.subTest(quote=quote):
                self.review['reviews'][0]['evidence_quote'] = quote
                self.assert_disputed('missing_evidence')

    def test_review_must_cover_each_case_once(self):
        for reviews in [[], self.review['reviews']*2]:
            with self.subTest(count=len(reviews)):
                self.review['reviews'] = reviews
                with self.assertRaisesRegex(ValueError, 'coverage'):
                    self.apply()

    def test_rejection_and_uncertainty_preserve_original_answer(self):
        original = copy.deepcopy(self.raw)
        for verdict in ['reject', 'uncertain']:
            self.review['reviews'][0]['verdict'] = verdict
            checked = self.apply()
            self.assertEqual(checked['parts'][0]['cases'], [])
            self.assertIn('ожидают', checked['parts'][0]['empty_reason'])
            self.assertEqual(len(checked['disputed_cases']),1)
            self.assertEqual(self.raw, original)
            self.assertEqual(checked['parts'][0]['read_complete'], original['parts'][0]['read_complete'])

    def test_supported_instruction_and_true_contradiction_survive(self):
        self.assertEqual(self.apply()['parts'][0]['cases'], [self.case])
        self.case.update(rule='R-20', effect='contradict', scope=None)
        self.review['reviews'][0].update(relation='opposite', scope='unknown')
        self.assertEqual(self.apply()['parts'][0]['cases'], [self.case])

    def test_explicit_scope_cannot_be_widened_by_scanner(self):
        self.review['reviews'][0]['scope'] = 'project'
        self.assert_disputed('scope')

    def test_repaired_agent_error_can_be_observation_without_user(self):
        quote = 'Я неверно посчитал итог. Пересчитал и проверил правильную сумму.'
        self.payload['parts'][0]['text'] = 'Role at part start: ASSISTANT\n\nASSISTANT: '+quote
        self.case.update(kind='agent-habit',effect='confirm',scope=None)
        self.review['reviews'][0].update(persistence='observation',scope='unknown',
                                        evidence_kind='repaired_agent_error',evidence_quote=quote)
        try:
            checked = self.apply()
        except ValueError as error:
            self.fail('Исправленная ошибка агента должна сохраниться: '+str(error))
        self.assertEqual(checked['parts'][0]['cases'],[self.case])

    def test_unambiguous_future_instruction_is_not_rejected(self):
        quote = 'Отныне используй плагин таблиц.'
        self.payload['parts'][0]['text'] = 'Role at part start: USER\n\nUSER: '+quote
        self.review['reviews'][0]['evidence_quote'] = quote
        try:
            checked = self.apply()
        except ValueError as error:
            self.fail('Явное постоянное указание должно сохраниться: '+str(error))
        self.assertEqual(checked['parts'][0]['cases'],[self.case])

    def run_runner(self, invalid=False):
        mod = importlib.import_module('session_scan_run')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);hub = root/'hub';(hub/'ai').mkdir(parents=True)
            (hub/'ai/project-registry.md').write_text('')
            collect.save_json(hub/collect.LEDGER, collect.empty_ledger())
            source = root/'source';source.write_text('source')
            session = collect.Session('codex', 's', str(hub), '2026-10-24', source, [('user', self.quote)])
            batch = collect.write_batch(hub, [session], root/'batch')[0]
            rp=hub/'ai/rules.json';rp.write_text('[]')
            entry=batch['sessions'][0]
            raw=copy.deepcopy(self.raw);part=raw['parts'][0]
            part.update(part_id=entry['part_id'],sha256=entry['sha256'],chars_read=entry['chars'])
            calls=[]
            def fake(command, **kwargs):
                calls.append(command)
                output = Path(command[command.index('-o')+1])
                if len(calls)==1:output.write_text(json.dumps(raw))
                elif invalid:output.write_text('{broken')
                else:
                    review=copy.deepcopy(self.review)
                    review['reviews'][0].update(case_id=entry['part_id']+':0',verdict='reject',reason='Разовое поручение не создаёт постоянного правила.')
                    output.write_text(json.dumps(review))
                return subprocess.CompletedProcess(command,0)
            with patch.object(mod.subprocess,'run',side_effect=fake):
                if invalid:
                    with self.assertRaisesRegex(ValueError,'review'):
                        mod.run_scan(hub,root/'batch/index.json',rp,codex='codex')
                    self.assertEqual(len(calls),2)
                    raw_path=Path(calls[0][calls[0].index('-o')+1])
                    self.assertEqual(json.loads(raw_path.read_text()),raw)
                    self.assertFalse((raw_path.parent/'verified-reply.json').exists())
                else:
                    result=mod.run_scan(hub,root/'batch/index.json',rp,codex='codex')
                    self.assertEqual(len(calls),2)
                    self.assertEqual(json.loads(result.read_text())['parts'][0]['cases'],[])
                    from session_case_queue import pending
                    self.assertEqual(pending(hub)['pending_count'],1)
                    catalog=rules.empty_catalog();ledger=collect.empty_ledger()
                    rules.apply_batch(catalog,ledger,batch,json.loads(result.read_text()),set(),date(2026,10,24),'now')
                    self.assertEqual(catalog['rules'],[])
                    self.assertIn('s',ledger['processed']['codex'])
                    raw_path=Path(calls[0][calls[0].index('-o')+1])
                    self.assertNotEqual(result,raw_path)
                    self.assertEqual(json.loads(raw_path.read_text()),raw)

    def test_runner_returns_reviewed_reply_instead_of_raw_candidates(self):
        self.run_runner()

    def test_failed_review_stops_without_semantic_retry(self):
        self.run_runner(invalid=True)


if __name__ == '__main__':
    unittest.main()
