#!/usr/bin/env python3
"""Собрать собственные события явных сценариев оболочки в формате строгого инструмента.

Каждый выбранный сценарий запускается отдельным процессом `bash <файл> --scenario <id>`.
События принимаются только из дескриптора 9 и только с одноразовым секретом запуска,
который передаётся один раз через дескриптор 8 и не попадает в окружение.
Код выхода, stdout и stderr не создают успеха или собственного утверждения:
они лишь разрешают или запрещают зачёт явных событий помощника. Отказ
засчитывается только после подтверждённой очистки. Ненулевой код или непустой
stderr требуют заранее заданного точного контракта доверенного теста; падение
интерпретатора и ошибка запуска запрещают зачёт даже с таким контрактом.
"""
import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCENARIO_ID = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
EVENT_FD = 9
TOKEN_FD = 8
HELPER_SOURCE = 'tests/helpers/shell-scenarios.sh'
ASSERT_CALL = re.compile(r'\s*(?:[^#]*?(?:;|&&|\|\||\bthen|\bdo|\{)\s*)?scenario_assert_exit\s')
# Признаки падения или ошибки запуска проверяемой команды: такой отказ не предметный.
CRASH_MARKERS = ('Traceback (most recent call last)', 'command not found', 'syntax error',
                 'Segmentation fault', 'Bus error', 'Abort trap', 'Killed', 'unbound variable',
                 'No such file or directory', 'Permission denied')


