#!/usr/bin/env python3
"""Входящая сверка: приложение хранит поля задач, Хаб — проверенную копию."""
import contextlib
import copy
import fcntl
import importlib.util
import json
import os
import re
from pathlib import Path
import threading

_mutex = threading.RLock()
_locks = {}


def enabled(config):
    if 'task_authority' not in config:
        return False
    ref=config['task_authority']
    if (not isinstance(ref,dict) or ref.get('mode')!='reminders' or ref.get('deletions')!='cancel'
            or not isinstance(ref.get('journal'),str) or not re.fullmatch(r'ai/reminders-authority/[0-9a-f-]{36}',ref['journal'])
            or not isinstance(ref.get('sha256'),str) or not re.fullmatch(r'[0-9a-f]{64}',ref['sha256'])):
        raise ValueError('invalid_task_authority_policy')
    return True


def archive_module():
    path = Path(__file__).with_name('reminders_authority_archive.py')
    if not path.exists():
        raise ValueError('authority_archive_support_missing')
    spec = importlib.util.spec_from_file_location('authority_archive_support', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def validate_policy(hub, config):
    if not enabled(config) or config['task_authority'].get('deletions') != 'cancel':
        raise ValueError('invalid_task_authority_policy')
    archive_module().validate_activation(hub, config)


@contextlib.contextmanager
def locked(hub):
    hub = Path(hub).absolute()
    if '..' in hub.parts or hub != hub.resolve() or any(p.is_symlink() for p in [hub, *hub.parents]):
        raise ValueError('unsafe_authority_lock_path')
    if not _mutex.acquire(blocking=False):
        raise BlockingIOError('reminders_sync_locked')
    key = (os.getpid(), str(hub))
    try:
        if key in _locks:
            yield hub
        else:
            path = hub / 'ai/.reminders-sync.lock'
            if path.is_symlink() or path.parent.is_symlink():
                raise ValueError('unsafe_authority_lock_path')
            with path.open('a') as stream:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                _locks[key] = stream
                try:
                    yield hub
                finally:
                    _locks.pop(key, None)
    finally:
        _mutex.release()


def bound_projects(hub, config):
    spec = importlib.util.spec_from_file_location('authority_registry_sync', Path(__file__).with_name('reminders_sync.py'))
    sync = importlib.util.module_from_spec(spec); spec.loader.exec_module(sync)
    validate_policy(hub, config)
    result = dict(sync.registered(hub))
    for pid, binding in config['projects'].items():
        if binding.get('archive'):
            path = archive_module().project_path(hub, config, pid)
            if path is not None:
                result[pid] = path
    return result


def validate_expected_lists(hub, config, observation, partial=False, project_ids=None):
    lists = {r['id']: r for r in observation['metadata']['lists']}
    groups = {r['id']: r for r in observation['metadata']['groups']}
    errors = {}
    for pid, binding in config['projects'].items():
        if project_ids is not None and pid not in project_ids:
            continue
        try:
            listing = lists.get(binding['list_id'])
            if listing is None or listing.get('name') != binding['list_name']:
                raise ValueError('authority_expected_list_missing_or_changed')
            if not binding.get('account_id') or listing.get('account_id') != binding['account_id']:
                raise ValueError('authority_expected_list_account_changed')
            gid = archive_module().archive_group(hub, config, pid) if binding.get('archive') else binding.get('native_group_id')
            if (not binding.get('archive') and 'native_group_id' not in binding) or listing.get('group_id') != gid:
                raise ValueError('authority_expected_list_group_changed')
            if gid and (gid not in groups or groups[gid].get('account_id') != binding['account_id']):
                raise ValueError('authority_expected_group_account_changed')
            pins_path = config.get('structure', {}).get('group_ids_allowlist_file')
            if gid and pins_path:
                path = Path(pins_path)
                if not path.is_absolute() or any(p.is_symlink() for p in [path, *path.parents]) or '..' in path.parts:
                    raise ValueError('unsafe_authority_group_pins')
                pins = json.loads(path.read_text()).get('groups', {})
                if gid not in pins or groups[gid].get('name') != pins[gid]:
                    raise ValueError('authority_expected_group_name_changed')
        except ValueError as error:
            if not partial:
                raise
            errors[pid] = str(error)
    return errors


def validate_target(sync_module, hub, config, project_id, native):
    """Свежая принадлежность цели; успешное чтение задач соседей не требуется."""
    if project_id not in config['projects']:
        raise ValueError('unbound_project')
    reads=sync_module.reads_module()
    if reads is not None:
        reads.refresh()
    value=native.call('list_lists',{})
    flags=('error','errors','isError','more','has_more')
    if not isinstance(value,dict) or any(value.get(k) for k in flags):
        raise ValueError('authority_target_metadata_incomplete')
    for key in ('lists','groups'):
        values=value.get(key)
        if not isinstance(values,list):raise ValueError('authority_target_metadata_incomplete')
        for row in values:
            if (not isinstance(row,dict) or any(row.get(k) for k in flags)
                    or any(not isinstance(row.get(k),str) or not row[k] for k in ('id','name','account_id'))
                    or (key=='lists' and ('group_id' not in row or row['group_id'] is not None and not isinstance(row['group_id'],str)))):
                raise ValueError('authority_target_metadata_invalid')
        if len({r['id'] for r in values})!=len(values):raise ValueError('authority_target_metadata_duplicate')
        count_key='list_count' if key=='lists' else 'group_count'
        if count_key in value and value[count_key]!=len(values):raise ValueError('authority_target_metadata_incomplete')
    validate_expected_lists(hub,config,{'metadata':value},project_ids={project_id})
    binding=config['projects'][project_id]
    if binding.get('archive'):
        helper=archive_module()
        receipt=helper.archive().read_receipt(hub,config,project_id)
        if receipt is None:raise ValueError('archive_authority_adoption_required')
        helper.verify_group(config,receipt[1]['archive_group'],{'groups':value['groups']})
    elif binding.get('native_group_id') and not config.get('structure',{}).get('group_ids_allowlist_file'):
        # Старые привязки без отдельного файла закреплений используют принятый снимок активации.
        plan=archive_module().validate_activation(hub,config)
        expected=[g for g in plan['snapshot']['groups'] if g['id']==binding['native_group_id']]
        actual=[g for g in value['groups'] if g['id']==binding['native_group_id']]
        if len(expected)!=1 or len(actual)!=1 or any(actual[0].get(k)!=expected[0].get(k) for k in ('id','name','account_id')):
            raise ValueError('authority_expected_group_name_changed')
    return value


def prepare_pull(sync_module, hub, config, apply=False, project=None, native=None):
    with locked(hub):
        validate_policy(hub, config)
        native = native or sync_module.Native(config)
        external = sync_module.external_retirement_module()
        if external is None:
            raise ValueError('external_retirement_support_missing')
        observation = external.observe(Path(hub), config, native, partial=True)
        if not observation['complete']:
            blocked = observation['blocked_projects']
            items = [dict(project=pid, error=error) for pid, error in blocked.items()]
            blocked_lists = {config['projects'][pid]['list_id'] for pid in blocked}
            items.extend(dict(error=e['error'], list_id=e['list_id']) for e in observation['errors'] if e['list_id'] not in blocked_lists)
            return dict(config=config, items=items, stop=False, blocked_projects=set(blocked), skip_structure=True, cancellation_disabled=True, observation=observation)
        if apply:
            root = Path(hub) / 'ai/reminders-external-retirements'
            for path in sorted(root.glob('*/plan.json')) if root.exists() else ():
                digest = external.cancel.digest(external.cancel.document_bytes(path))
                _, plan, state = external.read(path, digest)
                if state['approved'] and state['phase'] != 'complete' and (not project or project in plan['projects']):
                    external.apply(path, digest, approve=True, native=native)
                    config = sync_module.load_config(hub)
            validate_policy(hub, config)
        present = {r['id'] for rows in observation['lists'].values() for r in rows}
        targets = []
        for pid, binding in config['projects'].items():
            if project and pid != project:
                continue
            for tid, link in binding.get('tasks', {}).items():
                rid = link.get('reminder_id')
                if rid and rid not in present and not link.get('cancellation') and not link.get('external_retirement'):
                    targets.append(dict(project_id=pid, task_id=tid, reminder_id=rid))
        items = [dict(project=t['project_id'], task_id=t['task_id'], reminder_id=t['reminder_id'], action='external_retirement') for t in targets]
        if targets and not apply:
            return dict(config=config, items=items, stop=True)
        if targets:
            activation = archive_module().validate_activation(hub, config)
            ref = config['task_authority']
            intent = dict(confirmed=True, statement=activation['statement'], targets=copy.deepcopy(targets),
                          basis=dict(kind='standing_policy', journal=ref['journal'], sha256=ref['sha256']))
            plan = external.preview(Path(hub), targets, intent, native=native)
            external.apply(plan['plan'], plan['sha256'], approve=True, native=native)
            config = sync_module.load_config(hub)
        return dict(config=config, items=items, stop=False)
