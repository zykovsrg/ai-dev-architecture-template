"""Проверенная очистка старых списков напоминаний."""
import hashlib
import copy
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import uuid


def load_frozen_scope(raw, expected_sha256):
    """Load only the exact immutable proposal accepted for this cleanup."""
    if not isinstance(raw, bytes) or hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('scope_sha256_mismatch')
    value = json.loads(raw)
    if value.get('kind') != 'old_list_removal_readonly_preview' or value.get('version') != 1:
        raise ValueError('invalid_frozen_scope')
    validate_scope(value)
    return value


def validate_scope(value):
    scope = value.get('cleanup_scope')
    if not isinstance(scope, dict):
        raise ValueError('invalid_cleanup_scope')
    lists = scope.get('candidates')
    protected = scope.get('protected_project_lists')
    survivors = scope.get('survivor_records')
    parents = scope.get('retired_parent_records')
    ids = scope.get('candidate_list_ids')
    if (scope.get('candidate_old_lists') != 18 or len(lists or []) != 18 or len(ids or []) != 18 or
            len(set(ids or [])) != 18 or len(protected or []) != 76 or len(survivors or []) != 626 or
            len(parents or []) != 74 or scope.get('retired_parent_wrappers') != 74 or
            scope.get('protected_project_list_count') != 76):
        raise ValueError('cleanup_scope_count_mismatch')
    def unique_uuid(rows, key):
        values = [row.get(key) for row in rows]
        if any(not _safe_uuid(v) for v in values) or len(values) != len(set(values)):
            raise ValueError('cleanup_scope_identity_mismatch')
        return set(values)
    candidate_ids = unique_uuid([{'id': x} for x in ids], 'id')
    protected_ids = unique_uuid([row.get('list', {}) for row in protected], 'id')
    survivor_ids = unique_uuid(survivors, 'id')
    parent_ids = unique_uuid(parents, 'reminder_id')
    if candidate_ids & protected_ids or scope.get('preserve_current_content_system_list_id') not in protected_ids:
        raise ValueError('cleanup_scope_protected_overlap')
    if len({row.get('id') for row in survivors}) != len(survivor_ids):
        raise ValueError('cleanup_scope_duplicate_survivor')
    found = {}
    for candidate in lists:
        row = candidate.get('list', {})
        lid = row.get('id')
        if lid not in candidate_ids or lid in found:
            raise ValueError('cleanup_scope_candidate_mismatch')
        role = candidate.get('role')
        if (not isinstance(role, dict) or role.get('kind') not in {'direct', 'subgroup'} or
                (role.get('kind') == 'direct' and set(role) != {'kind'}) or
                (role.get('kind') == 'subgroup' and
                 (set(role) != {'kind', 'archiproject_id'} or not isinstance(role.get('archiproject_id'), str) or
                  not role.get('archiproject_id') or candidate.get('subgroup_ids') != [role['archiproject_id']])) or
                (role.get('kind') == 'direct' and candidate.get('subgroup_ids')) or
                candidate.get('expected_after_parent_cleanup_count') != 0 or
                candidate.get('deletion_blockers') != ['structure_role_present']):
            raise ValueError('cleanup_scope_candidate_role_or_children')
        found[lid] = candidate
        if (candidate.get('other_ids') or candidate.get('project_ids') or
                type(row.get('total')) is not int or row['total'] != len(candidate.get('full_snapshot', []))):
            raise ValueError('cleanup_scope_candidate_not_empty')
    if set(found) != candidate_ids:
        raise ValueError('cleanup_scope_candidate_mismatch')
    staged = set()
    parent_to_list = {}
    for candidate in lists:
        staged.update(candidate.get('retired_parent_ids', []))
        for row in candidate.get('full_snapshot', []):
            rid = row.get('id')
            if row.get('list') != candidate['list'].get('name'):
                raise ValueError('cleanup_scope_parent_list_mismatch')
            staged.add(rid); parent_to_list[rid] = candidate['list']['id']
    for parent in parents:
        rid = parent.get('reminder_id')
        owner = found.get(parent_to_list.get(rid))
        saved = next((item for item in owner.get('full_snapshot', []) if item.get('id') == rid), {}) if owner else {}
        if (parent.get('snapshot', {}).get('id') != rid or not owner or
                parent.get('snapshot') != saved or not isinstance(parent.get('project_id'), str) or
                not parent.get('project_id')):
            raise ValueError('cleanup_scope_parent_record_mismatch')
    if staged != parent_ids:
        raise ValueError('cleanup_scope_parent_mismatch')
    return dict(candidate_list_ids=candidate_ids, protected_list_ids=protected_ids,
                survivor_ids=survivor_ids, retired_parent_ids=parent_ids)


def delete_arguments(row):
    """Address a list by UUID and explicitly confirm its already-approved rows."""
    if not isinstance(row, dict) or not isinstance(row.get('id'), str):
        raise ValueError('invalid_list_identity')
    try:
        if str(uuid.UUID(row['id'])).upper() != row['id'].upper():
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise ValueError('invalid_list_identity')
    if type(row.get('total')) is not int or row['total'] < 0:
        raise ValueError('invalid_list_count')
    return {'action': 'delete', 'list': row['id'], 'confirm_delete_reminders': True}


def protected_snapshot(rows, expected_ids):
    """Capture every returned field for each protected working reminder."""
    if not isinstance(rows, list) or not isinstance(expected_ids, set):
        raise ValueError('invalid_protected_snapshot')
    snapshot = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or row['id'] in snapshot:
            raise ValueError('invalid_protected_snapshot')
        snapshot[row['id']] = row
    if set(snapshot) != expected_ids:
        raise ValueError('protected_reminder_set_changed')
    return snapshot


def same_protected_snapshot(before, after):
    """Compare all fields, including native versions and derived user data."""
    if before != after:
        raise ValueError('protected_reminder_changed')
    return True


def restore_refused(blocked_ids, reminder_id):
    """Keep a narrowly pinned refusal set; all other restore requests use normal guards."""
    return reminder_id in blocked_ids


def _modules():
    folder = Path(__file__).parent
    spec = importlib.util.spec_from_file_location('cleanup_project_lists', folder / 'reminders_project_lists.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n'


def _durable(path, data, exclusive=False):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or path != path.resolve() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('unsafe_path')
    if exclusive:
        with path.open('x') as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
    else:
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno()); temp = handle.name
        os.replace(temp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)


def _safe_uuid(value):
    try:
        return isinstance(value, str) and str(uuid.UUID(value)).upper() == value.upper()
    except (ValueError, TypeError, AttributeError):
        return False