def run_script(script, arguments, diag_dir):
    """Запустить сценарий с отдельным каналом событий; вернуть (код, события, ошибки)."""
    run_id = secrets.token_hex(16)
    read_end, write_end = os.pipe()
    token_read, token_write = os.pipe()
    os.write(token_write, (run_id + '\n').encode())
    os.close(token_write)
    saved = {}
    try:
        for fd in (EVENT_FD, TOKEN_FD):
            try:
                saved[fd] = os.dup(fd)
            except OSError:
                saved[fd] = None
        os.dup2(write_end, EVENT_FD)
        os.dup2(token_read, TOKEN_FD)
        os.close(write_end)
        os.close(token_read)
        env = {k: v for k, v in os.environ.items() if not k.startswith('SCENARIO_')}
        env.update(SCENARIO_EVENT_FD=str(EVENT_FD), SCENARIO_DIAG_DIR=str(diag_dir))
        process = subprocess.Popen(['bash', str(script), *arguments], pass_fds=(EVENT_FD, TOKEN_FD), env=env,
                                   stdin=subprocess.DEVNULL)
    finally:
        for fd, copy in saved.items():
            if copy is None:
                os.close(fd)
            else:
                os.dup2(copy, fd)
                os.close(copy)
    chunks = []
    with os.fdopen(read_end, 'rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            chunks.append(chunk)
    returncode = process.wait()
    events, errors = [], []
    for number, line in enumerate(b''.join(chunks).decode('utf-8', 'replace').splitlines(), 1):
        try:
            event = json.loads(line)
        except ValueError:
            errors.append(f'unreadable event line {number}')
            continue
        if not isinstance(event, dict) or event.get('v') != 2 or event.get('run') != run_id:
            errors.append(f'foreign or unversioned event line {number}')
            continue
        events.append(event)
    return returncode, events, errors


def declared_ids(script, diag_dir):
    returncode, events, errors = run_script(script, ['--list-scenarios'], diag_dir)
    if returncode != 0:
        errors.append(f'scenario listing exited with {returncode}')
    ids = []
    for event in events:
        identity = event.get('id')
        if event.get('event') != 'declare' or not isinstance(identity, str) or not SCENARIO_ID.fullmatch(identity):
            errors.append('listing produced a non-declaration event')
        elif identity in ids:
            errors.append('duplicate declared scenario: ' + identity)
        else:
            ids.append(identity)
    if not ids:
        errors.append('no declared scenarios')
    return ids, errors


def failure_location(script, event):
    """Место явного утверждения: только строка самого тестового файла с вызовом помощника."""
    file, line = event.get('file'), event.get('line')
    if not isinstance(file, str) or not isinstance(line, int) or isinstance(line, bool) or line < 1:
        return None
    path = Path(file) if Path(file).is_absolute() else Path.cwd() / file
    try:
        if path.resolve() != script:
            return None
        text = script.read_text(encoding='utf-8').splitlines()[line - 1]
    except (OSError, UnicodeError, IndexError):
        return None
    if not ASSERT_CALL.match(text):
        return None
    return {'path': str(script), 'line': line}, text.strip()


def child_outcome(event, diag_dir):
    """Перечитать сохранённую диагностику проверяемой команды; вернуть (данные, причина отказа)."""
    diag, child, actual = event.get('diag'), event.get('child'), event.get('actual')
    if not isinstance(diag, str) or not diag:
        return None, 'failed assertion has no checked command outcome'
    path = Path(diag)
    try:
        if path.is_symlink() or path.resolve().parent != diag_dir.resolve() or not path.is_file():
            return None, 'diagnostic file is outside the run directory'
        raw = path.read_bytes()
        text = raw.decode('utf-8', errors='replace')
    except OSError:
        return None, 'diagnostic file is unreadable'
    if not isinstance(child, int) or isinstance(child, bool) or child != actual:
        return None, 'asserted code is not the checked command exit code'
    data = {'exit_code': child, 'stderr_excerpt': text[-2000:]}
    if child >= 126:
        return data, f'checked command failed to launch or was signalled (exit {child})'
    marker = next((m for m in CRASH_MARKERS if m in text), None)
    if marker:
        return data, 'checked command crashed: ' + marker
    # Только точный контракт доверенного теста легализует ненулевой код или stderr.
    if child != 0 or text:
        contract = event.get('contract')
        accepted = event.get('accepted')
        if not isinstance(contract, str) or not contract or accepted != child:
            return data, 'checked command has no exact accepted outcome contract'
        expected = Path(contract)
        try:
            if expected.is_symlink() or expected.resolve().parent != diag_dir.resolve():
                return data, 'outcome contract is outside the run directory'
            exact = expected.read_bytes()
        except (OSError, UnicodeError):
            return data, 'outcome contract is unreadable'
        if raw != exact:
            return data, 'checked command differs from its exact accepted outcome contract'
    return data, None


def scenario_result(script, identity, prefix, diag_dir):
    returncode, events, errors = run_script(script, ['--scenario', identity], diag_dir)
    record = {'id': prefix + identity, 'parent_id': prefix + identity, 'kind': 'test', 'phase': 'call',
              'status': 'error', 'source_path': str(script), 'own_assertion': False, 'returncode': returncode}
    started = False
    if any(event.get('id') != identity for event in events):
        errors.append('event for another scenario')
    names = [event.get('event') for event in events]
    if not names or names[0] != 'start' or names.count('start') != 1:
        errors.append('scenario did not start exactly once before its assertions')
    else:
        started = True
    if not names or names[-1] != 'cleanup-ok' or names.count('cleanup-ok') != 1:
        errors.append('scenario cleanup did not finish successfully')
    else:
        events = events[:-1]
        names = names[:-1]
    body = names[1:] if started else []
    asserts = [event for event in events[1:] if event.get('event') == 'assert']
    if any(name not in ('exec', 'assert', 'pass') for name in body):
        errors.append('unknown scenario event')
    executions = [event for event in events if event.get('event') == 'exec']
    if not executions:
        errors.append('scenario has no checked command events')
    for event in executions:
        outcome, refusal = child_outcome(event, diag_dir)
        if refusal:
            errors.append(refusal)
            record['child_outcome'] = outcome
    if body and body[-1] == 'pass' and body.count('pass') == 1 and asserts and \
            all(event.get('ok') is True for event in asserts) and returncode == 0 and not errors:
        for event in asserts:
            outcome, refusal = child_outcome(event, diag_dir)
            if refusal:
                errors.append(refusal)
        if not errors:
            record['status'] = 'passed'
            record['assertions'] = len(asserts)
    elif body and body[-1] == 'assert' and 'pass' not in body and returncode == 1 and not errors and \
            all(event.get('ok') is True for event in asserts[:-1]) and asserts[-1].get('ok') is False:
        failed = asserts[-1]
        expected, actual = failed.get('expected'), failed.get('actual')
        location = failure_location(script, failed)
        outcome, refusal = child_outcome(failed, diag_dir)
        if refusal:
            errors.append(refusal)
            record['child_outcome'] = outcome
        elif location and isinstance(expected, int) and isinstance(actual, int) and expected != actual:
            where, source = location
            record['status'] = 'failed'
            record['own_assertion'] = True
            record['child_outcome'] = outcome
            message = f'expected exit {expected}, actual {actual}'
            record['exception'] = {'type': 'shell.AssertionFailure', 'message': message, 'location': where,
                                   'traceback': [where], 'assertion_origin': {
                                       'kind': 'shell_assert_exit', 'location': where, 'source': source,
                                       'expected': expected, 'actual': actual}}
        else:
            errors.append('failed assertion has no verifiable own location')
    else:
        errors.append(f'scenario ended without a verifiable result (exit {returncode})')
    return record, started, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-helper', action='append', default=[])
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    options = parser.parse_args()
    arguments = options.arguments[1:] if options.arguments[:1] == ['--'] else options.arguments
    envelope = {'schema_version': 2, 'framework': 'shell', 'complete': False, 'exit_code': 2,
                'collected_ids': [], 'started_ids': [], 'results': [], 'infrastructure_errors': []}
    try:
        if not arguments or not arguments[0].endswith('.sh'):
            raise ValueError('expected a shell scenario file followed by optional scenario IDs')
        script = Path(arguments[0]).resolve(strict=True)
        relative = arguments[0]
        prefix = relative + '::'
        if HELPER_SOURCE not in script.read_text(encoding='utf-8'):
            raise ValueError('scenario file does not source ' + HELPER_SOURCE)
        diag_dir = Path(tempfile.mkdtemp(prefix='shell-scenario-diag-')).resolve()
        ids, errors = declared_ids(script, diag_dir)
        envelope['infrastructure_errors'] += errors
        requested = arguments[1:]
        selected = []
        for value in requested:
            if not value.startswith(prefix) or value[len(prefix):] not in ids or value in selected:
                envelope['infrastructure_errors'].append('unknown or repeated scenario selection: ' + value)
            else:
                selected.append(value)
        names = [value[len(prefix):] for value in selected] if requested else ids
        envelope['collected_ids'] = [prefix + name for name in names]
        if not envelope['infrastructure_errors']:
            for name in names:
                record, started, errors = scenario_result(script, name, prefix, diag_dir)
                if started:
                    envelope['started_ids'].append(prefix + name)
                envelope['results'].append(record)
                envelope['infrastructure_errors'] += [f'{prefix}{name}: {error}' for error in errors]
        statuses = [record['status'] for record in envelope['results']]
        if envelope['infrastructure_errors'] or not statuses or 'error' in statuses:
            envelope['exit_code'] = 2
        else:
            envelope['exit_code'] = 1 if 'failed' in statuses else 0
        envelope['complete'] = bool(envelope['collected_ids'] and not envelope['infrastructure_errors']
                                    and len(statuses) == len(envelope['collected_ids']))
        shutil.rmtree(diag_dir, ignore_errors=True)
    except BaseException as error:
        envelope['complete'] = False
        envelope['exit_code'] = 2
        envelope['infrastructure_errors'].append(type(error).__name__ + ': ' + str(error))
    options.output.write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + '\n')
    return envelope['exit_code']


if __name__ == '__main__':
    sys.exit(main())
