#!/usr/bin/env python3
"""Точный перенос проекта в отдельный список с журналом до каждой записи."""
import argparse
import copy
import fcntl
import hashlib
import importlib.util
import json
import math
import os
import re
from pathlib import Path
import tempfile
import uuid
from contextlib import contextmanager


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n'


def sha(data):
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def safe(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or path != path.resolve() or any(x.is_symlink() for x in (path, *path.parents)):
        raise ValueError('unsafe_path')
    return path


def durable(path, data, exclusive=False):
    path = safe(path)
    if exclusive:
        with path.open('x') as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
    else:
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno()); name = handle.name
        os.replace(name, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def load_sync():
    spec = importlib.util.spec_from_file_location('migration_sync', Path(__file__).with_name('reminders_sync.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


@contextmanager
def locked(hub):
    with safe(Path(hub) / 'ai/.reminders-sync.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def config_read(hub):
    raw = safe(hub / 'ai/reminders-sync.json').read_text()
    config = json.loads(raw)
    load_sync().validate_binding_ids(config)
    if safe(config['allowlist_file']) != hub / 'ai/reminders-allowlist.json':
        raise ValueError('unsafe_original_allowlist')
    if config.get('standard_allowlist_file') and safe(config['standard_allowlist_file']) != hub / 'ai/reminders-standard-allowlist.json':
        raise ValueError('unsafe_standard_allowlist')
    return config, raw


def permission_data(hub, name):
    config, raw = config_read(hub)
    original = safe(config['allowlist_file']).read_text()
    names = json.loads(original)['names']
    target = safe(hub / 'ai/reminders-standard-allowlist.json')
    previous = target.read_text() if target.exists() else None
    permitted = json.loads(previous)['names'] if previous is not None else names
    if (not isinstance(names, list) or not isinstance(permitted, list) or
            any(not isinstance(x, str) or not x for x in names + permitted) or
            len(set(permitted)) != len(permitted) or not set(names) <= set(permitted) or not isinstance(name, str) or not name.strip()):
        raise ValueError('invalid_permission_names')
    after = permitted + ([name] if name not in permitted else [])
    return dict(original=original, before=previous, after=encoded({'names':after}), added=[x for x in after if x not in permitted])


def journal(hub, plan):
    root = safe(hub / 'ai/reminders-project-lists'); root.mkdir(exist_ok=True)
    folder = safe(root / str(uuid.uuid4())); folder.mkdir()
    plan = dict(plan, hub=str(hub), operation=folder.name)
    path = folder / 'plan.json'; raw = encoded(plan); durable(path, raw, True)
    durable(folder / 'state.json', encoded(dict(sha256=sha(raw), phase='preview', steps={})), True)
    return dict(plan=str(path), sha256=sha(raw), added=plan.get('permission', {}).get('added', []))


def read_plan(path, digest, kind=None):
    path = safe(path); raw = path.read_text()
    if sha(raw) != digest: raise ValueError('plan_sha256_mismatch')
    plan = json.loads(raw); hub = safe(plan['hub'])
    if path != hub / 'ai/reminders-project-lists' / plan['operation'] / 'plan.json': raise ValueError('unsafe_plan_location')
    if kind and plan['kind'] != kind: raise ValueError('wrong_plan_kind')
    state = json.loads(safe(path.parent / 'state.json').read_text())
    if state['sha256'] != digest: raise ValueError('state_sha256_mismatch')
    return path, plan, state


def permission_preview(hub, name):
    hub = safe(hub)
    with locked(hub):
        permission = permission_data(hub, name)
        result = journal(hub, dict(kind='permission', list_name=name, permission=permission))
        result.update(before_names=json.loads(permission['before'] or permission['original'])['names'], after_names=json.loads(permission['after'])['names'], removed=[])
        return result


def permission_apply(path, digest, approve=False):
    if not approve: raise ValueError('explicit_approval_required')
    path, plan, state = read_plan(path, digest, 'permission'); hub = safe(plan['hub'])
    with locked(hub):
        current = permission_data(hub, plan['list_name']); expected = plan['permission']
        target = hub / 'ai/reminders-standard-allowlist.json'
        if current['original'] != expected['original']: raise ValueError('original_permission_changed')
        if current['before'] == expected['after']:
            state.update(phase='complete', approved=True); durable(path.parent / 'state.json', encoded(state))
            return dict(phase='complete', names=json.loads(expected['after'])['names'])
        if current != expected: raise ValueError('permission_changed')
        state['phase'] = 'writing'; durable(path.parent / 'state.json', encoded(state))
        durable(target, expected['after']); state.update(phase='complete', approved=True); durable(path.parent / 'state.json', encoded(state))
        return dict(phase='complete', names=json.loads(target.read_text())['names'])


class Native:
    def __init__(self, config):
        self.cancellation = load_sync().Native(config)
        self.delegate = load_sync().structure_module().StructureNative(dict(config, structure=dict(config['structure'], bidirectional=True)))
    def call(self, tool, args):
        if tool.startswith('hub_cancel') or tool == 'hub_restore_reminder': return self.cancellation.call(tool, args)
        return self.delegate.call(tool, args)
    def get(self, rid, lid):
        row = self.call('get_reminder', {'id':rid})
        if row.get('list_id') != lid: raise ValueError('reminder_binding_mismatch')
        return row


def metadata(native):
    value = native.call('list_lists', {})
    for key in ('lists', 'groups'):
        rows = value.get(key)
        if not isinstance(rows, list) or any(not r.get('id') or not r.get('name') or not r.get('account_id') for r in rows) or len({r['id'] for r in rows}) != len(rows):
            raise ValueError('invalid_account_metadata')
    if len({r['name'] for r in value['lists']}) != len(value['lists']): raise ValueError('ambiguous_list_name')
    native._migration_detail_supported = value.get('detailed_reminder_snapshot') is True
    return value


def reset_cache(native):
    native._migration_detail_cache = {}
    native._migration_batch_lists = set()


def summary_projection(row):
    result = copy.deepcopy(row)
    for key in ('list_id', 'shared_list', 'alarms', 'early_alerts', 'urls', 'subtasks', 'smart_lists'):
        result.pop(key, None)
    if isinstance(result.get('images'), list): result['images'] = len(result['images'])
    return result


def validate_detailed_fields(row):
    """Типы присутствующих полей ровно из production Output/get; nil-поля там опущены."""
    text = lambda value: isinstance(value, str)
    boolean = lambda value: type(value) is bool
    integer = lambda value: type(value) is int
    number = lambda value: type(value) in (int,float) and math.isfinite(value)
    def sequence(check):
        return lambda value: isinstance(value,list) and all(check(item) for item in value)
    def record(value, required, optional=None):
        optional = optional or {}
        return (isinstance(value,dict) and set(required) <= set(value) <= set(required) | set(optional)
                and all(check(value[key]) for key,check in required.items())
                and all(check(value[key]) for key,check in optional.items() if key in value))
    image = lambda value: record(value, dict(id=text,type=text,width=integer,height=integer,bytes=integer))
    child = lambda value: record(value, dict(id=valid_uuid,title=text), dict(completed=boolean))
    alert = lambda value: record(value, dict(before=integer,unit=lambda unit: unit in ('minutes','hours','days','weeks','months')))
    repeat = lambda value: record(value, dict(frequency=text,interval=integer),
                dict(days_of_week=sequence(text),days_of_month=sequence(integer),months=sequence(integer),until=text,count=integer))
    def location(value):
        if isinstance(value,str): return value in ('getting-in-car','getting-out-of-car')
        return record(value, dict(title=text,latitude=number,longitude=number,radius=number,
                                  when=lambda item: item in ('arriving','leaving')), dict(address=text))
    messaging = lambda value: record(value,dict(phones=sequence(text),emails=sequence(text)))
    optional = {key:text for key in ('due','start','priority','notes','section','url','assigned_to','completed_at')}
    optional.update({key:boolean for key in ('completed','flagged','urgent','shared_list')})
    optional.update(parent_id=valid_uuid,tags=sequence(text),alarms=sequence(text),urls=sequence(text),
                    images=sequence(image),subtasks=sequence(child),early_alerts=sequence(alert),
                    repeat=repeat,location=location,when_messaging=messaging)
    if not record(row,dict(id=valid_uuid,list_id=valid_uuid,list=text,title=text,version=lambda value: text(value) and bool(value)),optional):
        raise ValueError('invalid_detailed_fields')


def validate_detailed_parents(result):
    for rid,row in result.items():
        seen={rid}; parent=row.get('parent_id')
        while parent is not None:
            if parent not in result or parent in seen: raise ValueError('invalid_detailed_parent_reference')
            seen.add(parent);parent=result[parent].get('parent_id')


def detailed_rows(native, lid):
    value = native.call('find_reminders', dict(list=lid, include_completed=True, limit=500, detail=True))
    listing = value.get('reminders') if isinstance(value, dict) else None
    if (not isinstance(listing, list) or value.get('detail') is not True or
            type(value.get('count')) is not int or value['count'] != len(listing) or
            ('more' in value and (type(value['more']) is not int or value['more'] < 0)) or
            ('has_more' in value and type(value['has_more']) is not bool) or
            value.get('more') or value.get('has_more') or len(listing) >= 500):
        raise ValueError('incomplete_detailed_snapshot')
    result = {}
    for row in listing:
        if (not isinstance(row, dict) or not isinstance(row.get('id'), str) or
                not valid_uuid(row['id']) or row['id'] in result or row.get('list_id') != lid or
                not isinstance(row.get('version'), str) or not row['version'] or
                not isinstance(row.get('title'), str) or not isinstance(row.get('list'), str) or
                'smart_lists' in row or ('images' in row and not isinstance(row['images'], list)) or
                ('subtasks' in row and (not isinstance(row['subtasks'], list) or
                    any(not isinstance(child, dict) or not valid_uuid(child.get('id')) or not isinstance(child.get('title'), str) for child in row['subtasks'])))):
            raise ValueError('invalid_detailed_snapshot')
        validate_detailed_fields(row)
        result[row['id']] = row
    validate_detailed_parents(result)
    for rid, row in result.items():
        children = row.get('subtasks', [])
        expected = {cid for cid,child in result.items() if child.get('parent_id') == rid}
        if len(children) != len({child['id'] for child in children}) or {child['id'] for child in children} != expected:
            raise ValueError('invalid_detailed_children')
        for child in children:
            actual = result[child['id']]
            if child['title'] != actual['title'] or child.get('completed',False) != actual.get('completed',False): raise ValueError('invalid_detailed_children')
    cache = getattr(native, '_migration_detail_cache', {})
    for rid, row in result.items(): cache[(lid, rid)] = (summary_projection(row), copy.deepcopy(row))
    native._migration_detail_cache = cache
    native._migration_batch_lists = getattr(native, '_migration_batch_lists', set()) | {lid}
    return copy.deepcopy(result)


def valid_uuid(value):
    try: return isinstance(value, str) and str(uuid.UUID(value)).upper() == value.upper()
    except (ValueError, TypeError, AttributeError): return False


def rows(native, lid):
    supported = getattr(native, '_migration_detail_supported', False)
    if supported and (lid not in getattr(native, '_migration_batch_lists', set()) or
            any(key[0] == lid and (cached[1].get('subtasks') or cached[1].get('parent_id'))
                for key, cached in getattr(native, '_migration_detail_cache', {}).items())):
        # Краткий find сортирует строки, а subtasks сохраняет исходный порядок.
        # Перестановка детей не меняет version: только полный пакет доказывает
        # точную иерархию без отдельного глобального чтения каждого родителя.
        return detailed_rows(native, lid)
    value = native.call('find_reminders', dict(list=lid, include_completed=True, limit=500))
    listing = value['reminders']
    if value.get('more') or value.get('has_more') or len(listing) >= 500 or value.get('count', len(listing)) != len(listing):
        raise ValueError('incomplete_reminder_snapshot')
    if supported and any(row.get('parent_id') for row in listing):
        return detailed_rows(native, lid)
    result = {}
    cache = getattr(native, '_migration_detail_cache', {})
    for row in listing:
        key = (lid, row['id'])
        cached = cache.get(key)
        # Версия покрывает поля, не входящие в краткий ответ. Изменение краткого
        # ответа тоже требует полного чтения, даже если версия осталась прежней.
        detail = copy.deepcopy(cached[1]) if cached and cached[0] == (summary_projection(row) if supported else row) else native.call('get_reminder', {'id':row['id']})
        # Производные дети перечитываются: нативная версия родителя может не измениться.
        if detail.get('subtasks') or any(child.get('parent_id') == row['id'] for child in listing): detail = native.call('get_reminder', {'id':row['id']})
        if supported: validate_detailed_fields(detail)
        cache[key] = (summary_projection(row) if supported else copy.deepcopy(row), copy.deepcopy(detail))
        if (row['id'] in result or detail.get('id') != row['id'] or not detail.get('version') or
                detail.get('version') != row.get('version') or detail.get('list_id') != lid):
            raise ValueError('invalid_reminder_snapshot')
        result[row['id']] = detail
    native._migration_detail_cache = cache
    return result


def canonical(hub, pid):
    m = load_sync(); registered = m.registered(hub)
    if pid not in registered: raise ValueError('unregistered_project')
    paths = [safe(registered[pid] / 'ai' / name) for name in m.NAMES.values()]
    paths += [hub / 'ai/project-registry.md']
    # Отсутствующий файл тоже входит в защиту: его создание делает план устаревшим.
    return {str(p.relative_to(hub)):sha(p.read_bytes()) if p.exists() else None for p in paths}


def pending_projects(hub, config, ignore_operation=None, ignore_reassignment=None):
    pending = set(config.get('project_list_migrations_pending', {}))
    pending.update(load_sync().task_reassignment_pending(hub, config, ignore_reassignment))
    external = load_sync().external_retirement_module()
    if external: pending.update(external.pending_projects(hub, config))
    elif config.get('external_retirements_pending') or any('external_retirement' in t for b in config['projects'].values() for t in b.get('tasks', {}).values()): pending.update(config['projects'])
    root = safe(Path(hub) / 'ai/reminders-project-lists')
    if not root.exists(): return pending
    try:
        for directory in root.iterdir():
            if directory.name == ignore_operation: continue
            directory = safe(directory)
            plan_path = safe(directory / 'plan.json'); state_path = safe(directory / 'state.json')
            plan_raw = plan_path.read_text(); plan = json.loads(plan_raw)
            if plan.get('kind') == 'rename':
                state = json.loads(state_path.read_text())
                if state.get('phase') not in {'preview', 'complete'}: pending.update(plan['affected'])
                continue
            if plan.get('kind') not in {'migration', 'empty_rebind'}: continue
            state = json.loads(state_path.read_text())
            if state.get('phase') == 'preview': continue
            pid = plan['project']
            completed_sha = config.get('project_list_migrations_completed', {}).get(pid)
            if (plan.get('kind') == 'empty_rebind' and state.get('phase') != 'complete' or
                    completed_sha != sha(plan_raw) and
                    not superseded_by_initial_binding(hub, config, pid, state,
                                                      directory.name, sha(plan_raw))):
                pending.add(pid)
    except (ValueError, OSError, KeyError):
        pending.update(config['projects'])
    cleanup_root = safe(Path(hub) / 'ai/reminders-list-cleanups')
    if cleanup_root.exists():
        try:
            for directory in cleanup_root.iterdir():
                directory = safe(directory)
                plan_path = safe(directory / 'plan.json')
                state_path = safe(directory / 'state.json')
                plan_raw = plan_path.read_bytes(); plan = json.loads(plan_raw)
                state = json.loads(state_path.read_text())
                if plan.get('kind') != 'old_list_cleanup' or plan.get('operation') != directory.name:
                    raise ValueError('invalid_cleanup_journal')
                if state.get('phase') in {'preview', 'complete'}:
                    continue
                affected = plan.get('affected_projects')
                if (not isinstance(affected, list) or not affected or
                        not set(affected) <= set(config['projects']) or
                        state.get('plan_sha256') != sha(plan_raw)):
                    raise ValueError('invalid_cleanup_journal')
                pending.update(affected)
        except (ValueError, OSError, KeyError):
            pending.update(config['projects'])
    return pending


def superseded_by_initial_binding(hub, config, project, old_state, old_operation, old_plan_sha256):
    """Accept an old completed migration only when a verified binding replaced it."""
    marker = old_state.get('superseded_by') if isinstance(old_state, dict) else None
    if (not isinstance(marker, dict) or marker.get('kind') != 'initial_binding' or
            marker.get('old_operation') != old_operation or
            marker.get('old_plan_sha256') != old_plan_sha256 or
            old_state.get('sha256') != old_plan_sha256):
        return False
    operation = marker.get('operation')
    if not isinstance(operation, str) or not re.fullmatch(r'[0-9a-f-]{36}', operation):
        return False
    try:
        folder = safe(Path(hub) / 'ai/reminders-project-bindings' / operation)
        plan_path = safe(folder / 'plan.json')
        state_path = safe(folder / 'state.json')
        raw = plan_path.read_bytes()
        digest = sha(raw)
        plan = json.loads(raw)
        state = json.loads(state_path.read_text())
        binding = config.get('projects', {}).get(project)
        baseline = config.get('structure', {}).get('projects', {}).get(project)
        return bool(
            plan.get('kind') == 'initial_binding' and plan.get('operation') == operation and
            plan.get('project') == project and marker.get('plan_sha256') == digest and
            state.get('sha256') == digest and state.get('phase') in {'binding_complete', 'complete'} and
            isinstance(state.get('list_id'), str) and marker.get('list_id') == state.get('list_id') and
            config.get('project_list_migrations_completed', {}).get(project) == digest and
            isinstance(binding, dict) and binding.get('layout') == 'project_list' and
            binding.get('list_id') == state.get('list_id') and
            isinstance(baseline, dict) and baseline.get('list_id') == state.get('list_id')
        )
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError):
        return False


def ensure_no_pending(hub, config, pid):
    m = load_sync()
    if pid in pending_projects(hub, config): raise ValueError('migration_recovery_required')
    cancel = m.cancellation_module()
    if cancel and pid in cancel.pending_projects(hub, config): raise ValueError('cancellation_recovery_required')
    if pid in m.structure_module().pending_structure_projects(hub, config): raise ValueError('structure_recovery_required')


def validate_children(config, pid, binding, snapshot, historical=None, external_retirements=None):
    parent = snapshot.get(binding['parent_id'])
    if not parent or parent.get('parent_id') is not None: raise ValueError('invalid_parent')
    children = {rid:row for rid,row in snapshot.items() if row.get('parent_id') == parent['id']}
    if any(row.get('parent_id') in children for row in snapshot.values()) or any(row.get('subtasks') for row in children.values()):
        raise ValueError('nested_children_not_supported')
    known = {t.get('reminder_id') for t in binding.get('tasks', {}).values()} | set(binding.get('history', {}))
    historical = dict(historical or {}, **(external_retirements or {}))
    if set(historical) & set(snapshot): raise ValueError('historical_uuid_active')
    if None in known or not (known - set(historical)) <= set(children): raise ValueError('missing_bound_child')
    # Нельзя переносить чужой UUID, даже если приложение поместило его под наш parent.
    foreign = {t.get('reminder_id') for other,b in config['projects'].items() if other != pid for t in b.get('tasks', {}).values()}
    foreign |= {rid for other,b in config['projects'].items() if other != pid for rid in b.get('history', {})}
    foreign |= {b.get('parent_id') for other,b in config['projects'].items() if other != pid}
    if foreign & set(children): raise ValueError('foreign_bound_child')
    sync_module = load_sync()
    identities = sync_module.compact_identities(config)
    for rid, history in binding.get('history', {}).items():
        try:
            if history['project_id'] != pid: raise ValueError('invalid_recurrence_history')
            sync_module.verify_history_row(children[rid], binding, identities)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError('invalid_recurrence_history') from exc
    bound_tasks = {link['reminder_id']:tid for tid,link in binding.get('tasks', {}).items()}
    for row in children.values():
        if load_sync().has_identity_marker(row.get('notes')):
            identity = load_sync().creation_identity(row, identities)
            if identity[0] != pid: raise ValueError('foreign_child_identity')
            if row['id'] in bound_tasks and identity != (pid, bound_tasks[row['id']]): raise ValueError('bound_child_identity_mismatch')
    return children


def preview(hub, pid, name, gid, native=None):
    hub = safe(hub)
    with locked(hub):
        config, raw = config_read(hub); ensure_no_pending(hub, config, pid)
        binding = config['projects'][pid]
        if binding.get('layout', 'parent') != 'parent': raise ValueError('already_project_list')
        if pid not in config.get('structure', {}).get('projects', {}): raise ValueError('missing_structure_baseline')
        permission = permission_data(hub, name)
        native = native or Native(config); reset_cache(native); meta = metadata(native)
        if any(r['name'] == name for r in meta['lists']): raise ValueError('destination_name_conflict')
        source = next((r for r in meta['lists'] if r['id'] == binding['list_id']), None)
        group = next((r for r in meta['groups'] if r['id'] == gid), None)
        if not source or not group or source['account_id'] != group['account_id'] or source['name'] != binding['list_name']:
            raise ValueError('account_or_group_conflict')
        cancellation = load_sync().cancellation_module()
        historical = cancellation.historical_module().collect(cancellation, hub, config, pid, native)
        snapshot = rows(native, binding['list_id'])
        external = load_sync().external_retirement_module().collect(hub,config,pid,native)
        children = validate_children(config, pid, binding, snapshot, historical, external)
        return journal(hub, dict(kind='migration', project=pid, list_name=name, group_id=gid, account_id=source['account_id'],
                                 config_raw=raw, canonical=canonical(hub,pid), permission=permission,
                                 metadata=meta, source=snapshot, children=sorted(children), external_retirements=external,
                                 **(dict(historical=historical, historical_runtime=cancellation.verification_module().runtime(cancellation,config)) if historical else {})))


def fields(row):
    return {k:v for k,v in row.items() if k not in {'list', 'list_id', 'parent_id', 'version', 'subtasks'}}


def moved(row, before, lid, name):
    return (fields(row) == fields(before) and row.get('list_id') == lid and row.get('list') == name and
            row.get('parent_id') is None and bool(row.get('version')) and not row.get('subtasks'))


def intended_config(plan, digest):
    c = json.loads(plan['config_raw']); c.setdefault('project_list_migrations_pending', {})[plan['project']] = digest
    return c


def final_document(plan, digest, lid, parent):
    final = intended_config(plan, digest); pid = plan['project']; old = final['projects'][pid]
    if fields(parent) != fields(plan['source'][old['parent_id']]) or parent.get('subtasks') or parent.get('list_id') != old['list_id'] or parent.get('parent_id') is not None:
        raise ValueError('invalid_final_parent')
    retired = dict(id=parent['id'], list_id=old['list_id'], snapshot=parent)
    old.update(layout='project_list', account_id=plan['account_id'], parent_id=None, list_id=lid, list_name=plan['list_name'], native_group_id=plan['group_id'], retired_parent=retired)
    if plan.get('historical'):
        c = load_sync().cancellation_module()
        old['historical_binding_migration'] = c.historical_module().reference(c, plan, digest, old)[0]
    final['structure']['list_roles'][lid] = dict(kind='project', project_id=pid)
    final['structure']['projects'][pid]['list_id'] = lid
    final['standard_allowlist_file'] = str(Path(plan['hub']) / 'ai/reminders-standard-allowlist.json')
    final['project_list_migrations_pending'].pop(pid, None)
    final.setdefault('project_list_migrations_completed', {})[pid] = digest
    return final


def permission_approved(hub, plan):
    root = safe(hub / 'ai/reminders-project-lists')
    for folder in root.iterdir():
        raw = safe(folder / 'plan.json').read_text(); receipt = json.loads(raw)
        if receipt.get('kind') != 'permission': continue
        state = json.loads(safe(folder / 'state.json').read_text())
        if (receipt.get('hub') == str(hub) and receipt.get('list_name') == plan['list_name'] and
                receipt['permission']['after'] == plan['permission']['after'] and
                receipt['permission']['original'] == plan['permission']['original'] and
                state.get('sha256') == sha(raw) and state.get('phase') == 'complete' and state.get('approved') is True):
            return True
    return False


def verify_guards(hub, plan, digest, state):
    config, raw = config_read(hub)
    m = load_sync(); cancellation = m.cancellation_module()
    if plan['project'] in m.task_reassignment_pending(hub, config): raise ValueError('task_reassignment_recovery_required')
    if cancellation and plan['project'] in cancellation.pending_projects(hub, config): raise ValueError('cancellation_recovery_required')
    if plan['project'] in m.structure_module().pending_structure_projects(hub, config): raise ValueError('structure_recovery_required')
    allowed = [plan['config_raw'], encoded(intended_config(plan, digest))]
    if state.get('final_config') is not None:
        try:
            stored = json.loads(state['final_config'])
            parent = stored['projects'][plan['project']]['retired_parent']['snapshot']
            expected = encoded(final_document(plan, digest, state['list_id'], parent))
        except (KeyError, TypeError, ValueError): raise ValueError('invalid_final_config')
        if state['final_config'] != expected: raise ValueError('invalid_final_config')
        allowed.append(expected)
        # Only a completed migration may gain this single independently accepted proof pin.
        # Pending/creating/moving configurations retain the original byte-exact CAS.
        if state.get('phase') == 'complete' and 'project_list_verification_sha256' in config and 'project_list_verification_sha256' not in stored:
            if cancellation is None: raise ValueError('verification_validator_unavailable')
            proof = cancellation.verification_module().accepted(cancellation, hub, config)
            if proof['list_id'] != state['list_id'] or proof['account_id'] != plan['account_id'] or proof['group_id'] != plan['group_id']:
                raise ValueError('verification_scope_mismatch')
            pinned = json.loads(expected); pinned['project_list_verification_sha256'] = config['project_list_verification_sha256']
            allowed.append(encoded(pinned))
    if raw not in allowed: raise ValueError('config_changed')
    if canonical(hub, plan['project']) != plan['canonical']: raise ValueError('canonical_changed')
    if safe(config['allowlist_file']).read_text() != plan['permission']['original']: raise ValueError('original_permission_changed')
    target = safe(hub / 'ai/reminders-standard-allowlist.json')
    if not target.exists() or target.read_text() != plan['permission']['after']: raise ValueError('permission_changed_or_not_approved')
    if not permission_approved(hub, plan): raise ValueError('permission_consent_missing')
    return config, raw


def metadata_identity(row, group=False):
    derived = {'lists'} if group else {'open', 'total'}
    return {k:v for k,v in row.items() if k not in derived}


def check_remote(native, plan, state):
    meta = metadata(native); old = plan['metadata']; lid = state.get('list_id')
    old_lists = {r['id']:r for r in old['lists']}; now = {r['id']:r for r in meta['lists']}
    if [metadata_identity(r, True) for r in meta['groups']] != [metadata_identity(r, True) for r in old['groups']] or any(k not in now or metadata_identity(now[k]) != metadata_identity(v) for k,v in old_lists.items()): raise ValueError('metadata_changed')
    new_ids = set(now) - set(old_lists)
    if new_ids != ({lid} if lid else set()): raise ValueError('metadata_changed')
    binding = json.loads(plan['config_raw'])['projects'][plan['project']]
    current = rows(native, binding['list_id']); target = rows(native, lid) if lid else {}
    expected_target = set()
    for rid, before in plan['source'].items():
        if rid in plan['children']:
            step = state['steps'].get(rid)
            if step and rid in target and moved(target[rid], before, lid, plan['list_name']):
                if rid in current: raise ValueError('duplicate_remote_row')
                expected_target.add(rid)
                if step.get('status') == 'done' and step.get('receipt') != target[rid]: raise ValueError('receipt_changed')
            elif current.get(rid) != before or rid in target: raise ValueError('remote_changed')
        elif rid == binding['parent_id']:
            actual = current.get(rid, {})
            if not target and actual != before: raise ValueError('parent_changed')
            if state.get('final_config') and actual != json.loads(state['final_config'])['projects'][plan['project']]['retired_parent']['snapshot']: raise ValueError('retired_parent_changed')
            if fields(actual) != fields(before) or actual.get('list_id') != before.get('list_id') or actual.get('parent_id') != before.get('parent_id'):
                raise ValueError('parent_changed')
        elif current.get(rid) != before: raise ValueError('neighbor_changed')
    if set(current) | set(target) != set(plan['source']) or set(target) != expected_target: raise ValueError('remote_membership_changed')
    if lid:
        dest = now[lid]
        expected_groups = {None, plan['group_id']} if state.get('group_pending') else {None}
        if state.get('group_done'): expected_groups = {plan['group_id']}
        if dest['name'] != plan['list_name'] or dest['account_id'] != plan['account_id'] or dest.get('group_id') not in expected_groups:
            raise ValueError('destination_changed')
    if plan.get('external_retirements'):
        current_config = load_sync().load_config(Path(plan['hub']))
        effective = dict(current_config, standard_allowlist_file=str(Path(plan['hub'])/'ai/reminders-standard-allowlist.json'))
        external = load_sync().external_retirement_module().collect(Path(plan['hub']), effective, plan['project'], native)
        if external != plan['external_retirements']: raise ValueError('external_retirement_migration_proof_changed')
    if plan.get('historical'):
        c = load_sync().cancellation_module()
        c.historical_module().recheck(c, Path(plan['hub']), plan['historical'], native)
    return meta, current, target


def apply(path, digest, approve=False, native=None, prepare_only=False):
    if not approve: raise ValueError('explicit_approval_required')
    path, plan, state = read_plan(path, digest, 'migration'); hub = safe(plan['hub'])
    with locked(hub):
        config, raw = verify_guards(hub, plan, digest, state)
        effective = dict(config, standard_allowlist_file=str(hub / 'ai/reminders-standard-allowlist.json'))
        native = native or Native(effective)
        reset_cache(native)
        def save(): durable(path.parent / 'state.json', encoded(state))
        if state['phase'] == 'complete' and config.get('project_list_migrations_completed', {}).get(plan['project']) == digest:
            check_remote(native, plan, state)
            return state
        if state.get('create_pending') and not state.get('list_id'): raise ValueError('creation_recovery_required_adopt_exact_uuid')
        meta, current, target = check_remote(native, plan, state)
        state['approved'] = True; save()
        if not state.get('list_id'):
            if meta.get('guarded_list_creation') is not True: raise ValueError('creation_account_unverifiable')
            # Пишем доверенный intent прежде любой внешней записи, чтобы потеря журнала закрывала sync.
            state['phase'] = 'creating'; state['create_pending'] = True; save()
            backup = path.parent / 'config-before.json'
            if not backup.exists(): durable(backup, plan['config_raw'], True)
            if raw == plan['config_raw']: durable(hub / 'ai/reminders-sync.json', encoded(intended_config(plan, digest)))
            created = native.call('manage_list', dict(action='create', list=plan['list_name'], expected_account_id=plan['account_id']))
            if not created.get('id'): raise ValueError('creation_recovery_required')
            state['list_id'] = created['id']; save()
            check_remote(native, plan, state)
        lid = state['list_id']
        meta, current, target = check_remote(native, plan, state)
        destination = next(x for x in meta['lists'] if x['id'] == lid)
        if not state.get('group_done'):
            verify_guards(hub, plan, digest, state)
            state['phase'] = 'grouping'; state['group_pending'] = True; save()
            if destination.get('group_id') is None:
                native.call('manage_list', dict(action='update', list=lid, group=plan['group_id'], expected_group_id=None))
            meta, current, target = check_remote(native, plan, state)
            if next(x for x in meta['lists'] if x['id']==lid)['group_id'] != plan['group_id']: raise ValueError('group_readback_failed')
            state['group_done'] = True; save()
        if prepare_only:
            state['phase'] = 'destination_ready'; save()
            return state
        for rid in plan['children']:
            verify_guards(hub, plan, digest, state)
            meta, current, target = check_remote(native, plan, state)
            if rid in target:
                state['steps'][rid] = dict(status='done', receipt=target[rid]); save(); continue
            before = native.call('get_reminder', {'id':rid})
            if before != current[rid]: raise ValueError('remote_changed_before_write')
            state['phase'] = 'moving'; state['steps'][rid] = dict(status='pending', before=before); save()
            native.call('update_reminder', dict(id=rid, version=before['version'], list=lid, parent_id=None))
            after = native.call('get_reminder', {'id':rid})
            if not moved(after, before, lid, plan['list_name']): raise ValueError('move_readback_failed')
            state['steps'][rid] = dict(status='done', receipt=after); save()
        reset_cache(native)
        meta, current, target = check_remote(native, plan, state)
        config, raw = verify_guards(hub, plan, digest, state)
        pid = plan['project']
        old_binding = json.loads(plan['config_raw'])['projects'][pid]; parent = current[old_binding['parent_id']]
        final = final_document(plan, digest, lid, parent)
        load_sync().validate_binding_ids(final)
        expected_final = encoded(final)
        if state.get('final_config') and state['final_config'] != expected_final: raise ValueError('final_config_changed')
        if plan.get('historical'):
            c = load_sync().cancellation_module()
            c.historical_module().publish(c, plan, digest, final['projects'][pid])
        state['final_config'] = expected_final; state['phase'] = 'committing'; save()
        backup = path.parent / 'config-before.json'
        if not backup.exists(): durable(backup, plan['config_raw'], True)
        if (hub / 'ai/reminders-sync.json').read_text() != raw: raise ValueError('config_cas_failed')
        if plan.get('historical'):
            # Доверие появляется только когда и журнал, и точная новая привязка опубликованы.
            # Сбой между ними оставляет pending в старой конфигурации и допускает повтор.
            state['phase'] = 'complete'; save()
        durable(hub / 'ai/reminders-sync.json', expected_final)
        if (hub / 'ai/reminders-sync.json').read_text() != expected_final or canonical(hub,pid) != plan['canonical']: raise ValueError('final_readback_failed')
        state['phase'] = 'complete'; save()
        return state


def adopt(path, digest, lid, approve=False, native=None):
    if not approve: raise ValueError('explicit_approval_required')
    path, plan, state = read_plan(path, digest, 'migration'); hub = safe(plan['hub'])
    with locked(hub):
        config, raw = verify_guards(hub,plan,digest,state)
        if not state.get('create_pending') or state.get('list_id'): raise ValueError('adopt_not_available')
        native = native or Native(dict(config, standard_allowlist_file=str(hub / 'ai/reminders-standard-allowlist.json')))
        reset_cache(native)
        trial = copy.deepcopy(state); trial['list_id'] = lid
        check_remote(native,plan,trial)
        if rows(native,lid): raise ValueError('adopt_requires_empty_list')
        state['list_id'] = lid; state['adopted_uuid'] = lid
        durable(path.parent / 'state.json', encoded(state))
        return state


def ensure_no_historical_container(hub, lid):
    root=safe(hub/'ai/reminders-cancellations')
    if not root.exists(): return
    for folder in root.iterdir():
        if folder.name.startswith('.draft-'): continue
        plan_path=safe(folder/'plan.json')
        if not plan_path.exists(): raise ValueError('rename_historical_scope_unknown')
        historical=json.loads(plan_path.read_text())
        items=historical.get('items')
        if not isinstance(items,list) or any(not isinstance(item,dict) or not item.get('list_id') for item in items): raise ValueError('rename_historical_scope_unknown')
        if any(item['list_id']==lid for item in items): raise ValueError('rename_historical_container_unsupported')


def rename_bindings(hub, config, lid):
    ensure_no_historical_container(hub,lid)
    affected = sorted(pid for pid,b in config['projects'].items() if b['list_id'] == lid)
    if not affected: raise ValueError('rename_without_legacy_bindings')
    for pid,b in config['projects'].items():
        if b.get('retired_parent', {}).get('list_id') == lid: raise ValueError('rename_retired_container_unsupported')
        if pid not in affected: continue
        if b.get('layout', 'parent') != 'parent' or b.get('retired_parent'): raise ValueError('rename_requires_legacy_container')
        if any('cancellation' in t or any(k.startswith('pending_') for k in t) for t in list(b.get('tasks', {}).values()) + list(b.get('history', {}).values())):
            raise ValueError('rename_history_or_pending_unsupported')
        if config.get('structure', {}).get('projects', {}).get(pid, {}).get('list_id') != lid: raise ValueError('missing_structure_baseline')
        canonical(hub, pid)
    return affected


def rename_preview(hub, lid, expected_name, retired_name, native=None):
    hub = safe(hub)
    if not valid_uuid(lid) or any(not isinstance(n, str) or not n.strip() or n.splitlines() != [n] for n in (expected_name,retired_name)) or expected_name == retired_name:
        raise ValueError('invalid_rename_arguments')
    with locked(hub):
        config, raw = config_read(hub); affected = rename_bindings(hub, config, lid)
        if config.get('standard_allowlist_file') != str(hub/'ai/reminders-standard-allowlist.json'): raise ValueError('rename_standard_permission_selection_required')
        for pid in affected: ensure_no_pending(hub, config, pid)
        permission = permission_data(hub, retired_name)
        if permission['added'] or expected_name not in json.loads(permission['after'])['names']: raise ValueError('rename_permissions_not_prepared')
        native = native or Native(dict(config, standard_allowlist_file=str(hub/'ai/reminders-standard-allowlist.json')))
        reset_cache(native); meta = metadata(native)
        source = next((r for r in meta['lists'] if r['id'] == lid), None)
        if meta.get('guarded_list_rename') is not True: raise ValueError('rename_capability_missing')
        if not source or source['name'] != expected_name or not valid_uuid(source['account_id']) or (source.get('group_id') is not None and not valid_uuid(source['group_id'])):
            raise ValueError('rename_source_identity_changed')
        if any(r['name'] == retired_name for r in meta['lists']): raise ValueError('rename_name_conflict')
        snapshot = rows(native, lid)
        for pid in affected:
            if config['projects'][pid]['list_name'] != expected_name: raise ValueError('rename_binding_name_changed')
            validate_children(config, pid, config['projects'][pid], snapshot)
        plan = dict(kind='rename', list_id=lid, expected_name=expected_name, list_name=retired_name,
                    affected=affected, config_raw=raw, config_sha256=sha(raw),
                    permission_sha256=dict(original=sha(permission['original']),standard=sha(permission['after'])),
                    canonical={pid:canonical(hub,pid) for pid in affected},
                    permission=permission, metadata=meta, source=snapshot, account_id=source['account_id'], group_id=source.get('group_id'))
        return journal(hub, plan)


def rename_documents(plan, digest):
    pending = json.loads(plan['config_raw'])
    for pid in plan['affected']: pending.setdefault('project_list_migrations_pending', {})[pid] = digest
    final = json.loads(plan['config_raw'])
    for pid in plan['affected']: final['projects'][pid]['list_name'] = plan['list_name']
    return encoded(pending), encoded(final)


def rename_arguments(plan):
    return dict(action='update', list=plan['list_id'], expected_name=plan['expected_name'], new_name=plan['list_name'],
                expected_account_id=plan['account_id'], expected_group_id=plan['group_id'])


def rename_guards(hub, plan, digest, state):
    config, raw = config_read(hub); pending, final = rename_documents(plan, digest)
    ensure_no_historical_container(hub,plan['list_id'])
    if state.get('phase') not in {'preview','renaming','committing','complete'}: raise ValueError('invalid_rename_phase')
    if state.get('final_config') is not None and state['final_config'] != final: raise ValueError('invalid_rename_final_config')
    allowed = [plan['config_raw']]
    if state.get('write_intent') == rename_arguments(plan) and state['phase'] != 'preview': allowed.append(pending)
    if state.get('final_config') == final and state['phase'] in {'committing','complete'}: allowed.append(final)
    if raw not in allowed: raise ValueError('rename_config_changed')
    if {pid:canonical(hub,pid) for pid in plan['affected']} != plan['canonical']: raise ValueError('rename_canonical_changed')
    if permission_data(hub, plan['list_name'])['original'] != plan['permission']['original']: raise ValueError('original_permission_changed')
    target = safe(hub/'ai/reminders-standard-allowlist.json')
    if not target.exists() or target.read_text() != plan['permission']['after']: raise ValueError('rename_permission_changed')
    if not permission_approved(hub, plan): raise ValueError('permission_consent_missing')
    clean = copy.deepcopy(config)
    for pid in plan['affected']:
        if clean.get('project_list_migrations_pending', {}).get(pid) == digest: clean['project_list_migrations_pending'].pop(pid)
    if set(plan['affected']) & pending_projects(hub, clean, ignore_operation=plan['operation']): raise ValueError('other_migration_pending')
    m = load_sync(); cancel = m.cancellation_module()
    if cancel and set(plan['affected']) & cancel.pending_projects(hub, config): raise ValueError('cancellation_recovery_required')
    if set(plan['affected']) & set(m.structure_module().pending_structure_projects(hub, config)): raise ValueError('structure_recovery_required')
    return config, raw


def rename_remote(native, plan, state):
    meta = metadata(native)
    if meta.get('guarded_list_rename') is not True: raise ValueError('rename_capability_missing')
    old = {r['id']:metadata_identity(r) for r in plan['metadata']['lists']}
    current = {r['id']:metadata_identity(r) for r in meta['lists']}
    if set(current) != set(old): raise ValueError('rename_metadata_changed')
    actual = current[plan['list_id']]['name']
    if actual not in {plan['expected_name'],plan['list_name']}: raise ValueError('rename_unknown_name')
    expected = copy.deepcopy(old); expected[plan['list_id']]['name'] = actual
    if current != expected or [metadata_identity(r,True) for r in meta['groups']] != [metadata_identity(r,True) for r in plan['metadata']['groups']]: raise ValueError('rename_metadata_changed')
    if actual == plan['list_name'] and (state.get('write_intent') != rename_arguments(plan) or state['phase'] not in {'renaming','committing','complete'}): raise ValueError('rename_outcome_unattested')
    snapshot = rows(native, plan['list_id'])
    expected_rows = copy.deepcopy(plan['source'])
    for row in expected_rows.values(): row['list'] = actual
    if snapshot != expected_rows: raise ValueError('rename_remote_changed')
    if state.get('receipt') is not None and state['receipt'] != snapshot: raise ValueError('rename_receipt_changed')
    return actual, snapshot


def rename_apply(path, digest, approve=False, native=None):
    if not approve: raise ValueError('explicit_approval_required')
    path, plan, state = read_plan(path,digest,'rename'); hub = safe(plan['hub'])
    with locked(hub):
        config, raw = rename_guards(hub,plan,digest,state)
        native = native or Native(dict(config,standard_allowlist_file=str(hub/'ai/reminders-standard-allowlist.json')))
        reset_cache(native); actual, snapshot = rename_remote(native,plan,state)
        pending, final = rename_documents(plan,digest)
        if state['phase'] == 'complete':
            if raw != final or actual != plan['list_name'] or state.get('receipt') != snapshot: raise ValueError('rename_completion_unattested')
            return state
        def save(): durable(path.parent/'state.json',encoded(state))
        if actual == plan['expected_name']:
            if state.get('receipt') or state['phase'] == 'committing': raise ValueError('rename_reverted_externally')
            state.update(phase='renaming',write_intent=rename_arguments(plan)); save()
            backup=path.parent/'config-before.json'
            if not backup.exists(): durable(backup,plan['config_raw'],True)
            if (hub/'ai/reminders-sync.json').read_text() != raw: raise ValueError('config_cas_failed')
            durable(hub/'ai/reminders-sync.json',pending)
            rename_guards(hub,plan,digest,state)
            native.call('manage_list',state['write_intent'])
        reset_cache(native); actual, snapshot = rename_remote(native,plan,state)
        if actual != plan['list_name']: raise ValueError('rename_readback_failed')
        _, raw = rename_guards(hub,plan,digest,state)
        state.update(phase='committing',receipt=snapshot,final_config=final); save()
        if (hub/'ai/reminders-sync.json').read_text() != raw: raise ValueError('config_cas_failed')
        durable(hub/'ai/reminders-sync.json',final)
        if (hub/'ai/reminders-sync.json').read_text() != final: raise ValueError('rename_final_readback_failed')
        state['phase']='complete'; save(); return state


def rename_resume(path, digest, approve=False, native=None):
    return rename_apply(path,digest,approve,native)


def rename_status(path, digest, native=None):
    path, plan, state = read_plan(path,digest,'rename'); hub=safe(plan['hub'])
    config,_=rename_guards(hub,plan,digest,state)
    native=native or Native(dict(config,standard_allowlist_file=str(hub/'ai/reminders-standard-allowlist.json')))
    reset_cache(native); name,_=rename_remote(native,plan,state)
    return dict(phase=state['phase'],list_id=plan['list_id'],list_name=name,affected=plan['affected'])


def verify_bulk_retired_parent(hub, binding, metadata, snapshots, native):
    retired=binding.get('retired_parent')
    if not retired:return
    listed={entry['id'] for entry in metadata['lists']}
    if binding.get('retired_parent_cleanup'):
        spec=importlib.util.spec_from_file_location('project_lists_old_list_cleanup',Path(__file__).with_name('reminders_old_list_cleanup.py'))
        cleanup=importlib.util.module_from_spec(spec);spec.loader.exec_module(cleanup)
        cleanup.retired_parent_cleaned(hub,binding)
        if retired['list_id'] in listed:
            raise ValueError('retired_parent_list_reappeared_after_cleanup')
        return
    if retired['list_id'] not in listed:
        raise ValueError('retired_parent_list_missing_without_receipt')
    if retired['list_id'] not in snapshots:snapshots[retired['list_id']]=rows(native,retired['list_id'])
    if snapshots[retired['list_id']].get(retired['id'])!=retired['snapshot']:
        raise ValueError('retired_project_parent_changed')


def bulk_candidates(hub, native=None):
    """Только чтение активных зарегистрированных связей; планов и разрешений не пишет."""
    hub=safe(hub);config,_=config_read(hub);m=load_sync();struct=m.structure_module()
    registry=safe(hub/'ai/project-registry.md').read_text();registered=m.registered(hub)
    arch=safe(hub/'ai/archiprojects.md').read_text();groups=struct.load_groups(arch);cards=struct.registry_cards(hub,registry)
    allowed=json.loads(safe(config['structure']['groups_allowlist_file']).read_text());allowed=allowed.get('names',[]) if isinstance(allowed,dict) else allowed
    native=native or Native(config);reset_cache(native);meta=metadata(native);snapshots={}
    result=dict(eligible=[],blocked=[],existing_project_lists=[]);labels={}
    for pid,binding in config['projects'].items():
        if pid not in registered: continue
        try:
            if binding.get('project_label') is None:
                body=re.findall(r'^## '+re.escape(pid)+r'\n(.*?)(?=^## |\Z)',registry,re.M|re.S)
                if len(body)!=1 or len(re.findall(r'^Name: (.+)$',body[0],re.M))!=1: raise ValueError('missing_registered_project_name')
            label=m.project_label(hub,pid,binding);labels.setdefault(label,[]).append(pid)
        except ValueError as exc: result['blocked'].append(dict(project_id=pid,reason=str(exc)))
    for label,pids in labels.items():
        for pid in pids:
            binding=config['projects'][pid];item=dict(project_id=pid,list_name=label)
            try:
                if len(pids)!=1: raise ValueError('duplicate_project_target_name')
                ensure_no_pending(hub,config,pid)
                group=struct.card_group(cards[pid].read_text(),pid,groups)
                baseline=config['structure']['projects'][pid]
                if group!=baseline['group'] or baseline['list_id']!=binding['list_id']: raise ValueError('project_structure_changed')
                top=group
                while True:
                    if groups[top]['status']!='active': raise ValueError('inactive_ancestor')
                    if groups[top]['parent'] is None: break
                    top=groups[top]['parent']
                matches=[r for r in meta['groups'] if config['structure']['native_groups'].get(r['id'])==top]
                if len(matches)!=1: raise ValueError('ambiguous_top_native_group')
                destination=matches[0]
                if not isinstance(allowed,list) or destination['name'] not in allowed and destination['id'] not in allowed: raise ValueError('top_group_not_permitted')
                source=next((r for r in meta['lists'] if r['id']==binding['list_id']),None)
                if not source or not valid_uuid(source['id']) or not valid_uuid(source['account_id']) or not valid_uuid(destination['id']) or source['name']!=binding['list_name'] or source['account_id']!=destination['account_id']: raise ValueError('source_account_or_name_changed')
                item.update(top_group=top,group_id=destination['id'],account_id=source['account_id'],source=copy.deepcopy(source))
                cancellation = m.cancellation_module()
                historical = cancellation.historical_module().collect(cancellation,hub,config,pid,native) if binding.get('layout','parent') == 'parent' else {}
                historical.update(m.external_retirement_module().collect(hub,config,pid,native))
                if binding.get('layout') == 'project_list':
                    for tid,link in binding.get('tasks',{}).items():
                        if 'cancellation' in link:
                            cancellation.verify_cancelled_link(hub,m.HubProject(hub,pid).rows()[tid],link,binding,native)
                            historical[link['reminder_id']] = {}
                if any(any(k.startswith('pending_') for k in t) for t in list(binding.get('tasks',{}).values())+list(binding.get('history',{}).values())): raise ValueError('unsupported_cancel_or_pending_binding')
                if binding['list_id'] not in snapshots: snapshots[binding['list_id']]=rows(native,binding['list_id'])
                if binding.get('layout','parent')=='project_list':
                    if source['name']!=label or source.get('group_id')!=destination['id']: raise ValueError('existing_project_list_changed')
                    current=snapshots[binding['list_id']]
                    if config['structure']['list_roles'].get(binding['list_id']) != dict(kind='project',project_id=pid): raise ValueError('existing_project_list_role_changed')
                    known=({t['reminder_id'] for t in binding.get('tasks',{}).values()}|set(binding.get('history',{})))-set(historical)
                    if any(rid not in current or current[rid].get('parent_id') is not None for rid in known): raise ValueError('missing_bound_root')
                    struct.validate_project_ownership(pid,current.values(),config)
                    identities=m.compact_identities(config)
                    bound={link['reminder_id']:tid for tid,link in binding.get('tasks',{}).items()}
                    for rid,row in current.items():
                        if m.has_identity_marker(row.get('notes')):
                            identity=m.creation_identity(row,identities)
                            if identity[0]!=pid or (rid in bound and identity!=(pid,bound[rid])): raise ValueError('existing_project_list_identity_conflict')
                    for rid in binding.get('history',{}):m.verify_history_row(current[rid],binding,identities)
                    retired=binding.get('retired_parent')
                    if retired:verify_bulk_retired_parent(hub,binding,meta,snapshots,native)
                    result['existing_project_lists'].append(item);continue

                if binding['list_id'] not in snapshots: snapshots[binding['list_id']]=rows(native,binding['list_id'])
                children=validate_children(config,pid,binding,snapshots[binding['list_id']],historical);item['children']=sorted(children)
                collision=next((r for r in meta['lists'] if r['name']==label),None)
                if collision:
                    if collision['id']!=binding['list_id']: raise ValueError('destination_name_conflict')
                    rename_bindings(hub,config,binding['list_id'])
                    retired=label+' — прежний список'
                    if any(r['name']==retired for r in meta['lists']): raise ValueError('retired_name_conflict')
                    item['rename']=dict(list_id=binding['list_id'],expected_name=label,new_name=retired)
                else:item['rename']=None
                result['eligible'].append(item)
            except (ValueError,KeyError,TypeError,OSError) as exc:result['blocked'].append(dict(item,reason=str(exc)))
    return result


def empty_rebind_route(hub, config, pid, meta):
    """Только имя существующего проекта и его точная верхняя группа реестра."""
    m=load_sync();struct=m.structure_module();registry=safe(hub/'ai/project-registry.md').read_text()
    cards=struct.registry_cards(hub,registry);arch=safe(hub/'ai/archiprojects.md');groups=struct.load_groups(arch.read_text())
    if pid not in m.registered(hub) or pid not in cards: raise ValueError('empty_rebind_unregistered_project')
    card=cards[pid];group=struct.card_group(card.read_text(),pid,groups);baseline=config['structure']['projects'][pid]
    if group!=baseline['group'] or baseline['list_id']!=config['projects'][pid]['list_id']: raise ValueError('empty_rebind_structure_changed')
    top=group
    while True:
        if groups[top]['status']!='active': raise ValueError('empty_rebind_inactive_group')
        if groups[top]['parent'] is None: break
        top=groups[top]['parent']
    matches=[r for r in meta['groups'] if config['structure']['native_groups'].get(r['id'])==top]
    if len(matches)!=1: raise ValueError('empty_rebind_ambiguous_top_group')
    destination=matches[0]
    if not valid_uuid(destination['id']) or not valid_uuid(destination['account_id']): raise ValueError('empty_rebind_invalid_group')
    permit=safe(config['structure']['groups_allowlist_file']);allowed=json.loads(permit.read_text());names=allowed.get('names',[]) if isinstance(allowed,dict) else allowed
    if not isinstance(names,list) or destination['name'] not in names and destination['id'] not in names: raise ValueError('empty_rebind_group_not_permitted')
    label=m.project_label(hub,pid,config['projects'][pid])
    if any(other!=pid and m.project_label(hub,other,b)==label for other,b in config['projects'].items()): raise ValueError('empty_rebind_duplicate_project_name')
    return dict(list_name=label,group_id=destination['id'],account_id=destination['account_id'],guards={str(p):sha(p.read_bytes()) for p in (hub/'ai/project-registry.md',arch,card,permit)})


def empty_rebind_proof(hub, config, pid, native, observation):
    m=load_sync();binding=config['projects'][pid]
    if binding.get('layout','parent')!='parent' or binding.get('retired_parent') or binding.get('external_retirement_rebind'):
        raise ValueError('empty_rebind_requires_legacy_existing_binding')
    if binding.get('history') or not binding.get('tasks') or any(r['status'] not in m.TERMINAL for r in m.HubProject(hub,pid).rows().values()):
        raise ValueError('empty_rebind_active_or_history')
    if any(not t.get('external_retirement') or t.get('cancellation') or any(k.startswith('pending_') for k in t) for t in binding['tasks'].values()):
        raise ValueError('empty_rebind_unproven_task')
    proof=m.external_retirement_module().collect(hub,config,pid,native)
    if set(proof)!={t['reminder_id'] for t in binding['tasks'].values()}: raise ValueError('empty_rebind_incomplete_retirement_proof')
    lid=binding['list_id'];role=config['structure']['list_roles'].get(lid,{})
    if role=={'kind':'direct'}:
        owners=[owner for owner,b in config['projects'].items() if b.get('list_id')==lid]
        foreign_previous=any(owner!=pid and (b.get('retired_parent',{}).get('list_id')==lid or
            b.get('external_retirement_rebind',{}).get('previous_binding',{}).get('list_id')==lid)
            for owner,b in config['projects'].items())
        foreign_baseline=any(owner!=pid and baseline.get('list_id')==lid
            for owner,baseline in config['structure']['projects'].items())
        if owners!=[pid] or foreign_previous or foreign_baseline: raise ValueError('empty_rebind_source_role_conflict')
    elif not isinstance(role,dict) or role.get('kind')!='group': raise ValueError('empty_rebind_source_role_conflict')
    m.external_retirement_module().absent(observation,[binding['parent_id'],*proof])
    source=[r for r in observation['metadata']['lists'] if r['id']==binding['list_id']]
    if any(r['name']==binding['list_name'] and r['id']!=binding['list_id'] for r in observation['metadata']['lists']): raise ValueError('empty_rebind_source_name_reused')
    if source and (source[0]['name']!=binding['list_name'] or observation['lists'][binding['list_id']] or source[0].get('shared',False) is not False):
        raise ValueError('empty_rebind_source_not_empty')
    return proof


def empty_rebind_preview(hub, pid, native=None):
    hub=safe(hub)
    with locked(hub):
        config,raw=config_read(hub);ensure_no_pending(hub,config,pid)
        native=native or Native(config);external=load_sync().external_retirement_module()
        observation=external.observe(hub,config,native);proof=empty_rebind_proof(hub,config,pid,native,observation)
        route=empty_rebind_route(hub,config,pid,observation['metadata']);permission=permission_data(hub,route['list_name'])
        if any(r['name']==route['list_name'] for r in observation['metadata']['lists']): raise ValueError('empty_rebind_destination_name_conflict')
        if native.call('list_lists',{}).get('guarded_list_creation') is not True: raise ValueError('creation_account_unverifiable')
        return journal(hub,dict(kind='empty_rebind',project=pid,config_raw=raw,canonical=canonical(hub,pid),permission=permission,external_retirements=proof,observation=observation,**route))


def empty_rebind_final(plan,digest,lid,pending=False):
    final=json.loads(plan['config_raw']);pid=plan['project'];binding=final['projects'][pid];previous=copy.deepcopy(binding);old=binding['list_id']
    binding.update(layout='project_list',parent_id=None,list_id=lid,list_name=plan['list_name'],account_id=plan['account_id'],native_group_id=plan['group_id'])
    binding['external_retirement_rebind']=dict(operation=plan['operation'],plan_sha256=digest,previous_binding=previous,observation=plan['observation'])
    structure=final['structure'];structure['projects'][pid]['list_id']=lid;structure['list_roles'][lid]=dict(kind='project',project_id=pid)
    source_present=any(r['id']==old for r in plan['observation']['metadata']['lists'])
    if not source_present and not any(other!=pid and b['list_id']==old for other,b in final['projects'].items()): structure['list_roles'].pop(old,None)
    final.setdefault('project_list_migrations_pending',{}).pop(pid,None)
    if pending:final['project_list_migrations_pending'][pid]=digest
    final.setdefault('project_list_migrations_completed',{})[pid]=digest
    final['standard_allowlist_file']=str(Path(plan['hub'])/'ai/reminders-standard-allowlist.json')
    return final


def empty_rebind_guards(hub,plan,digest,state):
    config,raw=config_read(hub);allowed=[plan['config_raw'],encoded(intended_config(plan,digest))]
    if state.get('list_id'):
        allowed.extend(encoded(empty_rebind_final(plan,digest,state['list_id'],pending)) for pending in (True,False))
    if raw not in allowed:raise ValueError('empty_rebind_config_cas_conflict')
    if state.get('phase')=='complete' and raw not in allowed[-2:]:raise ValueError('empty_rebind_completed_config_changed')
    if canonical(hub,plan['project'])!=plan['canonical'] or any(sha(safe(p).read_bytes())!=expected for p,expected in plan['guards'].items()):raise ValueError('empty_rebind_canonical_or_route_changed')
    if safe(config['allowlist_file']).read_text()!=plan['permission']['original']:raise ValueError('original_permission_changed')
    target=safe(hub/'ai/reminders-standard-allowlist.json')
    if not target.exists() or target.read_text()!=plan['permission']['after'] or not permission_approved(hub,plan):raise ValueError('permission_consent_missing')
    m=load_sync();pid=plan['project']
    if pid in m.external_retirement_module().pending_projects(hub,config) or pid in m.cancellation_module().pending_projects(hub,config) or pid in m.structure_module().pending_structure_projects(hub,config):raise ValueError('empty_rebind_other_operation_pending')
    # Исключаем только свой journal, оставляя все прочие blockers.
    clean=copy.deepcopy(config);clean.get('project_list_migrations_pending',{}).pop(pid,None)
    if pid in pending_projects(hub,clean,ignore_operation=plan['operation']):raise ValueError('empty_rebind_other_migration_pending')
    return config,raw


def empty_rebind_remote(hub,plan,state,config,native):
    external=load_sync().external_retirement_module();effective=dict(config,standard_allowlist_file=str(hub/'ai/reminders-standard-allowlist.json'));observation=external.observe(hub,effective,native,plan['observation']['scope'])
    current={r['id']:r for r in observation['metadata']['lists']};before={r['id']:r for r in plan['observation']['metadata']['lists']};lid=state.get('list_id')
    if set(current)!=set(before)|({lid} if lid else set()):raise ValueError('empty_rebind_remote_membership_changed')
    if any(metadata_identity(current[rid])!=metadata_identity(row) for rid,row in before.items()):raise ValueError('empty_rebind_source_metadata_changed')
    if [metadata_identity(r,True) for r in observation['metadata']['groups']]!=[metadata_identity(r,True) for r in plan['observation']['metadata']['groups']]:raise ValueError('empty_rebind_group_changed')
    old=json.loads(plan['config_raw'])['projects'][plan['project']]
    external.absent(observation,[old['parent_id'],*plan['external_retirements']])
    if observation['lists'].get(old['list_id']):raise ValueError('empty_rebind_source_not_empty')
    proof=external.collect(hub,effective,plan['project'],native)
    if proof!=plan['external_retirements']:raise ValueError('empty_rebind_retirement_proof_changed')
    if lid:
        row=current[lid];expected={None,plan['group_id']} if state.get('group_pending') else {None}
        if state.get('group_done'):expected={plan['group_id']}
        if (row['name']!=plan['list_name'] or row['account_id']!=plan['account_id'] or row.get('group_id') not in expected or
                row.get('shared',False) is not False or observation['lists'][lid]):raise ValueError('empty_rebind_destination_not_empty_or_changed')
        if any(other!=plan['project'] and b['list_id']==lid for other,b in config['projects'].items()):raise ValueError('exclusive_project_list')
    return observation


def empty_rebind_apply(path,digest,approve=False,native=None):
    if not approve:raise ValueError('explicit_approval_required')
    path,plan,state=read_plan(path,digest,'empty_rebind');hub=safe(plan['hub'])
    with locked(hub):
        config,raw=empty_rebind_guards(hub,plan,digest,state)
        native=native or Native(dict(config,standard_allowlist_file=str(hub/'ai/reminders-standard-allowlist.json')))
        if state.get('create_pending') and not state.get('list_id'):raise ValueError('empty_rebind_unknown_creation_do_not_retry')
        empty_rebind_remote(hub,plan,state,config,native)
        def clear_pending():
            # Native v2 видит только явную отметку. Снимаем её после readback и durable complete.
            current,current_raw=empty_rebind_guards(hub,plan,digest,state)
            final=empty_rebind_final(plan,digest,state['list_id'])
            if current!=final:
                if safe(hub/'ai/reminders-sync.json').read_text()!=current_raw:raise ValueError('empty_rebind_config_cas_conflict')
                durable(hub/'ai/reminders-sync.json',encoded(final))
            if config_read(hub)[0]!=final:raise ValueError('empty_rebind_config_readback_failed')
            return state
        if state['phase']=='complete':return clear_pending()
        def save():durable(path.parent/'state.json',encoded(state))
        state['approved']=True
        if not state.get('list_id'):
            if native.call('list_lists',{}).get('guarded_list_creation') is not True:raise ValueError('creation_account_unverifiable')
            state.update(phase='creating',create_pending=True);save()
            if safe(hub/'ai/reminders-sync.json').read_text()!=raw:raise ValueError('empty_rebind_config_cas_conflict')
            durable(hub/'ai/reminders-sync.json',encoded(intended_config(plan,digest)))
            created=native.call('manage_list',dict(action='create',list=plan['list_name'],expected_account_id=plan['account_id']))
            if not valid_uuid(created.get('id')):raise ValueError('empty_rebind_unknown_creation_do_not_retry')
            state['list_id']=created['id'];save()
        config,_=empty_rebind_guards(hub,plan,digest,state);empty_rebind_remote(hub,plan,state,config,native)
        if not state.get('group_done'):
            state.update(phase='grouping',group_pending=True);save()
            observation=empty_rebind_remote(hub,plan,state,config,native);row=next(r for r in observation['metadata']['lists'] if r['id']==state['list_id'])
            if row.get('group_id') is None:native.call('manage_list',dict(action='update',list=state['list_id'],group=plan['group_id'],expected_group_id=None))
            observation=empty_rebind_remote(hub,plan,state,config,native)
            if next(r for r in observation['metadata']['lists'] if r['id']==state['list_id']).get('group_id')!=plan['group_id']:raise ValueError('empty_rebind_group_readback_failed')
            state['group_done']=True;save()
        config,raw=empty_rebind_guards(hub,plan,digest,state);empty_rebind_remote(hub,plan,state,config,native)
        final=empty_rebind_final(plan,digest,state['list_id'],pending=True);load_sync().validate_binding_ids(final)
        state['phase']='committing';save()
        if safe(hub/'ai/reminders-sync.json').read_text()!=raw:raise ValueError('empty_rebind_config_cas_conflict')
        durable(hub/'ai/reminders-sync.json',encoded(final))
        if config_read(hub)[0]!=final:raise ValueError('empty_rebind_config_readback_failed')
        empty_rebind_remote(hub,plan,state,final,native)
        state['phase']='complete';save();return clear_pending()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['preview','apply','status','permission-preview','permission-apply','adopt','prepare-destination','rename-preview','rename-apply','rename-resume','rename-status','bulk-candidates','empty-rebind-preview','empty-rebind-apply','empty-rebind-resume'])
    parser.add_argument('--hub', type=Path); parser.add_argument('--project'); parser.add_argument('--list-name'); parser.add_argument('--group-id')
    parser.add_argument('--plan', type=Path); parser.add_argument('--sha256'); parser.add_argument('--approve', action='store_true'); parser.add_argument('--list-id')
    parser.add_argument('--expected-name'); parser.add_argument('--new-name')
    a = parser.parse_args()
    try:
        if a.command == 'empty-rebind-preview': result=empty_rebind_preview(a.hub,a.project)
        elif a.command in {'empty-rebind-apply','empty-rebind-resume'}: result=empty_rebind_apply(a.plan,a.sha256,a.approve)
        elif a.command == 'bulk-candidates': result=bulk_candidates(a.hub)
        elif a.command == 'rename-preview': result=rename_preview(a.hub,a.list_id,a.expected_name,a.new_name)
        elif a.command in {'rename-apply','rename-resume'}: result=rename_apply(a.plan,a.sha256,a.approve)
        elif a.command == 'rename-status': result=rename_status(a.plan,a.sha256)
        elif a.command == 'preview': result=preview(a.hub,a.project,a.list_name,a.group_id)
        elif a.command == 'permission-preview': result=permission_preview(a.hub,a.list_name)
        elif a.command == 'permission-apply': result=permission_apply(a.plan,a.sha256,a.approve)
        elif a.command in {'apply','prepare-destination'}: result=apply(a.plan,a.sha256,a.approve,prepare_only=a.command=='prepare-destination')
        elif a.command == 'adopt': result=adopt(a.plan,a.sha256,a.list_id,a.approve)
        else:
            _, plan, state=read_plan(a.plan,a.sha256);result=dict(phase=state['phase'],steps={k:v['status'] for k,v in state['steps'].items()},list_id=state.get('list_id'))
        print(encoded(result))
    except (ValueError, KeyError, OSError, RuntimeError) as exc:
        print(encoded({'ok':False,'error':str(exc)}));raise SystemExit(1)

if __name__ == '__main__': main()
