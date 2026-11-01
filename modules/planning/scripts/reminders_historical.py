"""Узкое доказательство переноса завершённой отмены; старые журналы неизменны."""
import copy
import importlib.util
import json
from pathlib import Path

KEYS = ('layout', 'list_id', 'list_name', 'parent_id', 'account_id', 'native_group_id', 'retired_parent')


def structural(binding):
    return {key: copy.deepcopy(binding[key]) for key in KEYS if key in binding}


def collect(c, hub, config, pid, native):
    binding = config['projects'][pid]
    entries = list(binding.get('tasks', {}).values()) + list(binding.get('history', {}).values())
    if any(any(key.startswith('pending_') for key in entry) for entry in entries):
        raise ValueError('unsupported_cancel_or_pending_binding')
    if any('cancellation' in entry for entry in binding.get('history', {}).values()):
        raise ValueError('historical_history_unsupported')
    result = {}
    for tid, link in binding.get('tasks', {}).items():
        if 'cancellation' not in link: continue
        if not isinstance(link['cancellation'],dict): raise ValueError('invalid_cancelled_link')
        c.valid_uuid(link['cancellation'].get('operation_id'))
        row = c.sync.HubProject(hub, pid).rows().get(tid, {})
        c.verify_cancelled_link(hub, row, link, binding, native)
        reference = link['cancellation']
        path, plan = c.read_plan(hub, hub/'ai/reminders-cancellations'/reference['operation_id']/'plan.json', reference['plan_sha256'])
        if plan['version'] != 1: raise ValueError('historical_requires_legacy_plan')
        item = next(i for i in plan['items'] if i['project_id'] == pid and i['task_id'] == tid)
        c.verify_parent(native, item)
        state = c.read_state(path, plan, reference['plan_sha256'])
        if not state['approved'] or state['items'][item['reminder_id']]['phase'] != 'committed': raise ValueError('historical_requires_committed')
        result[item['reminder_id']] = dict(plan=str(path), plan_sha256=reference['plan_sha256'],
            item_json=c.encoded(item), item_sha256=c.digest(c.encoded(item)),
            receipt_json=c.encoded(reference), receipt_sha256=c.digest(c.encoded(reference)),
            deleted_snapshot=state['items'][item['reminder_id']]['deleted_snapshot'])
    return result


def recheck(c, hub, proofs, native):
    for rid, proof in proofs.items():
        path, plan = c.read_plan(hub, proof['plan'], proof['plan_sha256'])
        item = json.loads(proof['item_json'])
        state = c.read_state(path, plan, proof['plan_sha256'])
        if (item not in plan['items'] or c.digest(proof['item_json']) != proof['item_sha256'] or
                not state['approved'] or state['items'][rid]['phase'] != 'committed' or
                state['items'][rid]['deleted_snapshot'] != proof['deleted_snapshot']): raise ValueError('historical_original_changed')
        if c.native_status(native, path, proof['plan_sha256'], item) != proof['deleted_snapshot']: raise ValueError('historical_deleted_changed')


def build(c, plan, digest, binding):
    before = json.loads(plan['config_raw'])['projects'][plan['project']]
    return dict(protocol=1, contract='legacy-restore-then-active-move-v1', migration_operation=plan['operation'],
        migration_plan=str(Path(plan['hub'])/'ai/reminders-project-lists'/plan['operation']/'plan.json'),
        migration_sha256=digest, project_id=plan['project'], before=structural(before), after=structural(binding),
        historical=copy.deepcopy(plan['historical']), runtime=plan['historical_runtime'],
        old_account_id=plan['account_id'], moved_ids=plan['children'])


def reference(c, plan, digest, binding):
    value = build(c, plan, digest, binding)
    path = Path(plan['hub'])/'ai/historical_binding_migrations'/plan['operation']/'receipt.json'
    return dict(path=str(path), sha256=c.digest(c.encoded(value))), value


