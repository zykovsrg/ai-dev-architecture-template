#!/usr/bin/env python3
"""Полный постоянный запуск: фактический состав, внешние инструменты и собственные доказательства."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DRIVER_FILES = ('mutation-check.py', 'mutation-inventory.py', 'mutation-test-strict.py',
                'mutation-test.py', 'mutation-filesystem.py', 'test-method-capture.py', 'test-shell-capture.py')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def catalog_claims(config):
    require(config.get('schema_version') == 2 and isinstance(config.get('suites'), dict) and
            isinstance(config.get('mutations'), list) and config['mutations'], 'Пустой постоянный каталог')
    claims, identities = [], set()
    for item in config['mutations']:
        require(item['id'] not in identities, 'Повтор определения')
        identities.add(item['id'])
        suite = config['suites'][item['suite']]
        expected = item['expected_ids']
        sources = item.get('expected_sources')
        require(isinstance(sources, dict) and set(sources) == set(expected), 'Нет точной привязки каждого ID к источнику')
        claims.extend(dict(framework=suite['framework'], source=sources[identity], id=identity) for identity in expected)
    return claims


def validate_coverage(actual, claims, inventory=None):
    if inventory is None:
        inventory = load('coverage_inventory', ROOT / 'scripts/mutation-inventory.py')
    missing, stale = inventory.coverage_gaps(actual, claims)
    require(not missing and not stale, 'Неполное подтверждение: отсутствуют ' + repr(missing) + '; лишние ' + repr(stale))


def proven_claims(config, report):
    require(report.get('complete') is True and report.get('proof_gate') is True and report.get('exit_code') == 0,
            'Строгий запуск не завершил собственное подтверждение')
    rows = report['mutations']
    definitions = {item['id']: item for item in config['mutations']}
    require(len(rows) == len(definitions) and {row['id'] for row in rows} == set(definitions),
            'В строгом отчёте отсутствует определение')
    claims = []
    for row in rows:
        item = definitions[row['id']]
        require(row['status'] == 'detected' and row['proof_gate'] is True and
                {proof['id'] for proof in row['proofs']} == set(item['expected_ids']), 'Нет всех собственных отказов')
        for proof in row['proofs']:
            identity = proof['id']
            require(proof['test_file'] == item['expected_sources'][identity], 'Доказательство принадлежит другому файлу')
            require(any(event.get('own_assertion') is True and event.get('parent_id') == identity
                        for event in proof['own_assertion_events']), 'Нет собственного события утверждения')
            claims.append(dict(framework=config['suites'][item['suite']]['framework'],
                               source=proof['test_file'], id=identity))
    return claims


def run(source, catalog, output, calendar_python=None, timeout=600):
    source, catalog, output = (Path(path).absolute() for path in (source, catalog, output))
    if calendar_python is not None:
        calendar_python = Path(calendar_python).absolute()
    require(source.resolve() == source and catalog.resolve() == catalog and catalog.is_file(), 'Неканонический вход')
    require(output.resolve() == output and not output.exists(), 'Выход уже существует или содержит ссылку')
    config_bytes = catalog.read_bytes()
    config = json.loads(config_bytes)
    expected_tools = config.get('driver_sha256')
    require(isinstance(expected_tools, dict) and set(expected_tools) == set(DRIVER_FILES), 'Нет закрепления всех инструментов')
    tool_paths = {name: ROOT / 'scripts' / name for name in DRIVER_FILES}
    for name, path in tool_paths.items():
        require(path.resolve() == path and sha(path) == expected_tools[name], 'Изменён закреплённый инструмент: ' + name)
    require(config.get('legacy_sha256') == expected_tools['mutation-test.py'] and
            config.get('capture_sha256') == expected_tools['test-method-capture.py'] and
            config.get('filesystem_helper_sha256') == expected_tools['mutation-filesystem.py'], 'Разные закрепления инструментов')
    filesystem = load('complete_filesystem', tool_paths['mutation-filesystem.py'])
    if output.is_relative_to(source):
        require(not filesystem.output_conflicts(output.relative_to(source).as_posix()), 'Отчёт изменил бы входы')
    strict_output = output.with_name(output.stem + '-strict.json')
    require(not strict_output.exists() and not strict_output.with_suffix('').with_name(strict_output.stem + '-artifacts').exists(),
            'Материалы строгого запуска уже существуют')
    before = filesystem.read_state(source)
    report = dict(schema_version=3, complete=False, proof_gate=False, stage='snapshot', inventory=[], proven_cases=[],
                  catalog_path=str(catalog), catalog_sha256=hashlib.sha256(config_bytes).hexdigest(),
                  driver_sha256=expected_tools, strict_report_path=str(strict_output))
    output.parent.mkdir(parents=True, exist_ok=True)
    code = 2
    try:
        with tempfile.TemporaryDirectory(prefix='complete-mutations-') as temporary:
            work = Path(temporary).resolve()
            snapshot, observer = work / 'source', work / 'observer/scripts'
            filesystem.snapshot(source, snapshot)
            observer.mkdir(parents=True)
            for name, path in tool_paths.items():
                shutil.copy2(path, observer / name)
                require(sha(observer / name) == expected_tools[name], 'Неверная копия инструмента')
            frozen_catalog = work / 'catalog.json'
            # Привязки и происхождение проверяет внешний gate. Узкий API
            # файловых операций получает прежние предметные поля, без metadata.
            strict_config = json.loads(config_bytes)
            for item in strict_config['mutations']:
                item.pop('expected_sources', None)
                item.pop('provenance', None)
            strict_bytes = (json.dumps(strict_config, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
            frozen_catalog.write_bytes(strict_bytes)
            report['strict_catalog_sha256'] = hashlib.sha256(strict_bytes).hexdigest()
            inventory = load('complete_inventory', observer / 'mutation-inventory.py')
            report['stage'] = 'collection'
            report['inventory'] = inventory.collect(snapshot, calendar_python)
            report['stage'] = 'coverage'
            validate_coverage(report['inventory'], catalog_claims(config), inventory)
            report['stage'] = 'mutations'
            command = [sys.executable, '-B', str(observer / 'mutation-test-strict.py'), '--source', str(snapshot),
                       '--catalog', str(frozen_catalog), '--output', str(strict_output), '--timeout', str(timeout)]
            if calendar_python:
                command += ['--calendar-python', str(calendar_python)]
            # Строгий инструмент сам ограничивает каждый дочерний запуск и ждёт его очистку.
            process = subprocess.run(command, cwd=work, stdin=subprocess.DEVNULL)
            require(process.returncode == 0 and strict_output.is_file(), 'Строгий запуск завершился отказом')
            strict_report = json.loads(strict_output.read_bytes())
            require(strict_report['manifest'] == strict_config and
                    strict_report['manifest_sha256'] == report['strict_catalog_sha256'], 'Подменён строгий каталог')
            claims = proven_claims(config, strict_report)
            validate_coverage(report['inventory'], claims, inventory)
            report['proven_cases'] = sorted((dict(framework=f, source=s, id=i) for f, s, i in
                {inventory.case_key(record) for record in claims}), key=inventory.case_key)
            report['strict_report_sha256'] = sha(strict_output)
            require(filesystem.read_state(snapshot) == before, 'Изменён общий снимок')
            require(all(sha(observer / name) == expected_tools[name] for name in DRIVER_FILES), 'Изменены внешние инструменты')
        require(filesystem.read_state(source) == before and catalog.read_bytes() == config_bytes, 'Изменены исходные входы')
        require(all(sha(path) == expected_tools[name] for name, path in tool_paths.items()), 'Изменены исходные инструменты')
        report.update(complete=True, proof_gate=True, stage='complete')
        code = 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
    with output.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT)
    parser.add_argument('--catalog', type=Path, default=ROOT / 'tests/mutations/catalog.json')
    parser.add_argument('--output', type=Path, default=ROOT / ('tmp/mutations-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.json'))
    parser.add_argument('--calendar-python', type=Path)
    parser.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args()
    python = args.calendar_python
    if python is None and (args.source / 'modules/calendar/policy/.venv/bin/python').is_file():
        python = args.source / 'modules/calendar/policy/.venv/bin/python'
    try:
        return run(args.source, args.catalog, args.output, python, args.timeout)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
