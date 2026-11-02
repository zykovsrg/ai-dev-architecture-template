#!/usr/bin/env python3
"""Узкие изменения путей и единый снимок входов строгого подтверждения."""
import hashlib
import os
from pathlib import Path
import shutil
import stat

COPY_ROOTS = ('scripts', 'modules', 'tests', 'getting-started', 'docs')
IGNORED = {'.venv', '__pycache__', '.pytest_cache', '.git', '.DS_Store'}
OPERATIONS = {
    'create_file': 'scripts/update-installed-architecture.sh',
    'create_empty_dir': 'template',
    'delete_file': 'modules/knowledge/skills/hub-knowledge-enable/SKILL.md',
}
CREATE_CONTENT = '#!/usr/bin/env bash\nexit 0\n'
GITIGNORE = 'modules/core/data/.gitignore'
BRIDGE_DOCUMENTS = frozenset({
    'modules/calendar/policy/bridge/hub_eventkit_bridge.swift',
    'modules/calendar/policy/bridge/Info.plist',
    'modules/calendar/policy/bridge/SHA256SUMS',
})


def require(condition, message):
    if not condition:
        raise ValueError(message)


def ignored(name):
    return (name in IGNORED or name.endswith(('.pyc', '.env')) or
            (name.startswith('.') and name not in ('.gitignore', '.gitkeep')))


def included(value, directory=False):
    """Та же политика для обхода и запрета записи отчёта во входы."""
    path = Path(value)
    if not path.parts or any(ignored(part) for part in path.parts):
        return False
    if path.parts[0] == 'README.md':
        return len(path.parts) == 1
    if path.parts[0] not in COPY_ROOTS:
        return False
    if path.parts[:2] in (('docs', 'audits'), ('docs', 'superpowers')):
        return False
    return (path.parts[0] not in ('getting-started', 'docs') or directory or
            path.suffix == '.md')


def output_conflicts(value):
    path = Path(value)
    return bool(path.parts and (path.parts[0] == 'template' or included(value) or included(value, directory=True)))


def checked_path(root, value, missing=False):
    require(isinstance(value, str) and value, 'Пустой относительный путь')
    path = Path(value)
    require(not path.is_absolute() and '..' not in path.parts and value == path.as_posix() and
            value not in ('.', ''), 'Неканонический относительный путь: ' + value)
    require(root.is_dir() and root.resolve() == root, 'Неканонический корень')
    probe = root
    for index, part in enumerate(path.parts):
        require(probe.is_dir() and not probe.is_symlink(), 'Родитель не является настоящим каталогом: ' + value)
        names = {entry.name for entry in probe.iterdir()}
        probe = probe / part
        exists = probe.exists() or probe.is_symlink()
        require(not exists or part in names, 'Неканонический регистр пути: ' + value)
        if not exists:
            require(missing and index == len(path.parts) - 1, 'Отсутствует вход: ' + value)
            return probe
        require(not stat.S_ISLNK(probe.lstat().st_mode), 'Ссылка вместо исходного файла: ' + value)
        require(index == len(path.parts) - 1 or probe.is_dir(), 'Родитель не является каталогом: ' + value)
    require(probe.resolve() == probe, 'Неканонический путь или ссылка: ' + value)
    return probe


def _walk(root):
    """Возвращает только разрешённые узлы, включая все пустые каталоги."""
    require(root.is_dir() and root.resolve() == root, 'Неканонический корень')
    nodes = []
    def visit(path):
        relative = path.relative_to(root).as_posix()
        mode = path.lstat().st_mode
        # Исключённые деревья не обследуются даже при наличии ссылки внутри.
        if not included(relative, directory=stat.S_ISDIR(mode)):
            return
        require(not stat.S_ISLNK(mode), 'Ссылка вместо исходного файла: ' + relative)
        require(stat.S_ISDIR(mode) or stat.S_ISREG(mode), 'Необычный тип входа: ' + relative)
        nodes.append((relative, path, stat.S_ISDIR(mode), stat.S_IMODE(mode)))
        if stat.S_ISDIR(mode):
            for child in sorted(path.iterdir()):
                if not ignored(child.name):
                    visit(child)
    for name in ('README.md',) + COPY_ROOTS:
        path = root / name
        if path.exists() or path.is_symlink():
            visit(path)
    return nodes