def publish(c, plan, digest, binding):
    ref, value = reference(c, plan, digest, binding)
    path = c.canonical(ref['path']); path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != c.encoded(value).encode(): raise ValueError('historical_receipt_changed')
    else: c.durable_json(path, value)


def load(c, hub, config, item, plan, sha):
    pid, rid, tid = item['project_id'], item['reminder_id'], item['task_id']
    binding = config['projects'][pid]
    ref = binding.get('historical_binding_migration', {})
    path = c.canonical(ref.get('path', ''))
    raw = c.document_bytes(path); value = json.loads(raw)
    if c.digest(raw) != ref.get('sha256') or value.get('protocol') != 1 or value.get('contract') != 'legacy-restore-then-active-move-v1': raise ValueError('historical_receipt_pin')
    operation = c.valid_uuid(value['migration_operation'])
    if path != hub/'ai/historical_binding_migrations'/operation/'receipt.json': raise ValueError('historical_receipt_path')
    migration_path = c.canonical(value['migration_plan'])
    if migration_path != hub/'ai/reminders-project-lists'/operation/'plan.json': raise ValueError('historical_migration_path')
    migration_raw = c.document_bytes(migration_path); migration = json.loads(migration_raw)
    state = json.loads(c.document_bytes(migration_path.with_name('state.json')))
    digest = c.digest(migration_raw)
    if (digest != value['migration_sha256'] or migration.get('kind') != 'migration' or migration.get('project') != pid or
            migration.get('operation') != operation or migration.get('hub') != str(hub) or
            state.get('phase') != 'complete' or state.get('approved') is not True or state.get('sha256') != digest or
            state.get('list_id') != binding['list_id'] or config.get('project_list_migrations_completed', {}).get(pid) != digest or
            pid in config.get('project_list_migrations_pending', {})): raise ValueError('historical_migration_uncommitted')
    final = json.loads(state['final_config'])['projects'][pid]
    if value != build(c, migration, digest, final) or structural(binding) != value['after'] or final.get('historical_binding_migration') != ref:
        raise ValueError('historical_binding_changed')
    proof = value['historical'].get(rid, {})
    if (proof.get('plan') != str(c.plan_location(hub, hub/'ai/reminders-cancellations'/plan['operation_id']/'plan.json')) or
            proof.get('plan_sha256') != sha or c.digest(proof['item_json']) != proof['item_sha256'] or json.loads(proof['item_json']) != item or
            c.digest(proof['receipt_json']) != proof['receipt_sha256'] or json.loads(proof['receipt_json']) != c.cancelled_link(item, plan, sha)['cancellation']): raise ValueError('historical_original_changed')
    # Читаем неизменный старый план: соседний проект мог быть архивирован.
    # Текущая привязка проверяется ниже; команды записи требуют активных проектов.
    original_path, original = c.read_plan(hub, proof['plan'], sha, require_active=False)
    state = c.read_state(original_path, original, sha)
    progress = state['items'][rid]
    if (not state['approved'] or progress['phase'] not in {'committed','restoring','restored'} or
            progress.get('deleted_snapshot') != proof['deleted_snapshot'] or proof['deleted_snapshot'].get('state') != 'deleted'): raise ValueError('historical_terminal_changed')
    expected_link=item['link'] if progress['phase']=='restored' else c.cancelled_link(item,plan,sha)
    allowed=[expected_link]
    if progress['phase']=='restoring' and progress.get('relocation',{}).get('phase') in {'canonical_restore','complete'}:allowed.append(item['link'])
    if binding['tasks'].get(tid) not in allowed: raise ValueError('historical_link_changed')
    if (binding.get('layout') != 'project_list' or binding.get('parent_id', 'missing') is not None or
            binding.get('account_id') != value['old_account_id'] or
            config.get('structure', {}).get('list_roles', {}).get(binding['list_id']) != dict(kind='project',project_id=pid) or
            config.get('structure', {}).get('projects', {}).get(pid, {}).get('list_id') != binding['list_id']): raise ValueError('historical_destination_role')
    current = dict(project_id=pid, layout='project_list', parent_id=None, list_id=binding['list_id'], list_name=binding['list_name'],
                   account_id=binding['account_id'], native_group_id=binding['native_group_id'])
    c.guard_bindings(config, [current], hub)
    if c.verification_module().runtime(c,config) != value['runtime']: raise ValueError('historical_runtime_changed')
    if c.allowlist(config, 'parent')[1] != plan['allowlist_sha256'] or item['list_name'] not in c.allowlist(config, 'parent')[0]: raise ValueError('historical_original_permissions')
    # Предыдущая область остаётся точной; производные дети изменились только по плану миграции.
    parent = value['after']['retired_parent']['snapshot']; source = migration['source'][item['parent_id']]
    if parent.get('id') != item['parent_id'] or parent.get('list_id') != item['list_id'] or parent.get('list') != item['list_name'] or parent.get('parent_id') is not None or parent.get('subtasks'):
        raise ValueError('historical_parent_changed')
    clean = lambda row: {k:v for k,v in row.items() if k not in {'version','subtasks'}}
    if clean(parent) != clean(source) or clean(source) != clean(item['parent']): raise ValueError('historical_parent_changed')
    steps=json.loads(c.document_bytes(migration_path.with_name('state.json')))['steps']
    if set(steps)!=set(migration['children']) or any(step.get('status') != 'done' for step in steps.values()): raise ValueError('historical_moves_incomplete')
    return value


