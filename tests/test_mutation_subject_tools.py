"""Самопроверки инструментов разрешены только в отдельном предмете и точном unittest suite."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'scripts/mutation-test-strict.py'
TOOLS = ('mutation-test.py', 'mutation-test-strict.py', 'mutation-filesystem.py',
         'test-method-capture.py', 'test-shell-capture.py')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SubjectToolTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='subject-tools-fixture-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.source = self.base / 'source'
        for name in ('scripts', 'tests/helpers', 'modules', 'docs', 'getting-started'):
            (self.source / name).mkdir(parents=True, exist_ok=True)
        for name in ('README.md', 'docs/contract.md', 'getting-started/start.md'):
            (self.source / name).write_text('# Локальная полная фикстура\n')
        self.external_hashes = {name: sha(ROOT / 'scripts' / name) for name in TOOLS}
        self.configure()

    def configure(self, pattern='test_test_method_capture.py', target='scripts/test-method-capture.py'):
        for file in (self.source / 'tests').glob('test_*.py'):
            file.unlink()
        self.target = target
        (self.source / target).parent.mkdir(parents=True, exist_ok=True)
        (self.source / target).write_text('def allowed(value):\n    return value > 0\n')
        self.pattern = pattern
        self.identity = Path(pattern).stem + '.DomainTests.test_boundary'
        self.test = self.source / 'tests' / pattern
        self.test.write_text('import importlib.util\nfrom pathlib import Path\nimport unittest\n'
                             'class DomainTests(unittest.TestCase):\n'
                             '    def test_boundary(self):\n'
                             '        root = Path(__file__).resolve().parents[1]\n'
                             f'        spec = importlib.util.spec_from_file_location("domain_tool", root / {target!r})\n'
                             '        domain = importlib.util.module_from_spec(spec)\n'
                             '        spec.loader.exec_module(domain)\n'
                             '        self.assertFalse(domain.allowed(0))\n')
        self.config = dict(schema_version=2,
                           legacy_sha256=self.external_hashes['mutation-test.py'],
                           capture_sha256=self.external_hashes['test-method-capture.py'],
                           filesystem_helper_sha256=self.external_hashes['mutation-filesystem.py'],
                           suites={'domain': dict(framework='unittest',
                                    args=['discover', '-s', 'tests', '-p', pattern, '-q'],
                                    subject_tools=[target])},
                           mutations=[dict(id='boundary', suite='domain', source=target, symbol='allowed',
                                           before='value > 0', after='value >= 0', expected_ids=[self.identity])])

    def run_check(self, runner=None):
        catalog = self.base / 'catalog.json'
        catalog.write_text(json.dumps(self.config))
        output = self.base / ('report-%02d.json' % len(list(self.base.glob('report-*.json'))))
        result = subprocess.run([sys.executable, '-B', str(runner or RUNNER), '--source', str(self.source),
                                 '--catalog', str(catalog), '--output', str(output)],
                                capture_output=True, text=True, timeout=25,
                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1'))
        self.assertTrue(output.is_file(), result.stdout + result.stderr)
        self.assertEqual({name: sha(ROOT / 'scripts' / name) for name in TOOLS}, self.external_hashes)
        return result, json.loads(output.read_text())

    def assert_cycle(self):
        before = {p.relative_to(self.source).as_posix(): p.read_bytes()
                  for p in self.source.rglob('*') if p.is_file()}
        result, report = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr + str(report.get('error')))
        self.assertTrue(report['complete'])
        self.assertTrue(report['proof_gate'])
        self.assertEqual([p['id'] for p in report['mutations'][0]['proofs']], [self.identity])
        self.assertEqual(report['mutations'][0]['mutant']['view']['own_assertion_ids'], [self.identity])
        self.assertTrue(report['mutations'][0]['before']['passed'])
        self.assertTrue(report['mutations'][0]['restored']['passed'])
        self.assertEqual({p.relative_to(self.source).as_posix(): p.read_bytes()
                          for p in self.source.rglob('*') if p.is_file()}, before)

    def assert_preflight_rejection(self, message):
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertFalse(report['complete'])
        self.assertEqual(report['executions'], [])
        self.assertIn(message, report['error'])

    def test_explicit_domain_capture_has_full_own_cycle(self):
        # Настоящий observer находится вне предмета; предметный capture — маленькая программа.
        self.assert_cycle()

    def test_default_keeps_capture_protected(self):
        del self.config['suites']['domain']['subject_tools']
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertFalse(report['complete'])
        self.assertIn('Нельзя мутировать', report['error'])
        self.assertEqual(report['mutations'], [])

    def test_strict_pair_allows_only_domain_driver(self):
        for pattern in ('test_mutation_strict.py', 'test_mutation_subject_tools.py'):
            with self.subTest(pattern=pattern):
                self.configure(pattern, 'scripts/mutation-test-strict.py')
                self.assert_cycle()

    def test_filesystem_selftest_can_target_domain_strict(self):
        self.configure('test_mutation_filesystem.py', 'scripts/mutation-test-strict.py')
        self.assert_cycle()

    def test_bridge_selftest_can_target_domain_strict(self):
        self.configure('test_mutation_bridge_documents.py', 'scripts/mutation-test-strict.py')
        self.assert_cycle()

    def make_shell_subject(self):
        self.configure('test_shell_scenario_capture.py', 'scripts/test-shell-capture.py')
        helper = self.source / 'tests/helpers/shell-scenarios.sh'
        helper.write_bytes((ROOT / 'tests/helpers/shell-scenarios.sh').read_bytes() +
                           b'\nsubject_answer() { printf "42\\n"; }\n')
        self.test.write_text(self.test.read_text().replace('import unittest\n', 'import unittest\nimport subprocess\n') + '')
        self.test.write_text(self.test.read_text() +
                            '        value = subprocess.check_output(["bash", "-c", \'source "$1"; subject_answer\', "_", str(root / "tests/helpers/shell-scenarios.sh")])\n'
                            '        self.assertEqual(value, b"42\\n")\n')
        self.config['suites']['domain']['subject_tools'] = ['scripts/test-shell-capture.py', 'tests/helpers/shell-scenarios.sh']
        self.config['mutations'].append(dict(id='helper-answer', suite='domain',
                        source='tests/helpers/shell-scenarios.sh', symbol='@shell',
                        before='subject_answer() { printf "42\\n"; }',
                        after='subject_answer() { printf "43\\n"; }', expected_ids=[self.identity]))

    def test_shell_capture_pair_can_mutate_domain_helper(self):
        self.make_shell_subject()
        result, report = self.run_check()
        self.assertEqual(result.returncode, 0, str(report.get('error')))
        self.assertTrue(report['proof_gate'])
        self.assertEqual([r['status'] for r in report['mutations']], ['detected', 'detected'])
        self.assertEqual([r['proofs'][0]['id'] for r in report['mutations']], [self.identity, self.identity])

    def test_wrong_pair_is_rejected_before_execution(self):
        self.configure('test_unrelated.py', 'scripts/test-method-capture.py')
        self.assert_preflight_rejection('subject_tools')

    def test_nonlist_subject_tools_is_rejected(self):
        self.config['suites']['domain']['subject_tools'] = self.target
        self.assert_preflight_rejection('subject_tools')

    def test_unknown_subject_descriptor_is_rejected(self):
        self.config['suites']['domain']['subject_tools'] = [{'path': self.target, 'allow_test_sources': True}]
        self.assert_preflight_rejection('subject_tools')

    def test_duplicate_subject_tools_are_rejected(self):
        self.config['suites']['domain']['subject_tools'] = [self.target, self.target]
        self.assert_preflight_rejection('subject_tools')

    def test_unknown_target_is_rejected_before_execution(self):
        self.configure(target='scripts/unlisted.py')
        self.assert_preflight_rejection('subject_tools')

    def test_shell_suite_cannot_request_subject_tools(self):
        self.config['suites']['domain'] = dict(framework='shell', args=['tests/test-domain.sh'],
                  helpers=['tests/helpers/shell-scenarios.sh'], subject_tools=[self.target])
        (self.source / 'tests/helpers/shell-scenarios.sh').write_bytes((ROOT / 'tests/helpers/shell-scenarios.sh').read_bytes())
        (self.source / 'tests/test-domain.sh').write_text('#!/usr/bin/env bash\nexit 0\n')
        self.config['shell_capture_sha256'] = self.external_hashes['test-shell-capture.py']
        self.assert_preflight_rejection('subject_tools')

    def test_internal_observer_is_rejected_before_execution(self):
        # Здесь реальные tools копируются только внутрь полной искусственной fixture.
        for name in TOOLS:
            shutil.copy2(ROOT / 'scripts' / name, self.source / 'scripts' / name)
        runner = self.source / 'scripts/mutation-test-strict.py'
        result, report = self.run_check(runner)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report['executions'], [])
        self.assertIn('внешний observer', report['error'])

    def make_combined_fixture(self):
        self.make_shell_subject()
        self.config['shell_capture_sha256'] = self.external_hashes['test-shell-capture.py']
        script = self.source / 'tests/test-active.sh'
        script.write_text('ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"\nsource "$ROOT/tests/helpers/shell-scenarios.sh"\n'
                          'active() { scenario_begin; scenario_accept_exit 1 ""; scenario_exec code test 1 = 1; scenario_assert_exit 0 "$code"; scenario_pass; }\n'
                          'scenario_declare active active\nscenario_main "$@"\n')
        self.config['suites']['active'] = dict(framework='shell', args=['tests/test-active.sh'],
                                               helpers=['tests/helpers/shell-scenarios.sh'])
        self.config['mutations'] = [self.config['mutations'][1]]

    def test_combined_selfsuite_can_mutate_its_domain_helper(self):
        self.make_combined_fixture()
        result, report = self.run_check()
        self.assertEqual(result.returncode, 0, str(report.get('error')))
        self.assertTrue(report['proof_gate'])
        self.assertEqual(report['mutations'][0]['proofs'][0]['id'], self.identity)
        self.assertTrue(report['final_restored']['active']['passed'])

    def test_active_shell_suite_cannot_mutate_its_helper(self):
        self.make_combined_fixture()
        self.config['mutations'][0]['suite'] = 'active'
        self.config['mutations'][0]['expected_ids'] = ['tests/test-active.sh::active']
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertFalse(report['complete'])
        self.assertIn('Нельзя мутировать', report['error'])
        self.assertEqual(report['mutations'], [])

    def test_capability_does_not_leak_to_another_suite(self):
        other = self.source / 'tests/test_other.py'
        other.write_text(self.test.read_text())
        self.config['suites']['other'] = dict(framework='unittest', args=['discover', '-s', 'tests', '-p', other.name, '-q'])
        self.config['mutations'][0]['suite'] = 'other'
        self.config['mutations'][0]['expected_ids'] = ['test_other.DomainTests.test_boundary']
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertFalse(report['complete'])
        self.assertIn('Нельзя мутировать', report['error'])
        self.assertEqual(report['mutations'], [])

    def test_selected_selfsuite_helper_remains_an_oracle(self):
        self.make_shell_subject()
        self.config['suites']['domain']['helpers'] = ['tests/helpers/shell-scenarios.sh']
        self.config['mutations'] = [self.config['mutations'][1]]
        result, report = self.run_check()
        self.assertEqual(result.returncode, 2)
        self.assertFalse(report['complete'])
        self.assertIn('Нельзя мутировать', report['error'])
        self.assertEqual(report['mutations'], [])

    def test_legacy_suite_metadata_remains_compatible(self):
        self.configure('test_sample.py', 'scripts/sample.py')
        del self.config['suites']['domain']['subject_tools']
        self.config['suites']['domain']['historical_note'] = {'review': 'metadata remains metadata'}
        self.assert_cycle()

    def test_subject_tools_cannot_weaken_exact_discovery(self):
        self.config['suites']['domain']['args'][4] = 'test_*.py'
        self.assert_preflight_rejection('subject_tools')