def _full_inventory(native, meta, list_ids, helper):
    result = {'lists': {}, 'reminders': {}}
    rows = {row['id']: row for row in meta['lists']}
    for lid in sorted(list_ids):
        if lid not in rows:
            continue
        reminders = helper.rows(native, lid)
        result['lists'][lid] = rows[lid]
        for rid, reminder in reminders.items():
            if rid in result['reminders']:
                raise ValueError('duplicate_inventory_reminder')
            result['reminders'][rid] = reminder
    return result


def _scope_inventory(scope):
    checked = validate_scope(scope)
    source = scope['cleanup_scope']
    candidate_lists = {row['list']['id']: row for row in source['candidates']}
    protected_lists = {row['list']['id']: row for row in source['protected_project_lists']}
    return checked, candidate_lists, protected_lists


def _ordered_candidate_ids(candidates, inventory):
    return sorted(candidates, key=lambda lid: (
        inventory['lists'][lid].get('total', 0) == 0,
        inventory['lists'][lid].get('total', 0),
        inventory['lists'][lid].get('name', '').casefold(), lid))


def _check_unique_ui_names(metadata, candidate_ids):
    rows = {row['id']: row for row in metadata['lists']}
    names = [row.get('name') for row in metadata['lists']]
    for lid in candidate_ids:
        if lid in rows and names.count(rows[lid].get('name')) != 1:
            raise ValueError('cleanup_ui_name_not_unique')


def _check_initial(scope, config, metadata, inventory, helper, hub):
    checked, candidates, protected = _scope_inventory(scope)
    cfg_sha = helper.sha((hub / 'ai/reminders-sync.json').read_bytes())
    if cfg_sha != scope.get('config_sha256'):
        raise ValueError('config_scope_sha256_mismatch')
    structure = config.get('structure', {})
    roles = structure.get('list_roles', {})
    if set(roles) != set(candidates) | set(protected):
        raise ValueError('cleanup_live_role_set_changed')
    subgroups = structure.get('subgroups', {})
    for lid, frozen in candidates.items():
        role = frozen['role']
        if isinstance(roles.get(lid), dict) and roles[lid].get('kind') == 'project':
            raise ValueError('cleanup_project_role_protected')
        if roles.get(lid) != role:
            raise ValueError('cleanup_live_role_changed')
        if role.get('kind') == 'subgroup':
            subgroup = subgroups.get(role['archiproject_id'])
            if not isinstance(subgroup, dict) or subgroup.get('list_id') != lid:
                raise ValueError('cleanup_subgroup_binding_changed')
    actual_lists = {row['id']: row for row in metadata['lists']}
    if set(actual_lists) != set(candidates) | set(protected):
        raise ValueError('cleanup_live_list_set_changed')
    _check_unique_ui_names(metadata, candidates)
    names = [row.get('name') for row in metadata['lists']]
    if len(names) != len(set(names)):
        raise ValueError('cleanup_list_name_ownership_ambiguous')
    by_name = {row['name']: row['id'] for row in metadata['lists']}
    groups = {row['id']: row for row in metadata['groups']}
    for row in actual_lists.values():
        group_id = row.get('group_id')
        if group_id is not None:
            group = groups.get(group_id)
            if not group or group.get('account_id') != row.get('account_id'):
                raise ValueError('cleanup_group_account_changed')
    if any(row.get('shared') for lid, row in actual_lists.items() if lid in candidates):
        raise ValueError('cleanup_shared_list')
    # list_lists does not expose a default-list flag; the Native deleteList guard checks it at the effect boundary.
    if any(lid not in actual_lists for lid in candidates):
        raise ValueError('cleanup_candidate_missing')
    for lid, frozen in candidates.items():
        row = actual_lists[lid]
        for field in ('id', 'name', 'account_id', 'group_id', 'group', 'sort', 'open', 'total'):
            if field in frozen['list'] and row.get(field) != frozen['list'][field]:
                raise ValueError('cleanup_candidate_metadata_changed')
        expected = {entry['id']: entry for entry in frozen['full_snapshot']}
        actual = {rid: reminder for rid, reminder in inventory['reminders'].items()
                  if reminder.get('list_id') == lid}
        if set(actual) != set(expected) or any(not _summary_matches(expected[rid], row)
                                               for rid, row in actual.items()):
            raise ValueError('cleanup_candidate_snapshot_changed')
        if any(reminder.get('parent_id') for reminder in actual.values()):
            raise ValueError('cleanup_candidate_has_children')
    actual_protected = {lid: row for lid, row in inventory['lists'].items() if lid in protected}
    for lid, frozen in protected.items():
        if actual_protected.get(lid) != frozen['list']:
            raise ValueError('cleanup_protected_list_changed')
    working = {rid: row for rid, row in inventory['reminders'].items() if row.get('list_id') in protected}
    if set(working) != checked['survivor_ids']:
        raise ValueError('cleanup_survivor_set_changed')
    frozen_survivors = {row['id']: row for row in scope['cleanup_scope']['survivor_records']}
    for rid, row in working.items():
        expected = frozen_survivors[rid]
        owner = by_name.get(expected.get('list'))
        if owner not in protected or row.get('list_id') != owner or not _summary_matches(expected, row):
            raise ValueError('cleanup_survivor_baseline_changed')
    parents = {row['reminder_id'] for row in scope['cleanup_scope']['retired_parent_records']}
    all_candidate_rows = {rid for rid, row in inventory['reminders'].items() if row.get('list_id') in candidates}
    if all_candidate_rows != parents:
        raise ValueError('cleanup_parent_set_changed')
    project_bindings = config.get('projects', {})
    for parent in scope['cleanup_scope']['retired_parent_records']:
        rid = parent['reminder_id']
        owner = next((lid for lid, frozen in candidates.items() if rid in frozen['retired_parent_ids']), None)
        binding = project_bindings.get(parent.get('project_id'), {})
        retired = binding.get('retired_parent', {})
        actual = inventory['reminders'].get(rid)
        if (not owner or retired.get('id') != rid or retired.get('list_id') != owner or
                retired.get('snapshot') != actual or not _summary_matches(parent['snapshot'], actual)):
            raise ValueError('cleanup_retired_parent_config_snapshot_changed')
    for frozen in scope['cleanup_scope']['protected_project_lists']:
        owner = by_name.get(frozen['list'].get('name'))
        if owner not in protected or inventory['lists'].get(owner) != frozen['list']:
            raise ValueError('cleanup_protected_list_ownership_changed')
        summaries = {row['id']: row for row in frozen.get('snapshot', [])}
        actual_rows = {rid: row for rid, row in working.items() if row.get('list_id') == owner}
        if set(actual_rows) != set(summaries) or any(not _summary_matches(summaries[rid], row)
                                                    for rid, row in actual_rows.items()):
            raise ValueError('cleanup_protected_list_snapshot_changed')
    return checked