def selected(config, plan):
    return plan['version']==1 and any(config['projects'][i['project_id']].get('historical_binding_migration') for i in plan['items'])


def list_snapshot(c, native, binding):
    response = native.call('find_reminders', dict(list=binding['list_id'], include_completed=True, limit=500))
    rows = response.get('reminders')
    if not isinstance(rows,list) or response.get('more') or response.get('has_more') or len(rows)>=500 or response.get('count',len(rows))!=len(rows): raise ValueError('historical_incomplete_list')
    result = {}
    for row in rows:
        rid = c.valid_uuid(row['id'])
        if rid in result: raise ValueError('historical_duplicate_row')
        full = native.call('get_reminder',dict(id=rid))
        if full.get('list_id') != binding['list_id'] or full.get('list') != binding['list_name'] or not full.get('version'): raise ValueError('historical_list_changed')
        result[rid] = full
    return result


def scope(c, hub, config, item, plan, sha, native):
    binding = config['projects'][item['project_id']]
    if binding.get('historical_binding_migration'):
        receipt = load(c,hub,config,item,plan,sha)
        parent = receipt['after']['retired_parent']['snapshot']
        destination = structural(binding)
        c.verify_list_identity(native,destination)
        # Старый контейнер тоже сохраняет учётную запись и политику общего доступа.
        meta = native.call('list_lists',{})
        old = [r for r in meta['lists'] if r['id']==item['list_id'] or r['name']==item['list_name']]
        if len(old)!=1 or old[0]['id']!=item['list_id'] or old[0]['name']!=item['list_name'] or old[0]['account_id']!=receipt['old_account_id'] or old[0].get('shared',False) is not False: raise ValueError('historical_source_identity')
        return parent,destination,binding['historical_binding_migration']
    if c.guard_bindings(config,[item],hub)!=plan['allowlist_sha256']: raise ValueError('allowlist_checksum_mismatch')
    return item['parent'],None,None


def without_target(row, rid):
    value = copy.deepcopy(row)
    children = [r for r in value.get('subtasks',[]) if r.get('id')!=rid]
    if children:value['subtasks']=children
    else:value.pop('subtasks',None)
    return value


