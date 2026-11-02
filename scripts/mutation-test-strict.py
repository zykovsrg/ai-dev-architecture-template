#!/usr/bin/env python3
"""Последовательное собственное подтверждение точных unittest/pytest и явных shell идентификаторов."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
COPY_ROOTS = ('scripts', 'modules', 'tests')
SHELL_SCRIPT_TESTS = {'scripts/assistant-workflows-test.sh', 'scripts/hub-smoke-test.sh',
                      'scripts/test-refresh-session-inventory.sh'}
IGNORED = {'.venv', '__pycache__', '.pytest_cache', '.git', '.DS_Store'}
SHELL_HELPER = 'tests/helpers/shell-scenarios.sh'
SUBJECT_TOOL_PAIRS = {
    'test_mutation_strict.py': {'scripts/mutation-test-strict.py'},
    'test_test_method_capture.py': {'scripts/test-method-capture.py'},
    'test_shell_scenario_capture.py': {'scripts/test-shell-capture.py', SHELL_HELPER},
    'test_mutation_filesystem.py': {'scripts/mutation-test-strict.py'},
    'test_mutation_bridge_documents.py': {'scripts/mutation-test-strict.py'},
    'test_mutation_subject_tools.py': {'scripts/mutation-test-strict.py'},
}
PYTHON_OWN_KINDS = ('python_assert', 'unittest_assertion', 'pytest_fail')
OWN_KINDS = {'unittest': PYTHON_OWN_KINDS, 'pytest': PYTHON_OWN_KINDS, 'shell': ('shell_assert_exit',)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ignored(name):
    return (name in IGNORED or name.endswith(('.pyc', '.env')) or
            (name.startswith('.') and name not in ('.gitignore', '.gitkeep')))


def load_filesystem(path):
    spec = importlib.util.spec_from_file_location('strict_filesystem_helpers', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


filesystem = None


def input_hashes(root):
    helper = filesystem if filesystem is not None else load_filesystem(ROOT / 'scripts/mutation-filesystem.py')
    return {name: value['sha256'] for name, value in helper.read_state(root)['files'].items()}


def safe_relative(root, value, directory=False):
    require(isinstance(value, str) and value, 'Пустой относительный путь')
    path = Path(value)
    require(value == path.as_posix(), 'Неканонический относительный путь: ' + value)
    require(not path.is_absolute() and '..' not in path.parts and path.parts and
            path.parts[0] in COPY_ROOTS and not any(ignored(part) for part in path.parts),
            'Путь вне копируемых исходников: ' + value)
    actual = root / path
    require(actual.resolve() == actual, 'Неканонический путь или ссылка: ' + value)
    require(actual.is_dir() if directory else actual.is_file(), 'Отсутствует вход: ' + value)
    return actual


def suite_paths(root, suite):
    require(isinstance(suite, dict), 'Набор должен быть объектом')
    framework = suite.get('framework')
    require(framework in ('unittest', 'pytest', 'shell'), 'Неподдерживаемый framework; оболочка требует собственного адаптера')
    arguments = suite.get('args')
    require(isinstance(arguments, list) and arguments and all(isinstance(v, str) and v for v in arguments),
            'Не заданы аргументы набора')
    helpers = suite.get('helpers', [])
    require(isinstance(helpers, list) and len(helpers) == len(set(helpers)), 'Повторные helper paths')
    for helper in helpers:
        require('tests' in Path(helper).parts, 'Разрешён только тестовый helper')
        safe_relative(root, helper)
    if framework == 'shell':
        require(helpers == [SHELL_HELPER], 'Сценарий оболочки требует только помощник явных сценариев')
        require(len(arguments) == 1 and arguments[0].endswith('.sh') and
                ('tests' in Path(arguments[0]).parts or arguments[0] in SHELL_SCRIPT_TESTS),
                'Набор оболочки задаёт ровно один тестовый сценарий .sh')
        safe_relative(root, arguments[0])
        return None
    if framework == 'unittest':
        require(arguments[0] == 'discover', 'Полный unittest набор требует discover')
        options = {}
        index = 1
        while index < len(arguments):
            flag = arguments[index]
            if flag in ('-v', '-q'):
                index += 1
                continue
            require(flag in ('-s', '-p', '-t') and flag not in options and index + 1 < len(arguments),
                    'Неизвестный или повторный аргумент unittest')
            options[flag] = arguments[index + 1]
            index += 2
        require('-s' in options, 'Требуется точный discovery start-directory')
        safe_relative(root, options['-s'], directory=True)
        if '-t' in options and options['-t'] != '.':
            safe_relative(root, options['-t'], directory=True)
        if '-p' in options:
            require('/' not in options['-p'] and not options['-p'].startswith('.'), 'Недопустимый discovery pattern')
        return options['-s']
    paths = []
    index = 0
    while index < len(arguments):
        value = arguments[index]
        if value in ('-q', '-v', '-vv', '--disable-warnings', '--strict-markers'):
            index += 1
            continue
        if value == '-p':
            require(index + 1 < len(arguments) and arguments[index + 1] in ('pytest_asyncio.plugin', 'no:cacheprovider'),
                    'Неизвестный pytest plugin')
            index += 2
            continue
        require(not value.startswith('-'), 'Неизвестный аргумент pytest')
        path = value.split('::', 1)[0]
        safe_relative(root, path, directory=(root / path).is_dir())
        paths.append(path)
        index += 1
    require(paths, 'Пустой выбор pytest')
    return None


def subject_tools_for(root, suite):
    if 'subject_tools' not in suite:
        return set()
    tools = suite['subject_tools']
    require(isinstance(tools, list) and tools and all(isinstance(v, str) and v for v in tools),
            'subject_tools требует непустой список точных путей')
    require(len(tools) == len(set(tools)), 'subject_tools содержит повторные пути')
    require(not ROOT.resolve().is_relative_to(root), 'subject_tools требует внешний observer вне source')
    arguments = suite['args']
    require(suite.get('framework') == 'unittest' and len(arguments) in (5, 6) and
            arguments[:4] == ['discover', '-s', 'tests', '-p'] and
            (len(arguments) == 5 or arguments[5] in ('-q', '-v')),
            'subject_tools требует точный unittest discover -s tests -p testfile')
    allowed = SUBJECT_TOOL_PAIRS.get(arguments[4], set())
    require(set(tools) <= allowed, 'subject_tools не соответствует точной паре testfile/tool')
    for tool in tools:
        safe_relative(root, tool)
    return set(tools)


def pinned_tool(name, expected):
    path = ROOT / 'scripts' / name
    require(isinstance(expected, str) and len(expected) == 64 and path.resolve() == path and sha(path) == expected,
            'Закреплённый инструмент изменён: ' + name)
    return path


def successful(run):
    view = run['view']
    return bool(view['valid'] and run['returncode'] == 0 and
                view['passed_ids'] == sorted(view['collected_ids']) and not view['failed_ids'])


def qualifies(run, expected):
    view = run['view']
    require(view['valid'] and run['returncode'] == 1 and set(view['failed_ids']) == set(expected),
            'Отказ среды или непредметный результат подмены')
    require(set(expected) <= set(view['own_assertion_ids']), 'Нет собственного assertion каждого ожидаемого ID')
    return True


def capture_view(capture, framework, returncode, copy, expected=None, bindings=None, helpers=()):
    """Представление не меняет сохранённые исходные события адаптера."""
    require(capture.get('schema_version') == 2 and capture.get('framework') == framework and
            capture.get('complete') is True and not capture.get('infrastructure_errors') and
            capture.get('exit_code') == returncode and returncode in (0, 1), 'Незавершённый capture')
    collected = capture['collected_ids']
    started = capture['started_ids']
    require(isinstance(collected, list) and collected and all(isinstance(v, str) and v for v in collected) and
            len(collected) == len(set(collected)) and len(started) == len(set(started)) and
            set(started) == set(collected), 'Нет точного собственного collected/started набора')
    if expected is not None:
        require(set(collected) == set(expected), 'Целевой выбор содержит посторонний или отсутствующий ID')
    grouped = {identity: [] for identity in collected}
    sources = {}
    seen = set()
    allowed_sources = input_hashes(copy)
    for event in capture['results']:
        parent = event['parent_id']
        require(parent in grouped and event['kind'] in ('test', 'subtest'), 'Событие fixture или постороннего ID')
        require(event['kind'] != 'test' or event['id'] == parent, 'Подмена родительского ID')
        key = (event['kind'], event['id'], event['phase'])
        require(key not in seen and '0x' not in event['id'], 'Повторный или неустойчивый runtime ID')
        seen.add(key)
        source = Path(event['source_path'])
        require(source.resolve() == source and source.is_relative_to(copy) and source.is_file(), 'Посторонний источник теста')
        relative = str(source.relative_to(copy))
        require(relative in allowed_sources, 'Источник теста вне закреплённой границы')
        require(parent not in sources or sources[parent] == relative, 'Неоднозначная привязка теста к файлу')
        sources[parent] = relative
        if bindings is not None:
            require(bindings.get(parent) == relative, 'Изменена привязка ID к исходному тесту')
        grouped[parent].append(event)
    passed, failed, own = [], [], []
    for identity, events in grouped.items():
        require(events, 'Нет результата собранного теста')
        if framework == 'pytest':
            require(len(events) == 3 and {e['phase'] for e in events} == {'setup', 'call', 'teardown'},
                    'Нет полного pytest lifecycle')
        else:
            require(all(e['phase'] == 'call' for e in events), 'Отказ fixture unittest')
        statuses = [e['status'] for e in events]
        if all(status == 'passed' for status in statuses):
            require(any(e['kind'] == 'test' and e['id'] == identity for e in events), 'Нет успешного родительского результата')
            passed.append(identity)
        elif all(status in ('passed', 'failed') for status in statuses):
            require(all(e['phase'] == 'call' for e in events if e['status'] == 'failed'), 'Отказ setup/teardown')
            failed.append(identity)
            failures = [e for e in events if e['status'] == 'failed']
            def own_event(event):
                exception = event.get('exception', {})
                origin = exception.get('assertion_origin') or {}
                location = origin.get('location') or {}
                allowed = {event['source_path']} | {str(copy / helper) for helper in helpers}
                return (event.get('own_assertion') is True and event['phase'] == 'call' and
                        origin.get('kind') in OWN_KINDS[framework] and
                        location.get('path') in allowed and location == exception.get('location') and
                        bool(origin.get('source')))
            if all(own_event(event) for event in failures):
                own.append(identity)
    return dict(valid=True, collected_ids=collected[:], passed_ids=sorted(passed), failed_ids=sorted(failed),
                own_assertion_ids=sorted(own), sources=sources)


def verify_saved_artifacts(report, suites):
    """Перед допуском повторно читаем сохранённые байты, а не доверяем памяти."""
    try:
        for run in report['executions']:
            raw_path, log_path = Path(run['capture_path']), Path(run['log_path'])
            require(raw_path.resolve() == raw_path and log_path.resolve() == log_path and
                    sha(raw_path) == run.get('capture_sha256') and sha(log_path) == run.get('log_sha256'),
                    'байты JSON или журнала изменены')
            raw = json.loads(raw_path.read_bytes())
            require(raw == run.get('capture'), 'JSON отличается от сохранённых событий')
            view = capture_view(raw, suites[run['suite']]['framework'], run['returncode'], Path(run['cwd']),
                                run['view']['collected_ids'], run['view']['sources'],
                                suites[run['suite']].get('helpers', []))
            require(view == run['view'] and successful(dict(view=view, returncode=run['returncode'])) == run['passed'],
                    'schema/view отличается от повторно вычисленного')
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise ValueError('Сохранённое доказательство недействительно: ' + str(error)) from error


def main():
    global filesystem
    filesystem = None
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--calendar-python', type=Path)
    parser.add_argument('--timeout', type=float, default=120)
    args = parser.parse_args()
    output = args.output.absolute()
    try:
        source = args.source.resolve(strict=True)
        require(not output.exists() and not output.is_symlink() and output.suffix == '.json' and
                output.resolve() == output,
                'Небезопасный или уже существующий выходной путь')
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    output_checked = False
    report = dict(schema_version=2, complete=False, baselines={}, mutations=[], final_restored={}, executions=[])
    artifacts = output.with_name(output.stem + '-artifacts')
    try:
        source = args.source.resolve(strict=True)
        catalog = args.catalog.resolve(strict=True)
        require(args.timeout > 0, 'Недопустимый timeout')
        require(not artifacts.exists(), 'Каталог доказательств уже существует')
        config_bytes = catalog.read_bytes()
        config = json.loads(config_bytes)
        require(isinstance(config, dict) and config.get('schema_version') == 2, 'Нужен strict manifest schema_version 2')
        legacy_path = pinned_tool('mutation-test.py', config.get('legacy_sha256'))
        extended = any(isinstance(item, dict) and ('operation' in item or item.get('source') in
                       ('README.md', 'modules/core/data/.gitignore',
                        'modules/calendar/policy/bridge/hub_eventkit_bridge.swift',
                        'modules/calendar/policy/bridge/Info.plist',
                        'modules/calendar/policy/bridge/SHA256SUMS')) for item in config.get('mutations', []))
        helper_pin = config.get('filesystem_helper_sha256')
        require(not extended or helper_pin is not None, 'Нужно явное закрепление помощника файловой системы')
        filesystem_path = pinned_tool('mutation-filesystem.py', helper_pin if helper_pin is not None else
                                      sha(ROOT / 'scripts/mutation-filesystem.py'))
        filesystem = load_filesystem(filesystem_path)
        if output.is_relative_to(source) and (filesystem.output_conflicts(output.relative_to(source).as_posix()) or
                filesystem.output_conflicts(artifacts.relative_to(source).as_posix())):
            print('Небезопасный выходной путь внутри входов или template', file=sys.stderr)
            return 2
        output_checked = True
        capture_path = pinned_tool('test-method-capture.py', config.get('capture_sha256'))
        declared_suites = config.get('suites')
        uses_shell = isinstance(declared_suites, dict) and any(
            isinstance(s, dict) and s.get('framework') == 'shell' for s in declared_suites.values())
        shell_capture_path = pinned_tool('test-shell-capture.py', config.get('shell_capture_sha256')) if uses_shell else None
        suites = config['suites']
        require(isinstance(suites, dict) and suites and config.get('mutations'), 'Пустой strict manifest')
        starts = {name: suite_paths(source, suite) for name, suite in suites.items()}
        subjects = {name: subject_tools_for(source, suite) for name, suite in suites.items()}
        report['subject_tools'] = {name: sorted(paths) for name, paths in subjects.items() if paths}
        canonical_state = filesystem.read_state(source)
        canonical_inputs = input_hashes(source)
        active_docs = filesystem.active_documents(source, canonical_state) if extended else {}
        require(canonical_state['absence_probes']['template']['kind'] == 'absent', 'Канонический template должен отсутствовать')
        require(canonical_inputs, 'Нет исходных файлов')
        definitions = {}
        for item in config['mutations']:
            require(isinstance(item['id'], str) and item['id'] and item['id'] not in definitions and item['suite'] in suites,
                    'Повторный ID или неизвестный набор подмены')
            expected = item.get('expected_ids')
            require(isinstance(expected, list) and expected and all(isinstance(v, str) and v for v in expected) and
                    len(expected) == len(set(expected)), 'Нужны непустые уникальные expected_ids')
            definitions[item['id']] = hashlib.sha256(json.dumps(item, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        output.parent.mkdir(parents=True, exist_ok=True)
        artifacts.mkdir()
        with tempfile.TemporaryDirectory(prefix='strict-method-mutations-') as temporary:
            work = Path(temporary).resolve()
            tools = work / '.tools'
            tools.mkdir()
            copied_legacy = tools / 'legacy.py'
            copied_capture = tools / 'capture.py'
            copied_filesystem = tools / 'filesystem.py'
            shutil.copy2(legacy_path, copied_legacy)
            shutil.copy2(capture_path, copied_capture)
            shutil.copy2(filesystem_path, copied_filesystem)
            filesystem = load_filesystem(copied_filesystem)
            tool_paths, copied_paths = [legacy_path, capture_path, filesystem_path, Path(__file__).resolve()], [copied_legacy, copied_capture, copied_filesystem]
            if shell_capture_path:
                copied_shell_capture = tools / 'shell_capture.py'
                shutil.copy2(shell_capture_path, copied_shell_capture)
                tool_paths.append(shell_capture_path)
                copied_paths.append(copied_shell_capture)
            tool_hashes = {str(p): sha(p) for p in tool_paths}
            copied_hashes = {str(p): sha(p) for p in copied_paths}
            spec = importlib.util.spec_from_file_location('strict_legacy_helpers', copied_legacy)
            legacy = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(legacy)
            always_protected = [legacy_path, capture_path, filesystem_path, Path(__file__).resolve()]
            if shell_capture_path:
                always_protected.append(shell_capture_path)
            source_protected = [p for p in always_protected if not p.is_relative_to(source) or
                                p.relative_to(source).as_posix() not in ('scripts/mutation-test.py', 'scripts/mutation-filesystem.py')]
            changes = {item['id']: filesystem.prepare_change(source, item, source_protected, legacy.mutate)
                       for item in config['mutations']}
            expected_tree_states = {}
            catalog_sha = hashlib.sha256(config_bytes).hexdigest()
            report.update(source_root=str(source), catalog_path=str(catalog), manifest=config,
                          manifest_sha256=catalog_sha, definitions_sha256=definitions, canonical_input_hashes=canonical_inputs,
                          canonical_tree_state=canonical_state, active_document_hashes=active_docs,
                          tools_sha256=tool_hashes, copied_tools_sha256=copied_hashes)
            def integrity(copy, expected, wrappers):
                require(sha(catalog) == catalog_sha, 'Изменены байты определения')
                require(input_hashes(source) == canonical_inputs, 'Изменены канонические исходники')
                require(filesystem.read_state(source) == canonical_state, 'Изменена структура канонических исходников')
                require(input_hashes(copy) == expected, 'Изменены исходники копии')
                require(filesystem.read_state(copy) == expected_tree_states[str(copy)], 'Изменена структура или режимы копии')
                require(all(Path(p).is_file() and not Path(p).is_symlink() and Path(p).resolve() == Path(p) and
                            sha(Path(p)) == h for p, h in tool_hashes.items()), 'Изменены канонические инструменты')
                require(all(Path(p).resolve() == Path(p) and sha(Path(p)) == h for p, h in copied_hashes.items()), 'Изменены скопированные инструменты')
                require(all(Path(p).is_file() and not Path(p).is_symlink() and sha(Path(p)) == h for p, h in wrappers.items()), 'Изменён runtime wrapper')
            def invoke(copy, suite_name, arguments, expected_inputs, expected_ids=None, bindings=None):
                number = len(report['executions']) + 1
                name = 'execution-%04d' % number
                raw_path = artifacts / (name + '.json')
                log = artifacts / (name + '.log')
                suite = suites[suite_name]
                python = str(args.calendar_python.absolute()) if suite['framework'] == 'pytest' and args.calendar_python else sys.executable
                runtime = work / name
                home, temporary_dir, binary = runtime / 'home', runtime / 'tmp', runtime / 'bin'
                for path in [home, temporary_dir, binary]:
                    path.mkdir(parents=True, exist_ok=True)
                wrapper = binary / 'python3'
                wrapper.write_text('#!/bin/sh\nexec ' + shlex.quote(python) + ' "$@"\n')
                wrapper.chmod(0o755)
                wrappers = {str(wrapper): sha(wrapper)}
                if args.calendar_python and (copy / 'modules/calendar/policy').is_dir():
                    calendar_wrapper = copy / 'modules/calendar/policy/.venv/bin/python'
                    calendar_wrapper.parent.mkdir(parents=True, exist_ok=True)
                    calendar_wrapper.write_text('#!/bin/sh\nexec ' + shlex.quote(str(args.calendar_python.absolute())) + ' "$@"\n')
                    calendar_wrapper.chmod(0o755)
                    wrappers[str(calendar_wrapper)] = sha(calendar_wrapper)
                pythonpaths = [str(copy)]
                if starts[suite_name]:
                    pythonpaths.append(str(copy / starts[suite_name]))
                calendar_source = copy / 'modules/calendar/policy/src'
                if calendar_source.is_dir():
                    pythonpaths.append(str(calendar_source))
                environment = dict(PATH=str(binary) + ':/usr/bin:/bin:/usr/sbin:/sbin', HOME=str(home),
                                   TMPDIR=str(temporary_dir) + '/', PYTHONPATH=os.pathsep.join(pythonpaths),
                                   PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
                                   HUB_CALENDAR_SKIP_VENV='1', HUB_CALENDAR_SKIP_BRIDGE='1')
                framework_args = list(arguments)
                if suite['framework'] == 'pytest':
                    framework_args += ['--rootdir', str(copy), '-p', 'no:cacheprovider']
                if suite['framework'] == 'shell':
                    command = [python, '-B', str(copied_shell_capture), '--output', str(raw_path)]
                else:
                    command = [python, '-B', str(copied_capture), '--framework', suite['framework'], '--output', str(raw_path)]
                for helper in suite.get('helpers', []):
                    command += ['--allow-helper', str(copy / helper)]
                command += ['--'] + framework_args
                integrity(copy, expected_inputs, wrappers)
                run = dict(suite=suite_name, command=command, cwd=str(copy), expected_tree_state=expected_tree_states[str(copy)], runtime_wrappers_sha256=wrappers,
                           capture_path=str(raw_path), log_path=str(log), returncode=None,
                           view=dict(valid=False, collected_ids=[], passed_ids=[], failed_ids=[], own_assertion_ids=[], sources={}))
                report['executions'].append(run)
                with log.open('wb') as stream:
                    process = subprocess.Popen(command, cwd=copy, env=environment, stdin=subprocess.DEVNULL,
                                               stdout=stream, stderr=subprocess.STDOUT, start_new_session=os.name == 'posix')
                    try:
                        process.wait(timeout=args.timeout)
                    except subprocess.TimeoutExpired:
                        if os.name == 'posix':
                            os.killpg(process.pid, signal.SIGKILL)
                        else:
                            process.kill()
                        process.wait()
                        run['timeout'] = True
                run['returncode'] = process.returncode
                run['log_sha256'] = sha(log)
                integrity(copy, expected_inputs, wrappers)
                run['source_and_tools_checked_before_after'] = True
                if raw_path.is_file():
                    run['capture_sha256'] = sha(raw_path)
                    try:
                        raw = json.loads(raw_path.read_bytes())
                        run['capture'] = raw
                        run['view'] = capture_view(raw, suite['framework'], process.returncode, copy, expected_ids, bindings, suite.get('helpers', []))
                    except (OSError, ValueError, TypeError, KeyError) as error:
                        run['capture_error'] = str(error)
                else:
                    run['capture_error'] = 'Нет структурированного результата'
                run['passed'] = successful(run)
                return run
            base = work / 'baseline'
            filesystem.snapshot(source, base)
            expected_tree_states[str(base)] = canonical_state
            for name, suite in suites.items():
                run = invoke(base, name, suite['args'], canonical_inputs)
                report['baselines'][name] = run
                require(successful(run), 'Полный исходный набор не прошёл')
            oracle_sources = {'scripts/mutation-test-strict.py', 'scripts/test-method-capture.py'}
            if shell_capture_path:
                oracle_sources.add('scripts/test-shell-capture.py')
            test_oracle_sources = set()
            for name, suite in suites.items():
                test_oracle_sources.update(report['baselines'][name]['view']['sources'].values())
                oracle_sources.update(suite.get('helpers', []))
            oracle_sources.update(test_oracle_sources)
            report['oracle_sources'] = sorted(oracle_sources)
            def item_oracle_sources(item):
                # Capability относится к доменным tools только этого suite.
                # Все test sources и helpers выбранного suite всегда защищены.
                return ((oracle_sources - subjects[item['suite']]) | test_oracle_sources |
                        set(suites[item['suite']].get('helpers', [])))
            for item in config['mutations']:
                oracle_files = [source / name for name in item_oracle_sources(item) if (source / name).is_file()]
                changes[item['id']] = filesystem.prepare_change(source, item, [*source_protected, *oracle_files], legacy.mutate)
                require(set(item['expected_ids']) <= set(report['baselines'][item['suite']]['view']['collected_ids']),
                        'Ожидаемый ID отсутствует в полном baseline')
            any_error, any_survivor = False, False
            for index, item in enumerate(config['mutations']):
                copy = work / ('variant-%04d' % index)
                filesystem.snapshot(source, copy)
                expected_tree_states[str(copy)] = canonical_state
                change = changes[item['id']]
                variant_oracles = [copy / name for name in item_oracle_sources(item) if (copy / name).is_file()]
                expected = set(item['expected_ids'])
                suite = suites[item['suite']]
                arguments = sorted(expected)
                if suite['framework'] == 'shell':
                    arguments = [suite['args'][0]] + arguments
                if suite['framework'] == 'pytest':
                    for position, value in enumerate(suite['args']):
                        if value == '-p':
                            arguments += ['-p', suite['args'][position + 1]]
                        elif value in ('-q', '-v', '-vv', '--disable-warnings', '--strict-markers'):
                            arguments.append(value)
                bindings = report['baselines'][item['suite']]['view']['sources']
                row = dict(id=item['id'], suite=item['suite'], definition_sha256=definitions[item['id']],
                           expected_ids=sorted(expected), status='error', proofs=[],
                           baseline_tree_state=canonical_state, change=dict(source=change['source'], operation=change['operation'],
                           original_mode=change['mode'], changed_mode=change['changed_mode']))
                report['mutations'].append(row)
                try:
                    before = invoke(copy, item['suite'], arguments, canonical_inputs, expected, bindings)
                    row['before'] = before
                    require(successful(before), 'Точный исходный выбор не прошёл')
                    mutated_state = filesystem.expected_state(canonical_state, change)
                    row['expected_mutant_tree_state'] = mutated_state
                    mutated_inputs = {name: value['sha256'] for name, value in mutated_state['files'].items()}
                    try:
                        filesystem.apply_change(copy, change, canonical_state, variant_oracles)
                        expected_tree_states[str(copy)] = mutated_state
                        mutant = invoke(copy, item['suite'], arguments, mutated_inputs, expected, bindings)
                        row['mutant'] = mutant
                    finally:
                        filesystem.restore_change(copy, change, variant_oracles)
                        require(filesystem.read_state(copy) == canonical_state, 'Полное состояние не восстановлено')
                        expected_tree_states[str(copy)] = canonical_state
                        row['restored_tree_state'] = filesystem.read_state(copy)
                    restored = invoke(copy, item['suite'], arguments, canonical_inputs, expected, bindings)
                    row['restored'] = restored
                    require(successful(restored), 'Точный восстановленный выбор не прошёл')
                    if mutant['returncode'] == 0:
                        require(successful(mutant), 'Неполный успешный результат подмены')
                        row['status'] = 'survived'
                        any_survivor = True
                    else:
                        qualifies(mutant, expected)
                        row['status'] = 'detected'
                        for identity in sorted(expected):
                            events = [event for event in mutant.get('capture', {}).get('results', [])
                                      if event.get('parent_id') == identity and event.get('own_assertion') is True]
                            row['proofs'].append(dict(id=identity, own_assertion_events=events,
                                                      test_file=bindings[identity], test_sha256=canonical_inputs[bindings[identity]],
                                                      definition_sha256=definitions[item['id']], before_execution=before['capture_path'],
                                                      mutant_execution=mutant['capture_path'], restored_execution=restored['capture_path']))
                except (OSError, ValueError, TypeError, KeyError) as error:
                    row['error'] = str(error)
                    any_error = True
                finally:
                    try:
                        filesystem.restore_change(copy, change, variant_oracles)
                        require(filesystem.read_state(copy) == canonical_state, 'Полное состояние не восстановлено')
                    except (OSError, ValueError) as error:
                        row['restoration_error'] = str(error)
                        row['status'] = 'error'
                        row['proofs'] = []
                        any_error = True
            for name, suite in suites.items():
                run = invoke(base, name, suite['args'], canonical_inputs)
                report['final_restored'][name] = run
                require(successful(run) and run['view']['collected_ids'] == report['baselines'][name]['view']['collected_ids'],
                        'Полный восстановленный набор изменился или не прошёл')
            verify_saved_artifacts(report, suites)
            report['complete'] = not any_error and not any_survivor
            report['exit_code'] = 2 if any_error else (1 if any_survivor else 0)
            report['manifest_sha256_after'] = sha(catalog)
            report['canonical_input_hashes_after'] = input_hashes(source)
            report['canonical_tree_state_after'] = filesystem.read_state(source)
            report['tools_sha256_after'] = {p: sha(Path(p)) for p in tool_hashes}
            report['copied_tools_sha256_after'] = {p: sha(Path(p)) for p in copied_hashes}
    except (OSError, ValueError, TypeError, KeyError, SyntaxError) as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
        report['exit_code'] = 2
    report['proof_gate'] = report['complete'] and report['exit_code'] == 0
    for row in report['mutations']:
        row['proof_gate'] = report['proof_gate'] and row['status'] == 'detected'
    if not output_checked and output.is_relative_to(source):
        # При недоступном/незакреплённом помощнике отчёт не должен менять входы.
        # Это только консервативный отказ до его загрузки; обычный допуск выше
        # использует общую политику снимка и отдельную пробу отсутствия template.
        parts = output.relative_to(source).parts
        excluded_audit = parts[:2] == ('docs', 'audits')
        if parts and parts[0] in ('scripts', 'modules', 'tests', 'README.md', 'getting-started', 'docs', 'template') and not excluded_audit:
            print(report.get('error', 'Небезопасный выходной путь'), file=sys.stderr)
            return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(complete=report['complete'], exit_code=report['exit_code'],
                          proofs=sum(len(item['proofs']) for item in report['mutations'])), ensure_ascii=False))
    return report['exit_code']


if __name__ == '__main__':
    sys.exit(main())
