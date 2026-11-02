#!/usr/bin/env python3
"""Record real outer framework events; never infer assertions from output text."""
import argparse
import ast
import dis
import inspect
import json
import os
import sys
import unittest
from pathlib import Path


def source_path(value):
    return str(Path(value).resolve()) if value else None


def python_assert_origin(location, code, offset):
    """Require an actual assert statement at the executing traceback position."""
    if location is None:
        return None
    try:
        source = Path(location['path']).read_text()
        tree = ast.parse(source)
    except (OSError, UnicodeError, SyntaxError):
        return None
    instruction = next((instruction for instruction in reversed(list(dis.get_instructions(code)))
                        if instruction.offset <= offset), None)
    position = getattr(instruction, 'positions', None)
    column = getattr(position, 'col_offset', None)
    line = location['line']

    def contains(node):
        if not node.lineno <= line <= node.end_lineno:
            return False
        if column is None:
            return True
        return ((line != node.lineno or column >= node.col_offset) and
                (line != node.end_lineno or column < node.end_col_offset))

    # Without column positions, ambiguous same-line raise/assert is refused.
    if any(contains(node) for node in ast.walk(tree) if isinstance(node, ast.Raise)):
        return None
    assertions = [node for node in ast.walk(tree) if isinstance(node, ast.Assert) and contains(node)]
    if not assertions:
        return None
    node = assertions[-1]
    return {'kind': 'python_assert', 'location': location,
            'source': ast.get_source_segment(source, node),
            'start_line': node.lineno, 'end_line': node.end_lineno}


def unittest_assertion_codes():
    methods = [value for name, value in vars(unittest.TestCase).items()
               if name.startswith('assert') or name in ('fail', '_baseAssertEqual')]
    methods.append(unittest.case._AssertRaisesBaseContext._raiseFailure)
    return {method.__code__ for method in methods if hasattr(method, '__code__')}


def exception_event(error, test_path, helper_paths, framework_paths, call_phase=True,
                    pytest_failure=None, pytest_assertions=()):
    kind, value, trace = error
    frames = []
    raw_frames = []
    while trace:
        frame = trace.tb_frame
        frames.append({'path': source_path(frame.f_code.co_filename),
                       'line': trace.tb_lineno, 'function': frame.f_code.co_name})
        raw_frames.append((frame.f_code, trace.tb_lasti))
        trace = trace.tb_next
    user_frames = [frame for frame in frames if not any(
        Path(frame['path']).is_relative_to(path) for path in framework_paths)]
    location = user_frames[-1] if user_frames else (frames[-1] if frames else None)
    allowed = {test_path} | helper_paths
    origin = None
    if raw_frames:
        last_code, last_offset = raw_frames[-1]
        if issubclass(kind, AssertionError):
            if last_code in unittest_assertion_codes():
                origin = {'kind': 'unittest_assertion', 'location': location}
            elif last_code in pytest_assertions:
                # Совпадение типа прошло, но доверенный pytest.raises отверг текст.
                # Внутреннюю ошибку контекста (например, без __enter__) не засчитываем.
                context = value.__traceback__
                while context and context.tb_next:
                    context = context.tb_next
                raises_context = context.tb_frame.f_locals.get('self') if context else None
                reason = getattr(raises_context, '_fail_reason', None)
                if reason is not None and str(value) == reason:
                    origin = {'kind': 'pytest_fail', 'location': location,
                              'assertion_api': 'pytest.raises'}
            else:
                origin = python_assert_origin(frames[-1], last_code, last_offset)
        elif pytest_failure and last_code is pytest_failure[0] and issubclass(kind, pytest_failure[1]):
            origin = {'kind': 'pytest_fail', 'location': location}
    if origin and 'source' not in origin and location:
        try:
            origin['source'] = Path(location['path']).read_text().splitlines()[location['line'] - 1]
        except (OSError, UnicodeError, IndexError):
            origin['source'] = None
    own = bool(call_phase and origin and location
               and location['path'] in allowed)
    return {'type': kind.__module__ + '.' + kind.__qualname__,
            'message': str(value), 'location': location, 'traceback': frames,
            'assertion_origin': origin}, own