def check_lists(c,native,item,row,owned=None):
    rid=item['reminder_id']
    for key,binding in [('old_members',item),('new_members',row['destination'])]:
        if binding is None:continue
        actual=list_snapshot(c,native,binding);expected=copy.deepcopy(row[key])
        for owned_id, snapshot in (owned or {}).items():
            if owned_id in actual:
                if actual[owned_id] != snapshot: raise ValueError('historical_owned_row_changed')
                actual.pop(owned_id)
        actual.pop(rid,None);expected.pop(rid,None)
        if key=='old_members':
            for owner_id in owned or {}:
                actual={key:without_target(value,owner_id) for key,value in actual.items()}
                expected={key:without_target(value,owner_id) for key,value in expected.items()}
            parent=item['parent_id']
            if parent in actual:actual[parent]=without_target(actual[parent],rid)
            if parent in expected:expected[parent]=without_target(expected[parent],rid)
        if actual!=expected:raise ValueError('historical_scope_snapshot_changed')


def restore_preview(c,hub,path,sha,config,native,plan,state):
    if json.loads(c.document_bytes(hub/'ai/reminders-sync.json'))!=config:raise ValueError('config_argument_stale')
    if not state['approved'] or any(p['phase']!='committed' for p in state['items'].values()):raise ValueError('cancel_not_rollbackable')
    items={}
    for item in plan['items']:
        rid=item['reminder_id'];binding=config['projects'][item['project_id']]
        if binding['tasks'][item['task_id']]!=c.cancelled_link(item,plan,sha):raise ValueError('cancelled_link_changed')
        cleanup_spec=importlib.util.spec_from_file_location('historical_old_list_cleanup',Path(__file__).with_name('reminders_old_list_cleanup.py'))
        cleanup=importlib.util.module_from_spec(cleanup_spec);cleanup_spec.loader.exec_module(cleanup)
        if cleanup.restore_refused_for_binding(hub,binding,rid):raise ValueError('historical_restore_retired_by_user_choice')
        parent,destination,reference=scope(c,hub,config,item,plan,sha,native)
        effective=dict(item,parent=parent);c.verify_parent(native,effective)
        remote=c.native_status(native,path,sha,item)
        if remote!=state['items'][rid]['deleted_snapshot']:raise ValueError('historical_deleted_changed')
        hp=c.cancelled_block(hub,item)
        row=dict(remote=remote,parent=parent,destination=destination,historical_binding_migration=reference,
                 before_texts=hp.texts,after_texts=c.restored_texts(hp,item),old_members=list_snapshot(c,native,item),
                 new_members=list_snapshot(c,native,destination) if destination else {})
        if rid in row['old_members'] or rid in row['new_members'] or any(r.get('parent_id')==rid for r in row['old_members'].values()):raise ValueError('historical_uuid_active')
        items[rid]=row
    value=dict(version=3,purpose='historical_composite_restore',operation_id=plan['operation_id'],plan_sha256=sha,
               items=items,config=copy.deepcopy(config),config_sha256=c.digest(c.document_bytes(hub/'ai/reminders-sync.json')),
               allowlist_sha256=c.allowlist(config,'parent')[1],standard_allowlist_sha256=c.allowlist(config,'project_list')[1],
               runtime=c.verification_module().runtime(c,config))
    token=c.digest(c.encoded(value));target=c.restore_path_for(path,token)
    if not target.exists():c.durable_json(target,value)
    elif c.digest(target.read_bytes())!=token:raise ValueError('restore_checksum_mismatch')
    return dict(ok=True,path=str(target),sha256=token)


def restore_config(c,hub,config,plan,sha,token):
    actual=json.loads(c.document_bytes(hub/'ai/reminders-sync.json'))
    if actual!=config:raise ValueError('config_argument_stale')
    expected=copy.deepcopy(token['config']);live=copy.deepcopy(actual)
    for item in plan['items']:
        pid,tid=item['project_id'],item['task_id']
        link=live['projects'][pid]['tasks'][tid]
        if link not in [item['link'],c.cancelled_link(item,plan,sha)]:raise ValueError('historical_link_changed')
        live['projects'][pid]['tasks'][tid]=copy.deepcopy(item['link']);expected['projects'][pid]['tasks'][tid]=copy.deepcopy(item['link'])
    if live!=expected:raise ValueError('historical_restore_config_changed')
    if (token.get('purpose')!='historical_composite_restore' or token.get('version')!=3 or token.get('runtime')!=c.verification_module().runtime(c,actual) or
            token['allowlist_sha256']!=c.allowlist(actual,'parent')[1] or token['standard_allowlist_sha256']!=c.allowlist(actual,'project_list')[1]):raise ValueError('historical_restore_permissions_runtime')
    return actual


