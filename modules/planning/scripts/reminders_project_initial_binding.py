"""Prepare and apply a journaled first binding for an unbound Hub project."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
import re
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path


def valid_uuid(value):
    try:
        return isinstance(value, str) and str(uuid.UUID(value)).upper() == value.upper()
    except (ValueError, TypeError, AttributeError):
        return False


def resolve_group_key(primary, groups, explicit=None):
    """Resolve a project's editorial group to its approved top-level app group."""
    if primary in (None, 'none'):
        if explicit is None:
            raise ValueError('unassigned_project_group')
        if explicit not in groups or groups[explicit].get('parent') is not None:
            raise ValueError('invalid_archiproject')
        return explicit
    current = primary
    seen = set()
    while current is not None:
        if current in seen:
            raise ValueError('invalid_archiproject')
        if current not in groups:
            raise ValueError('invalid_archiproject')
        seen.add(current)
        parent = groups[current].get('parent')
        if parent is None:
            return current
        current = parent
    raise ValueError('invalid_archiproject')


def validate_destination(lists, groups, list_id, list_name, group_id):
    """Validate a new-list destination or adoption of the exact existing list."""
    if not isinstance(list_name, str) or not list_name.strip():
        raise ValueError('invalid_list_name')
    if not isinstance(lists, list) or not isinstance(groups, list):
        raise ValueError('invalid_account_metadata')
    if len({row.get('id') for row in lists}) != len(lists) or len({row.get('name') for row in lists}) != len(lists):
        raise ValueError('ambiguous_list_metadata')
    group_matches = [row for row in groups if row.get('id') == group_id]
    if len(group_matches) != 1 or not valid_uuid(group_matches[0].get('account_id')):
        raise ValueError('destination_group_mismatch')
    account_id = group_matches[0]['account_id']
    matching_names = [row for row in lists if row.get('name') == list_name]
    if list_id is None:
        if matching_names:
            raise ValueError('destination_name_conflict')
        return {'mode': 'create', 'account_id': account_id}
    matches = [row for row in lists if row.get('id') == list_id]
    if len(matches) != 1:
        raise ValueError('destination_identity_mismatch')
    row = matches[0]
    if (row.get('name') != list_name or row.get('group_id') != group_id or
            row.get('account_id') != account_id or row.get('shared') is not False or
            matching_names != [row]):
        raise ValueError('destination_identity_mismatch')
    return {'mode': 'adopt', 'list': copy.deepcopy(row), 'account_id': account_id}


def validate_task_sources(hub_tasks, existing_reminders):
    """Only one side may contain unbound tasks when establishing a first link."""
    if not isinstance(hub_tasks, dict) or not isinstance(existing_reminders, dict):
        raise ValueError('invalid_task_snapshot')
    if hub_tasks and existing_reminders:
        raise ValueError('task_sources_overlap_requires_review')
    if existing_reminders:
        return 'import_existing'
    if hub_tasks:
        return 'publish_hub'
    return 'empty'


def active_task_rows(rows, terminal_statuses):
    """Select Hub tasks eligible for first publication; terminal records stay in Hub."""
    if not isinstance(rows, dict) or not isinstance(terminal_statuses, (set, frozenset)):
        raise ValueError('invalid_task_snapshot')
    selected = {}
    for task_id, row in rows.items():
        if not isinstance(row, dict) or not isinstance(row.get('status'), str):
            raise ValueError('invalid_task_snapshot')
        if row['status'] not in terminal_statuses:
            selected[task_id] = row
    return selected


def initial_binding_document(config, *, project_id, list_metadata, group_key, label, plan_sha,
                             created_by_operation=False):
    """Return the config after binding an unbound active project to one exact list."""
    if not isinstance(project_id, str) or not re.fullmatch(r'[a-z0-9-]+', project_id):
        raise ValueError('invalid_project_id')
    if project_id in config.get('projects', {}):
        raise ValueError('project_already_bound')
    structure = config.get('structure')
    if not isinstance(structure, dict):
        raise ValueError('structure_missing')
    if project_id in structure.get('projects', {}):
        raise ValueError('project_structure_already_bound')
    if not isinstance(group_key, str) or not group_key:
        raise ValueError('invalid_native_group')
    group_ids = [gid for gid, key in structure.get('native_groups', {}).items() if key == group_key]
    if len(group_ids) != 1:
        raise ValueError('native_group_mismatch')
    if not isinstance(label, str) or not label.strip():
        raise ValueError('invalid_list_name')
    if not isinstance(plan_sha, str) or not re.fullmatch(r'[0-9a-f]{64}', plan_sha):
        raise ValueError('invalid_plan_digest')
    if not isinstance(list_metadata, dict):
        raise ValueError('invalid_list_metadata')
    lid = list_metadata.get('id')
    account_id = list_metadata.get('account_id')
    if not valid_uuid(lid) or not valid_uuid(account_id):
        raise ValueError('invalid_list_identity')
    if list_metadata.get('name') != label:
        raise ValueError('list_name_mismatch')
    if list_metadata.get('group_id') != group_ids[0]:
        raise ValueError('native_group_mismatch')
    shared = list_metadata.get('shared')
    if shared is True or (not created_by_operation and shared is not False):
        raise ValueError('shared_list_not_supported')
    projects = config.get('projects', {})
    if any(binding.get('list_id') == lid for binding in projects.values()):
        raise ValueError('duplicate_list_binding')
    roles = structure.get('list_roles', {})
    if lid in roles:
        raise ValueError('list_role_already_bound')
    pending = config.get('project_list_migrations_pending', {})
    if pending.get(project_id) != plan_sha:
        raise ValueError('initial_binding_intent_missing')
    if project_id in config.get('project_initial_bindings_completed', {}):
        raise ValueError('initial_binding_already_completed')

    final = copy.deepcopy(config)
    final['projects'][project_id] = {
        'layout': 'project_list', 'parent_id': None,
        'list_id': lid, 'list_name': label, 'account_id': account_id,
        'native_group_id': group_ids[0], 'tasks': {}, 'history': {},
    }
    final['structure']['projects'][project_id] = {'group': group_key, 'list_id': lid}
    final['structure']['list_roles'][lid] = {'kind': 'project', 'project_id': project_id}
    final['project_list_migrations_pending'].pop(project_id)
    if not final['project_list_migrations_pending']:
        final.pop('project_list_migrations_pending')
    final.setdefault('project_initial_bindings_completed', {})[project_id] = plan_sha
    return final


