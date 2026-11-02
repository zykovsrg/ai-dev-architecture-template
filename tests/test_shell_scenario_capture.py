"""Сборщик сценариев оболочки засчитывает только явные события помощника."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / 'scripts/test-shell-capture.py'
HELPER = ROOT / 'tests/helpers/shell-scenarios.sh'
HEAD = ('#!/usr/bin/env bash\nset -euo pipefail\nROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"\n'
        'source "$ROOT/tests/helpers/shell-scenarios.sh"\n')
# Подделка от имени самого тестового файла: ему доступен секрет помощника.
FAKE = '  printf \'{"v":2,"run":"%s","event":"{event}","id":"{id}"{extra}}\\n\' "$SCENARIO__TOKEN" >&9'


def fake(event, identity='one', extra=''):
    line = FAKE.replace('{event}', event).replace('{id}', identity).replace('{extra}', extra)
    # Путь последней диагностики передаётся отдельным аргументом printf.
    return line.replace(' >&9', ' "$SCENARIO__LAST_DIAG" >&9') if '"diag":"%s"' in extra else line


def failed_fields(line, expected, actual, child):
    return (f',"ok":false,"file":"tests/test-sample.sh","line":{line},"expected":{expected},'
            f'"actual":{actual},"child":{child},"diag":"%s"')


class ShellScenarioCaptureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='shell-capture-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / 'tests/helpers').mkdir(parents=True)
        shutil.copy2(HELPER, self.root / 'tests/helpers/shell-scenarios.sh')

    def capture(self, body, *selection, head=HEAD):
        text = head + body
        lines = text.splitlines()
        assert_line = next((n for n, line in enumerate(lines, 1)
                            if line.strip().startswith('scenario_assert_exit')), 0)
        text = text.replace('@ASSERTLINE@', str(assert_line))
        script = self.root / 'tests/test-sample.sh'
        script.write_text(text)
        output = self.root / 'capture.json'
        arguments = ['tests/test-sample.sh', *('tests/test-sample.sh::' + value for value in selection)]
        subprocess.run([sys.executable, '-B', str(CAPTURE), '--output', str(output), '--', *arguments],
                       cwd=self.root, capture_output=True, text=True, errors='replace', timeout=30)
        return json.loads(output.read_text())

    def scenario(self, steps, name='one'):
        function = name.replace('-', '_')
        return f'{function}() {{\n{steps}\n}}\nscenario_declare {name} {function}\nscenario_main "$@"\n'

    def assert_infrastructure(self, envelope, reason=None):
        self.assertFalse(envelope['complete'], envelope)
        self.assertEqual(envelope['exit_code'], 2, envelope)
        self.assertTrue(envelope['infrastructure_errors'], envelope)
        self.assertFalse(any(record['own_assertion'] for record in envelope['results']), envelope)
        if reason:
            self.assertTrue(any(reason in error for error in envelope['infrastructure_errors']), envelope)

    def test_passing_scenario_is_passed(self):
        envelope = self.capture(self.scenario('  scenario_begin\n  scenario_exec code true\n'
                                              '  scenario_assert_exit 0 "$code"\n  scenario_pass'))
        self.assertTrue(envelope['complete'], envelope)
        self.assertEqual([r['status'] for r in envelope['results']], ['passed'])
        self.assertEqual(envelope['exit_code'], 0)

    def test_own_assertion_is_a_located_failure(self):
        envelope = self.capture(self.scenario('  scenario_begin\n  scenario_exec code true\n'
                                              '  scenario_assert_exit 1 "$code"\n  scenario_pass'))
        self.assertTrue(envelope['complete'], envelope)
        [record] = envelope['results']
        self.assertEqual((record['status'], record['own_assertion']), ('failed', True))
        origin = record['exception']['assertion_origin']
        self.assertEqual(origin['kind'], 'shell_assert_exit')
        self.assertEqual(origin['location'], {'path': str(self.root / 'tests/test-sample.sh'), 'line': 8})
        self.assertEqual(envelope['exit_code'], 1)

    def test_plain_exit_one_after_start_is_not_own(self):
        self.assert_infrastructure(self.capture(self.scenario('  scenario_begin\n  exit 1')))

    def test_cleanup_error_after_own_assertion_is_not_counted(self):
        body = self.scenario('  trap "exit 2" EXIT\n  scenario_begin\n  scenario_exec code true\n'
                             '  scenario_assert_exit 1 "$code"')
        self.assert_infrastructure(self.capture(body))

    def test_event_for_another_scenario_is_rejected(self):
        self.assert_infrastructure(self.capture(self.scenario(
            '  scenario_begin\n  scenario_exec code true\n  scenario_assert_exit 0 "$code"\n'
            + fake('assert', 'other', ',"ok":true') + '\n  scenario_pass')), 'event for another scenario')

    def test_event_with_another_run_id_is_rejected(self):
        forged = ('  printf \'{"v":2,"run":"%s","event":"assert","id":"one","ok":true}\\n\' "'
                  + '0' * 32 + '" >&9')
        self.assert_infrastructure(self.capture(self.scenario(
            '  scenario_begin\n  scenario_exec code true\n  scenario_assert_exit 0 "$code"\n'
            + forged + '\n  scenario_pass')), 'foreign or unversioned event')

    def test_production_child_cannot_write_events(self):
        child = ('  scenario_exec code bash -c \'printf "{\\"v\\":2,\\"run\\":\\"x\\",\\"event\\":\\"pass\\",'
                 '\\"id\\":\\"one\\"}\\n" 2>/dev/null >&9 || true\'')
        envelope = self.capture(self.scenario('  scenario_begin\n' + child +
                                              '\n  scenario_assert_exit 0 "$code"\n  scenario_pass'))
        self.assertEqual([r['status'] for r in envelope['results']], ['passed'], envelope)
        self.assertTrue(envelope['complete'], envelope)

    def test_direct_child_cannot_forge_an_own_failure(self):
        # Команда без scenario_exec видит канал событий и каталог диагностики,
        # но не секрет запуска: её поддельный отказ не засчитывается.
        forged = ('  bash -c \'printf "{\\"v\\":2,\\"run\\":\\"%s\\",\\"event\\":\\"assert\\",\\"id\\":\\"one\\",'
                  '\\"ok\\":false,\\"file\\":\\"tests/test-sample.sh\\",\\"line\\":@ASSERTLINE@,\\"expected\\":1,'
                  '\\"actual\\":0,\\"child\\":0,\\"diag\\":\\"%s\\"}\\n" "${SCENARIO__TOKEN:-none}" '
                  '"$SCENARIO_DIAG_DIR/exec-1.err" >&9; exit 1\'')
        envelope = self.capture(self.scenario('  scenario_begin\n  scenario_exec code true\n' + forged +
                                              '\n  scenario_assert_exit 0 "$code"\n  scenario_pass'))
        self.assert_infrastructure(envelope)

    def test_exit_zero_without_pass_is_not_success(self):
        self.assert_infrastructure(self.capture(self.scenario(
            '  scenario_begin\n  scenario_exec code true\n  scenario_assert_exit 0 "$code"\n  echo OK')))

    def test_duplicate_pass_is_rejected(self):
        self.assert_infrastructure(self.capture(self.scenario(
            '  scenario_begin\n  scenario_exec code true\n  scenario_assert_exit 0 "$code"\n  scenario_pass\n'
            + fake('pass'))))

    def test_duplicate_start_is_rejected(self):
        self.assert_infrastructure(self.capture(self.scenario(
            '  scenario_begin\n' + fake('start') + '\n  scenario_exec code true\n'
            '  scenario_assert_exit 0 "$code"\n  scenario_pass')), 'did not start exactly once')

    def test_pass_without_assertion_is_not_success(self):
        self.assert_infrastructure(self.capture(self.scenario('  scenario_begin\n  scenario_exec code true\n  scenario_pass')))

    def test_passed_requires_every_assertion_ok(self):
        self.assert_infrastructure(self.capture(self.scenario(
            '  scenario_begin\n  scenario_exec code true\n'
            + fake('assert', extra=failed_fields('@ASSERTLINE@', 1, 0, 0)) +
            '\n  scenario_assert_exit 0 "$code"\n  scenario_pass')))

    def test_failure_after_an_earlier_failure_is_rejected(self):
        self.assert_infrastructure(self.capture(self.scenario(
            '  scenario_begin\n  scenario_exec code true\n'
            + fake('assert', extra=failed_fields('@ASSERTLINE@', 1, 0, 0)) +
            '\n  scenario_assert_exit 1 "$code"')))

    def test_assertion_outside_the_scenario_file_is_not_own(self):
        (self.root / 'tests/other.sh').write_text('check() { scenario_assert_exit 1 "$1"; }\n')
        body = 'source "$ROOT/tests/other.sh"\n' + self.scenario('  scenario_begin\n  scenario_exec code true\n  check "$code"')
        self.assert_infrastructure(self.capture(body))

    def test_failure_line_must_call_the_helper(self):
        steps = ('  scenario_begin\n  scenario_exec code true\n'
                 '  # scenario_assert_exit is described here, not called\n'
                 + fake('assert', extra=failed_fields(8, 1, 0, 0)) + '\n  exit 1')
        self.assert_infrastructure(self.capture(self.scenario(steps)), 'no verifiable own location')

    def test_equal_codes_are_not_a_failure(self):
        steps = ('  scenario_begin\n  scenario_exec code true\n'
                 + fake('assert', extra=failed_fields('@ASSERTLINE@', 0, 0, 0)) + '\n  exit 1\n'
                 '  scenario_assert_exit 0 "$code"')
        self.assert_infrastructure(self.capture(self.scenario(steps)), 'no verifiable own location')

    def test_crashed_checked_command_is_not_own(self):
        steps = ('  scenario_begin\n  scenario_exec code python3 -c "raise NameError(\'crash\')"\n'
                 '  scenario_assert_exit 0 "$code"\n  scenario_pass')
        self.assert_infrastructure(self.capture(self.scenario(steps)), 'checked command crashed')

    def test_masked_signal_is_not_an_own_failure(self):
        steps = ('  scenario_begin\n'
                 '  scenario_exec code bash -c \'python3 -c "import os,signal; os.kill(os.getpid(),signal.SIGTERM)"; exit 1\'\n'
                 '  scenario_assert_exit 0 "$code"\n  scenario_pass')
        self.assert_infrastructure(self.capture(self.scenario(steps)))

    def test_unknown_nonzero_outcome_is_not_an_own_failure(self):
        steps = ('  scenario_begin\n  scenario_exec code bash -c "exit 7"\n'
                 '  scenario_assert_exit 0 "$code"\n  scenario_pass')
        self.assert_infrastructure(self.capture(self.scenario(steps)))

    def test_cleanup_false_after_own_failure_is_not_counted(self):
        body = ('cleanup() { if [ -f marker ]; then rm marker; false; fi; }\ntrap cleanup EXIT\n' +
                self.scenario('  scenario_begin\n  scenario_exec code touch marker\n'
                              '  scenario_assert_exit 1 "$code"'))
        self.assert_infrastructure(self.capture(body))

    def test_masked_signal_with_zero_code_is_not_own(self):
        steps = ('  scenario_begin\n'
                 '  scenario_exec code bash -c \'python3 -c "import os,signal; os.kill(os.getpid(),signal.SIGTERM)"; exit 0\'\n'
                 '  scenario_assert_exit 1 "$code"\n  scenario_pass')
        self.assert_infrastructure(self.capture(self.scenario(steps)))

    def test_earlier_unknown_command_cannot_hide_behind_a_later_assertion(self):
        steps = ('  scenario_begin\n  scenario_exec preparation bash -c "exit 7"\n'
                 '  scenario_exec code true\n  scenario_assert_exit 1 "$code"')
        self.assert_infrastructure(self.capture(self.scenario(steps)))

    def test_unknown_passing_command_outcome_is_not_success(self):
        steps = ('  scenario_begin\n  scenario_exec code bash -c "exit 7"\n'
                 '  scenario_assert_exit 7 "$code"\n  scenario_pass')
        self.assert_infrastructure(self.capture(self.scenario(steps)))

    def test_exact_domain_outcome_can_prove_an_own_failure(self):
        steps = ('  scenario_begin\n  scenario_accept_exit 1 $\'invalid_status\\n\'\n'
                 '  scenario_exec code bash -c \'printf "invalid_status\\n" >&2; exit 1\'\n'
                 '  scenario_assert_exit 0 "$code"\n  scenario_pass')
        envelope = self.capture(self.scenario(steps))
        self.assertTrue(envelope['complete'], envelope)
        self.assertEqual([(r['status'], r['own_assertion']) for r in envelope['results']], [('failed', True)])

    def test_domain_contract_compares_the_exact_stderr_bytes(self):
        steps = ('  scenario_begin\n  scenario_accept_exit 1 "�"\n'
                 '  scenario_exec code bash -c \'printf "\\377" >&2; exit 1\'\n'
                 '  scenario_assert_exit 0 "$code"')
        self.assert_infrastructure(self.capture(self.scenario(steps)))

    def test_domain_contract_requires_the_full_diagnostic(self):
        steps = ('  scenario_begin\n  scenario_accept_exit 1 $\'invalid_status\\n\'\n'
                 '  scenario_exec code bash -c \'printf "invalid_status\\nunknown failure\\n" >&2; exit 1\'\n'
                 '  scenario_assert_exit 0 "$code"\n  scenario_pass')
        self.assert_infrastructure(self.capture(self.scenario(steps)), 'differs from its exact accepted')

    def test_missing_cleanup_trap_fails_closed(self):
        steps = ('  scenario_begin\n  trap - EXIT\n  scenario_exec code true\n'
                 '  scenario_assert_exit 1 "$code"')
        self.assert_infrastructure(self.capture(self.scenario(steps)), 'cleanup did not finish')

    def test_cleanup_observes_the_original_exit_status(self):
        body = ('cleanup() { if [ "$?" -ne 0 ]; then false; fi; }\ntrap cleanup EXIT\n' +
                self.scenario('  scenario_begin\n  scenario_exec code true\n'
                              '  scenario_assert_exit 1 "$code"'))
        self.assert_infrastructure(self.capture(body))

    def test_declared_cleanup_runs_before_own_failure_is_credited(self):
        body = ('cleanup() { rm -f marker; }\ntrap cleanup EXIT\n' +
                self.scenario('  scenario_begin\n  scenario_exec code touch marker\n'
                              '  scenario_assert_exit 1 "$code"'))
        envelope = self.capture(body)
        self.assertFalse((self.root / 'marker').exists())
        self.assertTrue(envelope['complete'], envelope)
        self.assertTrue(envelope['results'][0]['own_assertion'], envelope)

    def test_launch_failure_code_is_not_own(self):
        steps = ('  scenario_begin\n  scenario_exec code bash -c "exit 127"\n'
                 '  scenario_assert_exit 0 "$code"\n  scenario_pass')
        self.assert_infrastructure(self.capture(self.scenario(steps)), 'failed to launch or was signalled')

    def test_asserted_code_must_be_the_checked_command_code(self):
        steps = ('  scenario_begin\n  scenario_exec code true\n'
                 '  scenario_assert_exit 0 2\n  scenario_pass')
        self.assert_infrastructure(self.capture(self.scenario(steps)), 'not the checked command exit code')

    def test_listing_must_exit_cleanly(self):
        body = ('one() {\n  scenario_begin\n  scenario_exec code true\n  scenario_assert_exit 0 "$code"\n'
                '  scenario_pass\n}\nscenario_declare one one\nscenario_main "$@"\n'
                '[ "${1:-}" != --list-scenarios ] || exit 4\n')
        self.assert_infrastructure(self.capture(body), 'scenario listing exited with 4')

    def test_scenario_file_must_source_the_helper(self):
        head = HEAD.replace('source "$ROOT/tests/helpers/shell-scenarios.sh"',
                            'H=tests/helpers; source "$ROOT/$H/shell-scenarios.sh"')
        envelope = self.capture(self.scenario('  scenario_begin\n  scenario_exec code true\n'
                                              '  scenario_assert_exit 0 "$code"\n  scenario_pass'), head=head)
        self.assert_infrastructure(envelope, 'does not source tests/helpers/shell-scenarios.sh')

    def test_unknown_selection_is_reported(self):
        envelope = self.capture(self.scenario('  scenario_begin\n  scenario_pass'), 'missing')
        self.assert_infrastructure(envelope)
        self.assertIn('unknown or repeated scenario selection: tests/test-sample.sh::missing',
                      envelope['infrastructure_errors'])


if __name__ == '__main__':
    unittest.main()
