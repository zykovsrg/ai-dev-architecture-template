"""Полный запуск обязан связывать собственный отказ с настоящим источником теста."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('mutation_check', ROOT / 'scripts/mutation-check.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class MutationCheckTests(unittest.TestCase):
    def config(self):
        return dict(schema_version=2, suites={'unit': dict(framework='unittest', args=['discover', '-s', 'tests', '-p', 'test_example.py'])},
                    mutations=[dict(id='number', suite='unit', source='scripts/value.py', symbol='number',
                                    before='return 1', after='return 2', expected_ids=['test_example.Example.test_number'],
                                    expected_sources={'test_example.Example.test_number': 'tests/test_example.py'})])

    def report(self):
        return dict(complete=True, proof_gate=True, exit_code=0, mutations=[
            dict(id='number', status='detected', proof_gate=True, proofs=[
                dict(id='test_example.Example.test_number', test_file='tests/test_example.py',
                     own_assertion_events=[dict(id='test_example.Example.test_number',
                         parent_id='test_example.Example.test_number', own_assertion=True)])])])

    def test_catalog_requires_exact_source_for_each_expected_id(self):
        for sources in ({}, dict(self.config()['mutations'][0]['expected_sources'],
                                 unselected='tests/test_other.py')):
            config = self.config()
            config['mutations'][0]['expected_sources'] = sources
            with self.subTest(sources=sources), self.assertRaises(ValueError):
                check.catalog_claims(config)

    def test_new_method_or_foreign_source_cannot_count_as_covered(self):
        claims = check.catalog_claims(self.config())
        for added in (dict(claims[0], id='test_example.Example.test_new'),
                      dict(claims[0], source='modules/new/tests/test_example.py')):
            with self.subTest(added=added), self.assertRaises(ValueError):
                check.validate_coverage(claims + [added], claims)

    def test_incomplete_strict_report_never_becomes_success(self):
        for field, value in (('complete', False), ('proof_gate', False), ('exit_code', 2)):
            report = self.report()
            report[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                check.proven_claims(self.config(), report)

    def test_assertion_without_own_event_cannot_be_credited(self):
        report = self.report()
        event = report['mutations'][0]['proofs'][0]['own_assertion_events'][0]
        # Настоящий подслучай имеет отдельный id, но относится к методу parent_id.
        event['id'] += ' (number=1)'
        try:
            claims = check.proven_claims(self.config(), report)
        except ValueError:
            claims = []
        self.assertEqual(claims, check.catalog_claims(self.config()))
        for field, value in (('own_assertion', False), ('parent_id', 'foreign.method')):
            original = event[field]
            event[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                check.proven_claims(self.config(), report)
            event[field] = original

    def test_proof_from_different_file_cannot_replace_expected_source(self):
        report = self.report()
        report['mutations'][0]['proofs'][0]['test_file'] = 'modules/new/tests/test_example.py'
        with self.assertRaises(ValueError):
            check.proven_claims(self.config(), report)

    def toy_command(self, extra='', operation=False):
        temporary = tempfile.TemporaryDirectory(prefix='mutation-check-fixture-')
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name).resolve()
        source = base / 'source'
        (source / 'scripts').mkdir(parents=True)
        (source / 'tests').mkdir()
        (source / 'docs').mkdir()
        (source / 'getting-started').mkdir()
        (source / 'README.md').write_text('# Пример\n')
        (source / 'docs/usage.md').write_text('# Применение\n')
        (source / 'getting-started/start.md').write_text('# Начало\n')
        for name in check.DRIVER_FILES:
            shutil.copy2(ROOT / 'scripts' / name, source / 'scripts' / name)
        (source / 'scripts/value.py').write_text('def number():\n    return 1\n')
        (source / 'tests/test_example.py').write_text('import unittest\nfrom scripts.value import number\n'
            'class Example(unittest.TestCase):\n    def test_number(self): self.assertEqual(number(), 1)\n' + extra)
        config = self.config()
        if operation:
            (source / 'tests/test_example.py').write_text('from pathlib import Path\nimport unittest\n'
                'ROOT=Path(__file__).resolve().parents[1]\nclass Example(unittest.TestCase):\n'
                '    def test_number(self): self.assertFalse((ROOT / "template").exists())\n')
            item = config['mutations'][0]
            for key in ('symbol', 'before', 'after'):
                item.pop(key)
            item.update(source='template', operation='create_empty_dir')
        config.update(legacy_sha256=check.sha(source / 'scripts/mutation-test.py'),
                      capture_sha256=check.sha(source / 'scripts/test-method-capture.py'),
                      filesystem_helper_sha256=check.sha(source / 'scripts/mutation-filesystem.py'),
                      driver_sha256={name: check.sha(source / 'scripts' / name) for name in check.DRIVER_FILES})
        catalog = base / 'catalog.json'
        catalog.write_text(json.dumps(config))
        output = base / 'result.json'
        result = subprocess.run([sys.executable, str(source / 'scripts/mutation-check.py'), '--source', str(source),
                                 '--catalog', str(catalog), '--output', str(output)], cwd=base,
                                capture_output=True, text=True, timeout=40)
        self.assertTrue(output.exists(), result.stderr)
        return result, json.loads(output.read_text()), source, output

    def test_complete_command_runs_real_mutation_and_restores_source(self):
        for operation in (False, True):
            with self.subTest(operation=operation):
                result, report, source, output = self.toy_command(operation=operation)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(report['complete'])
                self.assertTrue(report['proof_gate'])
                self.assertEqual(report['proven_cases'], report['inventory'])
                strict = json.loads(Path(report['strict_report_path']).read_text())
                self.assertEqual(strict['mutations'][0]['status'], 'detected')
                self.assertEqual((source / 'scripts/value.py').read_text(), 'def number():\n    return 1\n')
                self.assertFalse((source / 'template').exists())

    def test_new_test_stops_before_expensive_mutations(self):
        result, report, source, output = self.toy_command('    def test_new(self): self.assertEqual(number(), 1)\n')
        self.assertEqual(result.returncode, 2)
        self.assertFalse(report['complete'])
        self.assertEqual(report['stage'], 'coverage')
        self.assertFalse(output.with_name(output.stem + '-strict.json').exists())


if __name__ == '__main__':
    unittest.main()