def observed(c,native,path,sha,item,row,progress):
    rid=item['reminder_id'];phase=progress.get('relocation',{}).get('phase')
    if phase in {'move_pending','move_confirmed','canonical_restore','complete'} and row['destination']:
        current=native.call('get_reminder',dict(id=rid))
        destination=row['destination'];expected=row['remote']['snapshot']
        clean=lambda r:{k:v for k,v in r.items() if k not in {'version','deleted_version','list','list_id','parent_id'}}
        if (current.get('list_id')==destination['list_id'] and current.get('list')==destination['list_name'] and 'parent_id' not in current and
                current.get('id')==rid and current.get('version') and clean(current)==clean(expected)):
            return dict(state='active',version=current['version'],snapshot=current)
    return c.native_status(native,path,sha,item)


def execute(c,hub,path,sha,config,native,plan,state,token,token_sha):
    restore_config(c,hub,config,plan,sha,token)
    if not state['approved'] or state.get('restore_token') not in {None,token_sha}:raise ValueError('historical_restore_state')
    c.capabilities(native,plan.get('concurrency_policy','strict'),1,plan['items'])
    fresh={}
    # Весь пакет проверяется до первой мутации, включая оба списка и тексты.
    for item in plan['items']:
        rid=item['reminder_id'];row=token['items'][rid];progress=state['items'][rid]
        if progress['phase'] not in {'committed','restoring','restored'}:raise ValueError('historical_restore_state')
        parent,destination,reference=scope(c,hub,config,item,plan,sha,native)
        if (parent!=row['parent'] or destination!=row['destination'] or reference!=row['historical_binding_migration']):raise ValueError('historical_restore_scope_changed')
        c.verify_parent(native,dict(item,parent=row['parent']))
        local=dict(item,before_texts=row['after_texts'],after_texts=row['before_texts'])
        hp,_=c.local_progress(hub,local,True);c.validate_task_set(hp,row['after_texts'])
        remote=observed(c,native,path,sha,item,row,progress)
        phase=progress.get('relocation',{}).get('phase')
        if remote['state']=='deleted':
            if remote!=row['remote'] or phase not in {None,'remote_restore_old_pending'}:raise ValueError('historical_deleted_changed')
        else:
            if progress['phase'] not in {'restoring','restored'} or phase is None:raise ValueError('external_restore_requires_review')
            same=c.same_fields(remote['snapshot'],row['remote']['snapshot'])
            in_new=destination is not None and remote['snapshot']['list_id']==destination['list_id']
            if not same and not (in_new and phase in {'move_pending','move_confirmed','canonical_restore','complete'}):raise ValueError('historical_active_changed')
            receipt=progress.get('relocation',{}).get('new_snapshot' if in_new else 'old_snapshot')
            if receipt is not None and remote!=receipt:raise ValueError('historical_active_changed')
        fresh[rid]=remote
    owned={rid:remote['snapshot'] for rid,remote in fresh.items() if remote['state']=='active'}
    for item in plan['items']:check_lists(c,native,item,token['items'][item['reminder_id']],owned)
    state['restore_token']=token_sha;c.durable_json(path.with_name('state.json'),state)
    for item in plan['items']:
        rid=item['reminder_id'];row=token['items'][rid];progress=state['items'][rid]
        if progress['phase']=='restored':continue
        progress['phase']='restoring';step=progress.setdefault('relocation',{});remote=fresh[rid]
        def save():c.durable_json(path.with_name('state.json'),state)
        if remote['state']=='deleted':
            step['phase']='remote_restore_old_pending';save()
            check_lists(c,native,item,row,owned);c.verify_parent(native,dict(item,parent=row['parent']))
            c.native_status(native,path,sha,item)
            native.call('hub_restore_reminder',dict(plan=str(path),plan_sha256=sha,id=rid,version=remote['version'],restore_plan=str(c.restore_path_for(path,token_sha)),restore_sha256=token_sha))
            remote=c.native_status(native,path,sha,item)
            if remote['state']!='active' or not c.same_fields(remote['snapshot'],row['remote']['snapshot']):raise ValueError('historical_restore_readback')
        owned[rid]=remote['snapshot']
        if remote['snapshot']['list_id']==item['list_id']:
            step.update(phase='remote_restore_old_confirmed',old_snapshot=remote);save()
            if row['destination']:
                check_lists(c,native,item,row,owned);restore_config(c,hub,config,plan,sha,token)
                scope(c,hub,config,item,plan,sha,native)
                before=native.call('get_reminder',dict(id=rid))
                if before!=remote['snapshot']:raise ValueError('historical_before_move_changed')
                step['phase']='move_pending';save()
                native.call('update_reminder',dict(id=rid,version=before['version'],list=row['destination']['list_id'],parent_id=None))
                remote=observed(c,native,path,sha,item,row,progress)
                if remote['snapshot']['list_id']!=row['destination']['list_id']:raise ValueError('historical_move_readback')
        owned[rid]=remote['snapshot']
        step.update(phase='move_confirmed',new_snapshot=remote);save()
        check_lists(c,native,item,row,owned)
        step['phase']='canonical_restore';save()
        local=dict(item,before_texts=row['after_texts'],after_texts=row['before_texts']);hp,_=c.local_progress(hub,local,True)
        c.write_texts(hp,local,True)
        actual=restore_config(c,hub,config,plan,sha,token);actual['projects'][item['project_id']]['tasks'][item['task_id']]=copy.deepcopy(item['link'])
        c.durable_json(hub/'ai/reminders-sync.json',actual);config.clear();config.update(actual)
        if observed(c,native,path,sha,item,row,progress)!=remote:raise ValueError('historical_final_remote_changed')
        if c.sync.HubProject(hub,item['project_id']).texts!=row['after_texts']:raise ValueError('historical_canonical_readback')
        progress.update(phase='restored',restored_snapshot=remote);step['phase']='complete';save()
    return dict(ok=True,operation_id=plan['operation_id'],state='restored',path=str(path),sha256=sha)