def read_state(root):
    root = Path(root)
    files, directories = {}, {}
    for relative, path, directory, mode in _walk(root):
        if directory:
            directories[relative] = mode
        else:
            files[relative] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'mode': mode}
    probe = root / 'template'
    if probe.exists() or probe.is_symlink():
        checked_path(root, 'template')
        require(probe.is_dir() and not any(probe.iterdir()), 'template должен отсутствовать или быть пустым каталогом')
        template = {'kind': 'empty_directory', 'mode': stat.S_IMODE(probe.stat().st_mode)}
    else:
        template = {'kind': 'absent'}
    return {'files': files, 'directories': directories, 'absence_probes': {'template': template}}


def snapshot(source, destination):
    source, destination = Path(source), Path(destination)
    require(not destination.exists() and not destination.is_symlink(), 'Место копии уже занято')
    baseline = read_state(source)
    require(baseline['absence_probes']['template']['kind'] == 'absent', 'Канонический template должен отсутствовать')
    destination.mkdir()
    for relative, path, directory, mode in _walk(source):
        target = destination / relative
        if directory:
            target.mkdir()
            target.chmod(mode)
        else:
            # Независимые клоны большого каталога экономят место на «Макос».
            if (relative == 'tests/mutations/catalog.json' and os.name == 'posix' and
                    os.uname().sysname == 'Darwin'):
                copier = '/usr/bin/ditto'
                status = os.spawnv(os.P_WAIT, copier, [copier, '--clone', str(path), str(target)])
                require(status == 0, 'Не удалось клонировать каталог снимка')
            else:
                shutil.copy2(path, target)
    require(read_state(source) == baseline and read_state(destination) == baseline, 'Снимок отличается от входов')
    return baseline


def active_documents(root, state):
    """Для проверки распространения обязательны настоящие документы всех трёх корней."""
    require('README.md' in state['files'], 'Нет активного README.md')
    result = {'README.md': state['files']['README.md']['sha256']}
    for name in ('getting-started', 'docs'):
        require(name in state['directories'], 'Нет активного каталога ' + name)
        found = {p: v['sha256'] for p, v in state['files'].items() if p.startswith(name + '/') and p.endswith('.md')}
        require(found, 'Нет активных документов в ' + name)
        result.update(found)
    return result


def protected_target(root, value, protected_paths, missing=False):
    target = checked_path(root, value, missing=missing)
    require(not any(target == Path(p) or (target.exists() and Path(p).exists() and target.samefile(p))
                    for p in protected_paths), 'Нельзя мутировать исполняемый test/helper oracle')
    if target.exists():
        if target.is_file():
            require(target.stat().st_nlink == 1, 'Неканонический путь: жёсткая ссылка вместо цели подмены')
    return target