def _summary_matches(summary, full):
    return isinstance(summary, dict) and isinstance(full, dict) and all(
        key in full and full[key] == value for key, value in summary.items())


def _structure_reference_snapshot(config, candidate_ids):
    structure = config.get('structure')
    if not isinstance(structure, dict):
        raise ValueError('cleanup_structure_missing')
    subgroups = structure.get('subgroups')
    defaults = structure.get('group_default_lists')
    if not isinstance(subgroups, dict) or not isinstance(defaults, dict):
        raise ValueError('cleanup_structure_references_invalid')
    return {
        'subgroups': {key: copy.deepcopy(value) for key, value in subgroups.items()
                      if isinstance(value, dict) and value.get('list_id') in candidate_ids},
        'group_default_lists': {key: value for key, value in defaults.items() if value in candidate_ids},
    }


def preview(hub, scope_path, scope_sha256, native=None, delete_driver='native'):
    """Create an immutable executable plan from the already accepted read-only scope."""
    if delete_driver not in {'native', 'reminders_ui'}:
        raise ValueError('cleanup_delete_driver_invalid')
    helper = _modules()
    hub = helper.safe(Path(hub))
    expected_scope = hub / 'ai/tmp/reminders-project-lists/old-list-removal-readonly-preview-20261028.json'
    scope_path = helper.safe(Path(scope_path))
    if scope_path != expected_scope or scope_sha256 != 'ce482a4a85c4d02c1a2e247d5b1b332c30c50f303c822fae31ceb9b13761430a':
        raise ValueError('unapproved_scope_source')
    with helper.locked(hub):
        raw_scope = scope_path.read_bytes()
        scope = load_frozen_scope(raw_scope, scope_sha256)
        config, raw_config = helper.config_read(hub)
        native = native or helper.Native(config)
        helper.reset_cache(native)
        metadata = helper.metadata(native)
        checked, candidates, protected = _scope_inventory(scope)
        inventory = _full_inventory(native, metadata, set(candidates) | set(protected), helper)
        _check_initial(scope, config, metadata, inventory, helper, hub)
        ordered_candidate_ids = _ordered_candidate_ids(candidates, inventory)
        allow_path = helper.safe(Path(config['standard_allowlist_file']))
        allow_names = json.loads(allow_path.read_text())['names']
        if any(row['list']['name'] not in allow_names for row in candidates.values()):
            raise ValueError('cleanup_native_name_not_allowed')
        proofs = _historical_refusal_proofs(hub, config, native, helper)
        refused = set(proofs)
        if len(refused) != 5 or any(not _safe_uuid(rid) for rid in refused):
            raise ValueError('cleanup_restore_refusal_scope_mismatch')
        retired_ids = set(checked['retired_parent_ids'])
        for proof in proofs.values():
            binding = config['projects'].get(proof['project_id'], {})
            if binding.get('retired_parent', {}).get('id') not in retired_ids:
                raise ValueError('cleanup_forfeiture_parent_outside_scope')
        consent = dict(state='restoration_forfeited', statement='Удалить без сохранения возможности восстановить эти пять задач — быстрее', reminder_ids=sorted(refused))
        structure_references = _structure_reference_snapshot(config, set(candidates))
        expected_subgroups = {row['role']['archiproject_id']: config['structure']['subgroups'][row['role']['archiproject_id']]
                              for row in candidates.values() if row['role']['kind'] == 'subgroup'}
        if structure_references['subgroups'] != expected_subgroups:
            raise ValueError('cleanup_subgroup_reference_set_changed')
        operation = str(uuid.uuid4())
        root = hub / 'ai/reminders-list-cleanups'
        root.mkdir(exist_ok=True)
        folder = root / operation
        folder.mkdir()
        plan = dict(protocol=1, kind='old_list_cleanup', operation=operation, hub=str(hub),
                    scope_sha256=scope_sha256, delete_driver=delete_driver,
                    config_sha256=helper.sha(raw_config),
                    config_raw=raw_config, candidate_list_ids=ordered_candidate_ids,
                    protected_list_ids=sorted(protected), protected_reminder_ids=sorted(checked['survivor_ids']),
                    retired_parent_ids=sorted(checked['retired_parent_ids']),
                    affected_projects=sorted({row['project_id'] for row in scope['cleanup_scope']['retired_parent_records']}),
                    restore_refusal_ids=sorted(refused), restore_refusal_proofs=proofs,
                    restoration_forfeit_consent=consent, inventory=inventory,
                    removed_structure_references=structure_references,
                    expected_final_config=None)
        plan_path = folder / 'plan.json'
        plan_raw = _encoded(plan)
        _durable(plan_path, plan_raw, exclusive=True)
        digest = hashlib.sha256(plan_raw.encode()).hexdigest()
        _durable(folder / 'state.json', _encoded(dict(protocol=1, plan_sha256=digest,
                  approved=False, phase='preview', completed_lists=[], write_intent=None)), exclusive=True)
        return dict(ok=True, plan=str(plan_path), sha256=digest, candidate_lists=18,
                    retired_records=74, protected_lists=76, protected_reminders=626,
                    restore_refusals=5)


def _historical_refusal_proofs(hub, config, native, helper):
    proofs = {}
    sync = helper.load_sync()
    cancellation = sync.cancellation_module()
    if cancellation is None:
        raise ValueError('cleanup_cancellation_validator_unavailable')
    class Reader:
        def call(self, tool, args):
            if tool == 'hub_cancel_status' and hasattr(native, 'cancellation_status'):
                return native.cancellation_status(args)
            return native.call(tool, args)
    reader = Reader()
    for binding in config.get('projects', {}).values():
        if not binding.get('historical_binding_migration'):
            continue
        for task_id, link in binding.get('tasks', {}).items():
            if link.get('cancellation'):
                project_id = next(pid for pid, value in config['projects'].items() if value is binding)
                rows = sync.HubProject(hub, project_id).rows()
                if task_id not in rows:
                    raise ValueError('cleanup_cancelled_task_missing')
                row = dict(rows[task_id], project_id=project_id)
                native_status = cancellation.verify_cancelled_link(hub, row, link, binding, reader, return_status=True)
                if not isinstance(native_status, dict):
                    raise ValueError('cleanup_historical_cancel_unverified')
                rid = link.get('reminder_id')
                if rid in proofs:
                    raise ValueError('cleanup_duplicate_forfeiture_proof')
                cancel = link['cancellation']
                proofs[rid] = dict(project_id=project_id, task_id=task_id, reminder_id=rid,
                    operation_id=cancel['operation_id'], plan_sha256=cancel['plan_sha256'],
                    native_status=native_status)
    return proofs


