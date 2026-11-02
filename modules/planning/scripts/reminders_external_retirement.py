#!/usr/bin/env python3
"""Проверенное внешнее исключение: отсутствие только в разрешённой области."""
import argparse
import base64
import binascii
import copy
import importlib.util
import json
import os
import tempfile
from pathlib import Path
import uuid
import zlib


def cancellation_module():
    spec = importlib.util.spec_from_file_location('external_retirement_cancel', Path(__file__).with_name('reminders_cancel.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


cancel = cancellation_module()
sync = cancel.sync
KIND = 'external_retirement'
PACKED_LIMIT = 16_777_216


def permissions(hub, config):
    if cancel.canonical(config['allowlist_file']) != hub / 'ai/reminders-allowlist.json': raise ValueError('unsafe_original_allowlist')
    original = cancel.document_bytes(hub / 'ai/reminders-allowlist.json')
    selected = cancel.canonical(sync.standard_allowlist(config))
    names = json.loads(cancel.document_bytes(selected)).get('names')
    initial = json.loads(original).get('names')
    if (not isinstance(names, list) or not names or len(names) != len(set(names)) or
            any(not isinstance(n, str) or not n for n in names) or not isinstance(initial, list) or not set(initial) <= set(names)):
        raise ValueError('invalid_retirement_permissions')
    return dict(original_sha256=cancel.digest(original), names=sorted(names))


def metadata(native, names):
    value = native.call('list_lists', {})
    if not isinstance(value, dict) or value.get('error') or value.get('errors') or value.get('more') or value.get('has_more'):
        raise ValueError('retirement_metadata_incomplete')
    result = {}
    for key in ('lists', 'groups'):
        rows = value.get(key)
        if not isinstance(rows, list): raise ValueError('retirement_metadata_incomplete')
        for row in rows:
            if not isinstance(row, dict): raise ValueError('invalid_retirement_metadata')
            for field in ('id', 'account_id'): cancel.valid_uuid(row.get(field))
            if not isinstance(row.get('name'), str) or not row['name']: raise ValueError('invalid_retirement_metadata')
        if len({r['id'] for r in rows}) != len(rows): raise ValueError('invalid_retirement_metadata')
        result[key] = copy.deepcopy(rows)
    if len({r['name'] for r in result['lists']}) != len(result['lists']): raise ValueError('ambiguous_list_name')
    if any(r['name'] not in names and r['id'] not in names for r in result['lists']): raise ValueError('unallowed_list_metadata')
    return result


def observe(hub, config, native, previous=None, partial=False):
    """Полный снимок; частичное чтение никогда не доказывает отсутствие UUID."""
    scope = permissions(hub, config)
    if previous and (scope['original_sha256'] != previous['original_sha256'] or not set(previous['names']) <= set(scope['names'])):
        raise ValueError('retirement_scope_reduced')
    before = metadata(native, scope['names']); snapshots = {}; seen = set(); errors = []
    for listing in before['lists']:
        lid = listing['id']
        try:
            value = native.call('find_reminders', dict(list=lid, include_completed=True, limit=500))
            if not isinstance(value, dict) or value.get('error') or value.get('errors'): raise ValueError('retirement_snapshot_error')
            rows = value.get('reminders')
            if (not isinstance(rows, list) or len(rows) >= 500 or value.get('more') or value.get('has_more') or
                    value.get('count', len(rows)) != len(rows) or listing.get('total', len(rows)) != len(rows)):
                raise ValueError('incomplete_retirement_snapshot')
            local_ids = set()
            for row in rows:
                if not isinstance(row, dict): raise ValueError('invalid_retirement_snapshot')
                rid = cancel.valid_uuid(row.get('id'))
                if (rid in seen or rid in local_ids or not row.get('version') or not isinstance(row.get('title'), str) or
                        row.get('list_id', lid) != lid or row.get('list') != listing['name']):
                    raise ValueError('invalid_retirement_snapshot')
                local_ids.add(rid)
            seen.update(local_ids)
            snapshots[lid] = copy.deepcopy(rows)
        except (ValueError, RuntimeError, OSError) as error:
            if not partial:
                raise
            errors.append(dict(list_id=lid, error=str(error)))
    if metadata(native, scope['names']) != before: raise ValueError('retirement_metadata_changed_during_read')
    result = dict(scope=scope, metadata=before, lists=snapshots, completeness='all_returned_permitted_lists_under_500')
    expected = {}
    if sync.authority_enabled(config):
        sync.authority_module().validate_policy(hub, config)
        expected = sync.authority_module().validate_expected_lists(hub, config, result, partial=partial)
    if partial:
        blocked = dict(expected)
        for pid, binding in config['projects'].items():
            for error in errors:
                if binding['list_id'] == error['list_id']:
                    blocked[pid] = error['error']
        result.update(errors=errors, blocked_projects=blocked, complete=not errors and not blocked)
    return result


def absent(observation, ids):
    if set(ids) & {r['id'] for rows in observation['lists'].values() for r in rows}:
        raise ValueError('externally_retired_uuid_active')


def read(path, digest):
    path = cancel.canonical(path); raw = cancel.document_bytes(path)
    if cancel.digest(raw) != digest: raise ValueError('retirement_plan_checksum_mismatch')
    plan = unpack_plan(json.loads(raw)); hub = cancel.canonical(plan['hub'])
    cancel.valid_uuid(plan['operation'])
    if path != hub / 'ai/reminders-external-retirements' / plan['operation'] / 'plan.json' or plan.get('kind') != KIND or plan.get('version') not in (1, 2, 3):
        raise ValueError('invalid_retirement_plan')
    if plan['version'] in (2, 3):
        # В файле конфигурация хранится один раз; исходная строка нужна для побайтного CAS.
        if 'config' in plan or not isinstance(plan.get('config_raw'), str):
            raise ValueError('invalid_retirement_config')
        config = json.loads(plan['config_raw'])
        if not isinstance(config, dict):
            raise ValueError('invalid_retirement_config')
        plan['config'] = config
    state = json.loads(cancel.document_bytes(path.with_name('state.json')))
    if (state.get('sha256') != digest or type(state.get('approved')) is not bool or
            state.get('phase') not in {'preview','intent','canonical','committing','complete'} or
            state['phase'] != 'preview' and not state['approved']): raise ValueError('invalid_retirement_state')
    return path, plan, state


def pending_projects(hub, config):
    pending = set(config.get('external_retirements_pending', {}))
    root = cancel.canonical(Path(hub) / 'ai/reminders-external-retirements')
    if not root.exists(): return pending
    try:
        for directory in root.iterdir():
            path = directory / 'plan.json'; digest = cancel.digest(cancel.document_bytes(path))
            _, plan, state = read(path, digest)
            if state['approved'] and (state['phase'] != 'complete' or any(not committed(config,pid,plan['operation'],digest) for pid in plan['projects'])):
                pending.update(plan['projects'])
    except (OSError, ValueError, KeyError, TypeError): pending.update(config['projects'])
    return pending


def receipt(plan, digest, item):
    return dict(kind=KIND, operation=plan['operation'], plan_sha256=digest, reminder_id=item['reminder_id'])


def committed(config, pid, operation, digest):
    return config.get('external_retirements_completed', {}).get(pid, {}).get(operation) == digest


def changed_config(plan, digest, final=False):
    result = copy.deepcopy(plan['config'])
    for pid in plan['projects']:
        result.setdefault('external_retirements_pending', {})[pid] = digest
    if final:
        for item in plan['items']:
            result['projects'][item['project_id']]['tasks'][item['task_id']]['external_retirement'] = receipt(plan,digest,item)
        for pid in plan['projects']:
            result['external_retirements_pending'].pop(pid)
            result.setdefault('external_retirements_completed', {}).setdefault(pid, {})[plan['operation']] = digest
    return result


def preview(hub, targets, user_intent, native=None):
    hub = cancel.canonical(hub)
    if (not targets or any(set(t) != {'project_id','task_id','reminder_id'} for t in targets) or
            len({(t['project_id'],t['task_id']) for t in targets}) != len(targets) or len({t['reminder_id'] for t in targets}) != len(targets)):
        raise ValueError('invalid_retirement_targets')
    if (not isinstance(user_intent,dict) or user_intent.get('confirmed') is not True or
            not isinstance(user_intent.get('statement'),str) or not user_intent['statement'].strip() or user_intent.get('targets') != targets):
        raise ValueError('exact_user_retirement_intent_required')
    with cancel.locked(hub):
        config = sync.load_config(hub); config_raw = cancel.document_bytes(hub/'ai/reminders-sync.json').decode()
        if json.loads(config_raw)!=config: raise ValueError('retirement_config_cas_conflict')
        scope=permissions(hub,config)
        pids = sorted({t['project_id'] for t in targets})
        registered = {pid:sync.task_project_path(hub, pid, config) for pid in pids if pid in config['projects']}
        if set(pids) & (sync.migration_pending(hub,config) | cancel.pending_projects(hub,config) | set(sync.structure_module().pending_structure_projects(hub,config))):
            raise ValueError('retirement_other_operation_pending')
        items = []; projects = {}
        for pid in pids:
            if pid not in registered or pid not in config['projects']: raise ValueError('unregistered_retirement_project')
            hp = sync.HubProject(hub,pid); binding = config['projects'][pid]
            cancel.valid_uuid(binding['list_id'])
            if binding['list_name'] not in scope['names'] and binding['list_id'] not in scope['names']: raise ValueError('retirement_binding_outside_scope')
            if binding.get('layout','parent')=='parent': cancel.valid_uuid(binding.get('parent_id'))
            before = copy.deepcopy(hp.texts)
            for target in [t for t in targets if t['project_id']==pid]:
                row = hp.rows()[target['task_id']]; link = binding['tasks'][target['task_id']]
                cancel.valid_uuid(target['reminder_id'])
                forbidden_statuses = {'dropped', 'promoted'} if sync.authority_enabled(config) else sync.TERMINAL
                if row['status'] in forbidden_statuses or link != dict(link, reminder_id=target['reminder_id']) or any(k.startswith('pending_') or k in {'cancellation','external_retirement'} for k in link):
                    raise ValueError('retirement_target_binding_changed')
                hp.texts = cancel.cancellation_texts(hp,row)
                items.append(dict(target,link=copy.deepcopy(link),project_path=str(registered[pid])))
            projects[pid] = dict(project_id=pid,before_texts=before,after_texts=hp.texts)
        native = native or sync.Native(config); observation = observe(hub,config,native); absent(observation,[t['reminder_id'] for t in targets])
        plan = dict(version=2,kind=KIND,operation=str(uuid.uuid4()),hub=str(hub),config_raw=config_raw,user_intent=user_intent,items=items,projects=projects,observation=observation)
        return publish_preview(hub, plan)


def bounded_payload(value):
    payload = cancel.encoded(value).encode('utf-8')
    if len(payload) > 2_097_152:
        raise ValueError('file_too_large')
    return payload


def stage_bytes(path, payload):
    with path.open('xb') as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def unpack_plan(plan):
    if plan.get('version') != 3:
        return plan
    if ('config_raw' in plan or 'projects' in plan or
            not isinstance(plan.get('packed'), str)):
        raise ValueError('invalid_retirement_packed')
    try:
        compressed = base64.b64decode(plan['packed'], validate=True)
        decoder = zlib.decompressobj()
        raw = decoder.decompress(compressed, PACKED_LIMIT + 1)
        if len(raw) > PACKED_LIMIT or decoder.unconsumed_tail:
            raise ValueError('retirement_packed_too_large')
        if not decoder.eof or decoder.unused_data:
            raise ValueError('invalid_retirement_packed')
        value = json.loads(raw)
    except (binascii.Error, zlib.error, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError('invalid_retirement_packed') from error
    if (not isinstance(value, dict) or set(value) != {'config_raw', 'projects'} or
            not isinstance(value['config_raw'], str) or not isinstance(value['projects'], dict)):
        raise ValueError('invalid_retirement_packed')
    result = dict(plan)
    result.pop('packed')
    result.update(value)
    return result


def plan_payload(plan):
    payload = cancel.encoded(plan).encode('utf-8')
    if len(payload) <= 2_097_152:
        return payload
    # Сжимаем точные строки без потерь; лимит файла и проверка CAS сохраняются.
    value = {key: plan[key] for key in ('config_raw', 'projects')}
    raw = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if len(raw) > PACKED_LIMIT:
        raise ValueError('retirement_packed_too_large')
    packed = {key: value for key, value in plan.items() if key not in ('config_raw', 'projects')}
    packed.update(version=3, packed=base64.b64encode(zlib.compress(raw)).decode('ascii'))
    return bounded_payload(packed)


def publish_preview(hub, plan):
    # Проверяем размер до создания журнала. Читатели видят план и состояние вместе.
    payload = plan_payload(plan)
    digest = cancel.digest(payload)
    state = bounded_payload(dict(sha256=digest, approved=False, phase='preview'))
    root = cancel.canonical(hub / 'ai/reminders-external-retirements')
    root.mkdir(exist_ok=True)
    folder = root / plan['operation']
    if folder.exists():
        raise ValueError('retirement_operation_exists')
    # Соседняя временная папка не попадает в сканирование активных журналов.
    with tempfile.TemporaryDirectory(prefix='.retirement-preview-', dir=root.parent) as name:
        staging = Path(name)
        stage_bytes(staging / 'plan.json', payload)
        stage_bytes(staging / 'state.json', state)
        cancel.fsync_dir(staging)
        os.rename(staging, folder)
        cancel.fsync_dir(root)
    return dict(plan=str(folder / 'plan.json'), sha256=digest)


def target_block(hub, plan, item):
    hp = sync.HubProject(hub,item['project_id']); tid=item['task_id']
    rows=hp.rows(); row=rows.get(tid)
    expected=plan['projects'][item['project_id']]['after_texts']['future']
    if row is None or row['status']!='dropped' or row['kind']!='future': raise ValueError('invalid_external_retirement_canonical')
    if sync.chunk(hp.texts['future'],'future',tid)[2].rstrip() != sync.chunk(expected,'future',tid)[2].rstrip(): raise ValueError('external_retirement_block_changed')
    return row


def verify_link(hub, row, link, binding, native, observation=None):
    hub=cancel.canonical(hub);ref=link.get('external_retirement',{})
    operation=cancel.valid_uuid(ref.get('operation'));digest=ref.get('plan_sha256')
    _,plan,state=read(hub/'ai/reminders-external-retirements'/operation/'plan.json',digest)
    matches=[i for i in plan['items'] if (i['project_id'],i['task_id'])==(row.get('project_id'),row.get('task_id'))]
    if len(matches)!=1: raise ValueError('invalid_external_retirement_link')
    item=matches[0];pid=item['project_id'];tid=item['task_id']
    if (state['phase']!='complete' or not state['approved'] or ref!=receipt(plan,digest,item) or
            link!={**item['link'],'external_retirement':receipt(plan,digest,item)}): raise ValueError('invalid_external_retirement_receipt')
    config=sync.load_config(hub)
    if sync.task_project_path(hub, pid, config) != Path(item['project_path']): raise ValueError('retirement_project_path_changed')
    if config['projects'].get(pid)!=binding or binding['tasks'].get(tid)!=link: raise ValueError('retirement_binding_argument_stale')
    if not committed(config,pid,operation,digest) or pid in config.get('external_retirements_pending',{}): raise ValueError('retirement_not_committed')
    target_block(hub,plan,item)
    observation=observation or observe(hub,config,native,plan['observation']['scope'])
    prior=plan['observation']['scope'];scope=observation['scope']
    if scope['original_sha256']!=prior['original_sha256'] or not set(prior['names'])<=set(scope['names']): raise ValueError('retirement_scope_reduced')
    absent(observation,[item['reminder_id']])
    return True


def collect(hub, config, pid, native):
    binding=config['projects'][pid];links={tid:link for tid,link in binding.get('tasks',{}).items() if 'external_retirement' in link}
    if not links:return {}
    observation=observe(Path(hub),config,native);rows=sync.HubProject(hub,pid).rows();result={}
    for tid,link in links.items():
        verify_link(hub,rows[tid],link,binding,native,observation)
        result[link['reminder_id']]=copy.deepcopy(link['external_retirement'])
    return result


def apply(path, digest, approve=False, native=None):
    if not approve: raise ValueError('explicit_retirement_approval_required')
    path,plan,state=read(path,digest);hub=Path(plan['hub'])
    with cancel.locked(hub):
        config=sync.load_config(hub);raw=cancel.document_bytes(hub/'ai/reminders-sync.json').decode();native=native or sync.Native(config)
        observation=observe(hub,config,native,plan['observation']['scope']);absent(observation,[i['reminder_id'] for i in plan['items']])
        if state['phase']=='complete':
            for item in plan['items']:
                pid=item['project_id'];binding=config['projects'][pid];verify_link(hub,target_block(hub,plan,item),binding['tasks'][item['task_id']],binding,native,observation)
            return state
        allowed=[plan['config'],changed_config(plan,digest),changed_config(plan,digest,True)]
        raw_allowed=[plan['config_raw'],cancel.encoded(allowed[1]),cancel.encoded(allowed[2])]
        if config not in allowed or raw not in raw_allowed or state['phase'] in {'canonical','committing'} and config==plan['config']: raise ValueError('retirement_config_cas_conflict')
        if state['phase'] in {'canonical','committing'}:
            for project in plan['projects'].values():
                if sync.HubProject(hub,project['project_id']).texts!=project['after_texts']: raise ValueError('retirement_canonical_reverted')
        for item in plan['items']:
            if sync.task_project_path(hub, item['project_id'], config) != Path(item['project_path']): raise ValueError('retirement_project_path_changed')
        for project in plan['projects'].values(): cancel.local_progress(hub,project)
        state.update(approved=True,phase='intent');cancel.durable_json(path.with_name('state.json'),state)
        if sync.load_config(hub)!=config or cancel.document_bytes(hub/'ai/reminders-sync.json').decode()!=raw: raise ValueError('retirement_config_cas_conflict')
        if config==plan['config']:
            cancel.durable_json(hub/'ai/reminders-sync.json',changed_config(plan,digest))
        for project in plan['projects'].values():
            hp,_=cancel.local_progress(hub,project);cancel.write_texts(hp,project)
        state['phase']='canonical';cancel.durable_json(path.with_name('state.json'),state)
        for item in plan['items']:target_block(hub,plan,item)
        current=sync.load_config(hub);current_raw=cancel.document_bytes(hub/'ai/reminders-sync.json').decode()
        if current_raw not in raw_allowed[1:]: raise ValueError('retirement_config_cas_conflict')
        if current not in allowed[1:]: raise ValueError('retirement_config_cas_conflict')
        observe_now=observe(hub,current,native,plan['observation']['scope']);absent(observe_now,[i['reminder_id'] for i in plan['items']])
        state['phase']='committing';cancel.durable_json(path.with_name('state.json'),state)
        if sync.load_config(hub)!=current or cancel.document_bytes(hub/'ai/reminders-sync.json').decode()!=current_raw: raise ValueError('retirement_config_cas_conflict')
        cancel.durable_json(hub/'ai/reminders-sync.json',allowed[2])
        if sync.load_config(hub)!=allowed[2]: raise ValueError('retirement_config_readback_failed')
        for item in plan['items']:target_block(hub,plan,item)
        state.update(phase='complete',observation=observe_now);cancel.durable_json(path.with_name('state.json'),state)
        return state


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['preview','apply','resume','status'])
    parser.add_argument('--hub',type=Path);parser.add_argument('--target',action='append',help='project-id:task-id:UUID');parser.add_argument('--intent',type=Path)
    parser.add_argument('--plan',type=Path);parser.add_argument('--sha256');parser.add_argument('--approve',action='store_true');a=parser.parse_args()
    try:
        if a.command=='preview':
            targets=[dict(zip(('project_id','task_id','reminder_id'),t.split(':'))) for t in a.target or []]
            result=preview(a.hub,targets,json.loads(cancel.document_bytes(a.intent)))
        elif a.command in {'apply','resume'}:result=apply(a.plan,a.sha256,a.approve)
        else:
            _,plan,state=read(a.plan,a.sha256);result=dict(state=state,pending=sorted(pending_projects(Path(plan['hub']),sync.load_config(Path(plan['hub'])))))
        print(cancel.encoded(result),end='')
    except (ValueError,KeyError,TypeError,OSError,RuntimeError) as error:
        print(cancel.encoded(dict(ok=False,error=str(error))),end='');raise SystemExit(1)

if __name__=='__main__':main()
