#!/usr/bin/env python3
"""Синхронизация только явно привязанных проектов; по умолчанию без записи."""
import uuid
import argparse
import contextlib
import copy
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

TERMINAL = {'done', 'completed', 'dropped', 'promoted'}
NAMES = {'current': 'current-task.md', 'future': 'future-tasks.md', 'paused': 'paused-tasks.md'}
PROTECTED_REMINDER_FIELDS = ('id', 'title', 'due', 'completed', 'list', 'list_id', 'parent_id', 'repeat')


def safe_path(path):
    path = Path(path)
    if not path.is_absolute() or any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError('unsafe_path: ' + str(path))
    return path


def atomic_json(path, value):
    path = safe_path(path)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
        name = handle.name
    os.replace(name, path)



def standard_allowlist(config):
    original = safe_path(config['allowlist_file'])
    selected = safe_path(config.get('standard_allowlist_file', original))
    if 'standard_allowlist_file' in config and selected != original.parent / 'reminders-standard-allowlist.json':
        raise ValueError('unsafe_standard_allowlist')
    return str(selected)


def migration_pending(hub, config):
    reassignment = task_reassignment_pending(hub, config)
    script = Path(__file__).with_name('reminders_project_lists.py')
    if not script.exists():
        return set(config.get('project_list_migrations_pending', {})) | reassignment | set(config.get('archive_pending', {}).get('projects', []))
    spec = importlib.util.spec_from_file_location('reminders_migration', script)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module.pending_projects(hub, config) | reassignment | set(config.get('archive_pending', {}).get('projects', []))


def task_reassignment_pending(hub, config, ignore_operation=None):
    script = Path(__file__).with_name('reminders_task_reassignment.py')
    if not script.exists():
        return set(config['projects']) if config.get('task_reassignments_completed') or (Path(hub) / 'ai/reminders-task-reassignments').exists() else set()
    spec = importlib.util.spec_from_file_location('reminders_task_reassignment_pending', script)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module.pending_projects(hub, config, ignore_operation)


def validate_binding_ids(config):
    identifiers = []
    for binding in config['projects'].values():
        layout = binding.get('layout', 'parent')
        if layout not in {'parent', 'project_list'}:
            raise ValueError('unknown_project_layout')
        if not all(binding.get(k) for k in ('list_id', 'list_name')):
            raise ValueError('incomplete_project_binding')
        if layout == 'project_list':
            if binding.get('parent_id') is not None:
                raise ValueError('project_list_parent_forbidden')
            if sum(other.get('list_id') == binding['list_id'] for other in config['projects'].values()) != 1:
                raise ValueError('exclusive_project_list')
        elif not binding.get('parent_id'):
            raise ValueError('incomplete_project_binding')
        if binding.get('parent_id'):
            identifiers.append(binding['parent_id'])
        identifiers.extend(t['reminder_id'] for t in binding.get('tasks', {}).values() if t.get('reminder_id'))
        identifiers.extend(binding.get('history', {}))
    if len(identifiers) != len(set(identifiers)):
        raise ValueError('duplicate_reminder_binding')


def compact_code(project_id, task_id):
    return hashlib.sha256((project_id + '\0' + task_id).encode()).hexdigest()[:12]


def compact_identities(config):
    identities = {}
    for pid, binding in config['projects'].items():
        for tid in binding.get('tasks', {}):
            code = compact_code(pid, tid)
            if code in identities and identities[code] != (pid, tid):
                raise ValueError('compact_code_collision')
            identities[code] = (pid, tid)
    return identities


def has_identity_marker(notes):
    return any(line.lstrip().startswith(('Хаб:', 'Hub Task ID:', 'Hub project:', '--- Hub metadata', '--- /Hub metadata')) for line in (notes or '').splitlines())


def creation_identity(remote, identities=None):
    notes = remote.get('notes', '')
    compact = [line for line in notes.splitlines() if line.lstrip().startswith('Хаб:')]
    if compact:
        if len(compact) != 1 or not re.fullmatch(r'Хаб: [0-9a-f]{12}', compact[0]) or 'Hub metadata' in notes or any(line.startswith(('Hub Task ID:', 'Hub project:')) for line in notes.splitlines()):
            raise ValueError('ambiguous_creation_identity')
        code = compact[0][5:]
        if identities is None or code not in identities:
            raise ValueError('unknown_compact_identity')
        return identities[code]
    first, last = '--- Hub metadata ---', '--- /Hub metadata ---'
    if notes.count(first) != 1 or notes.count(last) != 1 or notes.index(first) >= notes.index(last):
        raise ValueError('ambiguous_creation_identity')
    lines = notes[notes.index(first) + len(first):notes.index(last)].strip().splitlines()
    tids = [s[13:] for s in lines if s.startswith('Hub Task ID: ')]
    pids = [s[13:] for s in lines if s.startswith('Hub project: ')]
    if len(tids) != 1 or len(pids) != 1 or sum(s.startswith('Hub Task ID: ') for s in notes.splitlines()) != 1 or sum(s.startswith('Hub project: ') for s in notes.splitlines()) != 1:
        raise ValueError('ambiguous_creation_identity')
    return pids[0], tids[0]


def load_config(hub):
    path = safe_path(Path(hub) / 'ai/reminders-sync.json')
    config = json.loads(path.read_text())
    if config.get('version') != 1 or not isinstance(config.get('projects'), dict):
        raise ValueError('invalid_config')
    authority_enabled(config)
    safe_path(config['binary'])
    if 'cancellation_binary' in config:
        cancellation_binary = safe_path(config['cancellation_binary'])
        if cancellation_binary != cancellation_binary.resolve():
            raise ValueError('unsafe_path: ' + str(cancellation_binary))
    safe_path(config['allowlist_file'])
    standard_allowlist(config)
    validate_binding_ids(config)
    compact_identities(config)
    return config


def parser_for(hub):
    script = safe_path(Path(hub) / 'scripts/task_records.py')
    spec = importlib.util.spec_from_file_location('reminders_canonical_records', script)
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    return parser



