#!/usr/bin/env python3
"""Фактический сбор ID без исполнения тел тестов; это не доказательство мутации."""
import argparse
import importlib.util
import inspect
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CALENDAR_TESTS = 'modules/calendar/policy/tests'
SCRIPT_TESTS = frozenset(('scripts/assistant-workflows-test.sh', 'scripts/hub-smoke-test.sh',
                          'scripts/test-refresh-session-inventory.sh'))
DISPATCHERS = frozenset(('scripts/architecture-test.sh',
                         'modules/calendar/tests/apple-calendar-policy-test.sh'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def case_key(record):
    framework, source, identity = (record.get(key) for key in ('framework', 'source', 'id'))
    require(framework in ('unittest', 'pytest', 'shell'), 'Неизвестный вид теста')
    require(isinstance(source, str) and source and Path(source).as_posix() == source and
            not Path(source).is_absolute() and '..' not in Path(source).parts and
            Path(source).parts[0] in ('scripts', 'tests', 'modules'), 'Неканонический источник теста')
    require(isinstance(identity, str) and identity and not any(c in identity for c in '\n\r\0'),
            'Пустой или повреждённый ID теста')
    return framework, source, identity


def coverage_gaps(inventory, claims):
    actual = [case_key(record) for record in inventory]
    require(actual and len(actual) == len(set(actual)), 'Пустой или повторный фактический состав')
    covered = {case_key(record) for record in claims}
    return sorted(set(actual) - covered), sorted(covered - set(actual))


def source_record(source, framework, identity, path):
    path = Path(path).absolute()
    require(path.resolve() == path and path.is_file() and path.is_relative_to(source),
            'Источник собранного теста вне снимка или является ссылкой')
    record = dict(framework=framework, source=path.relative_to(source).as_posix(), id=identity)
    case_key(record)
    return record


def worker(source, framework, target, diagnostics):
    sys.path.insert(0, str(source))
    if framework == 'unittest':
        suite = unittest.TestLoader().discover(str(source / target), pattern='test_*.py')
        records = []
        def visit(node):
            if isinstance(node, unittest.TestSuite):
                for child in node:
                    visit(child)
            else:
                require(not isinstance(node, unittest.loader._FailedTest), 'Ошибка импорта тестового файла')
                method = inspect.unwrap(getattr(node, node._testMethodName))
                records.append(source_record(source, framework, node.id(), inspect.getsourcefile(method)))
        visit(suite)
        return records
    if framework == 'pytest':
        import pytest
        records = []
        class Collector:
            def pytest_collection_finish(self, session):
                for item in session.items:
                    records.append(source_record(source, framework, item.nodeid, item.path))
        code = pytest.main([target, '--collect-only', '-q', '--rootdir', str(source),
                            '-p', 'no:cacheprovider', '-p', 'pytest_asyncio.plugin'], plugins=[Collector()])
        require(code == 0, 'Неуспешный сбор pytest')
        return records
    capture = load('inventory_shell_capture', ROOT / 'scripts/test-shell-capture.py')
    ids, errors = capture.declared_ids(source / target, diagnostics)
    require(not errors, 'Неуспешный сбор сценариев: ' + '; '.join(errors))
    return [source_record(source, framework, target + '::' + identity, source / target) for identity in ids]


def test_files(state):
    python, shell = set(), set()
    for name in state['files']:
        path = Path(name)
        if path.suffix == '.py' and (path.name.startswith('test_') or path.name.endswith('_test.py')):
            require('tests' in path.parts, 'Тестовый файл вне зарегистрированной области: ' + name)
            python.add(name)
        if path.suffix == '.sh' and (path.name.startswith(('test-', 'test_')) or path.name.endswith('-test.sh')):
            if name not in DISPATCHERS:
                require('tests' in path.parts or name in SCRIPT_TESTS,
                        'Новый сценарий вне зарегистрированной области: ' + name)
                shell.add(name)
    return python, shell


def collect(source, calendar_python=None):
    source = Path(source).absolute()
    if calendar_python is not None:
        calendar_python = Path(calendar_python).absolute()
    require(source.is_dir() and source.resolve() == source, 'Неканонический корень снимка')
    filesystem = load('inventory_filesystem', ROOT / 'scripts/mutation-filesystem.py')
    before = filesystem.read_state(source)
    python_files, shell_files = test_files(before)
    targets = set()
    # pytest поддерживает также *_test.py и настраиваемые имена. Наличие
    # области, а не найденного префикса файла, определяет запуск его сборщика.
    if (source / CALENDAR_TESTS).is_dir():
        targets.add(('pytest', CALENDAR_TESTS))
    for name in python_files:
        if name.startswith(CALENDAR_TESTS + '/'):
            targets.add(('pytest', CALENDAR_TESTS))
        else:
            parts = Path(name).parts
            targets.add(('unittest', Path(*parts[:parts.index('tests') + 1]).as_posix()))
    targets.update(('shell', name) for name in shell_files)
    records = []
    with tempfile.TemporaryDirectory(prefix='mutation-inventory-') as temporary:
        runtime = Path(temporary).resolve()
        home, temp = runtime / 'home', runtime / 'tmp'
        home.mkdir()
        temp.mkdir()
        for number, (framework, target) in enumerate(sorted(targets)):
            output = runtime / ('collection-%d.json' % number)
            diagnostics = runtime / ('diagnostics-%d' % number)
            diagnostics.mkdir()
            python = str(calendar_python) if framework == 'pytest' and calendar_python else sys.executable
            env = dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin', HOME=str(home), TMPDIR=str(temp) + '/',
                       PYTHONPATH=os.pathsep.join((str(source), str(source / 'modules/calendar/policy/src'))),
                       PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
            with (runtime / ('collection-%d.log' % number)).open('wb') as log:
                process = subprocess.Popen([python, '-B', str(Path(__file__).resolve()), '--worker', framework,
                                            '--source', str(source), '--target', target, '--output', str(output),
                                            '--diagnostics', str(diagnostics)], cwd=source, env=env,
                                           stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                           start_new_session=os.name == 'posix')
                try:
                    process.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    if os.name == 'posix':
                        os.killpg(process.pid, signal.SIGKILL)
                    else:
                        process.kill()
                    process.wait()
                    raise ValueError('Сбор превысил время ожидания: ' + target)
            require(process.returncode == 0 and output.is_file(), 'Ошибка фактического сбора: ' + target)
            result = json.loads(output.read_text())
            require(isinstance(result, list) and result, 'Пустой фактический набор: ' + target)
            records.extend(result)
    require(filesystem.read_state(source) == before, 'Сбор изменил входные файлы')
    coverage_gaps(records, records)
    represented = {record['source'] for record in records}
    require(represented == python_files | shell_files, 'Тестовые файлы потеряны или добавлены при сборе: ' +
            repr(sorted(represented ^ (python_files | shell_files))))
    return sorted(records, key=case_key)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--calendar-python', type=Path)
    parser.add_argument('--worker', choices=('unittest', 'pytest', 'shell'))
    parser.add_argument('--target')
    parser.add_argument('--diagnostics', type=Path)
    args = parser.parse_args()
    if args.worker:
        result = worker(args.source, args.worker, args.target, args.diagnostics)
    else:
        result = collect(args.source, args.calendar_python)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