def _read_plan(path, digest, helper):
    path = helper.safe(Path(path))
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('cleanup_plan_sha256_mismatch')
    plan = json.loads(raw)
    hub = helper.safe(Path(plan['hub']))
    if (path != hub / 'ai/reminders-list-cleanups' / plan['operation'] / 'plan.json' or
            plan.get('kind') != 'old_list_cleanup' or plan.get('protocol') != 1):
        raise ValueError('cleanup_plan_path_or_kind_invalid')
    if plan.get('delete_driver', 'native') not in {'native', 'reminders_ui'}:
        raise ValueError('cleanup_delete_driver_invalid')
    state_path = helper.safe(path.with_name('state.json'))
    state = json.loads(state_path.read_text())
    if state.get('plan_sha256') != digest or state.get('protocol') != 1:
        raise ValueError('cleanup_state_plan_mismatch')
    return path, plan, state, hub


def _load_live(helper, native, plan):
    helper.reset_cache(native)
    metadata = helper.metadata(native)
    inventory = _full_inventory(native, metadata,
                                set(plan['protected_list_ids']) | set(plan['candidate_list_ids']), helper)
    return metadata, inventory


def _check_survivors(plan, inventory):
    before = {rid: row for rid, row in plan['inventory']['reminders'].items()
              if row.get('list_id') in set(plan['protected_list_ids'])}
    after = {rid: row for rid, row in inventory['reminders'].items()
             if row.get('list_id') in set(plan['protected_list_ids'])}
    same_protected_snapshot(before, after)
    before_lists = {lid: row for lid, row in plan['inventory']['lists'].items()
                    if lid in set(plan['protected_list_ids'])}
    after_lists = {lid: row for lid, row in inventory['lists'].items()
                   if lid in set(plan['protected_list_ids'])}
    if before_lists != after_lists:
        raise ValueError('cleanup_protected_list_changed')
    return before


def _ui_action(plan, lid):
    initial = plan['inventory']
    list_row = initial['lists'][lid]
    service = sorted((row for row in initial['reminders'].values() if row.get('list_id') == lid),
                     key=lambda row: row['id'])
    protected = {rid: row for rid, row in initial['reminders'].items()
                 if row.get('list_id') in set(plan['protected_list_ids'])}
    return dict(driver='reminders_ui', list_id=lid, name=list_row['name'],
                group_id=list_row.get('group_id'), expected_count=len(service),
                service_snapshot_sha256=hashlib.sha256(_encoded(service).encode()).hexdigest(),
                protected_snapshot_sha256=hashlib.sha256(_encoded(protected).encode()).hexdigest(),
                protected_list_ids=plan['protected_list_ids'], protected_reminder_count=len(protected))


def _apply_ui_step(path, plan, state, helper, native, save):
    metadata, inventory = _load_live(helper, native, plan)
    _check_survivors(plan, inventory)
    completed = set(state.get('completed_lists', []))
    intent = state.get('write_intent')
    expected_live_lists = set(plan['protected_list_ids']) | (set(plan['candidate_list_ids']) - completed)
    if intent and intent not in inventory['lists']:
        expected_live_lists.discard(intent)
    if {row['id'] for row in metadata['lists']} != expected_live_lists:
        raise ValueError('cleanup_live_list_set_changed')
    _check_unique_ui_names(metadata, set(plan['candidate_list_ids']) - completed)
    _candidate_progress(plan, metadata, inventory, completed, intent)
    if intent:
        expected_action = _ui_action(plan, intent)
        stored = state.get('awaiting_ui_action')
        if stored != expected_action:
            raise ValueError('cleanup_ui_action_binding_mismatch')
        current_list = inventory['lists'].get(intent)
        current_rows = {rid: row for rid, row in inventory['reminders'].items()
                        if row.get('list_id') == intent}
        expected_list = plan['inventory']['lists'][intent]
        expected_rows = {rid: row for rid, row in plan['inventory']['reminders'].items()
                         if row.get('list_id') == intent}
        if current_list is None:
            if current_rows:
                raise ValueError('cleanup_ui_partial_delete')
            completed.add(intent)
            state.update(completed_lists=sorted(completed), write_intent=None, awaiting_ui_action=None)
            save()
        elif current_list != expected_list or current_rows != expected_rows:
            raise ValueError('cleanup_ui_partial_or_foreign_change')
        else:
            return dict(ok=True, phase='awaiting_ui_delete', action=stored)
    remaining = [lid for lid in plan['candidate_list_ids'] if lid not in completed]
    if remaining:
        lid = remaining[0]
        action = _ui_action(plan, lid)
        state.update(write_intent=lid, write_intent_started=True, awaiting_ui_action=action)
        save()
        return dict(ok=True, phase='awaiting_ui_delete', action=action)
    state.update(phase='config_pending')
    save()
    return None


def _candidate_progress(plan, metadata, inventory, completed, intent=None):
    rows = {row['id']: row for row in metadata['lists']}
    initial = plan['inventory']
    targets = set(plan['candidate_list_ids'])
    known = set(plan['retired_parent_ids'])
    active_known = {rid for rid, row in inventory['reminders'].items()
                    if row.get('list_id') in targets}
    if not active_known <= known:
        raise ValueError('cleanup_candidate_new_reminder')
    for lid in targets:
        expected = initial['lists'][lid]
        actual = rows.get(lid)
        actual_rows = {rid: row for rid, row in inventory['reminders'].items()
                       if row.get('list_id') == lid}
        original_rows = {rid: row for rid, row in initial['reminders'].items()
                         if row.get('list_id') == lid}
        if lid in completed:
            if actual is not None or actual_rows:
                raise ValueError('cleanup_completed_list_reappeared')
        elif actual is None:
            if actual_rows or lid != intent:
                raise ValueError('cleanup_deleted_list_reminders_active')
        else:
            for key, value in expected.items():
                if key not in {'open', 'total'} and actual.get(key) != value:
                    raise ValueError('cleanup_candidate_metadata_changed')
            if not set(actual_rows) <= set(original_rows):
                raise ValueError('cleanup_candidate_new_reminder')
            if lid != intent and actual_rows != original_rows:
                raise ValueError('cleanup_candidate_snapshot_changed')
            for rid, row in actual_rows.items():
                if row != original_rows[rid]:
                    raise ValueError('cleanup_candidate_reminder_changed')
            if actual.get('total') != len(actual_rows):
                raise ValueError('cleanup_candidate_count_mismatch')
            if lid != intent and any(actual.get(key) != expected.get(key) for key in ('open', 'total')):
                raise ValueError('cleanup_candidate_metadata_changed')
    return rows


