"""Проверки управляющего сценария на независимой маленькой программе."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

RUNNER = Path(__file__).resolve().parents[1] / 'scripts/mutation-test.py'


class MutationRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'scripts').mkdir()
        (self.root / 'tests').mkdir()
        self.source = self.root / 'scripts/sample.py'
        self.source.write_text('def allowed(value):\n    return value > 0\n')
        self.test = self.root / 'tests/test_sample.py'
        self.test.write_text('import unittest\nfrom scripts.sample import allowed\n'
                             'class Sample(unittest.TestCase):\n'
                             '    def test_allowed(self):\n        self.assertTrue(allowed(1))\n'
                             '    def test_zero(self):\n        self.assertFalse(allowed(0))\n')
        self.config = {'suites': {'demo': {'commands': [
            ['-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_sample.py', '-q']]}},
            'mutations': [{'id': 'zero', 'suite': 'demo', 'source': 'scripts/sample.py',
                           'symbol': 'allowed', 'before': 'value > 0', 'after': 'value >= 0'}]}

    def run_check(self, *extra):
        catalog = self.root / 'cases.json'
        catalog.write_text(json.dumps(self.config))
        output = self.root / 'report.json'
        result = subprocess.run([sys.executable, '-B', str(RUNNER), '--source', str(self.root),
                                 '--catalog', str(catalog), '--output', str(output), *extra],
                                capture_output=True, text=True, timeout=20)
        self.assertTrue(output.exists(), result.stderr + result.stdout)
        report = json.loads(output.read_text()) if output.exists() else {}
        return result, report

    def test_detects_error_and_keeps_original_bytes(self):
        before = self.source.read_bytes()
        result, report = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(report['mutations'][0]['status'], 'detected')
        self.assertEqual(self.source.read_bytes(), before)

    def test_surviving_error_fails_gate(self):
        self.config['mutations'][0]['after'] = 'value > -1'
        self.test.write_text('import unittest\nfrom scripts.sample import allowed\n'
                             'class Sample(unittest.TestCase):\n'
                             '    def test_allowed(self):\n        self.assertTrue(allowed(1))\n')
        result, report = self.run_check()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(report['mutations'][0]['status'], 'survived')

    def test_documented_equivalent_is_explicit(self):
        self.config['mutations'][0].update(after='value > (0)', equivalent_reason='Те же значения.')
        result, report = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report['mutations'][0]['status'], 'equivalent')

    def test_detected_equivalent_requires_review(self):
        self.config['mutations'][0]['equivalent_reason'] = 'Ошибочная классификация.'
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(report['mutations'][0]['status'], 'exception_changed')

    def test_missing_replacement_is_an_error(self):
        self.config['mutations'][0]['before'] = 'missing'
        result, _ = self.run_check()
        self.assertEqual(result.returncode, 2)

    def test_baseline_failure_stops_mutations(self):
        self.test.write_text('import unittest\nclass Sample(unittest.TestCase):\n'
                             '    def test_failure(self):\n        self.fail("baseline")\n')
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report['mutations'], [])

    def test_import_error_is_not_a_detected_mutation(self):
        self.config['mutations'][0]['after'] = '__import__("missing_mutation_dependency")'
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report['mutations'][0]['status'], 'error')

    def test_empty_suite_is_an_error(self):
        self.test.write_text('')
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report['mutations'], [])

    def test_fully_skipped_suite_is_an_error(self):
        self.test.write_text('import unittest\nclass Sample(unittest.TestCase):\n'
                             '    @unittest.skip("not available")\n'
                             '    def test_skipped(self):\n        pass\n')
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report['mutations'], [])

    def test_ambiguous_replacement_is_an_error(self):
        self.source.write_text('def allowed(value):\n    return value > 0 or value > 0\n')
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report['mutations'], [])

    def test_syntax_error_in_mutation_is_an_error(self):
        self.config['mutations'][0]['after'] = 'value >'
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report['mutations'], [])

    def test_timeout_is_an_error(self):
        self.test.write_text('import time\ntime.sleep(2)\n')
        result, _ = self.run_check('--timeout', '0.1')
        self.assertEqual(result.returncode, 2)

    def test_unknown_suite_is_an_error(self):
        result, _ = self.run_check('--suite', 'unknown')
        self.assertEqual(result.returncode, 2)

    def test_duplicate_ids_are_an_error(self):
        self.config['mutations'].append(dict(self.config['mutations'][0]))
        result, _ = self.run_check()
        self.assertEqual(result.returncode, 2)

    def test_source_outside_copy_is_rejected(self):
        # The file exists, so a missing-file check cannot impersonate the guard.
        outside = self.root / 'outside.py'
        outside.write_bytes(self.source.read_bytes())
        original = outside.read_bytes()
        spec = importlib.util.spec_from_file_location('mutation_runner_paths', RUNNER)
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        with self.assertRaisesRegex(ValueError, '^Недопустимый путь: '):
            runner.relative_file(self.root / 'scripts', '../outside.py')
        self.config['mutations'][0]['source'] = 'scripts/../outside.py'
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report.get('error'), 'Недопустимый путь: scripts/../outside.py')
        self.assertEqual(outside.read_bytes(), original)

    def test_symlink_is_not_followed(self):
        (self.root / 'scripts/link.py').symlink_to(self.source)
        result, _ = self.run_check()
        self.assertEqual(result.returncode, 2)

    def test_independent_mutations_start_from_original(self):
        self.config['mutations'].append(dict(self.config['mutations'][0], id='second'))
        result, report = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual([m['status'] for m in report['mutations']], ['detected', 'detected'])

    def test_document_mutation_checks_the_real_file(self):
        (self.root / 'modules').mkdir()
        (self.root / 'modules/rule.md').write_text('Проверяйте каждый новый тест мутацией.\n')
        self.test.write_text('import unittest\nfrom pathlib import Path\n'
                             'class Sample(unittest.TestCase):\n'
                             '    def test_rule(self):\n'
                             '        self.assertIn("мутацией", Path("modules/rule.md").read_text())\n')
        self.config['mutations'][0].update(source='modules/rule.md', symbol='@document',
                                           before='мутацией', after='')
        result, report = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(report['mutations'][0]['status'], 'detected')

    def shell_case(self):
        (self.root / 'scripts/sample.sh').write_text("printf 'allowed\\n'\n")
        self.test.write_text('import subprocess, unittest\n'
                             'class Sample(unittest.TestCase):\n'
                             '    def test_shell(self):\n'
                             '        result = subprocess.run(["bash", "scripts/sample.sh"], capture_output=True, text=True)\n'
                             '        self.assertEqual(result.stdout, "allowed\\n")\n')
        self.config['mutations'][0].update(source='scripts/sample.sh', symbol='@shell',
                                           before='allowed', after='denied')

    def test_shell_mutation_reaches_child_process(self):
        self.shell_case()
        result, report = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(report['mutations'][0]['status'], 'detected')

    def test_invalid_shell_mutation_is_rejected_before_tests(self):
        self.shell_case()
        self.config['mutations'][0].update(before="printf 'allowed\\n'", after='if then')
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertEqual(report['baselines'], {})
        self.assertIn('Некорректная мутация оболочки', report.get('error', ''))

    def test_template_hidden_files_are_copied(self):
        (self.root / 'scripts/.gitignore').write_text('template')
        with self.test.open('a') as stream:
            stream.write('    def test_template(self):\n'
                         '        from pathlib import Path\n'
                         '        self.assertEqual(Path("scripts/.gitignore").read_text(), "template")\n')
        result, _ = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
