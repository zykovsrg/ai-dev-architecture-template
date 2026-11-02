#!/usr/bin/env python3
"""Точные свидетельства повторений и отсутствующей истории, без записи в приложение."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
import uuid


def _module(name):
    spec = importlib.util.spec_from_file_location('recurrence_' + name, Path(__file__).with_name(name + '.py'))
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


sync = _module('reminders_sync')
KINDS = {'confirmed_recurrence', 'missing_recurrence'}
LIMIT = 33_554_432


def _encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n').encode()


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _path(path):
    path = sync.safe_path(Path(path))
    if '..' in path.parts or path != path.resolve():
        raise ValueError('unsafe_recurrence_path')
    return path


def _bytes(path):
    path = _path(path)
    if path.stat().st_size > LIMIT:
        raise ValueError('recurrence_file_too_large')
    value = path.read_bytes()
    if len(value) > LIMIT:
        raise ValueError('recurrence_file_too_large')
    return value


def _write(path, value):
    path = _path(path); raw = _encoded(value)
    if len(raw) > LIMIT:
        raise ValueError('recurrence_file_too_large')
    name = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            name = Path(handle.name); handle.write(raw); handle.flush(); os.fsync(handle.fileno())
        os.replace(name, path)
        fd = os.open(str(path.parent), os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)
    finally:
        if name is not None and name.exists(): name.unlink()


def _write_state(path, value):
    _write(path, value)


def _uuid(value):
    if not isinstance(value, str) or str(uuid.UUID(value)) != value.lower():
        raise ValueError('invalid_recurrence_uuid')
    return value


def _config(hub, sync_module):
    raw = _bytes(hub / 'ai/reminders-sync.json')
    config = sync_module.load_config(hub)
    if json.loads(raw) != config:
        raise ValueError('recurrence_config_changed')
    return config, raw


def _observation(sync_module, hub, config, native, observation=None, previous=None):
    external = sync_module.external_retirement_module()
    if external is None:
        raise ValueError('recurrence_observation_support_missing')
    if observation is None:
        reads = sync_module.reads_module()
        if reads is not None: reads.refresh()
        observation = external.observe(hub, config, native, previous=previous, partial=True)
    if (not isinstance(observation, dict) or observation.get('complete') is not True or
            observation.get('errors') or observation.get('blocked_projects') or
            observation.get('completeness') != 'all_returned_permitted_lists_under_500'):
        raise ValueError('recurrence_snapshot_incomplete')
    scope = external.permissions(hub, config)
    if observation.get('scope') != scope:
        raise ValueError('recurrence_scope_changed')
    if previous and (scope['original_sha256'] != previous['original_sha256'] or not set(previous['names']) <= set(scope['names'])):
        raise ValueError('recurrence_scope_reduced')
    metadata = observation.get('metadata', {}); lists = metadata.get('lists'); groups = metadata.get('groups')
    snapshots = observation.get('lists')
    if (not isinstance(lists, list) or not isinstance(groups, list) or not isinstance(snapshots, dict) or
            len({r['id'] for r in lists}) != len(lists) or set(snapshots) != {r['id'] for r in lists}):
        raise ValueError('recurrence_snapshot_incomplete')
    seen = set()
    for listing in lists:
        rows = snapshots[listing['id']]
        if not isinstance(rows, list) or len(rows) >= 500 or listing.get('total', len(rows)) != len(rows):
            raise ValueError('recurrence_snapshot_incomplete')
        for row in rows:
            rid = _uuid(row.get('id'))
            if (rid in seen or row.get('list_id', listing['id']) != listing['id'] or
                    row.get('list') != listing['name'] or not row.get('version')):
                raise ValueError('recurrence_snapshot_invalid')
            seen.add(rid)
    sync_module.authority_module().validate_expected_lists(hub, config, observation)
    return copy.deepcopy(observation)


def _binding_identity(binding):
    return {k: binding.get(k) for k in ('layout', 'list_id', 'list_name', 'parent_id', 'account_id', 'native_group_id', 'archive')}


def _active(sync_module, hub, config, pid, exclusive=True):
    binding = config['projects'][pid]
    if binding.get('archive') or pid not in sync_module.registered(hub):
        raise ValueError('recurrence_active_project_required')
    if exclusive and (binding.get('layout') != 'project_list' or binding.get('parent_id') is not None):
        raise ValueError('recurrence_exclusive_project_list_required')
    if exclusive and sum(b.get('list_id') == binding['list_id'] for b in config['projects'].values()) != 1:
        raise ValueError('recurrence_exclusive_project_list_required')
    return binding


def _marker(notes):
    # Даже цитата служебного маркера не становится подтверждением принадлежности.
    return any(line.lstrip(' >\t').startswith(('Хаб:', 'Hub Task ID:', 'Hub project:', '--- Hub metadata', '--- /Hub metadata'))
               for line in (notes or '').splitlines())


def _target(sync_module, hub, config, target, observation):
    if not isinstance(target, dict) or set(target) != {'project_id', 'task_id', 'live_id', 'completed_id'}:
        raise ValueError('invalid_recurrence_target')
    pid, tid = target['project_id'], target['task_id']; binding = _active(sync_module, hub, config, pid)
    live_id, completed_id = _uuid(target['live_id']), _uuid(target['completed_id'])
    if live_id == completed_id:
        raise ValueError('recurrence_distinct_uuid_required')
    link = binding.get('tasks', {}).get(tid, {})
    if link.get('reminder_id') != live_id or any(k in link for k in ('cancellation', 'external_retirement')) or any(k.startswith('pending_') for k in link):
        raise ValueError('recurrence_live_binding_changed')
    linked = [b.get('parent_id') for b in config['projects'].values()]
    linked += [t.get('reminder_id') for b in config['projects'].values() for t in b.get('tasks', {}).values()]
    linked += [rid for b in config['projects'].values() for rid in b.get('history', {})]
    if sum(isinstance(rid, str) and rid.lower() == live_id.lower() for rid in linked) != 1:
        raise ValueError('recurrence_live_uuid_already_bound')
    if any(isinstance(rid, str) and rid.lower() == completed_id.lower() for rid in linked):
        raise ValueError('recurrence_completed_uuid_already_bound')
    remotes = {r['id']: r for rows in observation['lists'].values() for r in rows}
    live, completed = remotes.get(live_id), remotes.get(completed_id)
    if not live or not completed or bool(live.get('completed')) or not live.get('repeat') or completed.get('completed') is not True:
        raise ValueError('recurrence_open_repeating_and_completed_required')
    for row in (live, completed):
        if row.get('list_id', binding['list_id']) != binding['list_id'] or row.get('list') != binding['list_name'] or row.get('parent_id') is not None:
            raise ValueError('recurrence_remote_ownership_changed')
    if _marker(completed.get('notes')):
        raise ValueError('recurrence_completed_identity_marker_forbidden')
    if _marker(live.get('notes')) and sync_module.creation_identity(live, sync_module.compact_identities(config)) != (pid, tid):
        raise ValueError('recurrence_live_identity_changed')
    return dict(target, binding_identity=_binding_identity(binding), live_snapshot=copy.deepcopy(live), completed_snapshot=copy.deepcopy(completed))


def _reference(plan, digest):
    return dict(plan=f"ai/reminders-recurrence/{plan['operation']}/plan.json", sha256=digest,
                state_receipt=_sha(_encoded(dict(kind=plan['kind'], operation=plan['operation'], plan_sha256=digest, phase='complete'))))


def _after(plan, digest):
    result = json.loads(plan['config_raw']); ref = _reference(plan, digest)
    for item in plan['items']:
        binding = result['projects'][item['project_id']]
        if plan['kind'] == 'confirmed_recurrence':
            binding.setdefault('history', {})[item['completed_id']] = dict(original_id=item['live_id'], task_id=item['task_id'], project_id=item['project_id'], confirmation_receipt=ref)
        else:
            binding['history'][item['completed_id']]['absence_receipt'] = ref
    return result


def _state(plan, digest, phase):
    before = json.loads(plan['config_raw']); after = _after(plan, digest)
    return dict(version=1, kind=plan['kind'], operation=plan['operation'], plan_sha256=digest, phase=phase,
                receipt=_reference(plan, digest)['state_receipt'], before_config=before, after_config=after,
                before_config_sha256=plan['config_sha256'], after_config_sha256=_sha(_encoded(after)))


def _read_state(path, plan, digest, complete=False):
    raw = _bytes(path.with_name('state.json'))
    for phase in ('complete',) if complete else ('prepared', 'complete'):
        if raw == _encoded(_state(plan, digest, phase)):
            return phase
    raise ValueError('recurrence_state_receipt_changed')


def _publish(hub, plan):
    raw = _encoded(plan)
    if len(raw) > LIMIT: raise ValueError('recurrence_file_too_large')
    root = _path(hub / 'ai/reminders-recurrence'); root.mkdir(exist_ok=True)
    directory = root / plan['operation']; directory.mkdir()
    path = directory / 'plan.json'
    with path.open('xb') as handle:
        handle.write(raw); handle.flush(); os.fsync(handle.fileno())
    digest = _sha(raw); _write_state(path.with_name('state.json'), _state(plan, digest, 'prepared'))
    return dict(plan=str(path), sha256=digest, items=copy.deepcopy(plan['items']))


def _read_plan(path, digest):
    path = _path(path); raw = _bytes(path)
    if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest) or _sha(raw) != digest:
        raise ValueError('recurrence_plan_checksum_mismatch')
    plan = json.loads(raw); hub = _path(plan['hub']); _uuid(plan['operation'])
    if (plan.get('version') != 1 or plan.get('kind') not in KINDS or
            path != hub / 'ai/reminders-recurrence' / plan['operation'] / 'plan.json' or
            _sha(plan['config_raw'].encode()) != plan['config_sha256'] or
            plan.get('snapshot_sha256') != {lid: _sha(_encoded(rows)) for lid, rows in plan['observation']['lists'].items()}):
        raise ValueError('invalid_recurrence_plan')
    return path, plan, hub


def _plan(hub, config_raw, observation, kind, items, intent=None):
    return dict(version=1, operation=str(uuid.uuid4()), kind=kind, hub=str(hub), config_raw=config_raw.decode(),
                config_sha256=_sha(config_raw), observation=observation,
                snapshot_sha256={lid: _sha(_encoded(rows)) for lid, rows in observation['lists'].items()},
                items=copy.deepcopy(items), user_intent=copy.deepcopy(intent))


def preview(hub, target, user_intent, native=None, sync_module=None):
    """Прямое решение пользователя содержит точные UUID и серию; названия не сопоставляются."""
    selected = sync_module or sync; hub = _path(hub)
    if (not isinstance(user_intent, dict) or user_intent.get('confirmed') is not True or
            not isinstance(user_intent.get('statement'), str) or not user_intent['statement'].strip() or user_intent.get('target') != target):
        raise ValueError('exact_user_recurrence_intent_required')
    with selected.authority_module().locked(hub):
        config, raw = _config(hub, selected); authority = selected.authority_module(); authority.validate_policy(hub, config)
        native = native or selected.Native(config); _active(selected, hub, config, target['project_id'])
        authority.validate_target(selected, hub, config, target['project_id'], native)
        observation = _observation(selected, hub, config, native)
        item = _target(selected, hub, config, target, observation)
        if _bytes(hub / 'ai/reminders-sync.json') != raw: raise ValueError('recurrence_config_changed')
        return _publish(hub, _plan(hub, raw, observation, 'confirmed_recurrence', [item], user_intent))


def apply(path, digest, native=None, sync_module=None):
    """Возобновление допускает только точный исходник либо собственный записанный результат."""
    selected = sync_module or sync; path, plan, hub = _read_plan(path, digest)
    with selected.authority_module().locked(hub):
        phase = _read_state(path, plan, digest); config, current_raw = _config(hub, selected)
        before = json.loads(plan['config_raw']); after = _after(plan, digest); after_raw = _encoded(after)
        if current_raw not in (plan['config_raw'].encode(), after_raw) or phase == 'complete' and current_raw != after_raw:
            raise ValueError('recurrence_config_cas_conflict')
        authority = selected.authority_module(); authority.validate_policy(hub, config)
        native = native or selected.Native(config)
        for item in plan['items']:
            _active(selected, hub, config, item['project_id'], exclusive=plan['kind'] == 'confirmed_recurrence')
        for pid in sorted({item['project_id'] for item in plan['items']}):
            authority.validate_target(selected, hub, config, pid, native)
        fresh = _observation(selected, hub, config, native, previous=plan['observation']['scope'])
        if fresh != plan['observation']:
            raise ValueError('recurrence_snapshot_changed')
        if plan['kind'] == 'confirmed_recurrence':
            target = {k: plan['items'][0][k] for k in ('project_id', 'task_id', 'live_id', 'completed_id')}
            intent = plan['user_intent']
            if (intent.get('confirmed') is not True or intent.get('target') != target or not intent.get('statement', '').strip() or
                    _target(selected, hub, before, target, fresh) != plan['items'][0]):
                raise ValueError('recurrence_confirmation_changed')
        else:
            present = {r['id'] for rows in fresh['lists'].values() for r in rows}
            for item in plan['items']:
                if item['completed_id'] in present: raise ValueError('recurrence_history_returned')
                if before['projects'][item['project_id']]['history'][item['completed_id']] != item['prior_history']:
                    raise ValueError('recurrence_history_changed')
                _history_series(selected, hub, config, item['project_id'], config['projects'][item['project_id']], item['prior_history'], native, observation=fresh)
        if _bytes(hub / 'ai/reminders-sync.json') != current_raw: raise ValueError('recurrence_config_cas_conflict')
        if current_raw != after_raw:
            _write(hub / 'ai/reminders-sync.json', after)
        if _bytes(hub / 'ai/reminders-sync.json') != after_raw: raise ValueError('recurrence_config_readback_failed')
        _write_state(path.with_name('state.json'), _state(plan, digest, 'complete'))
        _read_state(path, plan, digest, complete=True)
        return dict(config=after, items=copy.deepcopy(plan['items']), applied=True)


def _receipt(hub, ref, kind):
    if (not isinstance(ref, dict) or set(ref) != {'plan', 'sha256', 'state_receipt'} or
            not isinstance(ref.get('plan'), str) or not re.fullmatch(r'ai/reminders-recurrence/[0-9a-f-]{36}/plan.json', ref['plan'])):
        raise ValueError('recurrence_receipt_required')
    path, plan, plan_hub = _read_plan(Path(hub) / ref['plan'], ref['sha256'])
    if plan_hub != _path(hub) or plan['kind'] != kind or ref != _reference(plan, ref['sha256']):
        raise ValueError('recurrence_receipt_changed')
    _read_state(path, plan, ref['sha256'], complete=True)
    return plan


def validate_confirmed(hub, remote, binding, history):
    """Служебный код отсутствует: доверяем только точному принятому свидетельству."""
    plan = _receipt(hub, history.get('confirmation_receipt'), 'confirmed_recurrence')
    item = plan['items'][0]; pid, tid, rid = item['project_id'], item['task_id'], item['completed_id']
    expected = _after(plan, history['confirmation_receipt']['sha256'])['projects'][pid]['history'][rid]
    # Отдельная квитанция отсутствия не меняет подтверждение самой связи.
    current = {k: v for k, v in history.items() if k != 'absence_receipt'}
    link = binding.get('tasks', {}).get(tid, {})
    if (current != expected or _binding_identity(binding) != item['binding_identity'] or
            link.get('reminder_id') != item['live_id'] or any(k in link for k in ('cancellation', 'external_retirement')) or
            any(k.startswith('pending_') for k in link) or _marker(remote.get('notes')) or
            any(remote.get(k) != item['completed_snapshot'].get(k) for k in ('id', 'completed', 'list', 'parent_id')) or
            remote.get('list_id', binding['list_id']) != item['completed_snapshot'].get('list_id', binding['list_id'])):
        raise ValueError('invalid_confirmed_recurrence_history')
    return True


def _metadata_identity(observation):
    return {key: {r['id']: {k: r.get(k) for k in fields} for r in observation['metadata'][key]}
            for key, fields in (('lists', ('id', 'name', 'account_id')), ('groups', ('id', 'name', 'account_id')))}


def _history_series(sync_module, hub, config, pid, binding, history, native, observation=None):
    """Указатель истории сохраняется и после доказанной штатной отмены серии."""
    tid = history.get('task_id'); link = binding.get('tasks', {}).get(tid, {})
    if (history.get('project_id') != pid or not link.get('reminder_id') or
            history.get('original_id') != link['reminder_id'] or any(k.startswith('pending_') for k in link)):
        raise ValueError('recurrence_absence_live_binding_changed')
    stopped = [kind for kind in ('external_retirement', 'cancellation') if kind in link]
    if not stopped:
        return link
    if len(stopped) != 1:
        raise ValueError('recurrence_absence_ambiguous_cancellation')
    # При проверке части истории передаём штатному валидатору полную текущую привязку.
    current = config['projects'][pid]
    if current.get('tasks', {}).get(tid) != link or _binding_identity(current) != _binding_identity(binding):
        raise ValueError('recurrence_absence_live_binding_changed')
    native = native or sync_module.Native(config)
    row = sync_module.HubProject(hub, pid).rows().get(tid)
    if row is None:
        raise ValueError('recurrence_absence_canonical_task_missing')
    if stopped[0] == 'external_retirement':
        module = sync_module.external_retirement_module()
        if module is None: raise ValueError('recurrence_absence_retirement_support_missing')
        arguments = {'observation': observation} if observation is not None else {}
        valid = module.verify_link(hub, row, link, current, native, **arguments)
    else:
        module = sync_module.cancellation_module()
        if module is None: raise ValueError('recurrence_absence_cancellation_support_missing')
        valid = module.verify_cancelled_link(hub, row, link, current, native)
    if valid is not True:
        raise ValueError('recurrence_absence_unverified_cancellation')
    return link


def verified_missing(sync_module, hub, config, pid, binding, native, observation=None):
    """Отсутствие действительно только в свежем полном разрешённом снимке."""
    if binding.get('archive'): return set()
    history = binding.get('history', {})
    if not history: return set()
    sync_module.authority_module().validate_policy(hub, config)
    fresh = _observation(sync_module, _path(hub), config, native, observation=observation)
    present = {r['id'] for rows in fresh['lists'].values() for r in rows}; result = set()
    for rid, entry in history.items():
        ref = entry.get('absence_receipt')
        if ref is None:
            if rid not in present: raise ValueError('recurrence_absence_receipt_required')
            continue
        plan = _receipt(hub, ref, 'missing_recurrence')
        items = [i for i in plan['items'] if i['project_id'] == pid and i['completed_id'] == rid]
        if len(items) != 1: raise ValueError('recurrence_absence_receipt_subject_changed')
        item = items[0]
        if rid in present: raise ValueError('recurrence_history_returned')
        expected = dict(item['prior_history'], absence_receipt=ref)
        link = _history_series(sync_module, hub, config, pid, binding, entry, native, observation=fresh)
        if (entry != expected or _binding_identity(binding) != item['binding_identity'] or
                link.get('reminder_id') != item['live_id']):
            raise ValueError('recurrence_absence_history_changed')
        previous = plan['observation']
        if (fresh['scope']['original_sha256'] != previous['scope']['original_sha256'] or
                not set(previous['scope']['names']) <= set(fresh['scope']['names'])):
            raise ValueError('recurrence_scope_reduced')
        old, new = _metadata_identity(previous), _metadata_identity(fresh)
        if any(new[key].get(rid) != value for key in old for rid, value in old[key].items()):
            raise ValueError('recurrence_absence_metadata_changed')
        result.add(rid)
    return result


def prepare_missing(sync_module, hub, config, observation, apply=False, native=None, project=None):
    """Сохраняет прежнюю историю и полное наблюдение; не отменяет действующую серию."""
    hub = _path(hub)
    if not any(b.get('history') and not b.get('archive') and (project is None or pid == project) for pid, b in config['projects'].items()):
        return dict(config=config, items=[])
    with sync_module.authority_module().locked(hub):
        sync_module.authority_module().validate_policy(hub, config)
        fresh = _observation(sync_module, hub, config, native, observation=observation)
        present = {r['id'] for rows in fresh['lists'].values() for r in rows}; items = []
        for pid, binding in config['projects'].items():
            if project is not None and pid != project: continue
            if binding.get('archive'): continue
            existing = {rid: h for rid, h in binding.get('history', {}).items() if h.get('absence_receipt')}
            if existing:
                # Проверяем существующие квитанции, не требуя квитанций для ещё не принятых исчезновений.
                narrow = dict(binding, history=existing)
                verified_missing(sync_module, hub, config, pid, narrow, native, observation=fresh)
            for rid, history in binding.get('history', {}).items():
                if rid in present or history.get('absence_receipt'): continue
                _active(sync_module, hub, config, pid, exclusive=False); _uuid(rid)
                _history_series(sync_module, hub, config, pid, binding, history, native, observation=fresh)
                items.append(dict(project_id=pid, task_id=history['task_id'], completed_id=rid, live_id=history['original_id'],
                                  prior_history=copy.deepcopy(history), binding_identity=_binding_identity(binding)))
        reports = [dict(project=i['project_id'], task_id=i['task_id'], reminder_id=i['completed_id'], action='recurrence_history_missing') for i in items]
        if not items or not apply: return dict(config=config, items=reports)
        current, raw = _config(hub, sync_module)
        if current != config: raise ValueError('recurrence_config_cas_conflict')
        native = native or sync_module.Native(config)
        again = _observation(sync_module, hub, config, native, previous=fresh['scope'])
        if again != fresh: raise ValueError('recurrence_snapshot_changed')
        plan = _publish(hub, _plan(hub, raw, fresh, 'missing_recurrence', items))
        result = globals()['apply'](plan['plan'], plan['sha256'], native=native, sync_module=sync_module)
        return dict(config=result['config'], items=reports)


def main():
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command', required=True)
    pre = sub.add_parser('preview'); pre.add_argument('--hub', required=True); pre.add_argument('--target', required=True); pre.add_argument('--user-intent', required=True)
    app = sub.add_parser('apply'); app.add_argument('--plan', required=True); app.add_argument('--sha256', required=True)
    args = parser.parse_args()
    result = preview(args.hub, json.loads(_bytes(args.target)), json.loads(_bytes(args.user_intent))) if args.command == 'preview' else apply(args.plan, args.sha256)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