def load_module(name, path):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(name, None)
            raise
    return sys.modules[name]


def scope_metadata(value, list_name, group_id):
    if not isinstance(value, dict):
        raise ValueError('invalid_account_metadata')
    lists = value.get('lists')
    groups = value.get('groups')
    if not isinstance(lists, list) or not isinstance(groups, list):
        raise ValueError('invalid_account_metadata')
    if any(not isinstance(row, dict) or row.get('name') != list_name for row in lists):
        raise ValueError('unscoped_native_response')
    if len(lists) > 1 or any(not row.get('id') or not row.get('account_id') for row in lists):
        raise ValueError('invalid_account_metadata')
    if len(groups) != 1 or groups[0].get('id') != group_id or not groups[0].get('name') or not groups[0].get('account_id'):
        raise ValueError('unscoped_native_response')
    return copy.deepcopy(value)


def modules():
    scripts = Path(__file__).resolve().parent
    return (load_module('initial_binding_sync', scripts / 'reminders_sync.py'),
            load_module('initial_binding_project_lists', scripts / 'reminders_project_lists.py'),
            load_module('initial_binding_archiprojects', scripts / 'archiprojects.py'))


class ScopedNative:
    """Limit native calls to one list name, one group name and one group UUID."""
    def __init__(self, config, list_name, group_id, group_name, account_id=None):
        import tempfile
        sync, _, _ = modules()
        self.config = config
        self.list_name = list_name
        self.group_id = group_id
        self.group_name = group_name
        self.account_id = account_id
        self.temp = tempfile.TemporaryDirectory(prefix='hub-reminders-scope-', dir='/private/tmp')
        root = Path(self.temp.name)
        sync.safe_path(root)
        self.list_allowlist = root / 'lists.json'
        self.group_allowlist = root / 'groups.json'
        self.group_id_allowlist = root / 'group-ids.json'
        self.list_allowlist.write_text(encoded({'names': [list_name]}))
        self.group_allowlist.write_text(encoded({'names': [group_name]}))
        self.group_id_allowlist.write_text(encoded({'groups': {group_id: group_name}}))
        self.list_ids = set()
        self.reminder_ids = set()

    def call(self, tool, args):
        allowed = {'list_lists', 'find_reminders', 'get_reminder', 'manage_list', 'update_reminder'}
        if tool not in allowed:
            raise ValueError('initial_binding_native_operation_not_allowed')
        if tool == 'find_reminders':
            if args.get('list') not in self.list_ids or args.get('include_completed') is not True:
                raise ValueError('initial_binding_native_scope_mismatch')
        if tool == 'get_reminder' and args.get('id') not in self.reminder_ids:
            raise ValueError('initial_binding_native_scope_mismatch')
        if tool == 'manage_list':
            action = args.get('action')
            if action == 'create':
                if args.get('list') != self.list_name or args.get('expected_account_id') != self.account_id:
                    raise ValueError('initial_binding_native_scope_mismatch')
            elif action == 'update':
                if (args.get('list') not in self.list_ids or args.get('group') != self.group_id or
                        args.get('expected_group_id') is not None):
                    raise ValueError('initial_binding_native_scope_mismatch')
            else:
                raise ValueError('initial_binding_native_operation_not_allowed')
        if tool in {'update_reminder'}:
            raise ValueError('initial_binding_native_operation_not_allowed')
        sync, _, _ = modules()
        env = dict(os.environ,
                   HUB_REMINDERS_ALLOWED_LISTS_FILE=str(self.list_allowlist),
                   HUB_REMINDERS_ALLOWED_GROUPS_FILE=str(self.group_allowlist),
                   HUB_REMINDERS_ALLOWED_GROUP_IDS_FILE=str(self.group_id_allowlist))
        binary = self.config['binary']
        runner = lambda name, values: __import__('subprocess').run(
            [binary, 'call', name, json.dumps(values)], env=env, capture_output=True, text=True, timeout=50)
        reads = sync.reads_module()
        result = reads.call(binary, env, tool, args, runner) if reads else runner(tool, args)
        if result.returncode:
            raise RuntimeError('initial_binding_native_failed: ' + result.stderr[:500])
        raw = result.stdout
        value = json.loads(raw[raw.index('{'):])
        if value.get('error') or value.get('isError'):
            raise ValueError('initial_binding_native_error: ' + str(value)[:500])
        if tool == 'list_lists':
            scoped = scope_metadata(value, self.list_name, self.group_id)
            self.list_ids.update(row['id'] for row in scoped['lists'])
            return scoped
        if tool == 'find_reminders':
            reminders = value.get('reminders')
            if not isinstance(reminders, list) or value.get('more') or value.get('has_more') or len(reminders) >= 500:
                raise ValueError('incomplete_scoped_task_snapshot')
            if any(row.get('list_id') != args['list'] for row in reminders):
                raise ValueError('unscoped_native_response')
            self.reminder_ids.update(row['id'] for row in reminders if row.get('id'))
        if tool == 'get_reminder' and value.get('list_id') not in self.list_ids:
            raise ValueError('unscoped_native_response')
        if tool == 'manage_list' and args.get('action') == 'create':
            if not valid_uuid(value.get('id')):
                raise ValueError('initial_binding_invalid_created_list_id')
        return value

    def get(self, reminder_id, list_id):
        value = self.call('get_reminder', {'id': reminder_id})
        if value.get('list_id') != list_id:
            raise ValueError('reminder_binding_mismatch')
        return value


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n'


