"""Только три предметных документа моста, без разрешения суффиксов вообще."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ('modules/calendar/policy/bridge/hub_eventkit_bridge.swift',
           'modules/calendar/policy/bridge/Info.plist', 'modules/calendar/policy/bridge/SHA256SUMS')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BridgeDocumentMutationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='bridge-document-fixture-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.source = self.base / 'source'
        (self.source / 'modules/calendar/policy/bridge').mkdir(parents=True)
        (self.source / 'tests').mkdir()
        self.fs = load('domain_fs', ROOT / 'scripts/mutation-filesystem.py')
        self.legacy = load('domain_legacy', ROOT / 'scripts/mutation-test.py')
        for name in TARGETS:
            (self.source / name).write_text('unique-bridge-contract\n')

    def item(self, source):
        return dict(id='bridge-fixture', suite='demo', expected_ids=['fixture'], source=source,
                    symbol='@document', before='unique-bridge-contract', after='broken-bridge-contract')

    def test_three_exact_documents_change_and_restore(self):
        for index, name in enumerate(TARGETS):
            with self.subTest(source=name):
                try:
                    change = self.fs.prepare_change(self.source, self.item(name), [], self.legacy.mutate)
                except ValueError:
                    change = None
                self.assertIsNotNone(change, 'Один из трёх разрешённых документов отклонён')
                variant = self.base / ('variant-%d' % index)
                baseline = self.fs.snapshot(self.source, variant)
                expected = self.fs.apply_change(variant, change, baseline)
                self.assertEqual((variant / name).read_text(), 'broken-bridge-contract\n')
                self.assertEqual(self.fs.read_state(variant), expected)
                self.fs.restore_change(variant, change)
                self.assertEqual(self.fs.read_state(variant), baseline)
                self.assertEqual((self.source / name).read_text(), 'unique-bridge-contract\n')

    def test_neighbor_documents_and_aliases_remain_forbidden(self):
        parent = (self.source / TARGETS[0]).parent
        for name in ('neighbor.swift', 'neighbor.plist', 'OTHER_SUMS'):
            path = parent / name
            path.write_text('unique-bridge-contract\n')
            with self.subTest(source=name), self.assertRaises(ValueError):
                self.fs.prepare_change(self.source, self.item(path.relative_to(self.source).as_posix()), [], self.legacy.mutate)
        for name in ('modules/calendar/policy/bridge/./Info.plist', 'modules/calendar/policy/bridge//Info.plist',
                     str(self.source / TARGETS[0])):
            with self.subTest(alias=name), self.assertRaises(ValueError):
                self.fs.prepare_change(self.source, self.item(name), [], self.legacy.mutate)
        original = self.source / TARGETS[0]
        original.unlink()
        outside = self.base / 'outside.swift'
        outside.write_text('unique-bridge-contract\n')
        original.symlink_to(outside)
        with self.assertRaises(ValueError):
            self.fs.prepare_change(self.source, self.item(TARGETS[0]), [], self.legacy.mutate)
        self.assertEqual(outside.read_text(), 'unique-bridge-contract\n')
        original.unlink()
        os.link(outside, original)
        with self.assertRaises(ValueError):
            self.fs.prepare_change(self.source, self.item(TARGETS[0]), [], self.legacy.mutate)
        self.assertEqual(outside.read_text(), 'unique-bridge-contract\n')

    def test_bridge_document_requires_explicit_helper_pin(self):
        import hashlib
        sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        # Полный корректный предмет: без pin-guard весь строгий цикл обязан пройти.
        (self.source / 'README.md').write_text('# Пример\n')
        (self.source / 'getting-started').mkdir()
        (self.source / 'getting-started/start.md').write_text('# Начало\n')
        (self.source / 'docs').mkdir()
        (self.source / 'docs/usage.md').write_text('# Применение\n')
        (self.source / 'tests/test_bridge_fixture.py').write_text(
            'from pathlib import Path\nimport unittest\nROOT = Path(__file__).resolve().parents[1]\n'
            'class Fixture(unittest.TestCase):\n    def test_document(self):\n'
            '        self.assertEqual((ROOT / "modules/calendar/policy/bridge/hub_eventkit_bridge.swift").read_text(), "unique-bridge-contract\\n")\n')
        item = self.item(TARGETS[0])
        item['expected_ids'] = ['test_bridge_fixture.Fixture.test_document']
        config = dict(schema_version=2, legacy_sha256=sha(ROOT / 'scripts/mutation-test.py'),
                      capture_sha256=sha(ROOT / 'scripts/test-method-capture.py'),
                      suites={'demo': dict(framework='unittest', args=['discover', '-s', 'tests', '-p', 'test_bridge_fixture.py', '-q'])},
                      mutations=[item])
        catalog = self.base / 'catalog.json'; catalog.write_text(json.dumps(config))
        output = self.base / 'report.json'
        strict = load('domain_strict', ROOT / 'scripts/mutation-test-strict.py')
        with patch.object(sys, 'argv', ['strict', '--source', str(self.source), '--catalog', str(catalog), '--output', str(output)]), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = strict.main()
        self.assertEqual(code, 2)
        self.assertTrue(output.is_file())
        report = json.loads(output.read_text())
        self.assertEqual(report['executions'], [])
        self.assertIn('явное закрепление', report['error'])


if __name__ == '__main__':
    unittest.main()