def prepare_change(source, item, protected_paths, legacy_mutate):
    value, operation = item['source'], item.get('operation')
    require(isinstance(value, str), 'Источник должен быть строкой')
    if operation is not None:
        require(operation in OPERATIONS and value == OPERATIONS[operation], 'Недопустимая операция или цель')
        common = {'id', 'suite', 'source', 'expected_ids', 'operation'}
        require(set(item) == common | ({'content'} if operation == 'create_file' else set()), 'Неизвестные поля операции')
        target = protected_target(source, value, protected_paths, missing=operation.startswith('create_'))
        if operation.startswith('create_'):
            require(not target.exists() and not target.is_symlink(), 'Создаваемый путь уже существует')
            if operation == 'create_file':
                require(item['content'] == CREATE_CONTENT, 'Непредусмотренное содержимое нового файла')
            original, mode = None, None
            changed = CREATE_CONTENT.encode() if operation == 'create_file' else None
            changed_mode = 0o644 if operation == 'create_file' else 0o755
        else:
            require(target.is_file(), 'Удаление требует обычный файл')
            original, mode = target.read_bytes(), stat.S_IMODE(target.stat().st_mode)
            changed, changed_mode = None, None
    else:
        require(value == 'README.md' or (Path(value).parts and Path(value).parts[0] in ('scripts', 'modules', 'tests')),
                'Недопустимая текстовая цель')
        require(included(value), 'Цель не входит в снимок')
        target = protected_target(source, value, protected_paths)
        require(target.is_file(), 'Текстовая подмена требует обычный файл')
        original, mode = target.read_bytes(), stat.S_IMODE(target.stat().st_mode)
        if value == GITIGNORE:
            require(item.get('symbol') == '@document' and item.get('before') == '.DS_Store\n' and
                    item.get('after') == '', 'Недопустимая подмена .gitignore')
            text = original.decode()
            require(text.count('.DS_Store\n') == 1, 'Замена должна встретиться ровно один раз')
            changed = text.replace('.DS_Store\n', '').encode()
        elif value in BRIDGE_DOCUMENTS:
            require(item.get('symbol') == '@document', 'Точный документ моста требует @document')
            before, after = item.get('before'), item.get('after')
            text = original.decode()
            require(isinstance(before, str) and before and isinstance(after, str) and text.count(before) == 1,
                    'Замена должна встретиться ровно один раз')
            changed = text.replace(before, after).encode()
        else:
            changed = legacy_mutate(original.decode(), item).encode()
        require(changed != original, 'Изменение не меняет исходник')
        operation, changed_mode = 'replace_file', mode
    return {'source': value, 'operation': operation, 'original': original, 'mode': mode,
            'changed': changed, 'changed_mode': changed_mode,
            'protected': tuple(str(p) for p in protected_paths)}


def expected_state(baseline, change):
    result = {'files': {k: dict(v) for k, v in baseline['files'].items()},
              'directories': dict(baseline['directories']),
              'absence_probes': {'template': dict(baseline['absence_probes']['template'])}}
    source, operation = change['source'], change['operation']
    if operation == 'create_empty_dir':
        result['absence_probes']['template'] = {'kind': 'empty_directory', 'mode': change['changed_mode']}
    elif operation == 'delete_file':
        del result['files'][source]
    else:
        result['files'][source] = {'sha256': hashlib.sha256(change['changed']).hexdigest(), 'mode': change['changed_mode']}
    return result


def _variant_protected(root, change):
    # Действующие внешние инструменты проверяются непосредственно; местные oracle
    # дополнительно привязывает вызывающий строгий цикл по тому же относительному имени.
    return list(change['protected'])


def apply_change(variant, change, baseline_state, protected_paths=()):
    require(read_state(variant) == baseline_state, 'Исходное состояние копии изменено')
    operation = change['operation']
    target = protected_target(variant, change['source'], (*_variant_protected(variant, change), *protected_paths),
                              missing=operation.startswith('create_'))
    if operation.startswith('create_'):
        require(not target.exists() and not target.is_symlink(), 'Создаваемый путь уже существует')
        if operation == 'create_empty_dir':
            target.mkdir(mode=change['changed_mode'])
        else:
            with target.open('xb') as stream:
                stream.write(change['changed'])
        target.chmod(change['changed_mode'])
    else:
        require(target.is_file() and target.read_bytes() == change['original'] and
                stat.S_IMODE(target.stat().st_mode) == change['mode'], 'Цель не совпадает с исходным файлом')
        if operation == 'delete_file':
            target.unlink()
        else:
            target.write_bytes(change['changed'])
            target.chmod(change['changed_mode'])
    expected = expected_state(baseline_state, change)
    require(read_state(variant) == expected, 'Подмена изменила посторонние входы')
    return expected


def restore_change(variant, change, protected_paths=()):
    operation = change['operation']
    target = protected_target(variant, change['source'], (*_variant_protected(variant, change), *protected_paths),
                              missing=True)
    if operation == 'create_empty_dir':
        if target.exists():
            require(target.is_dir(), 'Неверный тип созданного каталога')
            target.rmdir()
    elif operation == 'create_file':
        if target.exists():
            require(target.is_file(), 'Неверный тип созданного файла')
            target.unlink()
    else:
        require(not target.exists() or target.is_file(), 'Неверный тип восстанавливаемого файла')
        if target.exists():
            target.write_bytes(change['original'])
        else:
            with target.open('xb') as stream:
                stream.write(change['original'])
        target.chmod(change['mode'])