def sha(value):
    data = value.encode('utf-8') if isinstance(value, str) else value
    return hashlib.sha256(data).hexdigest()


def permission_guard(permission, label):
    before = permission.get('before') or permission.get('original')
    names = json.loads(before).get('names', [])
    if label not in names or label in permission.get('added', []):
        raise ValueError('list_permission_required')
    return {'list_name': label,
            'original_sha256': sha(permission['original']),
            'standard_sha256': sha(before)}


def remote_task_snapshot(rows):
    return [dict(id=rid, fingerprint=sha(encoded(row)))
            for rid, row in sorted(rows.items())]


def atomic_write(path, data, exclusive=False):
    sync, _, _ = modules()
    path = sync.safe_path(Path(path))
    if exclusive:
        with path.open('x', encoding='utf-8') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        return
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = handle.name
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def locked(hub, project_lists):
    with project_lists.locked(Path(hub)):
        yield


def read_project(hub, project_id, config, explicit_group=None):
    sync, _, arch = modules()
    registered = sync.registered(hub)
    if project_id not in registered:
        raise ValueError('unregistered_or_inactive_project')
    cards = [card for card in arch.read_cards(hub) if card['project_id'] == project_id]
    if len(cards) != 1:
        raise ValueError('project_card_missing_or_ambiguous')
    groups = arch.parse_groups(Path(hub) / 'ai/archiprojects.md')
    group_key = resolve_group_key(cards[0]['primary_archiproject'], groups, explicit_group)
    native_groups = config.get('structure', {}).get('native_groups', {})
    matches = [gid for gid, key in native_groups.items() if key == group_key]
    if len(matches) != 1:
        raise ValueError('native_group_mismatch')
    group_id = matches[0]
    allowed_file = config['structure'].get('group_ids_allowlist_file')
    if not allowed_file:
        raise ValueError('native_group_allowlist_missing')
    allowed_path = sync.safe_path(Path(allowed_file))
    if not allowed_path.is_file():
        raise ValueError('unsafe_group_allowlist')
    allowed = json.loads(allowed_path.read_text()).get('groups', {})
    if group_id not in allowed:
        raise ValueError('native_group_not_allowed')
    label = sync.project_label(hub, project_id, {})
    return registered[project_id], cards[0], groups, group_key, group_id, label


def plan_path(hub, operation):
    sync, _, _ = modules()
    if not isinstance(operation, str) or not re.fullmatch(r'[0-9a-f-]{36}', operation):
        raise ValueError('unsafe_operation_id')
    root = sync.safe_path(Path(hub) / 'ai/reminders-project-bindings')
    return sync.safe_path(root / operation / 'plan.json')


def write_plan(hub, plan):
    sync, _, _ = modules()
    root = sync.safe_path(Path(hub) / 'ai/reminders-project-bindings')
    root.mkdir(exist_ok=True)
    root = sync.safe_path(root)
    operation = str(uuid.uuid4())
    folder = sync.safe_path(root / operation)
    folder.mkdir()
    folder = sync.safe_path(folder)
    plan = dict(plan, hub=str(hub), operation=operation)
    raw = encoded(plan)
    atomic_write(folder / 'plan.json', raw, exclusive=True)
    list_id = plan.get('destination', {}).get('id') if plan.get('mode') == 'adopt' else None
    atomic_write(folder / 'state.json', encoded({'sha256': sha(raw), 'phase': 'preview',
                                                 'steps': {}, 'list_id': list_id}), exclusive=True)
    return {'plan': str(folder / 'plan.json'), 'sha256': sha(raw), 'operation': operation}


