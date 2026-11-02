"""Проверки реальных вызовов общего запуска на подставных командах."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ENTRY_SOURCE = Path(__file__).resolve().parents[1] / 'scripts/architecture-test.sh'


class ArchitectureEntryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        (self.root / 'scripts').mkdir()
        self.entry = self.root / 'scripts/architecture-test.sh'
        self.entry.write_bytes(ENTRY_SOURCE.read_bytes())
        for relative in ('tests/test-example.sh', 'tests/test-example.py',
                         'modules/planning/tests/test-example.sh',
                         'modules/planning/tests/test-example.py'):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        self.binary = self.root / 'bin'
        self.binary.mkdir()
        self.trace = self.root / 'trace.jsonl'
        stub = '''import json, os, sys
from pathlib import Path
program = Path(sys.argv[0]).name
if program == 'uname':
    print(os.environ['SIMULATED_SYSTEM'])
else:
    with Path(os.environ['TRACE_FILE']).open('a') as handle:
        handle.write(json.dumps(dict(program=program, args=sys.argv[1:],
            pytest_addopts=os.environ.get('PYTEST_ADDOPTS'),
            plugin_autoload=os.environ.get('PYTEST_DISABLE_PLUGIN_AUTOLOAD'))) + '\\n')
if any(Path(arg).name == os.environ.get('FAIL_ENTRY') for arg in sys.argv[1:]):
    sys.exit(7)
'''
        for name in ('python3', 'bash', 'uname'):
            path = self.binary / name
            path.write_text('#!' + sys.executable + '\n' + stub)
            path.chmod(0o700)

    def run_entry(self, mode, system='Darwin', failing=None, extra=()):
        environment = dict(PATH=str(self.binary) + ':/usr/bin:/bin',
                           HOME=str(self.root), TMPDIR=str(self.root),
                           TRACE_FILE=str(self.trace), SIMULATED_SYSTEM=system)
        if failing:
            environment['FAIL_ENTRY'] = failing
        result = subprocess.run(['/bin/bash', str(self.entry), mode, *extra], cwd=self.root,
                                env=environment, capture_output=True, text=True, timeout=20)
        rows = [json.loads(line) for line in self.trace.read_text().splitlines()] if self.trace.exists() else []
        return result, rows

    def shell_names(self, rows):
        return [Path(row['args'][0]).name for row in rows
                if row['program'] == 'bash' and row['args']]

    def test_unit_runs_tasks_module(self):
        result, rows = self.run_entry('--unit')
        self.assertEqual(result.returncode, 0, result.stderr)
        tasks = str(self.root / 'modules/tasks/tests')
        self.assertTrue(any(row['program'] == 'python3' and '-s' in row['args']
                            and tasks in row['args'] for row in rows), rows)

    def test_archived_obsidian_module_is_not_run(self):
        for mode in ('--unit', '--integration'):
            result, rows = self.run_entry(mode)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(any('obsidian' in arg for row in rows for arg in row['args']), rows)

    def test_unit_runs_session_inventory_fixture(self):
        result, rows = self.run_entry('--unit')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('test-refresh-session-inventory.sh', self.shell_names(rows))

    def test_all_runs_complete_calendar_entries(self):
        result, rows = self.run_entry('--all')
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ('apple-calendar-policy-test.sh', 'calendar-venv-install-test.sh',
                     'calendar-policy-install-test.sh', 'apple-calendar-bridge-test.sh'):
            self.assertIn(name, self.shell_names(rows))
        self.assertTrue(any(row['program'] == 'python3' and
                            Path(row['args'][0]).name == 'mutation-check.py' for row in rows))

    def test_mutation_runs_complete_gate_and_forwards_arguments(self):
        result, rows = self.run_entry('--mutation', extra=('--output', 'trial.json'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(rows, [dict(program='python3',
            args=[str(self.root / 'scripts/mutation-check.py'), '--output', 'trial.json'],
            pytest_addopts=None, plugin_autoload=None)])

    def test_calendar_mode_runs_both_halves(self):
        result, rows = self.run_entry('--calendar')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.shell_names(rows), ['apple-calendar-policy-test.sh',
                         'calendar-venv-install-test.sh', 'calendar-policy-install-test.sh',
                         'apple-calendar-bridge-test.sh'])

    def test_calendar_unit_selects_only_python_suite(self):
        result, rows = self.run_entry('--calendar-unit')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.shell_names(rows), ['apple-calendar-policy-test.sh'])

    def test_calendar_integration_selects_only_installation_scenarios(self):
        result, rows = self.run_entry('--calendar-integration')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.shell_names(rows), ['calendar-venv-install-test.sh',
                         'calendar-policy-install-test.sh', 'apple-calendar-bridge-test.sh'])

    def test_calendar_uses_explicit_async_plugin(self):
        result, rows = self.run_entry('--calendar-unit')
        self.assertEqual(result.returncode, 0, result.stderr)
        calendar = [row for row in rows if row['program'] == 'bash'
                    and Path(row['args'][0]).name == 'apple-calendar-policy-test.sh']
        self.assertEqual(len(calendar), 1)
        self.assertEqual(calendar[0]['plugin_autoload'], '1')
        self.assertEqual(calendar[0]['pytest_addopts'], '-p pytest_asyncio.plugin')

    def test_non_macos_reports_skipped_bridge_scenarios(self):
        result, rows = self.run_entry('--calendar-integration', system='Linux')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.shell_names(rows), ['calendar-venv-install-test.sh'])
        self.assertIn('SKIP:', result.stdout)

    def test_non_macos_unit_reports_skipped_session_inventory(self):
        result, rows = self.run_entry('--unit', system='Linux')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('test-refresh-session-inventory.sh', self.shell_names(rows))
        self.assertIn('SKIP:', result.stdout)

    def test_calendar_failure_stops_all_before_mutations(self):
        result, rows = self.run_entry('--all', failing='apple-calendar-policy-test.sh')
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertFalse(any(any(Path(arg).name == 'mutation-check.py' for arg in row['args'])
                             for row in rows))

    def test_calendar_install_failure_stops_all_before_mutations(self):
        result, rows = self.run_entry('--all', failing='calendar-venv-install-test.sh')
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertFalse(any(any(Path(arg).name == 'mutation-check.py' for arg in row['args'])
                             for row in rows))


if __name__ == '__main__':
    unittest.main()
