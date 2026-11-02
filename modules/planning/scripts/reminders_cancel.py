#!/usr/bin/env python3
"""Точные планы отмены и восстановления. Приложение требует доказанных гарантий."""
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
import tempfile
import uuid

_spec = importlib.util.spec_from_file_location('cancellation_sync', Path(__file__).with_name('reminders_sync.py'))
sync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sync)
PHASES = {'prepared', 'deleting', 'remote_deleted', 'hub_cancelled', 'committed', 'restoring', 'restored'}


def verification_module():
    spec = importlib.util.spec_from_file_location('project_list_verification', Path(__file__).with_name('reminders_project_list_verification.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def historical_module():
    spec = importlib.util.spec_from_file_location('reminders_historical', Path(__file__).with_name('reminders_historical.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def coordinator():
    import sys
    return sys.modules.get(__name__) or type('Coordinator', (), globals())


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def encoded(value):
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n'
    if len(text.encode('utf-8')) > 2_097_152:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
    return text


def canonical(path):
    path = sync.safe_path(Path(path))
    if '..' in path.parts or path != path.resolve():
        raise ValueError('noncanonical_path')
    return path


def document_bytes(path):
    path = canonical(path)
    if path.stat().st_size > 2_097_152: raise ValueError('file_too_large')
    data = path.read_bytes()
    if len(data) > 2_097_152: raise ValueError('file_too_large')
    return data


def valid_uuid(value):
    try:
        if not isinstance(value, str) or str(uuid.UUID(value)) != value.lower():
            raise ValueError('invalid_uuid')
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError('invalid_uuid') from error
    return value


def fsync_dir(path):
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def durable_json(path, value):
    """Сначала файл, затем атомарная замена и fsync каталога."""
    path = canonical(path)
    payload = encoded(value)
    if len(payload.encode('utf-8')) > 2_097_152: raise ValueError('file_too_large')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False, encoding='utf-8') as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        fsync_dir(path.parent)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


@contextlib.contextmanager
def locked(hub):
    with sync.sync_lock(canonical(hub)) as selected:
        yield selected


def layout_for(config, items):
    layouts = {config['projects'][i['project_id']].get('layout', 'parent') for i in items}
    if len(layouts) != 1 or not layouts <= {'parent', 'project_list'}:
        raise ValueError('mixed_cancellation_layouts')
    return layouts.pop()


def allowlist(config, layout='parent'):
    path = canonical(config['standard_allowlist_file'] if layout == 'project_list' else config['allowlist_file'])
    original = canonical(config['allowlist_file'])
    if layout == 'project_list' and path != original.parent / 'reminders-standard-allowlist.json':
        raise ValueError('invalid_v2_allowlist_path')
    raw = document_bytes(path)
    value = json.loads(raw)
    names = value.get('names')
    if not isinstance(names, list) or not names or any(not isinstance(n, str) or not n for n in names):
        raise ValueError('invalid_allowlist')
    return names, digest(raw)


def guard_bindings(config, items, hub):
    layout = layout_for(config, items)
    if canonical(config['allowlist_file']) != hub / 'ai/reminders-allowlist.json': raise ValueError('invalid_legacy_allowlist_path')
    if layout == 'project_list' and canonical(config.get('standard_allowlist_file', '')) != hub / 'ai/reminders-standard-allowlist.json': raise ValueError('invalid_v2_allowlist_path')
    names, sha = allowlist(config, layout)
    for item in items:
        pid = item['project_id']
        binding = config['projects'][pid]
        if binding['list_name'] not in names:
            raise ValueError('list_outside_allowlist')
        valid_uuid(binding['list_id'])
        if layout == 'project_list':
            if 'parent_id' not in binding or binding['parent_id'] is not None or item.get('parent_id') is not None:
                raise ValueError('project_list_parent_forbidden')
            if sum(b.get('list_id') == binding['list_id'] for b in config['projects'].values()) != 1:
                raise ValueError('exclusive_project_list')
            for key in ('account_id', 'native_group_id'):
                valid_uuid(binding[key])
                if key in item and item[key] != binding[key]: raise ValueError('project_list_identity_changed')
            if item.get('layout', layout) != layout: raise ValueError('layout_changed')
            structure = config.get('structure', {})
            if structure.get('list_roles', {}).get(binding['list_id']) != dict(kind='project',project_id=pid) or structure.get('projects', {}).get(pid, {}).get('list_id') != binding['list_id']:
                raise ValueError('project_list_role_changed')
        else:
            valid_uuid(binding['parent_id'])
        if item.get('reminder_id'):
            valid_uuid(item['reminder_id'])
        if any(binding.get(key) != item.get(key, binding.get(key)) for key in ('list_id', 'list_name', 'parent_id')):
            raise ValueError('binding_changed')
    sync.validate_binding_ids(config)
    return sha


def permission_edge(hub, root, path, original, raw, state_raw):
    """Повторно используем только чистую проверку тех же байтов в одном запуске."""
    def verify():
        receipt = json.loads(raw)
        state = json.loads(state_raw)
        if not isinstance(receipt, dict) or receipt.get('kind') != 'permission':
            return None
        operation = valid_uuid(receipt.get('operation'))
        if receipt.get('hub') != str(hub) or path != root / operation / 'plan.json':
            return None
        if not isinstance(state, dict) or state.get('approved') is not True or state.get('phase') != 'complete' or state.get('sha256') != digest(raw):
            return None
        permission = receipt['permission']
        before = permission['before']
        after = permission['after']
        if permission['original'] != original or not isinstance(before, str) or not isinstance(after, str):
            return None
        old = json.loads(before); new = json.loads(after)
        if set(old) != {'names'} or set(new) != {'names'}:
            return None
        old_names, new_names = old['names'], new['names']
        if (not isinstance(old_names, list) or not isinstance(new_names, list) or
                any(not isinstance(n, str) or not n for n in old_names + new_names) or
                len(set(old_names)) != len(old_names) or len(set(new_names)) != len(new_names)):
            return None
        name = receipt['list_name']
        if not isinstance(name, str) or not name.strip():
            return None
        added = [] if name in old_names else [name]
        if new_names != old_names + added or permission['added'] != added:
            return None
        return digest(before), digest(after)
    reads = sync.reads_module()
    if reads is None:
        return verify()
    key = ('permission_edge', str(hub), str(root), str(path), original, digest(raw), digest(state_raw))
    return reads.memo(key, lambda: (verify(), True))


def terminal_allowlist_matches(hub, config, plan, current_sha):
    """Старые квитанции принимают только доказанную цепочку расширений разрешений.

    Используется при чтении завершённой отмены; планы новых записей остаются строгими.
    """
    previous_sha = plan['allowlist_sha256']
    if previous_sha == current_sha:
        return True
    if plan['version'] != 2:
        return False
    original = document_bytes(hub / 'ai/reminders-allowlist.json').decode('utf-8')
    root = canonical(hub / 'ai/reminders-project-lists')
    if not root.exists():
        return False
    edges = {}
    for path in root.glob('*/plan.json'):
        try:
            raw = document_bytes(path)
            state_raw = document_bytes(path.parent / 'state.json')
            edge = permission_edge(hub, root, path, original, raw, state_raw)
            if edge is not None:
                edges.setdefault(edge[0], set()).add(edge[1])
        except (ValueError, KeyError, TypeError, OSError):
            # Неисправная квитанция не даёт разрешений; другие цепочки независимы.
            continue
    pending, seen = [previous_sha], set()
    while pending:
        value = pending.pop()
        if value == current_sha:
            return True
        if value not in seen:
            seen.add(value)
            pending.extend(edges.get(value, ()))
    return False


def validate_policy(value):
    if value not in {'strict', 'no_concurrent_edits'}:
        raise ValueError('invalid_concurrency_policy')
    return value


def capabilities(native, policy='strict', version=1, items=None):
    policy = validate_policy(policy)
    value = native.call('hub_cancel_capabilities', {})
    if value.get('protocol') != 1 or (version == 1 and value.get('same_uuid_restore_verified') is not True):
        raise ValueError('native_capabilities_not_verified')
    if version == 2:
        scope = value.get('project_list_verified_scope', {})
        if 2 not in value.get('supported_versions', []) or value.get('project_list_same_uuid_restore_verified') is not True or any(
                scope not in [dict(list_id=i['list_id'], account_id=i['account_id'], group_id=i['native_group_id']), dict(family='same_os_executor_account',account_id=i['account_id'])] for i in items or []):
            raise ValueError('project_list_capabilities_not_verified')
    if policy == 'strict' and value.get('atomic_version_check') is not True:
        raise ValueError('native_capabilities_not_verified')
    if policy == 'no_concurrent_edits' and (value.get('optimistic_version_check') is not True or value.get('requires_no_concurrent_edits') is not True):
        raise ValueError('native_capabilities_not_verified')


def full_list(native, binding, target):
    value = native.call('find_reminders', {'list': binding['list_id'], 'include_completed': True, 'limit': 500})
    if value.get('more') or value.get('has_more') or not isinstance(value.get('reminders'), list) or len(value['reminders']) >= 500 or value.get('count', len(value['reminders'])) != len(value['reminders']):
        raise ValueError('incomplete_reminder_snapshot')
    seen = set()
    for row in value['reminders']:
        rid = valid_uuid(row['id'])
        if rid in seen or row.get('list_id', binding['list_id']) != binding['list_id'] or row.get('list') != binding['list_name']:
            raise ValueError('invalid_list_snapshot')
        seen.add(rid)
        if row.get('parent_id') == target:
            raise ValueError('target_has_children')


def verify_list_identity(native, item):
    meta = native.call('list_lists', {})
    lists = [r for r in meta.get('lists', []) if r.get('id') == item['list_id'] or r.get('name') == item['list_name']]
    groups = [g for g in meta.get('groups', []) if g.get('id') == item['native_group_id']]
    if (len(lists) != 1 or lists[0].get('id') != item['list_id'] or lists[0].get('name') != item['list_name'] or
            lists[0].get('account_id') != item['account_id'] or lists[0].get('group_id') != item['native_group_id'] or
            lists[0].get('shared', False) is not False or len(groups) != 1 or groups[0].get('account_id') != item['account_id']):
        raise ValueError('project_list_identity_changed')


def verify_parent(native, item):
    if item.get('layout') == 'project_list':
        verify_list_identity(native, item)
        return
    parent = native.get(item['parent_id'], item['list_id'])
    def comparable(value):
        value = copy.deepcopy(value)
        value['subtasks'] = [r for r in value.get('subtasks', []) if r.get('id') != item['reminder_id']]
        return value
    if comparable(parent) != comparable(item['parent']) or parent.get('completed') or parent.get('parent_id'):
        raise ValueError('parent_changed')


def quote(text):
    return '\n'.join('> ' + s for s in text.splitlines()) + '\n'


def cancellation_texts(hp, row):
    after = dict(hp.texts)
    kind, tid = row['kind'], row['task_id']
    first, last, body = sync.chunk(after[kind], kind, tid)
    if kind == 'future':
        changed, count = re.subn(r'^Status: .+$', 'Status: dropped', body, count=1, flags=re.M)
        if count != 1:
            raise ValueError('missing_status')
        after[kind] = after[kind][:first] + changed + after[kind][last:]
    else:
        archived = '### ' + tid + ' — ' + row['title'] + '\nStatus: dropped\n'
        if row.get('deadline'):
            archived += 'Due: ' + row['deadline'] + '\n'
        if row.get('planned_day'):
            archived += 'Запланировано: ' + row['planned_day'] + '.\n'
        archived += '\nИсходная запись:\n' + quote(body)
        previous = [r for r in hp.parser.read_records(hp.pid, 'future', after['future']) if r['task_id'] == tid]
        if previous:
            a, b, saved = sync.chunk(after['future'], 'future', tid)
            if previous[0]['status'] != 'promoted':
                raise ValueError('conflicting_archive')
            archived += '\nПрежняя запись:\n' + quote(saved)
            after['future'] = after['future'][:a] + archived + after['future'][b:]
        else:
            after['future'] += '\n' + archived
        after[kind] = '# Текущая задача\n\nStatus: empty\n' if kind == 'current' else after[kind][:first] + after[kind][last:]
    a, b, dropped = sync.chunk(after['future'], 'future', tid)
    dropped = dropped.rstrip() + '\n\nПрекращено по решению пользователя. Это отмена дальнейшей работы, не подтверждение успешного выполнения или установленной причины. Прежний контекст сохранён.\n'
    after['future'] = after['future'][:a] + dropped + after['future'][b:]
    for k, text in after.items():
        hp.parser.read_records(hp.pid, k, text)
        if hp.parser.unrecognized_headings(k, text.splitlines()):
            raise ValueError('unrecognized_heading')
    return after


def plan_location(hub, path):
    path = canonical(path)
    if path.name != 'plan.json' or path.parent.parent != hub / 'ai/reminders-cancellations':
        raise ValueError('invalid_plan_path')
    valid_uuid(path.parent.name)
    return path


def read_plan(hub, path, sha, require_active=True):
    path = plan_location(hub, path)
    raw = document_bytes(path)
    if not re.fullmatch('[0-9a-f]{64}', sha or '') or digest(raw) != sha:
        raise ValueError('plan_checksum_mismatch')
    plan = json.loads(raw)
    if plan.get('version') not in {1, 2} or plan.get('operation_id') != path.parent.name or not plan.get('items'):
        raise ValueError('invalid_plan')
    validate_policy(plan.get('concurrency_policy', 'strict'))
    if plan.get('purpose') == 'project_list_verification':
        if plan['version'] != 2 or plan.get('marker') != plan['operation_id'] or len(plan['items']) != 1:
            raise ValueError('invalid_verification_plan')
        item = plan['items'][0]
        if item.get('task_id') != 'verification-' + plan['operation_id'] or item.get('project_id') != 'content-system' or any(k in item for k in ('before_texts', 'after_texts', 'link')):
            raise ValueError('invalid_verification_target')
        valid_uuid(item['reminder_id'])
        return path, plan
    if (plan['version'] == 2 and plan.get('purpose') != 'task_cancellation') or plan.get('purpose', 'task_cancellation') != 'task_cancellation': raise ValueError('invalid_purpose')
    try:
        projects = {pid: sync.task_project_path(hub, pid) for pid in {i['project_id'] for i in plan['items']}} if require_active else {i['project_id']: hub / 'projects' / i['project_id'] for i in plan['items']}
    except ValueError as error:
        if error.args == ('unregistered_or_inactive_project',):
            raise ValueError('project_path_changed') from error
        raise
    seen = set()
    for item in plan['items']:
        pid = item['project_id']
        if pid in seen:
            raise ValueError('one_target_per_project')
        seen.add(pid)
        if pid not in projects or canonical(item['project_path']) != projects[pid]:
            raise ValueError('project_path_changed')
        valid_uuid(item['reminder_id'])
        if plan['version'] == 2:
            if item.get('layout') != 'project_list' or 'parent_id' not in item or item['parent_id'] is not None or 'parent_id' in item['remote']:
                raise ValueError('invalid_root_snapshot')
            valid_uuid(item['account_id']); valid_uuid(item['native_group_id'])
        else: valid_uuid(item['parent_id'])
        valid_uuid(item['list_id'])
        if item['source_path'] != str(projects[pid] / 'ai' / sync.NAMES[item['source_kind']]):
            raise ValueError('source_path_changed')
        if set(item['before_texts']) != set(sync.NAMES) or set(item['after_texts']) != set(sync.NAMES):
            raise ValueError('invalid_text_snapshots')
    return path, plan


def read_state(path, plan, sha):
    state_path = canonical(path.with_name('state.json'))
    state = json.loads(document_bytes(state_path))
    ids = {i['reminder_id'] for i in plan['items']}
    if state.get('plan_sha256') != sha or set(state.get('items', {})) != ids or type(state.get('approved')) is not bool:
        raise ValueError('invalid_cancellation_state')
    phases = verification_module().PHASES if plan.get('purpose') == 'project_list_verification' else PHASES
    if any(not isinstance(s, dict) or s.get('phase') not in phases for s in state['items'].values()):
        raise ValueError('invalid_cancellation_phase')
    if any(s['phase'] != 'prepared' for s in state['items'].values()) and not state['approved']:
        raise ValueError('unapproved_cancellation_state')
    for progress in state['items'].values():
        if plan.get('purpose') == 'project_list_verification' and progress['phase'] == 'cleaned' and not isinstance(progress.get('cleaned_snapshot'), dict): raise ValueError('invalid_verification_cleanup_receipt')
        if progress['phase'] in {'remote_deleted', 'hub_cancelled', 'committed'} and not isinstance(progress.get('deleted_snapshot'), dict):
            raise ValueError('invalid_cancellation_receipt')
        if progress['phase'] == 'restored' and not isinstance(progress.get('restored_snapshot'), dict):
            raise ValueError('invalid_restoration_receipt')
    return state


def cancelled_link(item, plan, sha):
    link = copy.deepcopy(item['link'])
    link['cancellation'] = {'operation_id': plan['operation_id'], 'plan_sha256': sha, 'reminder_id': item['reminder_id']}
    return link


def current_config(hub, config, plan, sha, allow_restored=False, terminal=False, terminal_phases=None):
    path = canonical(hub / 'ai/reminders-sync.json')
    raw = document_bytes(path)
    actual = json.loads(raw)
    if actual != config:
        raise ValueError('config_argument_stale')
    if {i['project_id'] for i in plan['items']} & sync.migration_pending(hub, actual):
        raise ValueError('migration_recovery_required')
    expected = copy.deepcopy(plan['config'])
    if terminal:
        for item in plan['items']:
            pid = item['project_id']
            live = copy.deepcopy(actual['projects'][pid]); before = copy.deepcopy(expected['projects'][pid])
            # Other tasks may advance; the exact target and every project-level binding field are fixed.
            live.pop('tasks', None); before.pop('tasks', None)
            if live != before: raise ValueError('target_binding_changed')
        if actual.get('cancellation_policy', 'strict') != expected.get('cancellation_policy', 'strict'):
            raise ValueError('cancellation_policy_changed')
    own = False
    for item in plan['items']:
        pid, tid = item['project_id'], item['task_id']
        link = actual['projects'][pid]['tasks'][tid]
        if terminal_phases is not None:
            expected_link = item['link'] if terminal_phases[item['reminder_id']]['phase'] == 'restored' else cancelled_link(item, plan, sha)
            if link != expected_link: raise ValueError('terminal_receipt_changed')
        if link == cancelled_link(item, plan, sha):
            expected['projects'][pid]['tasks'][tid] = copy.deepcopy(link)
            own = True
        elif link != item['link']:
            raise ValueError('config_link_changed')
    valid_hashes = {plan['config_sha256']}
    if allow_restored:
        valid_hashes.add(digest(encoded(expected)))
    if not terminal and (actual != expected or (not own and digest(raw) not in valid_hashes)):
        raise ValueError('config_checksum_mismatch')
    if guard_bindings(actual, plan['items'], hub) != plan['allowlist_sha256']:
        raise ValueError('allowlist_checksum_mismatch')
    return actual


def native_status(native, path, sha, item):
    value = native.call('hub_cancel_status', {'plan': str(path), 'plan_sha256': sha, 'id': item['reminder_id']})
    if value.get('state') not in {'active', 'deleted'} or not value.get('version') or not isinstance(value.get('snapshot'), dict):
        raise ValueError('invalid_native_status')
    snap = value['snapshot']
    if item.get('layout') == 'project_list' and 'parent_id' in snap:
        raise ValueError('native_root_parent_present')
    if value['version'] != snap.get('version') or snap.get('list') != item['list_name']: raise ValueError('native_status_snapshot_mismatch')
    if snap.get('id') != item['reminder_id'] or snap.get('list_id') != item['list_id'] or snap.get('parent_id') != item['parent_id']:
        raise ValueError('native_status_binding_mismatch')
    return value


def same_fields(actual, expected):
    return {k: v for k, v in actual.items() if k not in {'version', 'deleted_version'}} == {k: v for k, v in expected.items() if k not in {'version', 'deleted_version'}}


def local_progress(hub, item, restoring=False):
    hp = sync.HubProject(hub, item['project_id'])
    before, after = item['before_texts'], item['after_texts']
    # Отмена всегда сначала резервирует в future, затем очищает источник.
    # Восстановление сначала возвращает источник, затем очищает архив.
    order = ('current', 'paused', 'future') if restoring else ('future', 'current', 'paused')
    start, finish = (after, before) if restoring else (before, after)
    valid = [dict(start)]
    for kind in order:
        nxt = dict(valid[-1])
        nxt[kind] = finish[kind]
        valid.append(nxt)
    if hp.texts not in valid:
        raise ValueError('hub_snapshot_conflict')
    return hp, order


def write_texts(hp, item, restoring=False):
    _, order = local_progress(hp.hub, item, restoring)
    desired = item['before_texts'] if restoring else item['after_texts']
    for kind in order:
        text = desired[kind]
        if hp.texts[kind] == text:
            continue
        for k, path in hp.paths.items():
            if path.read_text() != hp.texts[k]:
                raise ValueError('hub_changed_since_read')
        config = json.loads(canonical(hp.hub / 'ai/reminders-sync.json').read_text())
        if sync.authority_enabled(config):
            sync.authority_module().validate_policy(hp.hub, config)
            if sync.task_project_path(hp.hub, hp.pid, config) != hp.project:
                raise ValueError('authority_projection_path_changed')
            hp.parser.write_task_file(hp.hub, hp.pid, kind, digest(hp.texts[kind]), text)
            if hp.paths[kind].read_text() != text:
                raise RuntimeError('hub_write_readback_failed')
        else:
            result = subprocess.run(['python3', str(hp.hub / 'scripts/task_records.py'), 'write', '--hub', str(hp.hub), '--project-id', hp.pid, '--kind', kind, '--expected-sha256', digest(hp.texts[kind])], input=text, text=True, capture_output=True, timeout=40)
            if result.returncode or hp.paths[kind].read_text() != text:
                raise RuntimeError('hub_write_failed: ' + result.stderr)
        fsync_dir(hp.paths[kind].parent)
        hp.texts[kind] = text


def pending_projects(hub, config):
    hub = canonical(hub)
    root = canonical(hub / 'ai/reminders-cancellations')
    pending = set()
    if not root.exists():
        return pending
    for folder in root.iterdir():
        if folder.name.startswith('.draft-'):
            continue
        canonical(folder)
        if not folder.is_dir():
            raise ValueError('invalid_cancellation_journal')
        try:
            path = folder / 'plan.json'
            if not path.exists() and (folder / 'bootstrap.json').exists():
                boot = json.loads(canonical(folder / 'bootstrap.json').read_text())
                if boot.get('purpose') != 'project_list_verification' or boot.get('operation_id') != folder.name or boot.get('approved') is not True: raise ValueError('invalid_verification_bootstrap')
                pending.add('content-system'); continue
            raw = path.read_bytes()
            sha = digest(raw)
            path, plan = read_plan(hub, path, sha, require_active=False)
            state = read_state(path, plan, sha)
            terminals = {'cleaned'} if plan.get('purpose') == 'project_list_verification' else {'committed', 'restored'}
            if state['approved'] and any(s['phase'] not in terminals for s in state['items'].values()):
                pending.update(i['project_id'] for i in plan['items'])
        except Exception as error:
            raise ValueError('corrupt_cancellation_journal: ' + str(error)) from error
    return pending


def preview(hub, config, targets, native, expected_uuid=None, concurrency_policy=None):
    with locked(hub) as hub:
        selected_policy = validate_policy(concurrency_policy if concurrency_policy is not None else config.get('cancellation_policy', 'strict'))
        if not targets or len({t[0] for t in targets}) != len(targets):
            raise ValueError('one_target_per_project')
        descriptors = [{'project_id': p, 'task_id': t} for p, t in targets]
        selected_layout = layout_for(config, descriptors)
        if {p for p, _ in targets} & sync.migration_pending(hub, config): raise ValueError('migration_recovery_required')
        allowed_sha = guard_bindings(config, descriptors, hub)  # До первого обращения к приложению.
        raw_config = canonical(hub / 'ai/reminders-sync.json').read_bytes()
        if json.loads(raw_config) != config:
            raise ValueError('config_argument_stale')
        if {p for p, _ in targets} & pending_projects(hub, config):
            raise ValueError('cancellation_recovery_required')
        items = []
        for pid, tid in targets:
            hp = sync.HubProject(hub, pid)
            row = hp.rows()[tid]
            if row['status'] in sync.TERMINAL:
                raise ValueError('task_not_open')
            binding = config['projects'][pid]
            link = binding['tasks'][tid]
            rid = valid_uuid(link['reminder_id'])
            if expected_uuid and (expected_uuid.get((pid, tid)) if isinstance(expected_uuid, dict) else expected_uuid) != rid:
                raise ValueError('expected_uuid_mismatch')
            if link.get('cancellation') or any(k.startswith('pending_') for k in link):
                raise ValueError('pending_binding')
            parent = None if selected_layout == 'project_list' else native.get(binding['parent_id'], binding['list_id'])
            if parent is not None and (parent.get('completed') or parent.get('parent_id') or not parent.get('version')):
                raise ValueError('parent_not_open')
            remote = native.get(rid, binding['list_id'], binding['parent_id'])
            if selected_layout == 'project_list':
                verify_list_identity(native, binding)
                if 'parent_id' in remote or 'subtasks' in remote: raise ValueError('invalid_root_snapshot')
            if remote.get('id') != rid or not remote.get('version'):
                raise ValueError('remote_not_open')
            if remote.get('completed') and (remote.get('repeat') or link.get('repeating')):
                raise ValueError('completed_series_requires_review')
            full_list(native, binding, rid)
            items.append(dict(project_id=pid, task_id=tid, project_path=str(hp.project), reminder_id=rid,
                              list_id=binding['list_id'], list_name=binding['list_name'], parent_id=binding['parent_id'],
                              remote=remote, parent=parent, link=copy.deepcopy(link), before_texts=hp.texts,
                              after_texts=cancellation_texts(hp, row), source_kind=row['kind'], source_path=row['source_path'],
                              scope='entire_series' if remote.get('repeat') or link.get('repeating') else 'single_reminder',
                              **(dict(layout='project_list', account_id=binding['account_id'], native_group_id=binding['native_group_id']) if selected_layout == 'project_list' else {})))
        operation = str(uuid.uuid4())
        root = canonical(hub / 'ai/reminders-cancellations')
        root.mkdir(exist_ok=True)
        fsync_dir(root.parent)
        staging = canonical(root / ('.draft-' + operation))
        folder = staging
        folder.mkdir()
        fsync_dir(root)
        path = folder / 'plan.json'
        plan = dict(version=2 if selected_layout == 'project_list' else 1, operation_id=operation, created_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                    concurrency_policy=selected_policy,
                    changes=('Не менять задачи Хаба и Напоминаний во время отмены и восстановления' if selected_policy == 'no_concurrent_edits'
                             else 'Строгая проверка версии перед изменением'),
                    config_sha256=digest(raw_config), allowlist_sha256=allowed_sha, config=copy.deepcopy(config), items=items)
        if selected_layout == 'project_list': plan['purpose'] = 'task_cancellation'
        durable_json(path, plan)
        sha = digest(path.read_bytes())
        durable_json(path.with_name('state.json'), dict(plan_sha256=sha, approved=False, items={i['reminder_id']: {'phase': 'prepared'} for i in items}))
        published = canonical(root / operation)
        os.replace(staging, published)
        fsync_dir(root)
        path = published / 'plan.json'
        return dict(ok=True, path=str(path), sha256=sha, plan=plan)


def cancelled_block(hub, item):
    hp = sync.HubProject(hub, item['project_id'])
    expected = sync.chunk(item['after_texts']['future'], 'future', item['task_id'])[2]
    actual = sync.chunk(hp.texts['future'], 'future', item['task_id'])[2]
    if actual.rstrip() != expected.rstrip():
        raise ValueError('cancelled_block_changed')
    return hp


def validate_task_set(hp, texts):
    """Разрешены только известные исторические пары, а не второй живой Task ID."""
    groups = {}
    for row in hp.parser.read_project_records(hp.pid, texts['current'], texts['future'], texts['paused']):
        groups.setdefault(row['task_id'], []).append(row)
    for tid, rows in groups.items():
        if len(rows) == 1:
            continue
        kinds = {row['source_kind'] for row in rows}
        future = next((row for row in rows if row['source_kind'] == 'future'), None)
        historical = len(rows) == 2 and len(kinds) == 2 and future is not None and (
            (future['status'] == 'promoted' and bool(kinds & {'current', 'paused'}))
            or (future['status'] == 'done' and 'paused' in kinds))
        if not historical:
            raise ValueError('duplicate_task_id: ' + tid)


def restored_texts(hp, item):
    validate_task_set(hp, hp.texts)
    if hp.texts == item['after_texts']:
        validate_task_set(hp, item['before_texts'])
        return copy.deepcopy(item['before_texts'])
    texts = dict(hp.texts)
    tid, kind = item['task_id'], item['source_kind']
    a, b, cancelled = sync.chunk(texts['future'], 'future', tid)
    if kind == 'future':
        original = sync.chunk(item['before_texts']['future'], 'future', tid)[2]
        # Сохраняем разделитель, появившийся с новой соседней задачей.
        suffix = cancelled[len(cancelled.rstrip()):]
        texts['future'] = texts['future'][:a] + original.rstrip() + suffix + texts['future'][b:]
    else:
        if kind == 'current':
            if texts['current'] != item['after_texts']['current']:
                raise ValueError('hub_current_restore_conflict')
            texts['current'] = item['before_texts']['current']
        else:
            first, last, source = sync.chunk(item['before_texts']['paused'], 'paused', tid)
            prefix = item['before_texts']['paused'][:first]
            if not texts['paused'].startswith(prefix):
                raise ValueError('hub_paused_restore_conflict')
            texts['paused'] = texts['paused'][:first] + source + texts['paused'][first:]
        old_rows = hp.parser.read_records(hp.pid, 'future', item['before_texts']['future'])
        old = next((r for r in old_rows if r['task_id'] == tid), None)
        prior = sync.chunk(item['before_texts']['future'], 'future', tid)[2] if old else ''
        texts['future'] = texts['future'][:a] + prior + texts['future'][b:]
    for k, text in texts.items():
        hp.parser.read_records(hp.pid, k, text)
        if hp.parser.unrecognized_headings(k, text.splitlines()):
            raise ValueError('unrecognized_restored_heading')
    validate_task_set(hp, texts)
    return texts


def restore_path_for(path, token):
    return canonical(path.with_name('restore-' + token + '.json'))


def _restore_plan(path, plan, sha, token):
    if not re.fullmatch('[0-9a-f]{64}', token or ''):
        raise ValueError('restore_token_required')
    restore_path = restore_path_for(path, token)
    raw = document_bytes(restore_path)
    if digest(raw) != token:
        raise ValueError('restore_checksum_mismatch')
    value = json.loads(raw)
    if value.get('plan_sha256') != sha or value.get('operation_id') != plan['operation_id'] or set(value.get('items', {})) != {i['reminder_id'] for i in plan['items']}:
        raise ValueError('invalid_restore_plan')
    return value


def restore_preview(hub, path, sha, config, native):
    with locked(hub) as hub:
        path, plan = read_plan(hub, path, sha)
        if plan.get('purpose') == 'project_list_verification': raise ValueError('verification_command_required')
        state = read_state(path, plan, sha)
        if historical_module().selected(config, plan):
            return historical_module().restore_preview(coordinator(),hub,path,sha,config,native,plan,state)
        # Завершённая отмена допускает новые несвязанные записи конфигурации.
        actual = json.loads(canonical(hub / 'ai/reminders-sync.json').read_text())
        if actual != config:
            raise ValueError('config_argument_stale')
        if guard_bindings(config, plan['items'], hub) != plan['allowlist_sha256']: raise ValueError('allowlist_checksum_mismatch')
        current_config(hub, config, plan, sha, terminal=all(p['phase'] in {'committed', 'restored'} for p in state['items'].values()), terminal_phases=state['items'] if all(p['phase'] in {'committed', 'restored'} for p in state['items'].values()) else None)
        if not state['approved'] or any(s['phase'] in {'restoring', 'restored'} for s in state['items'].values()):
            raise ValueError('cancel_not_rollbackable')
        snapshots = {}
        for item in plan['items']:
            binding = config['projects'][item['project_id']]
            link = binding['tasks'][item['task_id']]
            if link not in (item['link'], cancelled_link(item, plan, sha)):
                raise ValueError('cancelled_link_changed')
            verify_parent(native, item)
            committed = state['items'][item['reminder_id']]['phase'] == 'committed'
            if committed:
                hp = cancelled_block(hub, item)
                desired = restored_texts(hp, item)
            else:
                hp, _ = local_progress(hub, item)
                desired = copy.deepcopy(item['before_texts'])
            remote = native_status(native, path, sha, item)
            fresh_partial = (plan.get('concurrency_policy', 'strict') == 'no_concurrent_edits'
                             and not committed and remote['state'] == 'deleted')
            if (committed and remote['state'] != 'deleted') or (not fresh_partial and not same_fields(remote['snapshot'], item['remote'])):
                raise ValueError('restore_remote_conflict')
            if remote['state'] == 'active' and remote['snapshot'] != item['remote']:
                raise ValueError('restore_active_remote_changed')
            snapshots[item['reminder_id']] = dict(remote=remote, before_texts=hp.texts, after_texts=desired)
        value = dict(version=1, operation_id=plan['operation_id'], plan_sha256=sha, items=snapshots,
                     config=copy.deepcopy(config), config_sha256=digest(canonical(hub / 'ai/reminders-sync.json').read_bytes()),
                     allowlist_sha256=allowlist(config, layout_for(config, plan['items']))[1],
                     changes=('Восстановить UUID и расположение записей Хаба, сохранив текущие поля Напоминаний'
                              if plan.get('concurrency_policy', 'strict') == 'no_concurrent_edits'
                              else 'Восстановить исходные UUID, поля и расположение канонических записей'))
        token = digest(encoded(value))
        restore_path = restore_path_for(path, token)
        if not restore_path.exists():
            durable_json(restore_path, value)
        elif digest(restore_path.read_bytes()) != token:
            raise ValueError('restore_checksum_mismatch')
        return dict(ok=True, path=str(restore_path), sha256=token)


def execute(hub, path, sha, config, native, restore=False, restore_token=None):
    with locked(hub) as hub:
        path, plan = read_plan(hub, path, sha)
        if plan.get('purpose') == 'project_list_verification': raise ValueError('verification_command_required')
        state = read_state(path, plan, sha)
        rp = _restore_plan(path, plan, sha, restore_token) if restore else None
        if not restore and historical_module().selected(config, plan):
            if any(p['phase'] not in {'committed','restored'} for p in state['items'].values()): raise ValueError('cancellation_already_restoring')
            historical_module().status(coordinator(),hub,path,sha,config,native,plan,state)
            return dict(ok=True,operation_id=plan['operation_id'],state='terminal',path=str(path),sha256=sha)
        if restore and historical_module().selected(config, plan):
            return historical_module().execute(coordinator(),hub,path,sha,config,native,plan,state,rp,restore_token)
        execution_plan = copy.deepcopy(plan)
        if restore:
            execution_plan.update(config=rp['config'], config_sha256=rp['config_sha256'], allowlist_sha256=rp['allowlist_sha256'])
            # current_config принимает исходную либо принадлежащую этой операции связь.
            for item in execution_plan['items']:
                execution_plan['config']['projects'][item['project_id']]['tasks'][item['task_id']] = copy.deepcopy(item['link'])
        all_terminal = all(p['phase'] in {'committed', 'restored'} for p in state['items'].values())
        actual = current_config(hub, config, execution_plan, sha, allow_restored=restore, terminal=all_terminal and not restore, terminal_phases=state['items'] if all_terminal and not restore else None)
        if all_terminal and not restore:
            # No writes, including journal writes, in this idempotent branch.
            for item in plan['items']:
                progress = state['items'][item['reminder_id']]
                local_item = copy.deepcopy(item)
                if progress['phase'] == 'restored' and state.get('restore_token'):
                    saved_restore = _restore_plan(path, plan, sha, state['restore_token'])['items'][item['reminder_id']]
                    local_item.update(before_texts=saved_restore['after_texts'], after_texts=saved_restore['before_texts'])
                local_progress(hub, local_item, progress['phase'] == 'restored')
                verify_parent(native, item); full_list(native, item, item['reminder_id'])
                observed = native_status(native, path, sha, item)
                key = 'restored_snapshot' if progress['phase'] == 'restored' else 'deleted_snapshot'
                if observed != progress.get(key): raise ValueError('terminal_snapshot_changed')
            return dict(ok=True, operation_id=plan['operation_id'], state='terminal', path=str(path), sha256=sha)
        selected_policy = validate_policy(plan.get('concurrency_policy', 'strict'))
        capabilities(native, selected_policy, plan['version'], plan['items'])  # Проверяем гарантии именно выбранного плана.
        execution_items = []
        for item in plan['items']:
            effective = copy.deepcopy(item)
            if restore:
                effective['before_texts'] = rp['items'][item['reminder_id']]['after_texts']
                effective['after_texts'] = rp['items'][item['reminder_id']]['before_texts']
                if selected_policy == 'no_concurrent_edits' and state['items'][item['reminder_id']]['phase'] != 'committed':
                    effective['remote'] = copy.deepcopy(rp['items'][item['reminder_id']]['remote']['snapshot'])
            execution_items.append(effective)
        if restore and state.get('restore_token') not in {None, restore_token}:
            raise ValueError('restore_token_changed')
        # Проверяем весь пакет до первой записи или внешней мутации.
        fresh = {}
        for item in execution_items:
            rid = item['reminder_id']
            phase = state['items'][rid]['phase']
            verify_parent(native, item)
            full_list(native, item, rid)
            hp, _ = local_progress(hub, item, restore)
            if restore:
                validate_task_set(hp, item['before_texts'])
                if phase not in PHASES or not state['approved']:
                    raise ValueError('restore_requires_approved_cancel')
                if phase not in {'restoring', 'restored'} and hp.texts != item['after_texts']:
                    raise ValueError('hub_snapshot_conflict')
            elif phase in {'restoring', 'restored'}:
                raise ValueError('cancellation_already_restoring')
            remote = native_status(native, path, sha, item)
            if not same_fields(remote['snapshot'], item['remote']):
                raise ValueError('remote_snapshot_changed')
            if restore:
                expected = rp['items'][rid]['remote']
                if remote['state'] == 'deleted' and remote != expected:
                    raise ValueError('restore_remote_changed')
                if remote['state'] == 'active' and expected['state'] == 'deleted' and phase not in {'restoring', 'restored'}:
                    raise ValueError('external_restore_requires_review')
                if expected['state'] == 'active' and remote != expected:
                    raise ValueError('rollback_active_remote_changed')
                if remote['state'] == 'active' and state['items'][rid].get('restored_snapshot') and remote != state['items'][rid]['restored_snapshot']:
                    raise ValueError('restored_remote_changed')
            else:
                if remote['state'] == 'active' and (phase not in {'prepared', 'deleting'} or remote['snapshot'] != item['remote']):
                    raise ValueError('remote_version_changed')
                if remote['state'] == 'deleted' and phase == 'prepared':
                    raise ValueError('unexpected_remote_deleted')
                if remote['state'] == 'deleted' and state['items'][rid].get('deleted_snapshot') and remote != state['items'][rid]['deleted_snapshot']:
                    raise ValueError('deleted_remote_changed')
            fresh[rid] = remote
        state['approved'] = True
        if restore:
            state['restore_token'] = restore_token
        durable_json(path.with_name('state.json'), state)
        for item in execution_items:
            rid = item['reminder_id']
            progress = state['items'][rid]
            remote = fresh[rid]
            terminal = 'restored' if restore else 'committed'
            if progress['phase'] == terminal:
                continue
            progress['phase'] = 'restoring' if restore else 'deleting'
            durable_json(path.with_name('state.json'), state)
            # Повторная проверка родителя и всего списка непосредственно перед действием.
            verify_parent(native, item)
            full_list(native, item, rid)
            if remote['state'] == ('deleted' if restore else 'active'):
                native.call('hub_restore_reminder' if restore else 'hub_cancel_reminder',
                            dict(plan=str(path), plan_sha256=sha, id=rid, version=remote['version'],
                                 **({'restore_plan': str(restore_path_for(path, restore_token)), 'restore_sha256': restore_token} if restore else {})))
            remote = native_status(native, path, sha, item)
            if remote['state'] != ('active' if restore else 'deleted') or not same_fields(remote['snapshot'], item['remote']):
                raise ValueError('native_mutation_readback_failed')
            progress['restored_snapshot' if restore else 'deleted_snapshot'] = remote
            if not restore:
                progress['phase'] = 'remote_deleted'
            durable_json(path.with_name('state.json'), state)
            hp, _ = local_progress(hub, item, restore)
            write_texts(hp, item, restore)
            if not restore:
                progress['phase'] = 'hub_cancelled'
            durable_json(path.with_name('state.json'), state)
            actual = current_config(hub, config, execution_plan, sha, allow_restored=restore)
            link = copy.deepcopy(item['link']) if restore else cancelled_link(item, plan, sha)
            actual['projects'][item['project_id']]['tasks'][item['task_id']] = link
            durable_json(hub / 'ai/reminders-sync.json', actual)
            config.clear()
            config.update(copy.deepcopy(actual))
            if sync.HubProject(hub, item['project_id']).texts != (item['before_texts'] if restore else item['after_texts']):
                raise ValueError('hub_readback_failed')
            final = native_status(native, path, sha, item)
            if final != remote:
                raise ValueError('remote_changed_before_commit')
            progress['phase'] = terminal
            durable_json(path.with_name('state.json'), state)
        return dict(ok=True, operation_id=plan['operation_id'], state=terminal, path=str(path), sha256=sha)


def status(hub, path, sha, config, native):
    with locked(hub) as hub:
        path, plan = read_plan(hub, path, sha)
        if plan.get('purpose') == 'project_list_verification': raise ValueError('verification_command_required')
        state = read_state(path, plan, sha)
        if historical_module().selected(config, plan):
            return historical_module().status(coordinator(),hub,path,sha,config,native,plan,state)
        current_config(hub, config, plan, sha, allow_restored=all(p['phase'] == 'restored' for p in state['items'].values()), terminal=all(p['phase'] in {'committed', 'restored'} for p in state['items'].values()), terminal_phases=state['items'] if all(p['phase'] in {'committed', 'restored'} for p in state['items'].values()) else None)
        for item in plan['items']:
            progress = state['items'][item['reminder_id']]
            if progress['phase'] in {'committed', 'restored'}:
                verify_parent(native, item)
                remote = native_status(native, path, sha, item)
                if remote != progress.get('deleted_snapshot' if progress['phase'] == 'committed' else 'restored_snapshot'): raise ValueError('terminal_snapshot_changed')
        items = [dict(project_id=i['project_id'], task_id=i['task_id'], phase=state['items'][i['reminder_id']]['phase'], **native_status(native, path, sha, i)) for i in plan['items']]
        return dict(ok=True, operation_id=plan['operation_id'], items=items)


def verify_cancelled_link(hub, row, link, binding, native, return_status=False, *, read_context=None):
    hub = canonical(hub)
    receipt = link.get('cancellation', {})
    operation = valid_uuid(receipt.get('operation_id'))
    sha = receipt.get('plan_sha256')
    path, plan = read_plan(hub, hub / 'ai/reminders-cancellations' / operation / 'plan.json', sha, require_active=False)
    state = read_state(path, plan, sha)
    matches = [i for i in plan['items'] if i['project_id'] == row.get('project_id') and i['task_id'] == row.get('task_id')]
    if len(matches) != 1:
        raise ValueError('invalid_cancelled_link')
    item = matches[0]
    config = json.loads(canonical(hub / 'ai/reminders-sync.json').read_text())
    if canonical(item['project_path']) != sync.task_project_path(hub, item['project_id'], config):
        raise ValueError('project_path_changed')
    if config['projects'].get(item['project_id']) != binding: raise ValueError('binding_argument_stale')
    if plan['version']==1 and binding.get('historical_binding_migration'):
        historical_module().load(coordinator(), hub, config, item, plan, sha)
    elif not terminal_allowlist_matches(hub, config, plan, guard_bindings(config, [item], hub)):
        raise ValueError('allowlist_checksum_mismatch')
    if item['project_id'] in sync.migration_pending(hub, config): raise ValueError('migration_recovery_required')
    if row.get('status') != 'dropped' or link != cancelled_link(item, plan, sha) or state['items'][item['reminder_id']]['phase'] != 'committed' or cancelled_block(hub, item) is None:
        raise ValueError('invalid_cancelled_link')
    cleanup = sync.cleanup_module() if hasattr(sync, 'cleanup_module') else None
    if cleanup is None:
        spec = importlib.util.spec_from_file_location('cancel_old_list_cleanup', Path(__file__).with_name('reminders_old_list_cleanup.py'))
        cleanup = importlib.util.module_from_spec(spec); spec.loader.exec_module(cleanup)
    if cleanup.restoration_forfeited_for_binding(hub, binding, item['reminder_id'], native, **(dict(read_context=read_context) if read_context is not None else {})):
        return True
    remote = native_status(native, path, sha, item)
    if remote['state'] != 'deleted':
        raise ValueError('external_restore_requires_review')
    if remote != state['items'][item['reminder_id']].get('deleted_snapshot'):
        raise ValueError('deleted_remote_changed')
    return remote if return_status else True


def verify_forfeiture_proof(hub, proof):
    """Validate the original committed cancellation evidence without querying deleted-list SDK state."""
    hub = canonical(hub)
    operation = valid_uuid(proof.get('operation_id'))
    sha = proof.get('plan_sha256')
    rid = valid_uuid(proof.get('reminder_id'))
    if not operation or not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{64}', sha) or not rid:
        raise ValueError('forfeiture_source_proof_invalid')
    path, plan = read_plan(hub, hub / 'ai/reminders-cancellations' / operation / 'plan.json', sha, require_active=False)
    state = read_state(path, plan, sha)
    matches = [i for i in plan['items'] if i.get('project_id') == proof.get('project_id')
               and i.get('task_id') == proof.get('task_id') and i.get('reminder_id') == rid]
    if len(matches) != 1 or state.get('items', {}).get(rid, {}).get('phase') != 'committed':
        raise ValueError('forfeiture_source_proof_uncommitted')
    item = matches[0]
    remote = proof.get('native_status')
    saved = state['items'][rid].get('deleted_snapshot')
    if (not isinstance(remote, dict) or remote.get('state') != 'deleted' or
            remote != saved or remote.get('version') != remote.get('snapshot', {}).get('version') or
            remote.get('snapshot', {}).get('id') != rid or
            remote.get('snapshot', {}).get('list_id') != item.get('list_id') or
            remote.get('snapshot', {}).get('list') != item.get('list_name')):
        raise ValueError('forfeiture_source_status_invalid')
    config = json.loads(canonical(hub / 'ai/reminders-sync.json').read_text())
    if canonical(item['project_path']) != sync.task_project_path(hub, item['project_id'], config):
        raise ValueError('forfeiture_source_project_changed')
    binding = config.get('projects', {}).get(item['project_id'])
    expected_link = cancelled_link(item, plan, sha)
    if (not isinstance(binding, dict) or binding.get('tasks', {}).get(item['task_id']) != expected_link or
            cancelled_block(hub, item) is None):
        raise ValueError('forfeiture_source_link_changed')
    return True


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('command', choices=['preview', 'apply', 'status', 'restore-preview', 'restore', 'verification-create', 'verification-prepare', 'verification-status', 'verification-delete', 'verification-restore-preview', 'verification-restore', 'verification-cleanup', 'verification-close', 'verification-witness', 'verification-pin'])
    cli.add_argument('--approve', action='store_true')
    cli.add_argument('--independent-review-accepted', action='store_true')
    cli.add_argument('--expected-journal-sha256')
    cli.add_argument('--expected-config-sha256')
    cli.add_argument('--expected-witness-sha256')
    cli.add_argument('--operation')
    cli.add_argument('--migration-plan')
    cli.add_argument('--migration-sha256')
    cli.add_argument('--hub', required=True)
    cli.add_argument('--target', action='append', help='project-id:task-id')
    cli.add_argument('--plan')
    cli.add_argument('--sha256')
    cli.add_argument('--restore-token')
    cli.add_argument('--expected-uuid')
    cli.add_argument('--concurrency-policy', choices=['strict', 'no_concurrent_edits'])
    args = cli.parse_args()
    try:
        hub = canonical(Path(args.hub).absolute())
        config = sync.load_config(hub)
        native = sync.Native(config)
        if args.command.startswith('verification-'):
            import types
            coordinator = types.SimpleNamespace(**globals())
            v = verification_module()
            native = sync.Native(dict(config, standard_allowlist_file=str(hub / 'ai/reminders-standard-allowlist.json')))
            action = args.command.removeprefix('verification-')
            if action == 'witness': result = v.witness(coordinator, hub, args.plan, args.sha256, args.expected_journal_sha256, args.approve, args.independent_review_accepted)
            elif action == 'pin': result = v.pin(coordinator, hub, args.expected_config_sha256, args.expected_witness_sha256, args.approve)
            elif action == 'create': result = v.bootstrap(coordinator, hub, config, native, args.operation, args.migration_plan, args.migration_sha256, args.approve)
            elif action == 'prepare': result = v.prepare(coordinator, hub, config, native, args.operation, args.approve)
            elif action == 'close': result = v.close(coordinator, hub, args.plan, args.sha256, config, native, args.approve)
            else: result = v.step(coordinator, hub, args.plan, args.sha256, config, native, action, args.approve, args.restore_token)
        elif args.command == 'preview':
            result = preview(hub, config, [tuple(s.split(':', 1)) for s in args.target or []], native, args.expected_uuid, args.concurrency_policy)
        elif args.command in {'apply', 'restore'}:
            result = execute(hub, args.plan, args.sha256, config, native, args.command == 'restore', args.restore_token)
        else:
            result = (status if args.command == 'status' else restore_preview)(hub, args.plan, args.sha256, config, native)
        print(encoded(result), end='')
        return 0
    except Exception as error:
        print(encoded({'ok': False, 'error': str(error)}), end='')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
