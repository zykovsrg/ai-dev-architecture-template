#!/usr/bin/env python3
"""Общий снимок чтения «Напоминаний» внутри одного запуска синхронизации.

Вне `run_scope()` каждый вызов идёт в приложение как раньше. Внутри области
первый `list_lists` запускает полный снимок: перечень, все списки параллельно
и повторный перечень. Снимок принимается, только если перечень не изменился
за время чтения; иначе запуск продолжает читать напрямую. Любой вызов, кроме
чтения, сбрасывает снимок, поэтому после записи данные читаются заново.
Успешные ответы `hub_cancel_status` внутри области тоже переиспользуются до записи.

Внутри области код соседних скриптов переиспользуется в памяти по точным байтам
исходника. Каждый импорт создаёт новый модуль и новые глобальные переменные.
Для остальных модулей сохраняется прежний временный кэш байткода.
"""
import concurrent.futures
import contextlib
import importlib.machinery
import json
import os
from pathlib import Path
import sys
import tempfile
import threading

READ_TOOLS = {'list_lists', 'find_reminders', 'get_reminder', 'hub_cancel_status', 'hub_cancel_capabilities'}
WORKERS = 4
SCOPE_ENV = ('HUB_REMINDERS_ALLOWED_LISTS_FILE', 'HUB_REMINDERS_ALLOWED_GROUPS_FILE', 'HUB_REMINDERS_ALLOWED_GROUP_IDS_FILE')
_DISABLED = 'disabled'
_state = None
_memo = None
_epoch = 0


def _key(tool, args):
    return tool, json.dumps(args, sort_keys=True, ensure_ascii=False)


def _parsed(result):
    if result.returncode:
        return None
    try:
        value = json.loads(result.stdout[result.stdout.index('{'):])
    except ValueError:
        return None
    if not isinstance(value, dict) or value.get('error') or value.get('isError'):
        return None
    return value


@contextlib.contextmanager
def _code_scope():
    """Кэшируем объекты кода, не модули; проверяем исходные байты при каждом импорте."""
    directory = os.path.dirname(os.path.abspath(__file__))
    loader = importlib.machinery.SourceFileLoader
    previous = loader.get_code
    cache = {}
    lock = threading.RLock()

    def get_code(subject, fullname):
        filename = subject.get_filename(fullname)
        if (type(subject) is not loader or os.path.dirname(os.path.abspath(filename)) != directory or
                not filename.endswith('.py') or os.path.islink(filename)):
            return previous(subject, fullname)
        source = Path(filename).read_bytes()
        key = (filename, source)
        with lock:
            if key not in cache:
                cache[key] = compile(source, filename, 'exec', dont_inherit=True)
            return cache[key]

    loader.get_code = get_code
    try:
        yield
    finally:
        loader.get_code = previous


@contextlib.contextmanager
def run_scope():
    global _state, _memo
    outer = _state
    if outer is not None:
        yield
        return
    _state = {}
    _memo = {}
    saved = sys.dont_write_bytecode, sys.pycache_prefix
    with tempfile.TemporaryDirectory(prefix='hub-reminders-bytecode-') as bytecode, _code_scope():
        sys.dont_write_bytecode, sys.pycache_prefix = False, bytecode
        try:
            yield
        finally:
            _state = _memo = None
            sys.dont_write_bytecode, sys.pycache_prefix = saved


def _snapshot(runner, first):
    meta = _parsed(first)
    lists = meta.get('lists') if meta else None
    if not isinstance(lists, list) or any(not isinstance(row, dict) or not isinstance(row.get('id'), str) or not row['id'] for row in lists):
        return _DISABLED
    queries = [{'list': row['id'], 'include_completed': True, 'limit': 500} for row in lists]
    try:
        with concurrent.futures.ThreadPoolExecutor(WORKERS) as pool:
            results = list(pool.map(lambda args: runner('find_reminders', args), queries))
        # Повторный перечень доказывает, что списки не менялись во время чтения.
        again = _parsed(runner('list_lists', {}))
    except Exception:
        # Ошибку получит тот, кто прочитает этот список сам, как без снимка.
        return _DISABLED
    if any(_parsed(result) is None for result in results) or again != meta:
        return _DISABLED
    snapshot = {_key('list_lists', {}): first}
    snapshot.update((_key('find_reminders', args), result) for args, result in zip(queries, results))
    return snapshot


def generation():
    return _epoch


@contextlib.contextmanager
def direct_reads():
    """Новая граница снимка читает приложение без прежнего снимка области."""
    global _state
    saved = _state
    _state = None
    try:
        yield
    finally:
        _state = saved


def refresh():
    """Следующее чтение идёт в приложение: защитная проверка перед записью видит свежие данные."""
    global _epoch
    _epoch += 1
    if _state is not None:
        _state.clear()


def call(binary, env, tool, args, runner):
    """`runner(tool, args)` выполняет вызов; снимок делится по приложению и разрешённым спискам."""
    state = _state
    if state is None:
        return runner(tool, args)
    scope = (str(binary),) + tuple(str(env[name]) if env.get(name) else None for name in SCOPE_ENV)
    if tool not in READ_TOOLS:
        refresh()
        return runner(tool, args)
    snapshot = state.get(scope)
    if isinstance(snapshot, dict) and _key(tool, args) in snapshot:
        return snapshot[_key(tool, args)]
    if tool == 'hub_cancel_status':
        # Состояние отмены зависит от плана (его сумма входит в аргументы) и от «Напоминаний»,
        # которые до записи не меняются. Ошибки не сохраняются и повторяются.
        statuses = state.setdefault(('hub_cancel_status',) + scope, {})
        if _key(tool, args) not in statuses:
            result = runner(tool, args)
            if _parsed(result) is None:
                return result
            statuses[_key(tool, args)] = result
        return statuses[_key(tool, args)]
    result = runner(tool, args)
    if tool == 'list_lists' and args == {} and snapshot is None:
        state[scope] = _snapshot(runner, result)
    return result


def memo(key, verify):
    """Внутри области повторно отдаёт успешный результат проверки с тем же ключом.

    `verify()` возвращает пару: результат и признак, что входные файлы не менялись
    во время проверки. Ошибки не сохраняются и повторяются при следующем вызове.
    """
    cache = _memo
    if cache is not None and key in cache:
        return cache[key]
    result, stable = verify()
    if cache is not None and stable:
        cache[key] = result
    return result