def read_plan(path, digest):
    sync, _, _ = modules()
    path = sync.safe_path(Path(path))
    raw = path.read_text()
    if sha(raw) != digest:
        raise ValueError('plan_sha256_mismatch')
    plan = json.loads(raw)
    hub = sync.safe_path(Path(plan['hub']))
    if path != plan_path(hub, plan['operation']):
        raise ValueError('unsafe_plan_location')
    if plan.get('kind') != 'initial_binding':
        raise ValueError('wrong_plan_kind')
    state = json.loads((path.parent / 'state.json').read_text())
    if state.get('sha256') != digest:
        raise ValueError('state_sha256_mismatch')
    return path, plan, state


def preview(hub, project_id, explicit_group=None, list_id=None, native=None):
    sync, project_lists, _ = modules()
    hub = sync.safe_path(Path(hub))
    with locked(hub, project_lists):
        config, raw = project_lists.config_read(hub)
        if project_id in config.get('projects', {}):
            raise ValueError('project_already_bound')
        if project_id in config.get('structure', {}).get('projects', {}):
            raise ValueError('project_structure_already_bound')
        project_path, card, groups, group_key, group_id, label = read_project(hub, project_id, config, explicit_group)
        if project_lists.pending_projects(hub, config):
            raise ValueError('another_project_list_operation_pending')
        permission = project_lists.permission_data(hub, label)
        permission_summary = permission_guard(permission, label)
        group_name = allowed_group_name(config, group_id)
        if not group_name:
            raise ValueError('native_group_not_allowed')
        native = native or ScopedNative(config, label, group_id, group_name)
        project_lists.reset_cache(native)
        meta = scope_metadata(native.call('list_lists', {}), label, group_id)
        group = next((row for row in meta['groups'] if row['id'] == group_id), None)
        if group is None or not allowed_group_id(config, group_id):
            raise ValueError('destination_group_metadata_mismatch')
        destination = validate_destination(meta['lists'], meta['groups'], list_id, label, group_id)
        source_rows = {}
        if destination['mode'] == 'adopt':
            source_rows = project_lists.rows(native, list_id)
        hub_project = sync.HubProject(hub, project_id, project_path)
        task_rows = hub_project.rows()
        active_rows = active_task_rows(task_rows, sync.TERMINAL)
        task_route = validate_task_sources(active_rows, source_rows)
        canonical = project_lists.canonical(hub, project_id)
        card_path = Path(card['path'])
        guards = {
            str(card_path.relative_to(hub)): sha(card_path.read_bytes()),
            'ai/archiprojects.md': sha((hub / 'ai/archiprojects.md').read_bytes()),
            str(Path(config['structure']['group_ids_allowlist_file']).relative_to(hub)): sha(Path(config['structure']['group_ids_allowlist_file']).read_bytes()),
        }
        task_snapshot = [dict(task_id=tid, title=row['title'], status=row['status'], kind=row['kind'],
                              planned_day=row['planned_day'], deadline=row['deadline'])
                         for tid, row in sorted(active_rows.items())]
        source_snapshot = remote_task_snapshot(source_rows)
        plan = dict(kind='initial_binding', project=project_id, label=label, group_key=group_key,
                    group_id=group_id, group_snapshot=group_identity(group), mode=destination['mode'],
                    destination=destination.get('list'), account_id=destination['account_id'],
                    config_sha256=sha(raw), canonical=canonical, guards=guards,
                    permission=permission_summary, hub_task_total=len(task_rows),
                    terminal_hub_task_total=len(task_rows) - len(active_rows),
                    task_snapshot=task_snapshot, source_snapshot=source_snapshot,
                    task_route=task_route)
        result = write_plan(hub, plan)
        result.update(project=project_id, list_name=label, group=group_key,
                      mode=destination['mode'], hub_tasks=len(task_snapshot),
                      terminal_hub_tasks=len(task_rows) - len(active_rows),
                      active_hub_tasks=len(active_rows),
                      existing_reminders=len(source_snapshot), task_route=task_route,
                      changes=[{'action': 'bind_project_to_list'},
                               {'action': 'sync_tasks_after_binding', 'route': task_route}])
        return result


def allowed_group_id(config, group_id):
    return bool(allowed_group_name(config, group_id))


def allowed_group_name(config, group_id):
    sync, _, _ = modules()
    path = sync.safe_path(Path(config['structure']['group_ids_allowlist_file']))
    allowed = json.loads(path.read_text()).get('groups', {})
    value = allowed.get(group_id)
    return value if isinstance(value, str) and value else None


def group_identity(row):
    """Keep only stable ownership fields; list membership may change during creation."""
    if not isinstance(row, dict):
        raise ValueError('invalid_native_group_metadata')
    identity = {key: row.get(key) for key in ('id', 'name', 'account_id')}
    if not valid_uuid(identity['id']) or not valid_uuid(identity['account_id']) or not identity['name']:
        raise ValueError('invalid_native_group_metadata')
    return identity


def intended_config(config, project_id, digest):
    result = copy.deepcopy(config)
    result.setdefault('project_list_migrations_pending', {})[project_id] = digest
    return result


