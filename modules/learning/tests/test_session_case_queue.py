"""Спорные случаи ждут отдельного решения, не меняя действующие правила."""
import copy
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import session_rules as rules


class CaseQueueTests(unittest.TestCase):
    def setUp(self):
        self.queue=importlib.import_module('session_case_queue')
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.hub=Path(self.tmp.name);(self.hub/'ai').mkdir()
        (self.hub/'ai/project-registry.md').write_text('')
        rules.save_json(self.hub/rules.CATALOG,rules.empty_catalog())
        self.batch={'sessions':[dict(part_id='p',tool='codex',id='s',date='2026-10-24',project='hub',source_sha256='a'*64)]}
        self.item=dict(case_id='p:0',part_id='p',text='Использовать плагин таблиц.',kind='preference',
                       rule='new',original_effect='explicit',project=None,scope='global',reason='review_reject')

    def enqueue(self,items=None):
        return self.queue.enqueue(self.hub,self.batch,items or [self.item])

    def catalog(self):
        return rules.load_catalog(self.hub)

    def test_pending_is_durable_without_rule_or_transcript(self):
        self.item['evidence_quote']='СЫРАЯ РЕПЛИКА';self.item['note']='НЕ ПЕРЕНОСИТЬ ЗАМЕТКУ'
        self.enqueue();pending=self.queue.pending(self.hub)
        self.assertEqual(pending['pending_count'],1)
        self.assertEqual(pending['item']['text'],self.item['text'])
        self.assertIn(self.item['text'],pending['question'])
        self.assertTrue(pending['question'].endswith('Сохранить это как постоянное правило?'))
        self.assertEqual(self.catalog()['rules'],[])
        data=(self.hub/self.queue.QUEUE).read_text()
        self.assertNotIn('СЫРАЯ РЕПЛИКА',data);self.assertNotIn('НЕ ПЕРЕНОСИТЬ',data)

    def test_repeated_source_does_not_duplicate_or_reopen_decision(self):
        self.enqueue();self.enqueue();item=self.queue.pending(self.hub)['item']
        self.assertEqual(self.queue.pending(self.hub)['pending_count'],1)
        self.queue.resolve(self.hub,item['id'],'reject')
        self.enqueue()
        self.assertEqual(self.queue.pending(self.hub)['pending_count'],0)

    def test_accept_confirms_only_selected_text_as_user_instruction(self):
        other=dict(self.item,case_id='p:1',text='Показывать итог проверки.')
        self.enqueue([self.item,other]);item=self.queue.pending(self.hub)['item']
        result=self.queue.resolve(self.hub,item['id'],'accept')
        self.assertEqual(result['status'],'accepted')
        cat=self.catalog();self.assertEqual(len(cat['rules']),1)
        self.assertEqual(cat['rules'][0]['text'],self.item['text'])
        self.assertEqual(cat['rules'][0]['cases'][0]['effect'],'explicit')
        self.assertEqual(cat['rules'][0]['cases'][0]['tool'],'user')
        self.assertEqual(self.queue.pending(self.hub)['pending_count'],1)
        self.assertIn(self.item['text'],(self.hub/'ai/learned-rules.md').read_text())
        self.assertFalse((self.hub/'ai/learning/scan-ledger.json').exists())

    def test_reject_preserves_catalog_and_decision_history(self):
        self.enqueue();item=self.queue.pending(self.hub)['item'];before=(self.hub/rules.CATALOG).read_bytes()
        result=self.queue.resolve(self.hub,item['id'],'reject')
        self.assertEqual(result['status'],'rejected');self.assertEqual(self.queue.pending(self.hub)['pending_count'],0)
        self.assertEqual((self.hub/rules.CATALOG).read_bytes(),before)
        stored=json.loads((self.hub/self.queue.QUEUE).read_text())['items'][0]
        self.assertEqual([h['event'] for h in stored['history']],['pending','rejected'])

    def test_retry_after_render_failure_never_duplicates_confirmation(self):
        self.enqueue();item=self.queue.pending(self.hub)['item']
        with patch.object(rules,'write_render',side_effect=OSError('render unavailable')):
            with self.assertRaisesRegex(OSError,'render unavailable'):
                self.queue.resolve(self.hub,item['id'],'accept')
        self.assertEqual(self.queue.pending(self.hub)['pending_count'],1)
        self.queue.resolve(self.hub,item['id'],'accept')
        self.queue.resolve(self.hub,item['id'],'accept')
        self.assertEqual(len(self.catalog()['rules']),1)
        self.assertEqual(len(self.catalog()['rules'][0]['cases']),1)
        self.assertEqual(self.queue.pending(self.hub)['pending_count'],0)

    def test_unsafe_text_or_symlink_cannot_write_queue(self):
        self.item['text']='Написать на person@example.org'
        with self.assertRaises(ValueError):self.enqueue()
        self.assertFalse((self.hub/self.queue.QUEUE).exists())
        self.item['text']='Использовать плагин таблиц.'
        path=self.hub/self.queue.QUEUE;path.parent.mkdir(exist_ok=True)
        outside=self.hub/'outside';outside.write_text('KEEP');path.symlink_to(outside)
        with self.assertRaises(ValueError):self.enqueue()
        self.assertEqual(outside.read_text(),'KEEP')

    def test_accept_existing_rule_does_not_apply_false_contradiction(self):
        cat=rules.empty_catalog();cat['next_id']=2
        cat['rules']=[dict(id='R-1',text=self.item['text'],kind='preference',status='active',
                          merged_into=None,explicit_scope='global',created='2026-10-24',cases=[],history=[])]
        rules.save_json(self.hub/rules.CATALOG,cat)
        self.item.update(rule='R-1',original_effect='contradict');self.enqueue()
        self.queue.resolve(self.hub,self.queue.pending(self.hub)['item']['id'],'accept')
        self.assertEqual(len(self.catalog()['rules']),1)
        self.assertEqual([c['effect'] for c in self.catalog()['rules'][0]['cases']],['explicit'])

    def test_user_confirmation_is_not_hidden_by_old_model_score(self):
        cat=rules.empty_catalog();cat['next_id']=2
        cat['rules']=[dict(id='R-1',text=self.item['text'],kind='preference',status='active',
                          merged_into=None,explicit_scope='global',created='2026-10-24',history=[],
                          cases=[dict(effect='contradict',tool='codex',session='old',date='2026-10-24',project='hub',note='Прежняя оценка.')])]
        rules.save_json(self.hub/rules.CATALOG,cat);self.item['rule']='R-1';self.enqueue()
        self.queue.resolve(self.hub,self.queue.pending(self.hub)['item']['id'],'accept')
        self.assertIn(self.item['text'],(self.hub/'ai/learned-rules.md').read_text())
        self.assertEqual(self.catalog()['rules'][0]['cases'][0]['effect'],'contradict')

    def test_reordering_candidate_does_not_duplicate_or_reopen_it(self):
        self.enqueue();item=self.queue.pending(self.hub)['item']
        self.item['case_id']='p:1';self.enqueue()
        self.assertEqual(self.queue.pending(self.hub)['pending_count'],1)
        self.queue.resolve(self.hub,item['id'],'reject')
        self.item['case_id']='p:2';self.enqueue()
        self.assertEqual(self.queue.pending(self.hub)['pending_count'],0)

    def test_project_confirmation_does_not_promote_old_mixed_project_rule(self):
        for pid in ['p1','p2']:
            root=self.hub/'projects'/pid;root.mkdir(parents=True)
            with (self.hub/'ai/project-registry.md').open('a') as f:
                f.write(f'## {pid}\nStatus: active\nPath: {root}\n')
        cat=rules.empty_catalog();cat['next_id']=2
        cat['rules']=[dict(id='R-1',text=self.item['text'],kind='preference',status='active',
                          merged_into=None,explicit_scope=None,created='2026-10-24',history=[],
                          cases=[dict(effect='confirm',tool='codex',session=p,date='2026-10-24',project=p,note='Прежнее наблюдение.') for p in ['p1','p2']])]
        original=copy.deepcopy(cat['rules'][0]);rules.save_json(self.hub/rules.CATALOG,cat)
        self.item.update(rule='R-1',scope='project',project='p1');self.enqueue()
        self.queue.resolve(self.hub,self.queue.pending(self.hub)['item']['id'],'accept')
        self.assertNotIn(self.item['text'],(self.hub/'ai/learned-rules.md').read_text())
        self.assertIn(self.item['text'],(self.hub/'ai/learned-rules/p1.md').read_text())
        self.assertFalse((self.hub/'ai/learned-rules/p2.md').exists())
        self.assertEqual(self.catalog()['rules'][0],original)


if __name__=='__main__':unittest.main()