def status(c,hub,path,sha,config,native,plan,state):
    if json.loads(c.document_bytes(hub/'ai/reminders-sync.json'))!=config:raise ValueError('config_argument_stale')
    result=[]
    for item in plan['items']:
        rid=item['reminder_id'];progress=state['items'][rid]
        parent,destination,reference=scope(c,hub,config,item,plan,sha,native)
        c.verify_parent(native,dict(item,parent=parent))
        if progress['phase']=='committed':
            c.cancelled_block(hub,item)
            if config['projects'][item['project_id']]['tasks'][item['task_id']]!=c.cancelled_link(item,plan,sha):raise ValueError('historical_link_changed')
            remote=c.native_status(native,path,sha,item)
            if remote!=progress['deleted_snapshot']:raise ValueError('historical_deleted_changed')
        elif progress['phase'] in {'restoring','restored'}:
            token=c._restore_plan(path,plan,sha,state.get('restore_token'))
            remote=observed(c,native,path,sha,item,token['items'][rid],progress)
            if progress['phase']=='restored':
                if remote!=progress['restored_snapshot'] or config['projects'][item['project_id']]['tasks'][item['task_id']]!=item['link']:raise ValueError('historical_restored_changed')
        else:raise ValueError('historical_restore_state')
        result.append(dict(project_id=item['project_id'],task_id=item['task_id'],phase=progress['phase'],**remote))
    return dict(ok=True,operation_id=plan['operation_id'],items=result)