def archive_module(config=None):
    path = safe_path(Path(__file__).absolute().with_name('reminders_archive.py'))
    if not path.exists():
        if config and (config.get('archive_pending') or any(b.get('archive') for b in config['projects'].values())):
            raise ValueError('archive_support_missing')
        return None
    spec = importlib.util.spec_from_file_location('reminders_archive_support', path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def authority_enabled(config):
    if 'task_authority' not in config:
        return False
    return authority_module().enabled(config)


@contextlib.contextmanager
def sync_lock(hub, config=None):
    path = Path(__file__).with_name('reminders_authority.py')
    if path.exists():
        with authority_module().locked(hub) as selected:
            yield selected
    else:
        if config is None:
            config_path = Path(hub) / 'ai/reminders-sync.json'
            config = json.loads(safe_path(config_path).read_text()) if config_path.exists() else {}
        if authority_enabled(config):
            raise ValueError('authority_support_missing')
        with open(safe_path(Path(hub) / 'ai/.reminders-sync.lock'), 'a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield Path(hub)


def authority_module():
    key = 'hub_reminders_authority'
    if key not in sys.modules:
        path = Path(__file__).with_name('reminders_authority.py')
        if not path.exists():
            raise ValueError('authority_support_missing')
        spec = importlib.util.spec_from_file_location(key, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[key] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(key, None)
            raise
    return sys.modules[key]


def gateway_module():
    key = 'hub_reminders_task_gateway'
    if key not in sys.modules:
        path = Path(__file__).with_name('reminders_task_gateway.py')
        if not path.exists():
            raise ValueError('reminders_task_gateway_missing')
        spec = importlib.util.spec_from_file_location(key, path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        sys.modules[key] = module
    return sys.modules[key]


def task_projects(hub, config=None):
    if config is None:
        path = Path(hub) / 'ai/reminders-sync.json'
        config = json.loads(safe_path(path).read_text()) if path.exists() else {}
    if authority_enabled(config):
        return authority_module().bound_projects(hub, config)
    return registered(hub)


def task_project_path(hub, project_id, config=None):
    """Проверенный путь только выбранного проекта; общий перечень проверяется отдельно."""
    if config is None:
        path = Path(hub) / 'ai/reminders-sync.json'
        config = json.loads(safe_path(path).read_text()) if path.exists() else {}
    if not authority_enabled(config):
        try:
            return registered(hub)[project_id]
        except KeyError as error:
            raise ValueError('unregistered_or_inactive_project') from error
    authority = authority_module()
    authority.validate_policy(hub, config)
    if project_id not in config['projects']:
        raise ValueError('unbound_project')
    binding = config['projects'][project_id]
    if binding.get('archive'):
        path = authority.archive_module().project_path(hub, config, project_id)
        if path is None:
            raise ValueError('archive_authority_adoption_required')
        return path
    active = registered(hub)
    if project_id not in active:
        raise ValueError('unregistered_or_inactive_project')
    return active[project_id]


def registered(hub):
    hub = safe_path(Path(hub).absolute())
    registry = safe_path(hub / 'ai/project-registry.md').read_text()
    projects = {}
    for match in re.finditer(r'^## ([a-z0-9-]+)\n(.*?)(?=^## |\Z)', registry, re.M | re.S):
        pid, body = match.groups()
        if not re.search(r'^Status: active$', body, re.M):
            continue
        values = re.findall(r'^Path: (.+)$', body, re.M)
        if len(values) != 1 or pid in projects:
            raise ValueError('ambiguous_registry')
        path = safe_path(values[0])
        if path.parent != hub / 'projects' or not path.is_dir():
            raise ValueError('unsafe_project_path')
        projects[pid] = path
    return projects


def project_label(hub, project_id, binding):
    """Читаемая подпись из привязки или Name реестра."""
    label = binding.get('project_label')
    if label is None:
        registry = safe_path(Path(hub) / 'ai/project-registry.md').read_text()
        matches = re.findall(r'^## ' + re.escape(project_id) + r'\n(.*?)(?=^## |\Z)', registry, re.M | re.S)
        if len(matches) > 1:
            raise ValueError('ambiguous_project_label')
        names = re.findall(r'^Name: (.*)$', matches[0], re.M) if matches else []
        if len(names) > 1:
            raise ValueError('ambiguous_project_label')
        label = names[0] if names else project_id
    if not isinstance(label, str) or not label.strip() or label != label.strip() or any(not c.isprintable() for c in label):
        raise ValueError('invalid_project_label')
    return label


def chunk(text, kind, task_id):
    if kind == 'current':
        return (0, len(text), text)
    hits = []
    for m in re.finditer(r'^### [^\n]+\n.*?(?=^### |\Z)', text, re.M | re.S):
        if (kind == 'future' and m[0].startswith('### ' + task_id + ' — ')) or (kind == 'paused' and re.search(r'^Task ID: ' + re.escape(task_id) + r'$', m[0], re.M)):
            hits.append((m.start(), m.end(), m[0]))
    if len(hits) != 1:
        raise ValueError('ambiguous_task_chunk: ' + task_id)
    return hits[0]


def day_in(body):
    values = re.findall(r'^Запланировано: (?:релиз )?(\d{4}-\d{2}-\d{2})(?:[ .].*)?$', body, re.M)
    if len(set(values)) > 1:
        raise ValueError('conflicting_planned_days')
    value = values[0] if values else None
    if value:
        dt.date.fromisoformat(value)
    return value


class HubProject:
    def __init__(self, hub, pid, path=None):
        self.hub, self.pid = Path(hub), pid
        self.project = path or task_project_path(hub, pid)
        self.parser = parser_for(hub)
        self.paths = {k: safe_path(self.project / 'ai' / n) for k, n in NAMES.items()}
        self.texts = {k: p.read_text() for k, p in self.paths.items()}

    def rows(self):
        rows = self.parser.read_project_records(self.pid, self.texts['current'], self.texts['future'], self.texts['paused'])
        result = {}
        # Текущая запись имеет приоритет над историческим promoted-дубликатом.
        for row in rows:
            tid, kind = row['task_id'], row['source_kind']
            if tid in result:
                if row['status'] in TERMINAL and result[tid]['status'] in TERMINAL:
                    continue
                if kind == 'future' and row['status'] == 'promoted' and result[tid]['kind'] == 'current':
                    continue
                if not ((kind == 'paused' and result[tid]['kind'] == 'future' and result[tid]['status'] == 'done') or (kind == 'paused' and result[tid]['kind'] == 'future' and result[tid]['status'] == 'promoted')):
                    raise ValueError('duplicate_task_id: ' + tid)
            body = chunk(self.texts[kind], kind, tid)[2]
            result[tid] = dict(row, project_id=self.pid, TaskID=tid, kind=kind,
                               planned_day=day_in(body), deadline=row['due'], source_path=str(self.paths[kind]))
        return result

    def save(self, after, allow_removal=()):
        # Проверяем все тексты до первой записи. Due не удаляется и не используется как плановая дата.
        for kind, text in after.items():
            self.parser.read_records(self.pid, kind, text)
            if self.parser.unrecognized_headings(kind, text.splitlines()):
                raise ValueError('unrecognized_heading')
        for kind, path in self.paths.items():
            if path.read_text() != self.texts[kind]:
                raise RuntimeError('hub_changed_since_read')
        for kind in ('future', 'current', 'paused'):
            if after[kind] == self.texts[kind]:
                continue
            config_path = self.hub / 'ai/reminders-sync.json'
            config = json.loads(safe_path(config_path).read_text()) if config_path.exists() else {}
            if authority_enabled(config):
                authority_module().validate_policy(self.hub, config)
                if task_project_path(self.hub, self.pid, config) != self.project:
                    raise ValueError('authority_projection_path_changed')
                self.parser.write_task_file(self.hub, self.pid, kind, hashlib.sha256(self.texts[kind].encode()).hexdigest(), after[kind], allow_removal)
                if self.paths[kind].read_text() != after[kind]:
                    raise RuntimeError('hub_write_readback_failed')
            else:
                result = subprocess.run(['python3', str(self.hub / 'scripts/task_records.py'), 'write', '--hub', str(self.hub), '--project-id', self.pid, '--kind', kind, '--expected-sha256', hashlib.sha256(self.texts[kind].encode()).hexdigest()] + [arg for tid in allow_removal for arg in ('--allow-removal', tid)], input=after[kind], text=True, capture_output=True, timeout=40)
                if result.returncode or self.paths[kind].read_text() != after[kind]:
                    raise RuntimeError('hub_write_failed: ' + result.stderr)
            self.texts[kind] = after[kind]

    def update(self, row, title, day, completed, reopen_status=None):
        after = dict(self.texts)
        kind, tid = row['kind'], row['task_id']
        first, last, body = chunk(after[kind], kind, tid)
        if title != row['title']:
            if not title.strip() or '\n' in title or '\r' in title:
                raise ValueError('invalid_title')
            if kind == 'current':
                body = re.sub(r'(^## Goal\n\s*\n?)[^\n]+', lambda m: m[1] + title, body, count=1, flags=re.M)
            else:
                body = body.replace(body.splitlines()[0], body.splitlines()[0].split(' — ', 1)[0] + ' — ' + title, 1)
        if day != row['planned_day']:
            body = re.sub(r'^Запланировано:.*\n?', '', body, flags=re.M)
            if day:
                dt.date.fromisoformat(day)
                body = re.sub(r'(^Status: [^\n]+\n)', lambda m: m[0] + 'Запланировано: ' + day + '.\n', body, count=1, flags=re.M)
        if reopen_status is not None:
            if row['status'] not in {'done', 'completed'} or reopen_status not in {'active', 'idea', 'ready', 'blocked', 'in_progress', 'paused', 'waiting', 'review'}:
                raise ValueError('invalid_reopen_status')
            body = re.sub(r'^Status: .+$', 'Status: ' + reopen_status, body, count=1, flags=re.M)
        if completed and row['status'] not in TERMINAL:
            body = re.sub(r'^Status: .+$', 'Status: done', body, count=1, flags=re.M)
            if kind == 'paused':
                body = body.replace(body.splitlines()[0], '### ' + tid + ' — ' + title, 1)
                existing = [r for r in self.parser.read_records(self.pid, 'future', after['future']) if r['task_id'] == tid]
                if existing:
                    a, b, saved = chunk(after['future'], 'future', tid)
                    history_heading = '\n\nПрежняя запись до переноса с паузы:\n'
                    if existing[0]['status'] == 'promoted':
                        recovered = body.rstrip() + history_heading + '\n'.join('> ' + line for line in saved.splitlines()) + '\n'
                        after['future'] = after['future'][:a] + recovered + after['future'][b:]
                    elif saved.partition(history_heading)[0].strip() != body.strip():
                        raise ValueError('conflicting_paused_recovery')
                else:
                    after['future'] += '\n' + body + '\n'
                after[kind] = after[kind][:first] + after[kind][last:]
            else:
                after[kind] = after[kind][:first] + body + after[kind][last:]
        else:
            after[kind] = after[kind][:first] + body + after[kind][last:]
        self.save(after)

    def import_row(self, tid, remote):
        title = remote['title']
        if not title.strip() or '\n' in title or '\r' in title:
            raise ValueError('invalid_title')
        after = dict(self.texts)
        body = '\n### ' + tid + ' — ' + title + '\nStatus: ' + ('done' if remote.get('completed') else 'ready') + '\n'
        day = remote_day(remote)
        if day:
            body += 'Запланировано: ' + day + '.\n'
        # Внешние заметки — контекст, не канонические поля.
        if remote.get('notes'):
            body += '\nЗаметка из «Напоминаний»:\n' + '\n'.join('> ' + s for s in remote['notes'].splitlines()) + '\n'
        after['future'] += body
        self.save(after)


def inventory(hub):
    result = []
    for pid, path in task_projects(hub).items():
        result.extend(HubProject(hub, pid, path).rows().values())
    return result


_ANY_PARENT = object()


def reads_module():
    # Один экземпляр на процесс: модули Хаба загружают этот файл повторно.
    module = sys.modules.get('hub_reminders_reads')
    script = Path(__file__).with_name('reminders_reads.py')
    if module is None and script.exists():
        spec = importlib.util.spec_from_file_location('hub_reminders_reads', script)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        sys.modules['hub_reminders_reads'] = module
    return module


class Native:
    def __init__(self, config):
        self.config = config
    def call(self, tool, args):
        cancellation_tools = {'hub_cancel_capabilities', 'hub_cancel_status', 'hub_cancel_reminder', 'hub_restore_reminder'}
        parsed = {}
        selected = self.config['allowlist_file'] if tool in cancellation_tools else standard_allowlist(self.config)
        if tool in cancellation_tools and args.get('plan'):
            plan_path = safe_path(args['plan'])
            raw = plan_path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != args.get('plan_sha256'): raise ValueError('plan_checksum_mismatch')
            parsed = json.loads(raw)
            historical = any(self.config.get('projects',{}).get(i.get('project_id'),{}).get('historical_binding_migration') for i in parsed.get('items',[]) if i.get('reminder_id') == args.get('id'))
            if parsed.get('version') == 2 or historical:
                if 'standard_allowlist_file' not in self.config: raise ValueError('v2_standard_allowlist_required')
                selected = standard_allowlist(self.config)
        env = dict(os.environ, HUB_REMINDERS_ALLOWED_LISTS_FILE=selected)
        groups = self.config.get('structure', {}).get('groups_allowlist_file')
        if groups: env['HUB_REMINDERS_ALLOWED_GROUPS_FILE'] = str(safe_path(groups))
        env.pop('HUB_REMINDERS_ALLOWED_GROUP_IDS_FILE', None)
        pins = self.config.get('structure', {}).get('group_ids_allowlist_file')
        if pins: env['HUB_REMINDERS_ALLOWED_GROUP_IDS_FILE'] = str(safe_path(pins))
        binary = self.config.get('cancellation_binary', self.config['binary']) if tool in cancellation_tools else self.config['binary']
        # Совместимость чтения старых квитанций не заменяет проверенный исполнитель записей.
        if tool == 'hub_cancel_status' and parsed.get('version') == 2 and parsed.get('purpose') == 'task_cancellation':
            binary = self.config.get('cancellation_status_binary', binary)
        runner = lambda name, values: subprocess.run([binary, 'call', name, json.dumps(values, ensure_ascii=False)], env=env, capture_output=True, text=True, timeout=50)
        reads = reads_module()
        result = reads.call(binary, env, tool, args, runner) if reads else runner(tool, args)
        if result.returncode:
            raise RuntimeError('reminders_call_failed: ' + result.stderr[:500])
        if tool == 'manage_group' and args == {'action': 'create', 'group': 'Архив'}:
            # Штатный CLI возвращает для создания группы текст, а не JSON.
            match = re.fullmatch(r'Created the group "Архив"\. id: ([0-9A-Fa-f-]{36})\s*', result.stdout)
            if match:
                return {'id': str(uuid.UUID(match[1])).upper(), 'name': 'Архив'}
        value = json.loads(result.stdout[result.stdout.index('{'):])
        if value.get('error') or value.get('isError'):
            raise RuntimeError('reminders_error: ' + str(value)[:500])
        return value
    def get(self, rid, list_id, parent=_ANY_PARENT):
        value = self.call('get_reminder', {'id': rid})
        if value.get('list_id') != list_id or (parent is not _ANY_PARENT and value.get('parent_id') != parent):
            raise ValueError('reminder_binding_mismatch')
        return value
    def children(self, binding):
        value = self.call('find_reminders', {'list': binding['list_id'], 'include_completed': True, 'limit': 500})
        if (value.get('more') or value.get('has_more') or len(value['reminders']) > 500 or
                ('count' in value and value['count'] != len(value['reminders']))):
            raise ValueError('incomplete_reminder_snapshot')
        seen, children = set(), []
        for row in value['reminders']:
            if row.get('list') != binding['list_name'] or row.get('list_id', binding['list_id']) != binding['list_id']:
                raise ValueError('foreign_list_in_snapshot')
            if not row.get('id') or not row.get('version') or not isinstance(row.get('title'), str):
                raise ValueError('invalid_reminder_snapshot_row')
            if row['id'] in seen:
                raise ValueError('duplicate_reminder_in_snapshot')
            seen.add(row['id'])
            if row.get('parent_id') == binding.get('parent_id'):
                children.append(dict(row, list_id=binding['list_id']))
        return children
    def update(self, row, changes):
        self.call('update_reminder', dict(id=row['id'], version=row['version'], **changes))


def remote_day(remote):
    value = remote.get('due')
    if value is None:
        return None
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return dt.date.fromisoformat(value).isoformat()
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?', value):
        return dt.datetime.fromisoformat(value).date().isoformat()
    raise ValueError('invalid_remote_due')


def remote_due_for_day(day, remote):
    if day is None:
        return None
    original = remote.get('due')
    if original and 'T' in original:
        remote_day(remote)  # Сохраняем только проверенный хвост времени.
        return day + original[original.index('T'):]
    return day


def merge(local, remote, old_local, old_remote):
    lc, rc = local != old_local, remote != old_remote
    if lc and rc and local != remote:
        raise ValueError('two_sided_conflict')
    return remote if rc else local


def notes_for(row):
    label = row.get('project_label', row['project_id'])
    if not isinstance(label, str) or not label.strip() or any(not c.isprintable() for c in label):
        raise ValueError('invalid_project_label')
    return (label + '\n--- Hub metadata ---\nHub Task ID: ' + row['task_id'] +
            '\nHub project: ' + row['project_id'] + '\nHub label: ' + label + '\n--- /Hub metadata ---')


def managed_notes(existing, row, link, repeating=False):
    """Сохранить пользовательский текст и удалить только доказанно служебные части."""
    existing = existing or ''
    label = row.get('project_label', row['project_id'])
    if not isinstance(label, str) or not label.strip() or any(not c.isprintable() for c in label):
        raise ValueError('invalid_project_label')
    owner = link.get('notes_owner')
    if owner and 'line' in owner:
        start, end = owner.get('start'), owner.get('end')
        owned = owner.get('prefix', '') + owner['line']
        if (owner.get('snapshot') != existing or not isinstance(start, int) or
                not isinstance(end, int) or existing[start:end] != owned):
            previous = owner.get('snapshot')
            if (not isinstance(previous, str) or not isinstance(start, int) or
                    not isinstance(end, int) or previous[start:end] != owned):
                raise ValueError('notes_ownership_conflict')
            hits = [m.start() for m in re.finditer(re.escape(previous), existing)]
            if len(hits) != 1:
                raise ValueError('notes_ownership_conflict')
            start, end = hits[0] + start, hits[0] + end
        existing = existing[:start] + existing[end:]
        owner = None
    first, last = '--- Hub metadata ---', '--- /Hub metadata ---'
    compact = 'Хаб: ' + compact_code(row['project_id'], row['task_id'])
    if first in existing or last in existing:
        identity = creation_identity({'notes': existing})
        if identity != (row['project_id'], row['task_id']):
            raise ValueError('foreign_managed_notes')
        start = existing.index(first)
        end = existing.index(last) + len(last)
        block = existing[start:end]
        proof = re.findall(r'^Hub label: (.*)$', block, re.M)
        if proof and (len(proof) != 1 or proof[0] != label):
            raise ValueError('ambiguous_managed_notes')
        # Только новый временный блок доказывает владение соседней подписью.
        if proof:
            if start != len(label) + 1 or not existing.startswith(label + '\n'):
                raise ValueError('ambiguous_managed_notes')
            start = 0
            owner = None
        existing = existing[:start] + (compact if repeating else '') + existing[end:]
        if not proof and owner and 'label' in owner:
            owner = None  # Старый проверенный блок заменил прежнюю подпись; чужой текст не удаляем.
    elif has_identity_marker(existing):
        identity = creation_identity({'notes': existing}, {compact[5:]: (row['project_id'], row['task_id'])})
        if identity != (row['project_id'], row['task_id']):
            raise ValueError('foreign_managed_notes')
        if not repeating:
            match = re.search(r'(?m)^Хаб: [0-9a-f]{12}$', existing)
            existing = existing[:match.start()] + existing[match.end():]
        elif not owner and re.search(r'(?m)^Крайний срок: ', existing):
            raise ValueError('notes_ownership_conflict')
    elif repeating:
        existing += ('\n\n' if existing else '') + compact
    if owner and 'label' in owner:
        old_label = owner['label']
        if not isinstance(old_label, str) or not old_label:
            raise ValueError('notes_ownership_conflict')
        if existing == old_label or existing.startswith(old_label + '\n'):
            existing = existing[len(old_label):].removeprefix('\n')
        else:
            previous = owner.get('snapshot')
            if not isinstance(previous, str) or not previous.startswith(old_label):
                raise ValueError('notes_ownership_conflict')
            hits = [m.start() for m in re.finditer(re.escape(previous), existing)]
            if len(hits) != 1 or (hits[0] and existing[hits[0] - 1] != '\n'):
                raise ValueError('notes_ownership_conflict')
            start = hits[0]
            end = start + len(old_label)
            if end < len(existing) and existing[end] != '\n':
                raise ValueError('notes_ownership_conflict')
            if existing[end:end + 1] == '\n':
                end += 1
            existing = existing[:start] + existing[end:]
    existing = label + ('\n' + existing if existing else '')
    return existing, {'snapshot': existing, 'label': label}


def verify_history_row(remote, binding, identities=None):
    history = binding.get('history', {}).get(remote['id'])
    if not history or not remote.get('completed'):
        raise ValueError('invalid_recurrence_history')
    task = binding.get('tasks', {}).get(history['task_id'], {})
    if task.get('reminder_id') != history['original_id'] or creation_identity(remote, identities) != (history['project_id'], history['task_id']):
        raise ValueError('invalid_recurrence_history')


def verify_children_completed(native, binding, tasks, identities=None, cancelled=()):
    fresh = native.children(binding)
    expected = {t['reminder_id'] for tid, t in tasks.items() if t.get('reminder_id') and tid not in cancelled} | set(binding.get('history', {}))
    for row in fresh:
        if row['id'] in binding.get('history', {}):
            verify_history_row(row, binding, identities)
    if {r['id'] for r in fresh} != expected or any(not r.get('completed') for r in fresh):
        raise RuntimeError('cascade_children_changed_or_incomplete')


def verify_hub_completed(hp, tasks, cancelled=()):
    expected = set(hp.rows())
    fresh = HubProject(hp.hub, hp.pid, hp.project).rows()
    if set(fresh) != expected or any(tid not in fresh or fresh[tid]['status'] not in ({'dropped'} if tid in cancelled else {'done', 'completed'}) for tid in tasks):
        raise RuntimeError('cascade_hub_changed_or_incomplete')


def structure_module():
    script = safe_path(Path(__file__).absolute().with_name('reminders_structure.py'))
    spec = importlib.util.spec_from_file_location('reminders_structure', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def external_retirement_module():
    script = Path(__file__).with_name('reminders_external_retirement.py')
    if not script.exists(): return None
    spec = importlib.util.spec_from_file_location('reminders_external_retirement', script)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def cancellation_module():
    script = safe_path(Path(__file__).absolute().with_name('reminders_cancel.py'))
    if not script.exists():
        return None
    spec = importlib.util.spec_from_file_location('reminders_cancellation', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sync_notes(hub, config, apply=False, project=None, native=None):
    if authority_enabled(config):
        authority_module().validate_policy(hub, config)
        raise ValueError('authority_explicit_task_gateway_required')
    """Узкая сверка заметок существующих открытых привязанных задач."""
    reports = []
    if project and project not in config['projects']:
        return {'applied': apply, 'ok': False, 'items': [{'project': project, 'error': 'missing_project_binding'}], 'summary': {'changed': 0, 'skipped': 0}}
    allowed = registered(hub)
    identities = compact_identities(config)
    cancellation = cancellation_module()
    if cancellation is None and any(t.get('cancellation') for b in config['projects'].values() for t in b.get('tasks', {}).values()):
        raise ValueError('cancellation_support_missing')
    blocked = cancellation.pending_projects(hub, config) if cancellation else set()
    migrating = migration_pending(hub, config)
    if migrating & ({project} if project else set(config['projects'])):
        return {'applied': apply, 'ok': False, 'items': [{'project': pid, 'error': 'migration_recovery_required'} for pid in sorted(migrating)], 'summary': {'changed': 0, 'skipped': 0}}
    selected = {pid: binding for pid, binding in config['projects'].items() if not project or pid == project}
    names = json.loads(safe_path(standard_allowlist(config)).read_text())['names']
    for pid, binding in selected.items():
        if pid in blocked:
            reports.append({'project': pid, 'error': 'cancellation_recovery_required'})
        elif binding.get('archive'):
            continue
        elif pid not in allowed:
            reports.append({'project': pid, 'error': 'unregistered_or_inactive_project'})
        elif binding['list_name'] not in names:
            reports.append({'project': pid, 'error': 'list_outside_allowlist'})
    if reports:
        return {'applied': apply, 'ok': False, 'items': reports,
                'summary': {'changed': 0, 'skipped': 0}}
    native = native or Native(config)
    config_path = Path(hub) / 'ai/reminders-sync.json'

    def checkpoint():
        if apply:
            validate_binding_ids(config)
            atomic_json(config_path, config)

    for pid, binding in config['projects'].items():
        if project and pid != project:
            continue
        try:
            if pid in blocked:
                raise ValueError('cancellation_recovery_required')
            if binding.get('archive'):
                if not archive_module(config).verify_current(hub, config, pid, native):
                    raise ValueError('archive_unverified')
                reports.append({'project': pid, 'action': 'archive_verified'})
                continue
            if pid not in allowed:
                raise ValueError('unregistered_or_inactive_project')
            rows = HubProject(hub, pid, allowed[pid]).rows()
            external = external_retirement_module()
            if external: external.collect(hub, config, pid, native)
            label = project_label(hub, pid, binding)
            for tid, link in binding.get('tasks', {}).items():
                row = rows.get(tid)
                if not row or row['status'] in TERMINAL or link.get('cancellation') or not link.get('reminder_id'):
                    reports.append({'project': pid, 'task_id': tid, 'action': 'skipped'})
                    continue
                try:
                    remote = native.get(link['reminder_id'], binding['list_id'], binding.get('parent_id'))
                    if remote.get('id') != link['reminder_id'] or not remote.get('version'):
                        raise ValueError('invalid_bound_reminder_version')
                    if remote.get('completed'):
                        reports.append({'project': pid, 'task_id': tid, 'action': 'skipped'})
                        continue
                    pending = link.get('pending_notes')
                    before = remote.get('notes') or ''
                    effective_link = link
                    if pending:
                        if before == pending['after']:
                            protected = pending.get('protected')
                            if not isinstance(protected, dict):
                                raise ValueError('pending_notes_unverifiable')
                            if any(remote.get(key) != protected.get(key) for key in PROTECTED_REMINDER_FIELDS):
                                raise RuntimeError('remote_protected_fields_changed')
                            effective_link = dict(link, notes_owner=pending['owner'])
                            if apply:
                                link['notes_owner'] = pending['owner']
                                link.pop('pending_notes')
                                checkpoint()
                        elif before != pending['before']:
                            raise ValueError('pending_notes_conflict')
                    notes, owner = managed_notes(before, dict(row, project_label=label), effective_link,
                                                 repeating=bool(link.get('repeating') or remote.get('repeat')))
                    if notes == before:
                        if apply and link.get('notes_owner') != owner:
                            link['notes_owner'] = owner
                            checkpoint()
                        reports.append({'project': pid, 'task_id': tid, 'action': 'unchanged'})
                        continue
                    reports.append({'project': pid, 'task_id': tid, 'reminder_id': remote['id'],
                                    'version': remote['version'], 'action': 'notes',
                                    'before': before, 'after': notes})
                    if apply:
                        link['pending_notes'] = {'before': before, 'after': notes, 'owner': owner,
                                                 'protected': {key: remote.get(key) for key in PROTECTED_REMINDER_FIELDS}}
                        checkpoint()
                        native.update(remote, {'notes': notes})
                        fresh = native.get(remote['id'], binding['list_id'], binding.get('parent_id'))
                        if (fresh.get('notes') or '') != notes:
                            raise RuntimeError('remote_readback_failed')
                        if any(fresh.get(key) != remote.get(key) for key in PROTECTED_REMINDER_FIELDS):
                            raise RuntimeError('remote_protected_fields_changed')
                        link['notes_owner'] = owner
                        link.pop('pending_notes', None)
                        checkpoint()
                except Exception as error:
                    reports.append({'project': pid, 'task_id': tid, 'error': str(error)})
        except Exception as error:
            reports.append({'project': pid, 'error': str(error)})
    return {'applied': apply, 'ok': not any('error' in item for item in reports), 'items': reports,
            'summary': {'changed': sum(item.get('action') == 'notes' for item in reports),
                        'skipped': sum(item.get('action') == 'skipped' for item in reports)}}


def sync(hub, config, apply=False, project=None, native=None, structure_native=None, reconcile=True):
    if not authority_enabled(config):
        return _sync(hub, config, apply, project, native, structure_native, reconcile)
    authority = authority_module()
    with authority.locked(hub):
        authority.validate_policy(hub, config)
        pending = gateway_module().pending_projects(hub)
        if pending & ({project} if project else set(config['projects'])):
            return dict(applied=False, ok=False, items=[dict(project=pid, error='task_write_recovery_required') for pid in sorted(pending) if not project or pid == project])
        prepared = authority.prepare_pull(sys.modules.get(__name__) or type('Sync', (), globals()), hub, config, apply, project, native)
        if prepared['stop']:
            return dict(applied=False, ok=True, items=prepared['items'], stop=True)
        if config is not prepared['config']:
            config.clear(); config.update(prepared['config'])
        return _sync(hub, config, apply, project, native, structure_native, reconcile, prepared['items'], prepared)


def _sync(hub, config, apply=False, project=None, native=None, structure_native=None, reconcile=True, incoming_items=(), incoming_state=None):
    incoming = authority_enabled(config)
    incoming_state = incoming_state or {}
    partial_pull = incoming_state.get('cancellation_disabled', False)
    migrating = migration_pending(hub, config)
    if migrating & ({project} if project else set(config['projects'])):
        return {'applied': apply, 'ok': False, 'items': [{'project': pid, 'error': 'migration_recovery_required'} for pid in sorted(migrating)]}
    reports = list(incoming_items)
    blocked = set(incoming_state.get('blocked_projects', ()))
    cancellation = cancellation_module()
    has_receipts = any(t.get('cancellation') for b in config['projects'].values() for t in b.get('tasks', {}).values())
    if cancellation is None and (has_receipts or (Path(hub) / 'ai/reminders-cancellations').exists()):
        raise ValueError('cancellation_support_missing')
    cancellation_blocked = cancellation.pending_projects(hub, config) if cancellation else set()
    blocked.update(cancellation_blocked)
    reports.extend({'project': pid, 'error': 'cancellation_recovery_required'} for pid in sorted(cancellation_blocked) if not project or pid == project)
    if not incoming_state.get('skip_structure') and (config.get('structure', {}).get('enabled') or config.get('structure', {}).get('journal_file')):
        structural = structure_module()
        if reconcile and not project and config.get('structure',{}).get('enabled') and not cancellation_blocked:
            before_structure = config
            outcome = structural.reconcile_structure(hub, config, apply=apply, native=structure_native)
            config = outcome['config']
            if not apply:
                # Preview reads tasks where they physically are until the structural move is applied.
                config = copy.deepcopy(config)
                for item in outcome['items']:
                    pid=item.get('project')
                    if item.get('direction')=='outgoing' and pid in config['projects']:
                        for key in ('list_id','list_name'):
                            config['projects'][pid][key]=before_structure['projects'][pid][key]
            reports.extend(outcome['items'])
            blocked.update(outcome['blocked_projects'])
        else:
            blocked.update(structural.pending_structure_projects(hub, config))
            reports.extend({'project': pid, 'error': 'structure_recovery_required'} for pid in sorted(blocked) if not project or pid == project)
    identities = compact_identities(config)
    native = native or Native(config)
    allowed = task_projects(hub, config)
    config_path = Path(hub) / 'ai/reminders-sync.json'
    def checkpoint():
        if apply:
            validate_binding_ids(config)
            identities.update(compact_identities(config))
            atomic_json(config_path, config)
    if not project:
        for unbound_pid, path in allowed.items():
            if unbound_pid in config['projects']:
                continue
            try:
                if any(r['status'] not in TERMINAL for r in HubProject(hub, unbound_pid, path).rows().values()):
                    reports.append({'project': unbound_pid, 'error': 'missing_project_binding'})
            except Exception as error:
                reports.append({'project': unbound_pid, 'error': 'unbound_project_inventory_failed: ' + str(error)})
    for pid, binding in config['projects'].items():
        if (project and pid != project) or pid in blocked:
            continue
        try:
            if binding.get('archive') and not incoming:
                if not archive_module(config).verify_current(hub, config, pid, native):
                    raise ValueError('archive_unverified')
                reports.append({'project': pid, 'action': 'archive_verified'})
                continue
            if pid not in allowed:
                raise ValueError('unregistered_or_inactive_project')
            hp = HubProject(hub, pid, allowed[pid])
            rows = hp.rows()
            label = project_label(hub, pid, binding)
            rows = {tid: dict(row, project_label=label) for tid, row in rows.items()}
            tasks = binding.setdefault('tasks', {})
            cancelled = set()
            # Проверяем все записи об отмене до импорта и любой записи проекта.
            for tid, link in tasks.items():
                if link.get('external_retirement'):
                    if tid not in rows: raise ValueError('missing_hub_task: ' + tid)
                    external = external_retirement_module()
                    if external is None: raise ValueError('external_retirement_support_missing')
                    external.verify_link(hub, rows[tid], link, binding, native)
                    cancelled.add(tid)
                elif link.get('cancellation'):
                    if tid not in rows:
                        raise ValueError('missing_hub_task: ' + tid)
                    cancellation.verify_cancelled_link(hub, rows[tid], link, binding, native)
                    cancelled.add(tid)
            parent = {} if binding.get('layout') == 'project_list' else native.get(binding['parent_id'], binding['list_id'])
            if parent.get('parent_id'):
                raise ValueError('parent_is_subtask')
            children = native.children(binding)
            if binding.get('layout') == 'project_list':
                structure_module().validate_project_ownership(pid, children, config)
            remotes = {r['id']: r for r in children}
            history = binding.setdefault('history', {})
            if not set(history) <= set(remotes):
                raise ValueError('missing_recurrence_history')
            # Завершаем импорт после сбоя между сохранением привязки и канонической записью.
            for tid, link in tasks.items():
                if link.get('pending_import') and tid not in rows:
                    if partial_pull:
                        raise ValueError('partial_pull_import_recovery_required')
                    remote = remotes.get(link.get('reminder_id'))
                    if remote is None:
                        raise ValueError('missing_pending_import_reminder')
                    if apply:
                        hp.import_row(tid, remote)
                        rows = {key: dict(value, project_label=label) for key, value in hp.rows().items()}
                    else:
                        reports.append({'project': pid, 'task_id': tid, 'action': 'resume_import'})
            # Любая исчезнувшая связь блокирует проект до исправления, удаления не каскадируются.
            for tid, link in tasks.items():
                if tid not in rows and not (link.get('pending_import') and not apply):
                    raise ValueError('missing_hub_task: ' + tid)
                if link.get('reminder_id') and link['reminder_id'] not in remotes and tid not in cancelled:
                    raise ValueError('missing_remote_task: ' + tid)
            bound = {t['reminder_id'] for t in tasks.values() if t.get('reminder_id')}
            # Восстановление после неизвестного результата создания: только по уникальному маркеру.
            for tid, link in tasks.items():
                if link.get('pending_create') and not link.get('reminder_id'):
                    if partial_pull:
                        raise ValueError('partial_pull_creation_recovery_required')
                    found = [r for r in children if ('Hub Task ID: ' + tid) in r.get('notes', '').splitlines()]
                    if len(found) != 1:
                        raise ValueError('uncertain_creation_requires_review: ' + tid)
                    if creation_identity(found[0]) != (pid, tid):
                        raise ValueError('creation_identity_mismatch')
                    link['reminder_id'] = found[0]['id']
                    bound.add(found[0]['id'])
                    checkpoint()
            # Неизвестные дети импортируются с сохранением стабильного Task ID до записи в Хаб.
            for remote in children:
                if partial_pull and remote['id'] not in bound:
                    continue
                if remote['id'] in bound:
                    continue
                if remote['id'] in history:
                    verify_history_row(remote, binding, identities)
                    reports.append({'project': pid, 'action': 'recurrence_history_ignored', 'reminder_id': remote['id']})
                    continue
                markers = []
                if has_identity_marker(remote.get('notes')):
                    identity = creation_identity(remote, identities)
                    if identity[0] != pid:
                        raise ValueError('recurrence_history_identity_mismatch')
                    markers = [identity[1]]
                if markers:
                    series = tasks.get(markers[0], {})
                    live = remotes.get(series.get('reminder_id'), {})
                    if remote.get('completed') and (series.get('repeating') or live.get('repeat')):
                        history[remote['id']] = {'original_id': series['reminder_id'], 'task_id': markers[0], 'project_id': pid}
                        checkpoint()
                        reports.append({'project': pid, 'action': 'recurrence_history_ignored', 'reminder_id': remote['id']})
                        continue
                    raise ValueError('unbound_hub_marker_requires_review')
                has_live_repeat = any(remotes.get(t.get('reminder_id'), {}).get('repeat') or t.get('repeating') for t in tasks.values())
                if remote.get('completed') and has_live_repeat:
                    raise ValueError('unidentified_completed_task_requires_review')
                reports.append({'project': pid, 'action': 'import', 'reminder_id': remote['id']})
                if apply:
                    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).strftime('%Y%m%d')
                    number = 1
                    while f'TASK-{pid}-{stamp}-{number:03}' in rows or f'TASK-{pid}-{stamp}-{number:03}' in tasks:
                        number += 1
                    tid = f'TASK-{pid}-{stamp}-{number:03}'
                    tasks[tid] = {'reminder_id': remote['id'], 'pending_import': True}
                    checkpoint()
                    hp.import_row(tid, remote)
                    rows = {key: dict(value, project_label=label) for key, value in hp.rows().items()}
                    bound.add(remote['id'])
            cascade = not incoming and (bool(parent.get('completed')) or bool(binding.get('complete_requested')))
            for tid, row in list(rows.items()):
                try:
                    if tid in cancelled:
                        reports.append({'project': pid, 'task_id': tid, 'action': 'cancellation_verified'})
                        continue
                    link = tasks.get(tid)
                    if link is None and row['status'] in TERMINAL:
                        continue
                    if link is None and incoming:
                        continue
                    if link is None:
                        reports.append({'project': pid, 'task_id': tid, 'action': 'publish'})
                        if not apply:
                            continue
                        tasks[tid] = link = {'pending_create': True}
                        checkpoint()
                        remote = native.call('create_reminder', {'title': row['title'], 'list': binding['list_id'], **({} if binding.get('layout') == 'project_list' else {'parent_id': binding['parent_id']}), 'notes': notes_for(row), **({'due': row['planned_day']} if row['planned_day'] else {})})
                        link['reminder_id'] = remote['id']
                        checkpoint()  # Полученный идентификатор сохраняется до любых следующих изменений.
                        remote = native.get(remote['id'], binding['list_id'], binding.get('parent_id'))
                        remotes[remote['id']] = remote
                        link.update(last_hub_day=row['planned_day'], last_remote_day=remote_day(remote), last_hub_title=row['title'], last_remote_title=remote['title'], last_completed=False)
                        checkpoint()
                    if not link.get('reminder_id'):
                        continue
                    remote = remotes[link['reminder_id']]
                    pending = link.get('pending_notes')
                    if pending:
                        if 'protected' in pending:
                            remote = native.get(link['reminder_id'], binding['list_id'], binding.get('parent_id'))
                            protected = pending['protected']
                            if (not isinstance(protected, dict) or
                                    any(remote.get(key) != protected.get(key) for key in PROTECTED_REMINDER_FIELDS)):
                                raise RuntimeError('remote_protected_fields_changed')
                            remotes[link['reminder_id']] = remote
                        actual_notes = remote.get('notes') or ''
                        if actual_notes == pending['after']:
                            link['notes_owner'] = pending['owner']
                            link.pop('pending_notes')
                            checkpoint()
                        elif actual_notes != pending['before']:
                            raise ValueError('pending_notes_conflict')
                    repeating = bool(link.get('repeating') or remote.get('repeat'))
                    if repeating and cascade:
                        raise ValueError('cascade_repeating_requires_explicit_cancel')
                    reopen_status = None
                    if incoming:
                        if row['status'] in {'dropped', 'promoted'}:
                            raise ValueError('terminal_status_requires_review')
                        if repeating and row['status'] in TERMINAL:
                            raise ValueError('repeating_hub_terminal_requires_review')
                        day, title = remote_day(remote), remote['title']
                        completed = False if repeating else bool(remote.get('completed'))
                        if not completed and not repeating and row['status'] in {'done', 'completed'}:
                            reopened = link.get('last_open_status', 'ready')
                            reopen_status = reopened if reopened in {'active', 'idea', 'ready', 'blocked', 'in_progress', 'paused', 'waiting', 'review'} else 'ready'
                        changes = {}
                        notes_owner = link.get('notes_owner')
                        hub_changed = title != row['title'] or day != row['planned_day'] or (completed and row['status'] not in TERMINAL) or reopen_status is not None
                    else:
                        day = merge(row['planned_day'], remote_day(remote), link.get('last_hub_day', row['planned_day']), link.get('last_remote_day', remote_day(remote)))
                        title = merge(row['title'], remote['title'], link.get('last_hub_title', row['title']), link.get('last_remote_title', row['title']))
                        if row['status'] in {'dropped', 'promoted'}:
                            raise ValueError('terminal_status_requires_review')
                        completed = False if repeating else (cascade or row['status'] in {'done', 'completed'} or bool(remote.get('completed')))
                        if repeating and row['status'] in TERMINAL:
                            raise ValueError('repeating_hub_terminal_requires_review')
                        if link.get('last_completed') and not remote.get('completed') and row['status'] in {'done', 'completed'}:
                            raise ValueError('remote_reopen_requires_review')
                        changes = {}
                        notes, notes_owner = managed_notes(remote.get('notes'), row, link, repeating=repeating)
                        if notes != (remote.get('notes') or ''): changes['notes'] = notes
                        if title != remote['title']: changes['title'] = title
                        if day != remote_day(remote): changes['due'] = remote_due_for_day(day, remote)
                        if completed and not remote.get('completed'): changes['completed'] = True
                        hub_changed = title != row['title'] or day != row['planned_day'] or (completed and row['status'] not in TERMINAL)
                    if changes or hub_changed:
                        reports.append({'project': pid, 'task_id': tid, 'action': 'sync', 'hub': hub_changed, 'remote_fields': list(changes)})
                    if apply:
                        if changes:
                            if 'notes' in changes:
                                link['pending_notes'] = {'before': remote.get('notes') or '', 'after': notes, 'owner': notes_owner}
                                checkpoint()  # Журнал владения сохраняется до удалённого изменения.
                            native.update(remote, changes)
                            remote = native.get(remote['id'], binding['list_id'], binding.get('parent_id'))
                            if any(((remote.get(k) or '') if k == 'notes' else remote.get(k)) != v for k, v in changes.items()):
                                raise RuntimeError('remote_readback_failed')
                        if hub_changed:
                            if incoming and completed and row['status'] not in TERMINAL:
                                link['last_open_status'] = row['status']
                            hp.update(row, title, day, completed, reopen_status=reopen_status)
                        if not incoming:
                            link['notes_owner'] = notes_owner
                            link.pop('pending_notes', None)
                        link.update(last_hub_day=day, last_remote_day=day, last_hub_title=title, last_remote_title=title, last_completed=completed)
                        link.pop('pending_create', None)
                        link.pop('pending_import', None)
                        checkpoint()
                except Exception as error:
                    reports.append({'project': pid, 'task_id': tid, 'error': str(error)})
            if cascade and apply and not any(r.get('error') and r['project'] == pid for r in reports):
                for tid in cancelled:
                    (external_retirement_module().verify_link if tasks[tid].get('external_retirement') else cancellation.verify_cancelled_link)(hub, rows[tid], tasks[tid], binding, native)
                verify_children_completed(native, binding, tasks, identities, cancelled)
                verify_hub_completed(hp, tasks, cancelled)
                if parent and not parent.get('completed'):
                    native.update(parent, {'completed': True})
                    if not native.get(parent['id'], binding['list_id']).get('completed'):
                        raise RuntimeError('parent_completion_readback_failed')
                for tid in cancelled:
                    (external_retirement_module().verify_link if tasks[tid].get('external_retirement') else cancellation.verify_cancelled_link)(hub, rows[tid], tasks[tid], binding, native)
                verify_children_completed(native, binding, tasks, identities, cancelled)
                verify_hub_completed(hp, tasks, cancelled)
                binding.pop('complete_requested', None)
                binding['last_completed'] = True
                checkpoint()
        except Exception as error:
            reports.append({'project': pid, 'error': str(error)})
    if project and project not in config['projects']:
        reports.append({'project': project, 'error': 'missing_project_binding'})
    summary={direction:sum(r.get('direction')==direction for r in reports) for direction in ('incoming','outgoing','converged','conflict')}
    summary['task_fields_merged']=sum(r.get('action')=='sync' and r.get('hub',False) and bool(set(r.get('remote_fields',[]))&{'title','due'}) for r in reports)
    summary['pending_projects']=len(structure_module().pending_structure_projects(hub,config)) if config.get('structure',{}).get('journal_file') else 0
    result = {'applied': apply, 'ok': not any('error' in r for r in reports), 'items': reports, 'summary':summary}
    if partial_pull:
        result['complete'] = False
    return result


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('command', choices=['inventory', 'sync', 'publish', 'complete-project', 'notes'])
    cli.add_argument('--hub', required=True)
    cli.add_argument('--project')
    cli.add_argument('--apply', action='store_true')
    args = cli.parse_args()
    try:
        hub = safe_path(Path(args.hub).absolute())
        if args.command == 'inventory':
            result = inventory(hub)
        else:
            # Не допускаем одновременные записи двух процессов планирования.
            with sync_lock(hub):
                config = load_config(hub)
                if authority_enabled(config) and args.command in {'publish', 'complete-project', 'notes'}:
                    raise ValueError('authority_explicit_task_gateway_required')
                if args.command == 'complete-project':
                    if args.project in structure_module().pending_structure_projects(hub, config):
                        raise ValueError('structure_recovery_required')
                    if not args.project or args.project not in config['projects']:
                        raise ValueError('complete_project_requires_bound_project')
                    config['projects'][args.project]['complete_requested'] = True
                    if args.apply:
                        atomic_json(hub / 'ai/reminders-sync.json', config)
                reads = reads_module()
                with reads.run_scope() if reads else contextlib.nullcontext():
                    result = (sync_notes(hub, config, args.apply, args.project) if args.command == 'notes' else
                              sync(hub, config, args.apply, args.project, reconcile=args.command == 'sync'))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if isinstance(result, list) or result['ok'] else 1
    except Exception as error:
        print(json.dumps({'ok': False, 'error': str(error)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