def verify_plan_guards(hub, plan, digest, state):
    sync, project_lists, _ = modules()
    config, raw = project_lists.config_read(hub)
    intended = encoded(intended_config(config, plan['project'], digest))
    allowed_hashes = {plan['config_sha256'], sha(intended)}
    if state.get('final_config_sha'):
        allowed_hashes.add(state['final_config_sha'])
    if sha(raw) not in allowed_hashes:
        raise ValueError('initial_binding_config_changed')
    if project_lists.canonical(hub, plan['project']) != plan['canonical']:
        raise ValueError('initial_binding_canonical_changed')
    for relative, expected in plan['guards'].items():
        target = sync.safe_path(Path(hub) / relative)
        actual = sha(target.read_bytes()) if target.exists() else None
        if actual != expected:
            raise ValueError('initial_binding_route_changed')
    current_permission = project_lists.permission_data(hub, plan['label'])
    if permission_guard(current_permission, plan['label']) != plan['permission']:
        raise ValueError('initial_binding_permission_changed')
    clean = copy.deepcopy(config)
    if clean.get('project_list_migrations_pending', {}).get(plan['project']) == digest:
        clean['project_list_migrations_pending'].pop(plan['project'])
        if not clean['project_list_migrations_pending']:
            clean.pop('project_list_migrations_pending')
    if plan['project'] in project_lists.pending_projects(hub, clean, ignore_operation=plan['operation']):
        raise ValueError('initial_binding_other_operation_pending')
    if plan['project'] in config.get('projects', {}) and state.get('phase') not in {'binding_complete', 'complete'}:
        raise ValueError('initial_binding_project_already_bound')
    return config, raw


def verify_remote(plan, state, native, config):
    _, project_lists, _ = modules()
    project_lists.reset_cache(native)
    meta = scope_metadata(native.call('list_lists', {}), plan['label'], plan['group_id'])
    group = next((row for row in meta['groups'] if row.get('id') == plan['group_id']), None)
    if group is None or group_identity(group) != group_identity(plan['group_snapshot']):
        raise ValueError('initial_binding_group_changed')
    if state.get('list_id'):
        matches = [row for row in meta['lists'] if row.get('id') == state['list_id']]
        if len(matches) != 1:
            raise ValueError('initial_binding_destination_changed')
        row = matches[0]
        allowed_group_ids = {plan['group_id']}
        if plan['mode'] == 'create' and not state.get('group_done'):
            allowed_group_ids.add(None)
        shared = row.get('shared')
        sharing_ok = shared is False or (plan['mode'] == 'create' and shared is None)
        if (row.get('name') != plan['label'] or row.get('account_id') != plan['account_id'] or
                row.get('group_id') not in allowed_group_ids or not sharing_ok):
            raise ValueError('initial_binding_destination_changed')
        matching_names = [item for item in meta['lists'] if item.get('name') == plan['label']]
        if matching_names != [row]:
            raise ValueError('initial_binding_destination_changed')
        if plan['mode'] == 'adopt' and row != plan['destination']:
            raise ValueError('initial_binding_destination_changed')
        destination = {'mode': 'adopt', 'list': copy.deepcopy(row), 'account_id': plan['account_id']}
        current_rows = project_lists.rows(native, state['list_id'])
        if remote_task_snapshot(current_rows) != plan['source_snapshot']:
            raise ValueError('initial_binding_source_tasks_changed')
    else:
        if plan['mode'] != 'create':
            raise ValueError('initial_binding_destination_id_missing')
        if any(row.get('name') == plan['label'] for row in meta['lists']):
            raise ValueError('initial_binding_destination_appeared')
        destination = {'mode': 'create', 'account_id': plan['account_id']}
    return meta, group, destination


def recover_unknown_create(plan, state, native, state_path):
    """Recover a pending create only from one exact, empty list in the expected account."""
    _, project_lists, _ = modules()
    meta = scope_metadata(native.call('list_lists', {}), plan['label'], plan['group_id'])
    matches = [row for row in meta['lists'] if row.get('name') == plan['label']]
    if not matches:
        raise ValueError('initial_binding_create_outcome_unknown')
    if len(matches) != 1:
        raise ValueError('initial_binding_recovery_ambiguous_name')
    row = matches[0]
    if (not valid_uuid(row.get('id')) or row.get('account_id') != plan['account_id'] or
            row.get('group_id') not in (None, plan['group_id']) or
            row.get('shared') not in (None, False)):
        raise ValueError('initial_binding_recovery_identity_mismatch')
    if project_lists.rows(native, row['id']):
        raise ValueError('initial_binding_recovery_list_not_empty')
    state.update(list_id=row['id'], create_pending=False, recovered_create_uuid=row['id'], phase='created')
    if row.get('shared') is None:
        state['sharing_metadata'] = 'not_exposed_by_native_metadata'
    atomic_write(Path(state_path), encoded(state))
    return row


