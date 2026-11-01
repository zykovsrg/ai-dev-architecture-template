"""Большие планы: сжатие без потери точных проекций и границы распаковки."""
import base64
import json
from pathlib import Path
from unittest.mock import patch
import zlib
import test_reminders_external_retirement as base

m = base.m

class PlanSizeTests(base.ExternalRetirementTests):
    def large(self):
        self.config['padding'] = 'я' * 280_000
        self.save()
        p = self.paths['future']
        p.write_text(p.read_text() + '\n' + 'Контекст большого проекта. ' * 22_000)
        return self.prepare()

    def test_large_plan_apply_and_receipt_preserve_exact_history(self):
        p = self.large()
        disk = json.loads(Path(p['plan']).read_bytes())
        self.assertEqual(disk['version'], 3)
        self.assertLessEqual(Path(p['plan']).stat().st_size, 2_097_152)
        _, plan, _ = m.read(p['plan'], p['sha256'])
        self.assertEqual(plan['config_raw'].encode(), (self.hub/'ai/reminders-sync.json').read_bytes())
        self.assertEqual(plan['projects']['demo']['before_texts']['future'], self.paths['future'].read_text())
        self.apply(p)
        self.assertTrue(self.verify())
        self.assertEqual(self.paths['future'].read_text().count('Контекст большого проекта.'), 22_000)
        self.assertEqual(self.native.writes, [])

    def rewrite(self, p, value):
        path = Path(p['plan']); m.cancel.durable_json(path, value)
        digest = m.cancel.digest(path.read_bytes())
        state = json.loads(path.with_name('state.json').read_bytes());state['sha256'] = digest
        m.cancel.durable_json(path.with_name('state.json'), state)
        return dict(plan=str(path), sha256=digest)

    def test_decompression_limit_rejects_bomb(self):
        p = self.prepare(); value = json.loads(Path(p['plan']).read_bytes())
        value.update(version=3, packed=base64.b64encode(zlib.compress(b'x' * (16_777_216 + 1))).decode())
        value.pop('config_raw');value.pop('projects')
        p = self.rewrite(p, value)
        with self.assertRaisesRegex(ValueError, 'retirement_packed_too_large'):
            m.read(p['plan'], p['sha256'])

    def test_invalid_or_trailing_compressed_payload_rejected(self):
        p = self.large(); original = json.loads(Path(p['plan']).read_bytes())
        raw = base64.b64decode(original['packed'])
        for suffix in (b'extra', b''):
            value = dict(original)
            value['packed'] = base64.b64encode(raw + suffix if suffix else raw[:-1]).decode()
            p = self.rewrite(p, value)
            with self.assertRaisesRegex(ValueError, 'invalid_retirement_packed'):
                m.read(p['plan'], p['sha256'])

    def test_packed_plan_rejects_ambiguous_plain_fields(self):
        p = self.large();value=json.loads(Path(p['plan']).read_bytes());value['projects']={}
        p = self.rewrite(p, value)
        with self.assertRaisesRegex(ValueError, 'invalid_retirement_packed'):
            m.read(p['plan'], p['sha256'])

    def test_oversize_expansion_leaves_no_journal(self):
        p=self.paths['future'];p.write_text(p.read_text()+'\n'+'x'*8_500_000)
        with self.assertRaisesRegex(ValueError,'retirement_packed_too_large'):
            self.prepare()
        self.assertFalse((self.hub/'ai/reminders-external-retirements').exists())

    def test_large_plan_resume_after_canonical_write(self):
        p=self.large();write=m.cancel.write_texts
        def fail(hp,project):
            write(hp,project);raise OSError('after canonical')
        with patch.object(m.cancel,'write_texts',side_effect=fail):
            with self.assertRaisesRegex(OSError,'after canonical'):self.apply(p)
        self.apply(p);self.assertTrue(self.verify())
        self.assertEqual(m.pending_projects(self.hub,self.read()),set())

    def test_large_plan_exact_config_cas_is_preserved(self):
        p=self.large();path=self.hub/'ai/reminders-sync.json'
        path.write_text(json.dumps(self.read(),ensure_ascii=False,indent=2))
        with self.assertRaisesRegex(ValueError,'cas_conflict'):self.apply(p)
