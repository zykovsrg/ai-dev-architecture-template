"""Строгий цикл проверяется на маленькой независимой программе, не на всём Хабе."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'scripts/mutation-test-strict.py'
CALENDAR_PYTHON = ROOT / 'modules/calendar/policy/.venv/bin/python'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class StrictMutationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='strict-fixture-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        (self.root / 'scripts').mkdir()
        (self.root / 'tests').mkdir()
        self.source = self.root / 'scripts/sample.py'
        self.source.write_text('def allowed(value):\n    return value > 0\n')
        self.test = self.root / 'tests/test_sample.py'
        self.test.write_text('import unittest\nfrom scripts.sample import allowed\n'
                             'class Sample(unittest.TestCase):\n'
                             '    def test_positive(self):\n        self.assertTrue(allowed(1))\n'
                             '    def test_zero(self):\n        self.assertFalse(allowed(0))\n')
        self.catalog = self.root / 'cases.json'
        self.config = dict(schema_version=2,
                           legacy_sha256=sha(ROOT / 'scripts/mutation-test.py'),
                           capture_sha256=sha(ROOT / 'scripts/test-method-capture.py'),
                           suites={'demo': dict(framework='unittest', args=['discover', '-s', 'tests', '-p', 'test_sample.py', '-q'])},
                           mutations=[dict(id='zero', suite='demo', source='scripts/sample.py', symbol='allowed',
                                           before='value > 0', after='value >= 0', expected_ids=['test_sample.Sample.test_zero'])])

    def run_check(self, *arguments):
        self.catalog.write_text(json.dumps(self.config))
        output = self.root / 'report.json'
        result = subprocess.run([sys.executable, '-B', str(RUNNER), '--source', str(self.root),
                                 '--catalog', str(self.catalog), '--output', str(output), *arguments],
                                capture_output=True, text=True, timeout=40)
        self.assertTrue(output.is_file(), result.stdout + result.stderr)
        return result, json.loads(output.read_text())

    def test_unittest_own_cycle_and_original_bytes(self):
        before = self.source.read_bytes()
        result, report = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(report['complete'])
        self.assertEqual(self.source.read_bytes(), before)
        case = report['mutations'][0]
        self.assertEqual(case['status'], 'detected')
        self.assertEqual([p['id'] for p in case['proofs']], ['test_sample.Sample.test_zero'])
        self.assertEqual(case['before']['capture']['collected_ids'], ['test_sample.Sample.test_zero'])
        self.assertEqual(case['restored']['capture']['collected_ids'], ['test_sample.Sample.test_zero'])
        self.assertTrue(report['final_restored']['demo']['passed'])
        self.assertEqual(report['baselines']['demo']['capture']['collected_ids'],
                         report['final_restored']['demo']['capture']['collected_ids'])

    @unittest.skipUnless(CALENDAR_PYTHON.is_file(), 'Нужно местное окружение pytest, сеть не используется')
    def test_pytest_parameter_has_separate_own_proof(self):
        self.test.write_text('import pytest\nfrom scripts.sample import allowed\n'
                             '@pytest.mark.parametrize("value,expected", [(1,True),(0,False)], ids=["positive","zero"])\n'
                             'def test_boundary(value, expected):\n    assert allowed(value) == expected\n')
        identity = 'tests/test_sample.py::test_boundary[zero]'
        self.config['suites']['demo'] = dict(framework='pytest', args=['tests/test_sample.py', '-q'])
        self.config['mutations'][0]['expected_ids'] = [identity]
        result, report = self.run_check('--calendar-python', str(CALENDAR_PYTHON))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([p['id'] for p in report['mutations'][0]['proofs']], [identity])
        self.assertEqual(report['mutations'][0]['mutant']['capture']['collected_ids'], [identity])
        self.assertEqual(len(report['baselines']['demo']['capture']['collected_ids']), 2)

    def test_unittest_subcase_proves_only_its_exact_parent(self):
        self.test.write_text('import unittest\nfrom scripts.sample import allowed\n'
                             'class Sample(unittest.TestCase):\n'
                             '    def test_zero(self):\n'
                             '        for value in (0, -1):\n'
                             '            with self.subTest(value=value):\n'
                             '                self.assertFalse(allowed(value))\n')
        result, report = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        proof = report['mutations'][0]['proofs'][0]
        self.assertEqual(proof['id'], 'test_sample.Sample.test_zero')
        self.assertEqual([event['kind'] for event in proof['own_assertion_events']], ['subtest'])
        self.assertEqual(proof['own_assertion_events'][0]['parent_id'], proof['id'])
        self.assertNotEqual(proof['own_assertion_events'][0]['id'], proof['id'])

    def test_import_error_has_no_own_credit(self):
        self.config['mutations'][0]['after'] = '__import__("strict_missing_dependency")'
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertFalse(report['complete'])
        self.assertEqual(report['mutations'][0]['proofs'], [])
        self.assertTrue(report['mutations'][0]['restored']['passed'])

    def test_bare_assertion_from_production_has_no_own_credit(self):
        self.config['mutations'][0]['after'] = '(_ for _ in ()).throw(AssertionError("bare"))'
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report['mutations'][0]['proofs'], [])

    def test_skipped_baseline_is_not_success(self):
        self.test.write_text('import unittest\nclass Sample(unittest.TestCase):\n'
                             '    @unittest.skip("fixture")\n    def test_zero(self):\n        pass\n')
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report['mutations'], [])

    def test_neighbor_assertion_does_not_prove_selected_method(self):
        self.config['mutations'][0]['expected_ids'] = ['test_sample.Sample.test_positive']
        result, report = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report['mutations'][0]['status'], 'survived')
        self.assertEqual(report['mutations'][0]['proofs'], [])
        self.assertEqual(report['mutations'][0]['mutant']['capture']['collected_ids'], ['test_sample.Sample.test_positive'])

    def test_unsafe_output_is_rejected_without_writes(self):
        self.catalog.write_text(json.dumps(self.config))
        outside = self.root / 'outside.json'
        link = self.root / 'linked.json'
        link.symlink_to(outside)
        for output in (self.root / 'scripts/rejected.json', link):
            with self.subTest(output=output.name):
                result = subprocess.run([sys.executable, '-B', str(RUNNER), '--source', str(self.root),
                                         '--catalog', str(self.catalog), '--output', str(output)],
                                        capture_output=True, text=True, timeout=40)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(output.exists())
                self.assertFalse(outside.exists())

    def test_capture_pin_mismatch_stops_before_test_execution(self):
        self.config['capture_sha256'] = '0' * 64
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report['executions'], [])

    def test_changed_copy_invalidates_proof(self):
        self.test.write_text(self.test.read_text().replace('self.assertTrue(allowed(1))',
                             'self.assertTrue(allowed(1)); __import__("pathlib").Path("scripts/extra.txt").write_text("changed")'))
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertFalse(report['complete'])

    def test_missing_selected_identity_is_rejected_before_mutation(self):
        self.config['mutations'][0]['expected_ids'] = ['test_sample.Sample.test_absent']
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report['mutations'], [])

    def test_shell_framework_is_rejected_before_adapter(self):
        # Без помощника явных сценариев оболочка по-прежнему не запускается,
        # даже когда сборщик оболочки закреплён.
        self.config['shell_capture_sha256'] = sha(ROOT / 'scripts/test-shell-capture.py')
        self.config['suites']['demo'] = dict(framework='shell', args=['tests/test_sample.py'])
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report['executions'], [])

    def test_unknown_framework_is_rejected_before_execution(self):
        self.config['suites']['demo'] = dict(framework='bash', args=['tests/test_sample.py'])
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report['executions'], [])

    def make_shell_fixture(self, body_extra=''):
        (self.root / 'tests/helpers').mkdir(exist_ok=True)
        (self.root / 'tests/helpers/shell-scenarios.sh').write_bytes((ROOT / 'tests/helpers/shell-scenarios.sh').read_bytes())
        (self.root / 'scripts/sample.sh').write_text('[ "$1" -gt 0 ]\n')
        script = self.root / 'tests/test-sample.sh'
        script.write_text('#!/usr/bin/env bash\nset -euo pipefail\nROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"\n'
                          'source "$ROOT/tests/helpers/shell-scenarios.sh"\n'
                          'positive() {\n  scenario_begin\n  scenario_accept_exit 1 \'\'\n  scenario_exec code bash "$ROOT/scripts/sample.sh" 1\n'
                          '  scenario_assert_exit 0 "$code"\n' + body_extra + '  scenario_pass\n}\n'
                          'zero() {\n  scenario_begin\n  scenario_accept_exit 1 \'\'\n  scenario_exec code bash "$ROOT/scripts/sample.sh" 0\n'
                          '  scenario_assert_exit 1 "$code"\n  scenario_pass\n}\n'
                          'scenario_declare positive positive\nscenario_declare zero zero\nscenario_main "$@"\n')
        self.config['shell_capture_sha256'] = sha(ROOT / 'scripts/test-shell-capture.py')
        self.config['suites']['demo'] = dict(framework='shell', args=['tests/test-sample.sh'],
                                             helpers=['tests/helpers/shell-scenarios.sh'])
        self.config['mutations'][0] = dict(id='zero', suite='demo', source='scripts/sample.sh', symbol='@shell',
                                           before='-gt 0', after='-ge 0', expected_ids=['tests/test-sample.sh::zero'])

    def test_shell_scenario_own_cycle_proves_only_selected_scenario(self):
        self.make_shell_fixture()
        identity = 'tests/test-sample.sh::zero'
        result, report = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        case = report['mutations'][0]
        self.assertEqual(case['status'], 'detected')
        self.assertEqual([p['id'] for p in case['proofs']], [identity])
        self.assertEqual(case['mutant']['capture']['collected_ids'], [identity])
        self.assertEqual(len(report['baselines']['demo']['capture']['collected_ids']), 2)

    def test_shell_suite_without_helper_is_rejected_before_execution(self):
        self.make_shell_fixture()
        self.config['suites']['demo'].pop('helpers')
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report['executions'], [])

    def test_shell_suite_requires_one_shell_script(self):
        self.make_shell_fixture()
        self.config['suites']['demo']['args'] = ['tests/test_sample.py']
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report['executions'], [])

    def test_shell_capture_pin_mismatch_stops_before_execution(self):
        self.make_shell_fixture()
        self.config['shell_capture_sha256'] = '0' * 64
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report['executions'], [])

    def test_changed_copied_shell_capture_is_rejected(self):
        self.make_shell_fixture('  printf "\\n" >> ../.tools/shell_capture.py\n')
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertFalse(report['complete'])

    def test_python_and_shell_assertion_kinds_do_not_mix(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('strict_under_test', RUNNER)
        strict = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(strict)
        source = str(self.test.resolve())
        identity = 'test_sample.Sample.test_zero'
        def capture(framework, kind):
            location = {'path': source, 'line': 6}
            event = dict(id=identity, parent_id=identity, kind='test', phase='call', status='failed',
                         source_path=source, own_assertion=True,
                         exception=dict(location=location, assertion_origin=dict(kind=kind, location=location, source='x')))
            return dict(schema_version=2, framework=framework, complete=True, exit_code=1, collected_ids=[identity],
                        started_ids=[identity], results=[event], infrastructure_errors=[])
        for framework, kind, credited in (('unittest', 'shell_assert_exit', False), ('shell', 'unittest_assertion', False),
                                          ('unittest', 'unittest_assertion', True), ('shell', 'shell_assert_exit', True)):
            with self.subTest(framework=framework, kind=kind):
                view = strict.capture_view(capture(framework, kind), framework, 1, self.root)
                self.assertEqual(view['own_assertion_ids'], [identity] if credited else [])

    def test_non_object_suites_are_rejected_with_a_report(self):
        self.config['suites'] = []
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertIn('Пустой strict manifest', report.get('error', ''))

    def test_changed_copied_capture_is_rejected(self):
        self.test.write_text(self.test.read_text().replace('self.assertTrue(allowed(1))',
                             'self.assertTrue(allowed(1)); __import__("pathlib").Path(__import__("__main__").__file__).open("a").write("\\n")'))
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertFalse(report['complete'])

    def test_changed_definition_bytes_are_rejected(self):
        change = '__import__("pathlib").Path(' + repr(str(self.catalog)) + ').open("a").write(" ")'
        self.test.write_text(self.test.read_text().replace('self.assertTrue(allowed(1))', 'self.assertTrue(allowed(1)); ' + change))
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertFalse(report['complete'])

    def test_failed_target_restoration_does_not_create_proof(self):
        self.source.write_text('from pathlib import Path\ndef allowed(value):\n'
                               '    if Path(".marker").exists(): return True\n    return value > 0\n')
        self.config['mutations'][0]['after'] = '(Path(".marker").write_text("x") or True)'
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report['mutations'][0]['proofs'], [])
        self.assertFalse(report['mutations'][0]['restored']['passed'])

    def test_executable_oracle_cannot_be_mutation_target(self):
        for kind in ('test', 'helper', 'domain_data'):
            with self.subTest(kind=kind):
                if kind == 'test':
                    self.config['mutations'][0].update(source='tests/test_sample.py', symbol='Sample.test_zero',
                        before='self.assertFalse(allowed(0))', after='self.assertTrue(allowed(0))')
                elif kind == 'helper':
                    (self.root / 'tests/oracle.py').write_text('def check(value):\n    assert not value\n')
                    self.test.write_text('import unittest\nfrom scripts.sample import allowed\nfrom oracle import check\n'
                        'class Sample(unittest.TestCase):\n    def test_zero(self):\n        check(allowed(0))\n')
                    self.config['suites']['demo']['helpers'] = ['tests/oracle.py']
                    self.config['mutations'][0].update(source='tests/oracle.py', symbol='check',
                        before='assert not value', after='assert value')
                else:
                    (self.root / 'tests/testfixtures.py').write_text('def allowed(value):\n    return value > 0\n')
                    self.test.write_text('import unittest\nfrom testfixtures import allowed\n'
                        'class Sample(unittest.TestCase):\n    def test_zero(self):\n        self.assertFalse(allowed(0))\n')
                    self.config['suites']['demo'].pop('helpers', None)
                    self.config['mutations'][0].update(source='tests/testfixtures.py', symbol='allowed',
                        before='value > 0', after='value >= 0')
                result, report = self.run_check()
                (self.root / 'report.json').unlink()
                __import__('shutil').rmtree(self.root / 'report-artifacts')
                if kind == 'domain_data':
                    self.assertEqual(result.returncode, 0, report)
                    self.assertTrue(report['proof_gate'])
                else:
                    self.assertEqual(result.returncode, 2, report)
                    self.assertFalse(report['proof_gate'])
                    self.assertEqual(report['mutations'], [])
                    self.assertIn('oracle', report['error'])

    def test_saved_raw_artifacts_are_checked_at_final_gate(self):
        for suffix in ('json', 'log'):
            with self.subTest(suffix=suffix):
                self.config['mutations'][0]['after'] = ('(__import__("pathlib").Path(__import__("sys").argv['
                    '__import__("sys").argv.index("--output")+1]).with_name("execution-0001.' + suffix +
                    '").write_text("{}") and value >= 0)')
                result, report = self.run_check()
                (self.root / 'report.json').unlink()
                __import__('shutil').rmtree(self.root / 'report-artifacts')
                self.assertEqual(result.returncode, 2, report)
                self.assertFalse(report['proof_gate'])
                self.assertIn('Сохранённое доказательство', report['error'])

    def test_oracle_aliases_are_the_same_protected_file(self):
        oracle = self.root / 'tests/oracle.py'
        oracle.write_text('def check(value):\n    assert not value\n')
        self.test.write_text('import unittest\nfrom scripts.sample import allowed\nfrom oracle import check\n'
            'class Sample(unittest.TestCase):\n    def test_zero(self):\n        check(allowed(0))\n')
        aliases = ['tests/./oracle.py', 'tests//oracle.py']
        case_alias = self.root / 'tests/ORACLE.py'
        if case_alias.exists() and case_alias.samefile(oracle):
            aliases.append('tests/ORACLE.py')
        hardlink = self.root / 'tests/oracle_link.py'
        __import__('os').link(oracle, hardlink)
        aliases.append('tests/oracle_link.py')
        for index, alias in enumerate(aliases):
            with self.subTest(alias=alias):
                self.config['suites']['demo']['helpers'] = [alias]
                self.config['mutations'][0].update(source='tests/oracle.py', symbol='check',
                    before='assert not value', after='assert value')
                result, report = self.run_check()
                saved = self.root / ('alias-evidence-%02d' % index)
                saved.mkdir()
                (self.root / 'report.json').rename(saved / 'report.json')
                (self.root / 'report-artifacts').rename(saved / 'report-artifacts') if (self.root / 'report-artifacts').exists() else None
                self.assertEqual(result.returncode, 2, report)
                self.assertFalse(report['proof_gate'])
                self.assertEqual(report['mutations'], [])
                self.assertTrue('Неканонический' in report.get('error', '') or 'oracle' in report.get('error', ''), report)


if __name__ == '__main__':
    unittest.main()