def apply_binding(path, digest, approve=False, native=None):
    if not approve:
        raise ValueError('explicit_approval_required')
    path, plan, state = read_plan(path, digest)
    hub = Path(plan['hub']).resolve()
    sync, project_lists, _ = modules()
    with locked(hub, project_lists):
        config, raw = verify_plan_guards(hub, plan, digest, state)
        if state.get('phase') == 'complete':
            return {'phase': 'complete', 'project': plan['project'], 'list_id': state['list_id']}
        if state.get('phase') == 'binding_complete':
            return {'phase': 'binding_complete', 'project': plan['project'],
                    'list_id': state['list_id'], 'task_sync_required': True}
        effective = dict(config, standard_allowlist_file=str(hub / 'ai/reminders-standard-allowlist.json'))
        native = native or ScopedNative(effective, plan['label'], plan['group_id'],
                                        plan['group_snapshot']['name'], plan['account_id'])
        if state.get('create_pending') and not state.get('list_id'):
            recover_unknown_create(plan, state, native, path.parent / 'state.json')
        meta, group, destination = verify_remote(plan, state, native, config)
        if state.get('phase') == 'committing' and sha(raw) == state.get('final_config_sha'):
            state.update(phase='binding_complete')
            save = lambda: atomic_write(path.parent / 'state.json', encoded(state))
            save()
            return {'phase': 'binding_complete', 'project': plan['project'],
                    'list_id': state['list_id'], 'task_sync_required': True}
        def save():
            atomic_write(path.parent / 'state.json', encoded(state))
        intended = intended_config(config, plan['project'], digest)
        intended_raw = encoded(intended)
        if state['phase'] == 'preview':
            state.update(phase='intent', intent_recorded=True)
            save()
        if state['phase'] == 'intent':
            if sha(raw) == plan['config_sha256']:
                project_lists.durable(hub / 'ai/reminders-sync.json', intended_raw)
                if (hub / 'ai/reminders-sync.json').read_text() != intended_raw:
                    raise ValueError('initial_binding_intent_readback_failed')
                config, raw = project_lists.config_read(hub)
            elif raw != intended_raw:
                raise ValueError('initial_binding_config_cas_conflict')
            state.update(phase='intent_written')
            save()
        if not state.get('list_id'):
            if meta.get('guarded_list_creation') is not True:
                raise ValueError('creation_account_unverifiable')
            state.update(phase='creating', create_pending=True)
            save()
            created = native.call('manage_list', dict(action='create', list=plan['label'],
                                                       expected_account_id=plan['account_id']))
            if not valid_uuid(created.get('id')):
                raise ValueError('initial_binding_recovery_required')
            state['list_id'] = created['id']
            state['create_pending'] = False
            save()
        meta, group, destination = verify_remote(plan, state, native, json.loads(intended_raw))
        row = next((item for item in meta['lists'] if item.get('id') == state['list_id']), None)
        if row is None:
            raise ValueError('initial_binding_destination_missing')
        if row.get('group_id') is None:
            state.update(phase='grouping', group_pending=True)
            save()
            native.call('manage_list', dict(action='update', list=state['list_id'],
                                             group=plan['group_id'], expected_group_id=None))
            meta, group, destination = verify_remote(plan, state, native, json.loads(intended_raw))
            row = next((item for item in meta['lists'] if item.get('id') == state['list_id']), None)
        if row is None or row.get('group_id') != plan['group_id']:
            raise ValueError('initial_binding_group_readback_failed')
        if row.get('shared') is None:
            state['sharing_metadata'] = 'not_exposed_by_native_metadata'
        state['group_done'] = True
        save()
        final = initial_binding_document(json.loads(intended_raw), project_id=plan['project'],
                                         list_metadata=row, group_key=plan['group_key'],
                                         label=plan['label'], plan_sha=digest,
                                         created_by_operation=plan['mode'] == 'create')
        final.setdefault('project_list_migrations_completed', {})[plan['project']] = digest
        sync.validate_binding_ids(final)
        final_raw = encoded(final)
        current_raw = (hub / 'ai/reminders-sync.json').read_text()
        if current_raw != intended_raw:
            raise ValueError('initial_binding_config_cas_conflict')
        state.update(phase='committing', final_config_sha=sha(final_raw))
        save()
        project_lists.durable(hub / 'ai/reminders-sync.json', final_raw)
        if (hub / 'ai/reminders-sync.json').read_text() != final_raw:
            raise ValueError('initial_binding_config_readback_failed')
        verify_remote(plan, state, native, final)
        state.update(phase='binding_complete', final_config_sha=sha(final_raw))
        save()
        return {'phase': state['phase'], 'project': plan['project'],
                'list_id': state['list_id'], 'task_sync_required': True}


def adopt_exact_uuid(path, digest, list_id, native=None):
    """Recover an unknown create result only from one exact, empty native list."""
    path, plan, state = read_plan(path, digest)
    if not state.get('create_pending') or state.get('list_id'):
        raise ValueError('initial_binding_adopt_not_available')
    if not valid_uuid(list_id):
        raise ValueError('invalid_list_identity')
    hub = Path(plan['hub']).resolve()
    _, project_lists, _ = modules()
    with locked(hub, project_lists):
        config, _ = verify_plan_guards(hub, plan, digest, state)
        native = native or ScopedNative(dict(config, standard_allowlist_file=str(hub / 'ai/reminders-standard-allowlist.json')),
                                        plan['label'], plan['group_id'], plan['group_snapshot']['name'],
                                        plan['account_id'])
        project_lists.reset_cache(native)
        meta = scope_metadata(native.call('list_lists', {}), plan['label'], plan['group_id'])
        row = next((item for item in meta['lists'] if item.get('id') == list_id), None)
        if row is None or row.get('name') != plan['label'] or row.get('account_id') != plan['account_id']:
            raise ValueError('initial_binding_adopt_identity_mismatch')
        if row.get('group_id') not in (None, plan['group_id']) or row.get('shared') is not False:
            raise ValueError('initial_binding_adopt_identity_mismatch')
        if [item for item in meta['lists'] if item.get('name') == plan['label']] != [row]:
            raise ValueError('initial_binding_adopt_identity_mismatch')
        if project_lists.rows(native, list_id):
            raise ValueError('initial_binding_adopt_requires_empty_list')
        state['list_id'] = list_id
        state['create_pending'] = False
        state['adopted_uuid'] = list_id
        state['phase'] = 'created'
        atomic_write(path.parent / 'state.json', encoded(state))
        return {'phase': state['phase'], 'list_id': list_id, 'project': plan['project']}


