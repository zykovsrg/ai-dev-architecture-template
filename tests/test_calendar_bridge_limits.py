"""Реальный сборщик передаёт ограничения ресурсов конечной команде компиляции."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / 'modules/calendar/scripts/build-calendar-bridge.sh'
BRIDGE = ROOT / 'modules/calendar/policy/bridge'


@unittest.skipUnless(Path('/usr/libexec/PlistBuddy').is_file(),
                     'Сборщик требует системную утилиту PlistBuddy в macOS')
class CalendarBridgeLimitsTests(unittest.TestCase):
    def test_builder_bounds_actual_compiler_and_preserves_source_output(self):
        with tempfile.TemporaryDirectory(prefix='calendar-bridge-limits-') as temporary:
            work = Path(temporary).resolve()
            bridge = work / 'bridge with spaces'
            bridge.mkdir()
            binary = work / 'bin'
            binary.mkdir()
            log = work / 'actual-commands.jsonl'
            for name in ['hub_eventkit_bridge.swift', 'Info.plist']:
                shutil.copy2(BRIDGE / name, bridge / name)
            stub = '''import json, os, sys
from pathlib import Path
name = Path(sys.argv[0]).name
with Path(os.environ['BRIDGE_TEST_COMMAND_LOG']).open('a') as stream:
    stream.write(json.dumps({'command': name, 'argv': sys.argv[1:]}) + '\\n')
if name == 'swiftc':
    output = Path(sys.argv[sys.argv.index('-o') + 1])
    output.write_text('#!/bin/sh\\nexit 0\\n')
    output.chmod(0o755)
'''
            for name in ['swiftc', 'codesign']:
                executable = binary / name
                executable.write_text('#!' + sys.executable + '\n' + stub, encoding='utf-8')
                executable.chmod(0o755)
            environment = os.environ.copy()
            environment.update(PATH=str(binary) + os.pathsep + environment.get('PATH', ''),
                               BRIDGE_TEST_COMMAND_LOG=str(log))
            result = subprocess.run(['bash', str(BUILDER), '--bridge-dir', str(bridge) + '/.'],
                                    env=environment, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            calls = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual([call['command'] for call in calls], ['swiftc', 'codesign'])
            arguments = calls[0]['argv']
            self.assertEqual(arguments.count('-j'), 1, 'Компилятор должен получить один предел -j')
            self.assertEqual(arguments[arguments.index('-j') + 1], '2', 'Предел -j должен равняться 2')
            self.assertEqual(arguments.count('-num-threads'), 1, 'Компилятор должен получить один предел потоков')
            self.assertEqual(arguments[arguments.index('-num-threads') + 1], '1', 'Предел потоков должен равняться 1')
            self.assertIn('-O', arguments)
            source = bridge / 'hub_eventkit_bridge.swift'
            self.assertEqual([value for value in arguments if value.endswith('.swift')], [str(source)])
            output = bridge / 'HubCalendarBridge.app/Contents/MacOS/HubCalendarBridge'
            self.assertEqual(arguments.count('-o'), 1)
            self.assertEqual(arguments[arguments.index('-o') + 1], str(output))
            self.assertEqual(result.stdout.strip(), str(output))
            self.assertTrue(output.is_file())
            self.assertTrue(os.access(output, os.X_OK))
            self.assertEqual((output.parent.parent / 'Info.plist').read_bytes(), (bridge / 'Info.plist').read_bytes())
            self.assertEqual(arguments[-2:], ['-Xlinker', str(bridge / 'Info.plist')])
            self.assertEqual(calls[1]['argv'][-1], str(bridge / 'HubCalendarBridge.app'))
            self.assertIn('com.personal-ai-hub.calendar-bridge', calls[1]['argv'])


if __name__ == '__main__':
    unittest.main()