def run_unittest(arguments, envelope, helpers):
    framework_paths = [Path(unittest.__file__).resolve().parent]

    class RecordingResult(unittest.TextTestResult):
        def startTest(self, test):
            super().startTest(test)
            envelope['started_ids'].append(test.id())

        def record(self, test, status, error=None, kind='test'):
            parent = getattr(test, 'test_case', test)
            method_name = getattr(parent, '_testMethodName', None)
            method = getattr(parent, method_name, None) if method_name else None
            definition = inspect.unwrap(method) if method else type(parent)
            path = source_path(inspect.getsourcefile(definition)) if method else None
            if method_name is None:
                kind = 'fixture'
            record = {'id': test.id(), 'parent_id': parent.id(), 'kind': kind,
                      'phase': 'fixture' if kind == 'fixture' else 'call', 'status': status, 'source_path': path,
                      'own_assertion': False}
            if error:
                trace = error[2]
                call_phase = False
                while trace:
                    if method and trace.tb_frame.f_code is getattr(method, '__code__', None):
                        call_phase = True
                    trace = trace.tb_next
                record['exception'], record['own_assertion'] = exception_event(
                    error, path, helpers, framework_paths, call_phase)
                if not call_phase:
                    record['phase'] = 'fixture'
                if path is None and record['exception']['location']:
                    record['source_path'] = record['exception']['location']['path']
            envelope['results'].append(record)

        def addSuccess(self, test):
            super().addSuccess(test)
            self.record(test, 'passed')

        def addFailure(self, test, error):
            self.record(test, 'failed', error)
            super().addFailure(test, error)

        def addError(self, test, error):
            self.record(test, 'error', error)
            super().addError(test, error)

        def addSkip(self, test, reason):
            super().addSkip(test, reason)
            self.record(test, 'skipped', kind='subtest' if hasattr(test, 'test_case') else 'test')

        def addExpectedFailure(self, test, error):
            self.record(test, 'expected_failure', error)
            super().addExpectedFailure(test, error)
            envelope['results'][-1]['own_assertion'] = False

        def addUnexpectedSuccess(self, test):
            super().addUnexpectedSuccess(test)
            self.record(test, 'unexpected_success')

        def addSubTest(self, test, subtest, error):
            status = 'passed' if error is None else ('failed' if issubclass(error[0], test.failureException) else 'error')
            self.record(subtest, status, error, 'subtest')
            super().addSubTest(test, subtest, error)

    class RecordingRunner(unittest.TextTestRunner):
        resultclass = RecordingResult

        def run(self, suite):
            def collect(node):
                if isinstance(node, unittest.TestSuite):
                    for child in node:
                        collect(child)
                else:
                    envelope['collected_ids'].append(node.id())
                    if isinstance(node, unittest.loader._FailedTest):
                        envelope['infrastructure_errors'].append('unittest collection failed: ' + node.id())
            collect(suite)
            return super().run(suite)

    program = unittest.main(module=None, argv=['unittest'] + arguments,
                            testRunner=RecordingRunner, exit=False)
    result = program.result
    envelope['exit_code'] = 0 if result.wasSuccessful() else 1
    if not envelope['collected_ids']:
        envelope['exit_code'] = 5
    envelope['complete'] = bool(envelope['collected_ids'] and not envelope['infrastructure_errors'])


def run_pytest(arguments, envelope, helpers):
    import pytest
    import _pytest
    framework_paths = [Path(_pytest.__file__).resolve().parent, Path(pytest.__file__).resolve().parent,
                       Path(unittest.__file__).resolve().parent]
    fail_callable = pytest.fail if inspect.isfunction(pytest.fail) else type(pytest.fail).__call__
    raises_assertions = {type(pytest.raises(Exception)).__exit__.__code__}

    class Recorder:
        def pytest_collection_finish(self, session):
            envelope['collected_ids'] = [item.nodeid for item in session.items]

        def pytest_collectreport(self, report):
            if report.failed:
                envelope['infrastructure_errors'].append('pytest collection failed: ' + report.nodeid)

        def pytest_runtest_logstart(self, nodeid, location):
            envelope['started_ids'].append(nodeid)

        @pytest.hookimpl(hookwrapper=True)
        def pytest_runtest_makereport(self, item, call):
            outcome = yield
            report = outcome.get_result()
            record = {'id': item.nodeid, 'parent_id': item.nodeid, 'kind': 'test',
                      'phase': report.when, 'status': 'passed' if report.passed else
                      ('skipped' if report.skipped else ('failed' if report.when == 'call' else 'error')),
                      'source_path': source_path(str(item.path)), 'own_assertion': False}
            if call.excinfo is not None:
                error = (call.excinfo.type, call.excinfo.value, call.excinfo.tb)
                call_phase = report.when == 'call'
                if isinstance(getattr(item, 'instance', None), unittest.TestCase):
                    # pytest объединяет setUp/tearDown и метод в фазу call.
                    # Собственное утверждение требует кадр самого выбранного метода.
                    code = getattr(inspect.unwrap(item.obj), '__code__', None)
                    trace = call.excinfo.tb
                    method_called = False
                    while trace:
                        if trace.tb_frame.f_code is code:
                            method_called = True
                        trace = trace.tb_next
                    call_phase = call_phase and method_called
                record['exception'], own = exception_event(
                    error, record['source_path'], helpers, framework_paths, call_phase,
                    pytest_failure=(fail_callable.__code__, pytest.fail.Exception),
                    pytest_assertions=raises_assertions)
                record['own_assertion'] = bool(report.failed and own)
            envelope['results'].append(record)

    envelope['exit_code'] = int(pytest.main(arguments, plugins=[Recorder()]))
    envelope['complete'] = bool(envelope['collected_ids'] and envelope['exit_code'] in (0, 1)
                                and not envelope['infrastructure_errors'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--framework', choices=('unittest', 'pytest'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-helper', action='append', default=[])
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    options = parser.parse_args()
    arguments = options.arguments[1:] if options.arguments[:1] == ['--'] else options.arguments
    envelope = {'schema_version': 2, 'framework': options.framework, 'complete': False,
                'exit_code': 2, 'collected_ids': [], 'started_ids': [], 'results': [],
                'infrastructure_errors': []}
    sys.path.insert(0, os.getcwd())
    try:
        helpers = {source_path(path) for path in options.allow_helper}
        if options.framework == 'unittest':
            run_unittest(arguments, envelope, helpers)
        else:
            run_pytest(arguments, envelope, helpers)
    except BaseException as error:
        envelope['complete'] = False
        envelope['exit_code'] = 2
        envelope['infrastructure_errors'].append(type(error).__name__ + ': ' + str(error))
    options.output.write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + '\n')
    return envelope['exit_code']


if __name__ == '__main__':
    sys.exit(main())
