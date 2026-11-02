#!/usr/bin/env python3
"""Проверять каталог контрольных ошибок в отдельной временной копии проекта."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
COPY_ROOTS = ('scripts', 'modules', 'tests')
IGNORED = {'.venv', '__pycache__', '.pytest_cache', '.git', '.DS_Store'}


def relative_file(root, value):
    path = Path(value)
    if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0] not in COPY_ROOTS:
        raise ValueError('Недопустимый путь: ' + value)
    probe = root
    for part in path.parts:
        probe = probe / part
        if probe.is_symlink():
            raise ValueError('Ссылка вместо исходного файла: ' + value)
    if not probe.is_file():
        raise ValueError('Нет исходного файла: ' + value)
    return probe


def mutate(text, item):
    if item['symbol'] == '@shell':
        if Path(item['source']).suffix != '.sh':
            raise ValueError('Мутация оболочки требует сценарий .sh')
        if not item['before'] or text.count(item['before']) != 1:
            raise ValueError('Замена должна встретиться ровно один раз: ' + item['id'])
        changed = text.replace(item['before'], item['after'])
        if changed == text:
            raise ValueError('Изменение не меняет исходник: ' + item['id'])
        validation = subprocess.run(['bash', '-n'], input=changed, capture_output=True,
                                    text=True, timeout=10)
        if validation.returncode:
            raise ValueError('Некорректная мутация оболочки: ' + item['id'])
        return changed
    if item['symbol'] == '@document':
        if Path(item['source']).suffix not in ('.md', '.txt', '.json'):
            raise ValueError('Мутация документа требует текстовый документ')
        if not item['before'] or text.count(item['before']) != 1:
            raise ValueError('Замена должна встретиться ровно один раз: ' + item['id'])
        changed = text.replace(item['before'], item['after'])
        if changed == text:
            raise ValueError('Изменение не меняет исходник: ' + item['id'])
        if Path(item['source']).suffix == '.json':
            json.loads(changed)
        return changed
    nodes = ast.parse(text).body
    node = None
    for name in item['symbol'].split('.'):
        matches = [n for n in nodes if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == name]
        if len(matches) != 1:
            raise ValueError('Не найден единственный символ: ' + item['symbol'])
        node = matches[0]
        nodes = node.body
    lines = text.splitlines(keepends=True)
    section = ''.join(lines[node.lineno - 1:node.end_lineno])
    if not item['before'] or section.count(item['before']) != 1:
        raise ValueError('Замена должна встретиться ровно один раз: ' + item['id'])
    section = section.replace(item['before'], item['after'])
    changed = ''.join(lines[:node.lineno - 1]) + section + ''.join(lines[node.end_lineno:])
    if changed == text:
        raise ValueError('Изменение не меняет исходник: ' + item['id'])
    ast.parse(changed)
    return changed


def snapshot(source, destination):
    def ignore(directory, names):
        skipped = [n for n in names if n in IGNORED
                   or (n.startswith('.') and n not in ('.gitignore', '.gitkeep'))
                   or n.endswith(('.pyc', '.env'))]
        for name in names:
            if name not in skipped and (Path(directory) / name).is_symlink():
                raise ValueError('Ссылки в копии запрещены: ' + str(Path(directory) / name))
        return skipped
    for name in COPY_ROOTS:
        origin = source / name
        if origin.is_symlink():
            raise ValueError('Ссылка вместо каталога: ' + name)
        if origin.is_dir():
            shutil.copytree(origin, destination / name, ignore=ignore)


def invoke(command, root, python, timeout):
    started = time.monotonic()
    env = dict(os.environ)
    # Запрещаем импорт установленной версии календаря и пользовательских расширений.
    env['PYTHONPATH'] = os.pathsep.join([str(root), str(root / 'modules/calendar/policy/src')])
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONNOUSERSITE'] = '1'
    env['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    proc = subprocess.Popen([python, '-B', *command], cwd=root, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            start_new_session=os.name == 'posix')
    try:
        output, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if os.name == 'posix':
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
        output, _ = proc.communicate()
        return {'status': 'error', 'reason': 'timeout', 'output': output, 'seconds': round(time.monotonic()-started, 3)}
    counts = re.findall(r'Ran (\d+) tests?\b', output)
    pytest_counts = re.findall(r'(\d+) (?:passed|failed)\b', output)
    count = sum(map(int, counts or pytest_counts))
    if counts:
        count -= sum(map(int, re.findall(r'\bskipped=(\d+)', output)))
    import_error = any(s in output for s in ('ImportError', 'ModuleNotFoundError', 'SyntaxError', 'Failed to import test module', 'ERROR collecting'))
    assertions = re.search(r'FAILED \([^\n]*failures=[1-9]', output) or re.search(r'\b[1-9]\d* failed\b', output)
    if import_error or not count:
        status = 'error'
    elif proc.returncode == 0:
        status = 'passed'
    elif proc.returncode == 1 and assertions:
        status = 'failed'
    else:
        status = 'error'
    return {'status': status, 'tests': count, 'returncode': proc.returncode,
            'seconds': round(time.monotonic()-started, 3), 'output': output}


def run_suite(suite, root, python, timeout):
    commands = []
    for command in suite['commands']:
        result = invoke(command, root, python, timeout)
        commands.append(result)
        if result['status'] != 'passed':
            return {'status': result['status'], 'commands': commands}
    return {'status': 'passed', 'commands': commands}


def validate(config, source, selected):
    suites = config['suites']
    if not selected or any(name not in suites for name in selected):
        raise ValueError('Неизвестный или пустой набор проверок')
    ids = set()
    selected_items = []
    for item in config['mutations']:
        if item['id'] in ids:
            raise ValueError('Повторяющийся идентификатор: ' + item['id'])
        ids.add(item['id'])
        if item['suite'] not in suites:
            raise ValueError('Нет набора для ошибки: ' + item['id'])
        if 'equivalent_reason' in item and not item['equivalent_reason'].strip():
            raise ValueError('Исключение требует объяснения')
        if item['suite'] in selected:
            file = relative_file(source, item['source'])
            mutate(file.read_text(encoding='utf-8'), item)
            selected_items.append(item)
    for name in selected:
        if not any(i['suite'] == name for i in selected_items):
            raise ValueError('Набор не содержит контрольных ошибок: ' + name)
        commands = suites[name]['commands']
        if not commands or any(not c or not all(isinstance(v, str) for v in c) for c in commands):
            raise ValueError('Не заданы команды проверок: ' + name)
    return selected_items


def execute(source, config, selected, timeout, calendar_python, report):
    items = validate(config, source, selected)
    with tempfile.TemporaryDirectory(prefix='hub-mutation-') as temporary:
        base = Path(temporary) / 'baseline'
        snapshot(source, base)
        interpreters = {s: calendar_python if s == 'calendar' else sys.executable for s in selected}
        for name in selected:
            result = run_suite(config['suites'][name], base, interpreters[name], timeout)
            report['baselines'][name] = result
            print('Исходные проверки ' + name + ': ' + result['status'], flush=True)
            if result['status'] != 'passed':
                report['error'] = 'Исходные проверки не прошли: ' + name
                return 2
        exit_code = 0
        for index, item in enumerate(items):
            work = Path(temporary) / ('variant-' + str(index))
            shutil.copytree(base, work)
            file = relative_file(work, item['source'])
            original = file.read_text(encoding='utf-8')
            file.write_text(mutate(original, item), encoding='utf-8')
            result = run_suite(config['suites'][item['suite']], work, interpreters[item['suite']], timeout)
            equivalent = item.get('equivalent_reason')
            if result['status'] == 'error':
                status = 'error'
            elif equivalent:
                status = 'equivalent' if result['status'] == 'passed' else 'exception_changed'
            else:
                status = 'detected' if result['status'] == 'failed' else 'survived'
            report['mutations'].append({**item, 'status': status, 'result': result,
                                        'source_sha256': hashlib.sha256(original.encode()).hexdigest()})
            print(item['id'] + ': ' + status, flush=True)
            if status in ('error', 'exception_changed'):
                exit_code = 2
            elif status == 'survived' and exit_code == 0:
                exit_code = 1
            shutil.rmtree(work)
        return exit_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT)
    parser.add_argument('--catalog', type=Path, default=ROOT / 'tests/mutation-cases.json')
    parser.add_argument('--suite', action='append', help='Выбрать участок; можно повторить')
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--calendar-python', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'tmp/mutation-results.json')
    parser.add_argument('--list', action='store_true')
    args = parser.parse_args()
    report = {'baselines': {}, 'mutations': [], 'exit_code': 2}
    try:
        source = args.source.resolve(strict=True)
        config = json.loads(args.catalog.read_text(encoding='utf-8'))
        selected = list(dict.fromkeys(args.suite or config['suites']))
        if args.timeout <= 0:
            raise ValueError('Ожидание должно быть положительным')
        if args.list:
            validate(config, source, selected)
            for item in config['mutations']:
                if item['suite'] in selected:
                    print(item['suite'] + '/' + item['id'])
            return 0
        local_python = source / 'modules/calendar/policy/.venv/bin/python'
        calendar_python = args.calendar_python or (local_python if local_python.exists() else Path(sys.executable))
        report['exit_code'] = execute(source, config, selected, args.timeout, str(calendar_python.absolute()), report)
    except (OSError, ValueError, KeyError, TypeError, SyntaxError) as error:
        report['error'] = str(error)
        print('Ошибка: ' + str(error), file=sys.stderr)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Отчёт: ' + str(args.output))
    return report['exit_code']


if __name__ == '__main__':
    sys.exit(main())