def _final_config(config, plan, receipt_ref, receipt):
    final = json.loads(json.dumps(config))
    roles = final['structure']['list_roles']
    references = _structure_reference_snapshot(config, set(plan['candidate_list_ids']))
    if references != plan.get('removed_structure_references') or references != receipt.get('removed_structure_references'):
        raise ValueError('cleanup_structure_reference_cas_failed')
    for subgroup_id in references['subgroups']:
        final['structure']['subgroups'].pop(subgroup_id)
    for group_id in references['group_default_lists']:
        final['structure']['group_default_lists'].pop(group_id)
    for lid in plan['candidate_list_ids']:
        if lid not in roles:
            raise ValueError('cleanup_role_missing_before_commit')
        roles.pop(lid)
    parents = set(plan['retired_parent_ids'])
    count = 0
    for binding in final['projects'].values():
        retired = binding.get('retired_parent')
        if retired and retired.get('id') in parents:
            binding['retired_parent_cleanup'] = dict(operation=receipt_ref['operation'],
                                                     path=receipt_ref['path'],
                                                     sha256=receipt_ref['sha256'])
            refusals = sorted({link.get('reminder_id') for link in binding.get('tasks', {}).values()
                               if link.get('reminder_id') in set(plan['restore_refusal_ids'])})
            if refusals:
                binding['retired_parent_cleanup']['restore_refusal_ids'] = refusals
                binding['restoration_forfeit_state'] = dict(state='restoration_forfeited', reminder_ids=refusals)
            count += 1
    if count != 74 or len(roles) != 76:
        raise ValueError('cleanup_config_target_count_mismatch')
    helper = _modules()
    helper.load_sync().validate_binding_ids(final)
    return final


def _receipt_path(hub, operation):
    return hub / 'ai/reminders-list-cleanups' / operation / 'receipt.json'


def _receipt_files_stamp(reference):
    try:
        path = Path(reference['path'])
        return tuple((item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns)
                     for item in (os.stat(path.with_name(name)) for name in ('receipt.json', 'plan.json', 'state.json')))
    except (KeyError, TypeError, OSError):
        return None


def _verify_receipt(hub, reference, expected_parent_id=None, reminder_id=None):
    # Синхронизация проверяет одну квитанцию тысячи раз; внутри запуска полный разбор
    # повторяется, только если изменился файл квитанции, плана или состояния.
    # Результат общий для повторных вызовов: вызывающие только читают его.
    reads = sys.modules.get('hub_reminders_reads')
    stamp = _receipt_files_stamp(reference) if reads else None
    if stamp is None:
        return _verify_receipt_contents(hub, reference, expected_parent_id, reminder_id)
    key = ('cleanup_receipt', str(hub), json.dumps(reference, sort_keys=True), expected_parent_id, reminder_id, stamp)
    def verify():
        result = _verify_receipt_contents(hub, reference, expected_parent_id, reminder_id)
        return result, _receipt_files_stamp(reference) == stamp
    return reads.memo(key, verify)