def status(path, digest):
    _, plan, state = read_plan(path, digest)
    return {'phase': state['phase'], 'project': plan['project'],
            'list_id': state.get('list_id'), 'task_sync_required': state.get('phase') == 'binding_complete'}


def supersession_folder(hub, operation):
    sync, _, _ = modules()
    if not valid_uuid(operation):
        raise ValueError('invalid_supersession_operation')
    return sync.safe_path(Path(hub) / 'ai/reminders-binding-supersessions' / operation)


def supersession_marker(plan):
    return {
        'kind': 'initial_binding', 'operation': plan['new_operation'],
        'plan_sha256': plan['new_binding_plan_sha256'], 'list_id': plan['new_list_id'],
        'old_operation': plan['old_operation'], 'old_plan_sha256': plan['old_plan_sha256'],
    }


def matches_supersession_marker(old_state, plan):
    return bool(
        isinstance(old_state, dict) and old_state.get('phase') == 'complete' and
        old_state.get('sha256') == plan.get('old_plan_sha256') and
        old_state.get('list_id') == plan.get('old_list_id') and
        old_state.get('superseded_by') == supersession_marker(plan)
    )


def supersession_preview(binding_path, binding_digest, old_operation=None):
    path, binding_plan, binding_state = read_plan(binding_path, binding_digest)
    if binding_state.get('phase') not in {'binding_complete', 'complete'}:
        raise ValueError('supersession_binding_not_complete')
    hub = Path(binding_plan['hub']).resolve()
    sync, project_lists, _ = modules()
    with locked(hub, project_lists):
        config, raw = project_lists.config_read(hub)
        current = config.get('projects', {}).get(binding_plan['project'])
        baseline = config.get('structure', {}).get('projects', {}).get(binding_plan['project'])
        if (not isinstance(current, dict) or current.get('layout') != 'project_list' or
                current.get('list_id') != binding_state.get('list_id') or
                not isinstance(baseline, dict) or baseline.get('list_id') != binding_state.get('list_id') or
                config.get('project_list_migrations_completed', {}).get(binding_plan['project']) != binding_digest):
            raise ValueError('supersession_binding_config_mismatch')
        old_root = sync.safe_path(hub / 'ai/reminders-project-lists')
        candidates = []
        for plan_path in old_root.glob('*/plan.json'):
            try:
                old_raw = plan_path.read_bytes()
                old_plan = json.loads(old_raw)
                old_state_path = sync.safe_path(plan_path.parent / 'state.json')
                old_state_raw = old_state_path.read_bytes()
                old_state = json.loads(old_state_raw)
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                continue
            if (old_plan.get('kind') == 'empty_rebind' and
                    old_plan.get('project') == binding_plan['project'] and
                    old_state.get('phase') == 'complete' and
                    old_state.get('sha256') == sha(old_raw) and
                    config.get('project_list_migrations_completed', {}).get(binding_plan['project']) != sha(old_raw)):
                candidates.append((plan_path, old_raw, old_state_path, old_state_raw, old_plan, old_state))
        if old_operation is not None:
            candidates = [item for item in candidates if item[0].parent.name == old_operation]
        if len(candidates) != 1:
            raise ValueError('supersession_old_operation_not_unique')
        old_path, old_raw, old_state_path, old_state_raw, old_plan, old_state = candidates[0]
        if old_state.get('superseded_by'):
            raise ValueError('supersession_already_recorded')
        operation = str(uuid.uuid4())
        plan = {
            'kind': 'initial_binding_supersession', 'operation': operation,
            'hub': str(hub),
            'project': binding_plan['project'],
            'old_operation': old_path.parent.name, 'old_plan_sha256': sha(old_raw),
            'old_state_sha256': sha(old_state_raw), 'old_list_id': old_state.get('list_id'),
            'new_operation': binding_plan['operation'], 'new_binding_plan_sha256': binding_digest,
            'new_list_id': binding_state['list_id'], 'config_sha256': sha(raw),
        }
        folder = supersession_folder(hub, operation)
        folder.mkdir(parents=True)
        folder = sync.safe_path(folder)
        plan_raw = encoded(plan)
        atomic_write(folder / 'plan.json', plan_raw, exclusive=True)
        atomic_write(folder / 'state.json', encoded({'sha256': sha(plan_raw), 'phase': 'preview'}), exclusive=True)
        return {'plan': str(folder / 'plan.json'), 'sha256': sha(plan_raw),
                'project': plan['project'], 'old_operation': plan['old_operation'],
                'old_list_id': plan['old_list_id'], 'new_operation': plan['new_operation'],
                'new_list_id': plan['new_list_id'], 'phase': 'preview'}


def apply_supersession(path, digest, approve=False):
    if not approve:
        raise ValueError('explicit_approval_required')
    sync, project_lists, _ = modules()
    path = sync.safe_path(Path(path))
    raw = path.read_bytes()
    if sha(raw) != digest:
        raise ValueError('supersession_plan_sha256_mismatch')
    plan = json.loads(raw)
    hub = sync.safe_path(Path(plan['hub']))
    if (plan.get('kind') != 'initial_binding_supersession' or
            supersession_folder(hub, plan.get('operation')) != path.parent):
        raise ValueError('unsafe_supersession_plan')
    state_path = sync.safe_path(path.parent / 'state.json')
    state = json.loads(state_path.read_text())
    if state.get('sha256') != digest or state.get('phase') not in {'preview', 'complete'}:
        raise ValueError('supersession_state_mismatch')
    with locked(hub, project_lists):
        config, config_raw = project_lists.config_read(hub)
        if sha(config_raw) != plan['config_sha256']:
            raise ValueError('supersession_config_changed')
        new_plan_path = plan_path(hub, plan['new_operation'])
        new_raw = new_plan_path.read_bytes()
        new_plan = json.loads(new_raw)
        new_state = json.loads((new_plan_path.parent / 'state.json').read_text())
        if (sha(new_raw) != plan['new_binding_plan_sha256'] or
                new_plan.get('kind') != 'initial_binding' or new_plan.get('project') != plan['project'] or
                new_state.get('sha256') != plan['new_binding_plan_sha256'] or
                new_state.get('phase') not in {'binding_complete', 'complete'} or
                new_state.get('list_id') != plan['new_list_id'] or
                config.get('project_list_migrations_completed', {}).get(plan['project']) != plan['new_binding_plan_sha256']):
            raise ValueError('supersession_new_binding_changed')
        old_dir = sync.safe_path(hub / 'ai/reminders-project-lists' / plan['old_operation'])
        old_plan_path = sync.safe_path(old_dir / 'plan.json')
        old_state_path = sync.safe_path(old_dir / 'state.json')
        old_raw = old_plan_path.read_bytes()
        old_state_raw = old_state_path.read_bytes()
        old_plan = json.loads(old_raw)
        old_state = json.loads(old_state_raw)
        if (sha(old_raw) != plan['old_plan_sha256'] or
                old_plan.get('kind') != 'empty_rebind' or old_plan.get('project') != plan['project'] or
                old_state.get('phase') != 'complete' or old_state.get('sha256') != plan['old_plan_sha256'] or
                old_state.get('list_id') != plan['old_list_id']):
            raise ValueError('supersession_old_operation_changed')
        current = config.get('projects', {}).get(plan['project'])
        baseline = config.get('structure', {}).get('projects', {}).get(plan['project'])
        if (not isinstance(current, dict) or current.get('layout') != 'project_list' or
                current.get('list_id') != plan['new_list_id'] or
                not isinstance(baseline, dict) or baseline.get('list_id') != plan['new_list_id']):
            raise ValueError('supersession_binding_config_mismatch')
        marker_matches = matches_supersession_marker(old_state, plan)
        if old_state.get('superseded_by') and not marker_matches:
            raise ValueError('supersession_old_operation_changed')
        if not marker_matches:
            if sha(old_state_raw) != plan['old_state_sha256']:
                raise ValueError('supersession_old_operation_changed')
            old_state['superseded_by'] = supersession_marker(plan)
            atomic_write(old_state_path, encoded(old_state))
            old_state = json.loads(old_state_path.read_text())
            if not matches_supersession_marker(old_state, plan):
                raise ValueError('supersession_state_readback_failed')
        state.update({'phase': 'complete', 'old_state_after_sha256': sha(encoded(old_state))})
        atomic_write(state_path, encoded(state))
        return {'phase': 'complete', 'project': plan['project'],
                'old_operation': plan['old_operation'], 'new_operation': plan['new_operation']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['preview', 'apply', 'adopt', 'status',
                                            'supersede-preview', 'supersede-apply'])
    parser.add_argument('--hub', type=Path)
    parser.add_argument('--project')
    parser.add_argument('--group-key')
    parser.add_argument('--list-id')
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--sha256')
    parser.add_argument('--old-operation')
    parser.add_argument('--approve', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'preview':
            result = preview(args.hub, args.project, args.group_key, args.list_id)
        elif args.command == 'apply':
            result = apply_binding(args.plan, args.sha256, args.approve)
        elif args.command == 'adopt':
            result = adopt_exact_uuid(args.plan, args.sha256, args.list_id)
        elif args.command == 'supersede-preview':
            result = supersession_preview(args.plan, args.sha256, args.old_operation)
        elif args.command == 'supersede-apply':
            result = apply_supersession(args.plan, args.sha256, args.approve)
        else:
            result = status(args.plan, args.sha256)
        print(encoded(result))
    except (ValueError, KeyError, OSError, RuntimeError) as error:
        print(encoded({'ok': False, 'error': str(error)}))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