def _verify_receipt_contents(hub, reference, expected_parent_id=None, reminder_id=None):
    helper = _modules()
    hub = helper.safe(Path(hub))
    if (not isinstance(reference, dict) or not _safe_uuid(reference.get('operation')) or
            not isinstance(reference.get('sha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', reference['sha256'])):
        raise ValueError('cleanup_receipt_reference_invalid')
    path = helper.safe(Path(reference.get('path', '')))
    if path != _receipt_path(hub, reference['operation']):
        raise ValueError('cleanup_receipt_path_invalid')
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != reference['sha256']:
        raise ValueError('cleanup_receipt_sha256_mismatch')
    value = json.loads(raw)
    if value.get('protocol') != 1 or value.get('state') != 'complete' or value.get('operation') != reference['operation']:
        raise ValueError('cleanup_receipt_not_terminal')
    if (len(value.get('deleted_list_ids', [])) != 18 or len(value.get('deleted_parent_ids', [])) != 74 or
            len(value.get('protected_list_ids', [])) != 76 or value.get('protected_reminder_count') != 626):
        raise ValueError('cleanup_receipt_scope_invalid')
    plan_path = helper.safe(path.with_name('plan.json'))
    plan_raw = plan_path.read_bytes()
    plan_sha = hashlib.sha256(plan_raw).hexdigest()
    if (plan_sha != value.get('plan_sha256') or value.get('deleted_list_ids') != json.loads(plan_raw).get('candidate_list_ids') or
            value.get('deleted_parent_ids') != json.loads(plan_raw).get('retired_parent_ids') or
            value.get('protected_list_ids') != json.loads(plan_raw).get('protected_list_ids') or
            value.get('restore_refusal_ids') != json.loads(plan_raw).get('restore_refusal_ids')):
        raise ValueError('cleanup_receipt_plan_mismatch')
    plan_value = json.loads(plan_raw)
    if value.get('removed_structure_references') != plan_value.get('removed_structure_references'):
        raise ValueError('cleanup_receipt_structure_reference_mismatch')
    config_raw = plan_value.get('config_raw')
    if (not isinstance(config_raw, str) or helper.sha(config_raw) != plan_value.get('config_sha256') or
            _structure_reference_snapshot(json.loads(config_raw), set(plan_value.get('candidate_list_ids', []))) !=
            plan_value.get('removed_structure_references')):
        raise ValueError('cleanup_receipt_structure_reference_snapshot_invalid')
    consent = plan_value.get('restoration_forfeit_consent')
    proofs = plan_value.get('restore_refusal_proofs')
    if (not isinstance(consent, dict) or consent.get('state') != 'restoration_forfeited' or
            consent.get('statement') != 'Удалить без сохранения возможности восстановить эти пять задач — быстрее' or
            consent.get('reminder_ids') != value.get('restore_refusal_ids') or
            value.get('restoration_forfeit_consent') != consent or
            not isinstance(proofs, dict) or set(proofs) != set(value.get('restore_refusal_ids', [])) or
            value.get('restore_refusal_proofs') != proofs):
        raise ValueError('cleanup_forfeiture_proof_invalid')
    expected_old_lists = {lid: plan_value['inventory']['lists'][lid] for lid in plan_value['candidate_list_ids']}
    expected_parents = {rid: plan_value['inventory']['reminders'][rid] for rid in plan_value['retired_parent_ids']}
    expected_protected = {rid: row for rid, row in plan_value['inventory']['reminders'].items()
                          if row.get('list_id') in set(plan_value['protected_list_ids'])}
    if (value.get('deleted_list_snapshots') != expected_old_lists or
            value.get('deleted_parent_snapshots') != expected_parents or
            value.get('protected_reminder_snapshot') != expected_protected or len(expected_protected) != 626):
        raise ValueError('cleanup_receipt_protected_snapshot_mismatch')
    if expected_parent_id is not None and expected_parent_id not in value.get('deleted_parent_ids', []):
        raise ValueError('cleanup_receipt_parent_not_owned')
    if reminder_id is not None and reminder_id not in value.get('restore_refusal_ids', []):
        return False
    state_path = helper.safe(path.with_name('state.json'))
    state = json.loads(state_path.read_text())
    if state.get('phase') not in {'config_writing', 'complete'} or state.get('receipt_sha256') != digest:
        raise ValueError('cleanup_receipt_state_unverified')
    return value if reminder_id is None else True


def retired_parent_cleaned(hub, binding):
    """Only a terminal receipt can replace a live retired-parent requirement."""
    reference = binding.get('retired_parent_cleanup')
    retired = binding.get('retired_parent')
    if not reference:
        return False
    if not isinstance(retired, dict) or not _safe_uuid(retired.get('id')):
        raise ValueError('cleanup_retired_parent_binding_invalid')
    if hub is None:
        receipt_path = Path(reference.get('path', ''))
        if receipt_path.name != 'receipt.json' or len(receipt_path.parents) < 4:
            raise ValueError('cleanup_receipt_path_invalid')
        hub = receipt_path.parents[3]
    _verify_receipt(hub, reference, expected_parent_id=retired['id'])
    return True


def restore_refused_for_binding(hub, binding, reminder_id):
    """Block only a UUID proven to be one of the five abandoned historical restores."""
    reference = binding.get('retired_parent_cleanup')
    if not reference:
        return False
    bound_ids = reference.get('restore_refusal_ids', [])
    if reminder_id not in bound_ids:
        return False
    return restore_refused(set(_verify_receipt(hub, reference).get('restore_refusal_ids', [])), reminder_id)


def _current_active_ids(hub, native, helper, project_id, expected_binding):
    config, config_raw = helper.config_read(hub)
    sync = helper.load_sync()
    sync.validate_binding_ids(config)
    projects = config.get('projects')
    structure = config.get('structure')
    roles = structure.get('list_roles') if isinstance(structure, dict) else None
    if not isinstance(projects, dict) or not isinstance(roles, dict) or not roles:
        raise ValueError('cleanup_forfeiture_current_scope_incomplete')
    if projects.get(project_id) != expected_binding:
        raise ValueError('cleanup_forfeiture_current_project_identity_changed')
    expected_ids = set()
    for lid, role in roles.items():
        if not _safe_uuid(lid) or not isinstance(role, dict):
            raise ValueError('cleanup_forfeiture_current_scope_identity_invalid')
        expected_ids.add(lid)
    for pid, binding in projects.items():
        if (not isinstance(binding, dict) or not _safe_uuid(binding.get('list_id')) or
                not isinstance(binding.get('list_name'), str) or not binding['list_name']):
            raise ValueError('cleanup_forfeiture_current_scope_identity_invalid')
        expected_ids.add(binding['list_id'])
        role = roles.get(binding['list_id'])
        if binding.get('layout', 'parent') == 'project_list':
            if not isinstance(role, dict) or role.get('kind') != 'project' or role.get('project_id') != pid:
                raise ValueError('cleanup_forfeiture_current_project_role_changed')
        elif isinstance(role, dict) and role.get('kind') == 'project':
            raise ValueError('cleanup_forfeiture_current_project_role_changed')
    if not expected_ids:
        raise ValueError('cleanup_forfeiture_current_scope_incomplete')

    def read_metadata():
        value = helper.metadata(native)
        if (value.get('error') or value.get('errors') or value.get('more') or value.get('has_more') or
                not isinstance(value.get('lists'), list) or not isinstance(value.get('groups'), list)):
            raise ValueError('cleanup_forfeiture_active_area_incomplete')
        list_ids = [row.get('id') for row in value['lists'] if isinstance(row, dict)]
        if (len(list_ids) != len(value['lists']) or len(list_ids) != len(set(list_ids)) or
                not expected_ids <= set(list_ids)):
            raise ValueError('cleanup_forfeiture_current_scope_incomplete')
        groups = {}
        for group in value['groups']:
            gid = group.get('id')
            if not _safe_uuid(gid) or gid in groups or not _safe_uuid(group.get('account_id')):
                raise ValueError('cleanup_forfeiture_active_group_identity_invalid')
            groups[gid] = group
        rows = {}
        names = set()
        for row in value['lists']:
            lid, account_id, name = row.get('id'), row.get('account_id'), row.get('name')
            total = row.get('total')
            if (not _safe_uuid(lid) or not _safe_uuid(account_id) or not isinstance(name, str) or not name or
                    name in names or type(total) is not int or total < 0):
                raise ValueError('cleanup_forfeiture_active_list_identity_invalid')
            names.add(name); rows[lid] = row
            group_id = row.get('group_id')
            if group_id is not None:
                group = groups.get(group_id)
                if not group or group.get('account_id') != account_id:
                    raise ValueError('cleanup_forfeiture_active_list_account_changed')
        for pid, binding in projects.items():
            expected_group = binding.get('native_group_id')
            if binding.get('archive'):
                archive = sync.archive_module(config)
                receipt = archive.read_receipt(hub, config, pid)
                if receipt is None: raise ValueError('cleanup_archive_unverified')
                expected_group = receipt[1]['archive_group']['id']
            row = rows.get(binding['list_id'])
            if (row is None or row.get('name') != binding['list_name'] or
                    ('account_id' in binding and row.get('account_id') != binding['account_id']) or
                    ('native_group_id' in binding and row.get('group_id') != expected_group)):
                raise ValueError('cleanup_forfeiture_current_project_identity_changed')
        structure_projects = structure.get('projects', {})
        if not isinstance(structure_projects, dict):
            raise ValueError('cleanup_forfeiture_current_scope_identity_invalid')
        for pid, project in structure_projects.items():
            if not isinstance(project, dict):
                raise ValueError('cleanup_forfeiture_current_scope_identity_invalid')
            lid = project.get('list_id')
            if lid is not None and (not _safe_uuid(lid) or lid not in rows or
                                    (pid in projects and projects[pid]['list_id'] != lid)):
                raise ValueError('cleanup_forfeiture_current_project_identity_changed')
        return value, rows

    metadata, list_rows = read_metadata()
    active_ids = set()
    archive_rows = {}
    for lid, list_row in list_rows.items():
        page = native.call('find_reminders', dict(list=lid, include_completed=True, limit=500))
        rows = page.get('reminders') if isinstance(page, dict) else None
        if (not isinstance(rows, list) or page.get('error') or page.get('errors') or page.get('more') or
                page.get('has_more') or type(page.get('count')) is not int or len(rows) >= 500 or
                page['count'] != len(rows) or len(rows) != list_row['total']):
            raise ValueError('cleanup_forfeiture_current_list_rows_incomplete')
        local_ids = set()
        for row in rows:
            rid = row.get('id') if isinstance(row, dict) else None
            if (not _safe_uuid(rid) or row.get('list') != list_row.get('name') or
                    ('list_id' in row and row.get('list_id') != lid) or rid in local_ids or rid in active_ids):
                raise ValueError('cleanup_forfeiture_active_reminder_identity_invalid')
            local_ids.add(rid); active_ids.add(rid)
            archive_rows[rid] = dict(row, list_id=lid)
    for pid, binding in projects.items():
        if binding.get('archive'):
            if not sync.archive_module(config).verify_archived(hub, config, pid, dict(lists=list_rows, reminders=archive_rows, groups=metadata['groups'])):
                raise ValueError('cleanup_archive_unverified')
    final_metadata, _ = read_metadata()
    metadata_signature = (
        {row['id']: row for row in metadata['lists']},
        {row['id']: row for row in metadata['groups']})
    final_signature = (
        {row['id']: row for row in final_metadata['lists']},
        {row['id']: row for row in final_metadata['groups']})
    if final_signature != metadata_signature or helper.config_read(hub)[1] != config_raw:
        raise ValueError('cleanup_forfeiture_current_area_changed')
    return active_ids


def restoration_forfeited_for_binding(hub, binding, reminder_id, native):
    """Verify the logical terminal and full active area; never reinterpret an SDK error as absence."""
    reference = binding.get('retired_parent_cleanup')
    if not reference:
        return False
    if 'restore_refusal_ids' not in reference:
        # Финализатор пишет список только для проектов с отказами восстановления.
        if 'restoration_forfeit_state' in binding:
            raise ValueError('cleanup_forfeiture_config_state_invalid')
        return False
    local_refusals = reference.get('restore_refusal_ids')
    if (not isinstance(local_refusals, list) or len(local_refusals) != len(set(local_refusals)) or
            any(not _safe_uuid(rid) for rid in local_refusals)):
        raise ValueError('cleanup_forfeiture_config_state_invalid')
    if reminder_id not in local_refusals:
        return False
    retired = binding.get('retired_parent')
    if not isinstance(retired, dict) or not _safe_uuid(retired.get('id')):
        raise ValueError('cleanup_retired_parent_binding_invalid')
    receipt = _verify_receipt(hub, reference, expected_parent_id=retired['id'])
    receipt_refusals = receipt.get('restore_refusal_ids')
    if (not isinstance(receipt_refusals, list) or len(receipt_refusals) != 5 or
            len(set(receipt_refusals)) != 5 or any(not _safe_uuid(rid) for rid in receipt_refusals) or
            not set(local_refusals) <= set(receipt_refusals) or reminder_id not in receipt_refusals):
        raise ValueError('cleanup_forfeiture_config_state_invalid')
    if binding.get('restoration_forfeit_state') != dict(state='restoration_forfeited',
            reminder_ids=local_refusals):
        raise ValueError('cleanup_forfeiture_config_state_invalid')
    proof = receipt['restore_refusal_proofs'].get(reminder_id)
    cancel = _modules().load_sync().cancellation_module()
    if cancel is None or not cancel.verify_forfeiture_proof(hub, proof):
        raise ValueError('cleanup_forfeiture_source_unverified')
    helper = _modules()
    helper.reset_cache(native)
    active_ids = _current_active_ids(hub, native, helper, proof.get('project_id'), binding)
    if active_ids.intersection(receipt_refusals):
        raise ValueError('cleanup_forfeited_reminder_active')
    return True


def status(path, digest, native=None):
    helper = _modules()
    path, plan, state, hub = _read_plan(path, digest, helper)
    config, raw_config = helper.config_read(hub)
    if raw_config not in {plan['config_raw'], state.get('final_config_raw')}:
        raise ValueError('cleanup_config_changed')
    if state.get('phase') in {'preview', 'complete'}:
        return dict(ok=True, phase=state['phase'], completed_lists=len(state.get('completed_lists', [])),
                    candidate_lists=18, receipt=state.get('receipt_ref'))
    native = native or helper.Native(config)
    metadata, inventory = _load_live(helper, native, plan)
    _check_survivors(plan, inventory)
    _candidate_progress(plan, metadata, inventory, set(state.get('completed_lists', [])), state.get('write_intent'))
    return dict(ok=True, phase=state['phase'], completed_lists=len(state.get('completed_lists', [])),
                candidate_lists=18, receipt=state.get('receipt_ref'))


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description='Строгое удаление согласованных прежних списков')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('preview')
    p.add_argument('--hub', required=True); p.add_argument('--scope', required=True); p.add_argument('--scope-sha256', required=True)
    p.add_argument('--delete-driver', choices=('native', 'reminders_ui'), default='native')
    for name in ('apply', 'status'):
        p = sub.add_parser(name); p.add_argument('--plan', required=True); p.add_argument('--sha256', required=True)
        if name == 'apply': p.add_argument('--approve', action='store_true')
    args = parser.parse_args(argv)
    if args.command == 'preview':
        result = preview(args.hub, args.scope, args.scope_sha256, delete_driver=args.delete_driver)
    elif args.command == 'apply':
        result = apply(args.plan, args.sha256, args.approve)
    else:
        result = status(args.plan, args.sha256)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def apply(path, digest, approve=False, native=None):
    helper = _modules()
    path, plan, state, hub = _read_plan(path, digest, helper)
    if approve is not True:
        raise ValueError('explicit_approval_required')
    with helper.locked(hub):
        config, raw_config = helper.config_read(hub)
        native = native or helper.Native(config)
        if state.get('phase') == 'complete':
            _verify_receipt(hub, state['receipt_ref'])
            return dict(ok=True, phase='complete', receipt=state['receipt_ref'])
        if hashlib.sha256(plan['config_raw'].encode()).hexdigest() != plan['config_sha256']:
            raise ValueError('cleanup_config_baseline_invalid')
        if raw_config not in {plan['config_raw'], state.get('final_config_raw')}:
            raise ValueError('cleanup_config_changed')
        state_path = path.with_name('state.json')
        def save(): _durable(state_path, _encoded(state))
        if state.get('phase') in {'preview', 'deleting'}:
            if raw_config != plan['config_raw']:
                raise ValueError('cleanup_config_changed_before_commit')
            state.update(approved=True, phase='deleting')
            save()
            completed = set(state.get('completed_lists', []))
            if plan.get('delete_driver', 'native') == 'reminders_ui':
                result = _apply_ui_step(path, plan, state, helper, native, save)
                if result is not None:
                    return result
            else:
                for lid in plan['candidate_list_ids']:
                  metadata, inventory = _load_live(helper, native, plan)
                  _check_survivors(plan, inventory)
                  _candidate_progress(plan, metadata, inventory, completed, state.get('write_intent'))
                  if lid in completed:
                      continue
                  present = {row['id'] for row in metadata['lists']}
                  if lid not in present:
                      if state.get('write_intent') != lid:
                          raise ValueError('cleanup_unowned_missing_list')
                      completed.add(lid); state.update(completed_lists=sorted(completed), write_intent=None); save()
                      continue
                  intent = state.get('write_intent')
                  if intent not in (None, lid):
                      raise ValueError('cleanup_other_list_intent_pending')
                  state.update(write_intent=lid, write_intent_started=True)
                  save()
                  error = None
                  try:
                      native.call('manage_list', delete_arguments(inventory['lists'][lid]))
                  except Exception as exc:
                      error = exc
                  fresh_meta, fresh_inventory = _load_live(helper, native, plan)
                  _check_survivors(plan, fresh_inventory)
                  _candidate_progress(plan, fresh_meta, fresh_inventory, completed, lid)
                  fresh_present = {row['id'] for row in fresh_meta['lists']}
                  if lid not in fresh_present:
                      completed.add(lid); state.update(completed_lists=sorted(completed), write_intent=None); save()
                  elif error is not None:
                      raise RuntimeError('cleanup_native_result_unknown_after_readback') from error
                  else:
                      raise ValueError('cleanup_delete_readback_failed')
            state.update(phase='config_pending')
            save()
        if state.get('phase') == 'config_pending':
            metadata, inventory = _load_live(helper, native, plan)
            _check_survivors(plan, inventory)
            _candidate_progress(plan, metadata, inventory, set(plan['candidate_list_ids']))
            if set(state.get('completed_lists', [])) != set(plan['candidate_list_ids']):
                raise ValueError('cleanup_incomplete_lists')
            receipt = dict(protocol=1, state='complete', operation=plan['operation'],
                           scope_sha256=plan['scope_sha256'], config_sha256_before=plan['config_sha256'],
                           plan_sha256=digest,
                           deleted_list_ids=plan['candidate_list_ids'], deleted_parent_ids=plan['retired_parent_ids'],
                           deleted_list_snapshots={lid: plan['inventory']['lists'][lid]
                                                   for lid in plan['candidate_list_ids']},
                           deleted_parent_snapshots={rid: plan['inventory']['reminders'][rid]
                                                     for rid in plan['retired_parent_ids']},
                           protected_list_ids=plan['protected_list_ids'], protected_reminder_count=626,
                           protected_reminder_snapshot={rid: row for rid, row in plan['inventory']['reminders'].items()
                                                        if row.get('list_id') in set(plan['protected_list_ids'])},
                           restore_refusal_ids=plan['restore_refusal_ids'],
                           restore_refusal_proofs=plan['restore_refusal_proofs'],
                           restoration_forfeit_consent=plan['restoration_forfeit_consent'],
                           removed_structure_references=plan['removed_structure_references'])
            receipt_path = _receipt_path(hub, plan['operation'])
            receipt_raw = _encoded(receipt)
            if receipt_path.exists():
                if receipt_path.read_text() != receipt_raw:
                    raise ValueError('cleanup_receipt_changed')
            else:
                _durable(receipt_path, receipt_raw, exclusive=True)
            receipt_sha = hashlib.sha256(receipt_raw.encode()).hexdigest()
            receipt_ref = dict(operation=plan['operation'], path=str(receipt_path), sha256=receipt_sha)
            final = _final_config(config, plan, receipt_ref, receipt)
            final_raw = _encoded(final)
            if raw_config == plan['config_raw']:
                state.update(final_config_raw=final_raw, phase='config_writing', receipt_sha256=receipt_sha,
                             receipt_ref=receipt_ref)
                save()
                if (hub / 'ai/reminders-sync.json').read_text() != plan['config_raw']:
                    raise ValueError('cleanup_config_cas_failed')
                _durable(hub / 'ai/reminders-sync.json', final_raw)
                raw_config = (hub / 'ai/reminders-sync.json').read_text()
            if raw_config != final_raw:
                raise ValueError('cleanup_config_readback_failed')
            state.update(phase='complete', receipt_sha256=receipt_sha, receipt_ref=receipt_ref)
            save()
            return dict(ok=True, phase='complete', deleted_lists=18, deleted_records=74,
                        preserved_lists=76, preserved_reminders=626, receipt=receipt_ref)
        if state.get('phase') == 'config_writing':
            final_raw = state.get('final_config_raw')
            if raw_config != final_raw:
                if raw_config != plan['config_raw']:
                    raise ValueError('cleanup_config_recovery_conflict')
                _durable(hub / 'ai/reminders-sync.json', final_raw)
            receipt_ref = state['receipt_ref']
            _verify_receipt(hub, receipt_ref)
            state.update(phase='complete')
            save()
            return dict(ok=True, phase='complete', receipt=receipt_ref)
        raise ValueError('cleanup_invalid_state')


if __name__ == '__main__':
    raise SystemExit(main())
