#!/usr/bin/env python3
"""Один явно разрешённый искусственный цикл; реальные задачи и их файлы не меняются."""
import copy,json,os,subprocess
from pathlib import Path
PHASES={'prepared','deleting','deleted','restoring','restored','cleanup_deleting','cleaned'}
PURPOSE='project_list_verification'

def title(op):return 'Проверка восстановления списка: '+op

def notes(op):return 'Тестовая запись операции '+op+'. Не является задачей проекта.'

def read(c,path):
    path=c.canonical(path)
    if path.stat().st_size>2_097_152:raise ValueError('verification_file_too_large')
    return json.loads(path.read_bytes())

def normal(config,op):
    value=copy.deepcopy(config)
    value['project_list_verifications'][op]['plan_sha256']=None
    return value

def simple(snapshot,op,rid,lid,name):
    return (set(snapshot)<= {'id','version','list','list_id','title','notes','completed'} and
            snapshot.get('id')==rid and snapshot.get('list_id')==lid and snapshot.get('list')==name and
            snapshot.get('title')==title(op) and snapshot.get('notes')==notes(op) and
            snapshot.get('completed',False) is False and isinstance(snapshot.get('version'),str) and bool(snapshot['version']))

def migration(c,hub,path,sha,config):
    path=c.canonical(path);p=read(c,path);state=read(c,path.with_name('state.json'))
    if (path!=hub/'ai/reminders-project-lists'/p['operation']/'plan.json' or c.digest(path.read_bytes())!=sha or p.get('kind')!='migration' or
            p.get('hub')!=str(hub) or p.get('project')!='content-system' or p.get('list_name')!='Система контента' or
            state.get('sha256')!=sha or state.get('phase')!='destination_ready' or state.get('steps')!={} or state.get('group_done') is not True or
            config.get('project_list_migrations_pending',{}).get('content-system')!=sha):raise ValueError('verification_destination_not_ready')
    lid=c.valid_uuid(state['list_id']);aid=c.valid_uuid(p['account_id']);gid=c.valid_uuid(p['group_id'])
    old=json.loads(p['config_raw']);old.setdefault('project_list_migrations_pending',{})['content-system']=sha
    return p,state,dict(project_id='content-system',layout='project_list',parent_id=None,list_id=lid,list_name=p['list_name'],account_id=aid,native_group_id=gid),old

def unbound(c,hub,config,rid,tid,op):
    for binding in config['projects'].values():
        if rid==binding.get('parent_id') or rid in binding.get('history',{}) or tid in binding.get('tasks',{}) or any(rid==v.get('reminder_id') for v in binding.get('tasks',{}).values()):raise ValueError('verification_real_binding_collision')
    root=c.canonical(hub/'ai/reminders-cancellations')
    if root.exists():
        for folder in root.iterdir():
            c.canonical(folder)
            if folder.name==op:continue
            for name in ('plan.json','state.json'):
                path=c.canonical(folder/name)
                if path.exists():
                    data=path.read_text()
                    if rid in data or tid in data:raise ValueError('verification_old_plan_collision')

def runtime(c,config):
    binary=c.canonical(config['cancellation_binary'])
    return {'binary_sha256':c.digest(binary.read_bytes()),'os_build':subprocess.check_output(['sw_vers','-buildVersion'],text=True).strip()}

def bootstrap(c,hub,config,native,op,migration_path,migration_sha,approve=False):
    if not approve:raise ValueError('explicit_verification_consent_required')
    op=c.valid_uuid(op);hub=c.canonical(hub)
    with c.locked(hub):
        raw=c.canonical(hub/'ai/reminders-sync.json').read_bytes()
        if json.loads(raw)!=config:raise ValueError('config_argument_stale')
        p,ms,binding,expected=migration(c,hub,migration_path,migration_sha,config)
        if config!=expected:raise ValueError('verification_pending_config_changed')
        if any(b.get('list_id')==binding['list_id'] for b in config['projects'].values()):raise ValueError('verification_destination_bound')
        c.sync.registered(hub)['content-system']
        effective=dict(config,standard_allowlist_file=str(hub/'ai/reminders-standard-allowlist.json'))
        if c.canonical(effective['standard_allowlist_file']).read_text()!=p['permission']['after']:raise ValueError('verification_permission_changed')
        c.verify_list_identity(native,binding);c.full_list(native,binding,'unused')
        rows=native.call('find_reminders',{'list':binding['list_id'],'include_completed':True,'limit':500})
        if rows.get('reminders')!=[]:raise ValueError('verification_destination_not_empty')
        root=c.canonical(hub/'ai/reminders-cancellations');root.mkdir(exist_ok=True);folder=c.canonical(root/op)
        if folder.exists():raise ValueError('verification_create_already_attempted')
        folder.mkdir();c.fsync_dir(root)
        intent=dict(version=2,purpose=PURPOSE,operation_id=op,marker=op,approved=True,migration_plan=str(migration_path),migration_sha256=migration_sha,
                    migration_state_sha256=c.digest(c.canonical(migration_path).with_name('state.json').read_bytes()),config_before_raw=raw.decode(),binding=binding,
                    runtime=runtime(c,config),create_args=dict(title=title(op),notes=notes(op),list=binding['list_id']),phase='creating')
        c.durable_json(folder/'bootstrap.json',intent)
        # Exactly one ordinary create. Unknown results stop; never retry creation.
        result=native.call('create_reminder',intent['create_args']);rid=c.valid_uuid(result['id'])
        snapshot=native.get(rid,binding['list_id'])
        if not simple(snapshot,op,rid,binding['list_id'],binding['list_name']):raise ValueError('verification_synthetic_snapshot_changed')
        unbound(c,hub,config,rid,'verification-'+op,op);c.full_list(native,binding,rid)
        intent.update(phase='created',reminder_id=rid,snapshot=snapshot,create_receipt=result);c.durable_json(folder/'bootstrap.json',intent)
        return dict(ok=True,operation_id=op,reminder_id=rid,bootstrap=str(folder/'bootstrap.json'))

def prepare(c,hub,config,native,op,approve=False):
    if not approve:raise ValueError('explicit_verification_consent_required')
    hub=c.canonical(hub);c.valid_uuid(op)
    with c.locked(hub):
        folder=c.canonical(hub/'ai/reminders-cancellations'/op);boot=read(c,folder/'bootstrap.json')
        if boot.get('phase')!='created' or boot.get('approved') is not True or boot.get('operation_id')!=op or boot.get('marker')!=op:raise ValueError('verification_bootstrap_invalid')
        raw=c.canonical(hub/'ai/reminders-sync.json').read_bytes()
        existing=folder/'plan.json'
        if existing.exists() and raw.decode()!=boot['config_before_raw']:
            sha=c.digest(existing.read_bytes());saved,state,item,closed=validate(c,hub,existing,sha,config,native)
            if closed or state['items'][item['reminder_id']]['phase']!='prepared':raise ValueError('verification_prepare_already_executing')
            return dict(ok=True,path=str(existing),sha256=sha,plan=saved)
        if raw.decode()!=boot['config_before_raw'] or json.loads(raw)!=config:raise ValueError('verification_pending_config_changed')
        p,ms,binding,expected=migration(c,hub,boot['migration_plan'],boot['migration_sha256'],config)
        if binding!=boot['binding'] or c.digest(c.canonical(boot['migration_plan']).with_name('state.json').read_bytes())!=boot['migration_state_sha256']:raise ValueError('verification_migration_changed')
        rid=boot['reminder_id'];tid='verification-'+op;unbound(c,hub,config,rid,tid,op)
        snapshot=native.get(rid,binding['list_id']);c.full_list(native,binding,rid);c.verify_list_identity(native,binding)
        if snapshot!=boot['snapshot'] or not simple(snapshot,op,rid,binding['list_id'],binding['list_name']):raise ValueError('verification_synthetic_snapshot_changed')
        if runtime(c,config)!=boot['runtime']:raise ValueError('verification_runtime_changed')
        special=dict(binding,operation_id=op,marker=op,task_id=tid,reminder_id=rid,plan_sha256=None,approved=True)
        effective=copy.deepcopy(config);effective['standard_allowlist_file']=str(hub/'ai/reminders-standard-allowlist.json');effective.setdefault('project_list_verifications',{})[op]=special
        item=dict(binding,project_path=str(hub/'projects/content-system'),task_id=tid,reminder_id=rid,remote=snapshot,parent=None)
        plan=dict(version=2,purpose=PURPOSE,operation_id=op,marker=op,concurrency_policy='no_concurrent_edits',items=[item],config=effective,
                  config_sha256=c.digest(c.encoded(normal(effective,op))),config_normalized_json=c.encoded(normal(effective,op)),allowlist_sha256=c.digest(c.canonical(effective['standard_allowlist_file']).read_bytes()),
                  config_before_raw=boot['config_before_raw'],runtime=boot['runtime'],bootstrap_sha256=c.digest((folder/'bootstrap.json').read_bytes()),
                  migration_plan=boot['migration_plan'],migration_sha256=boot['migration_sha256'],migration_state_sha256=boot['migration_state_sha256'],migration_state=ms)
        path=folder/'plan.json'
        if path.exists():
            if path.read_text()!=c.encoded(plan):raise ValueError('verification_plan_already_prepared')
        else:c.durable_json(path,plan)
        sha=c.digest(path.read_bytes());effective['project_list_verifications'][op]['plan_sha256']=sha
        initial=dict(plan_sha256=sha,approved=True,items={rid:dict(phase='prepared')},events=[])
        state_path=folder/'state.json'
        if state_path.exists():
            if read(c,state_path)!=initial:raise ValueError('verification_prepare_already_executing')
        else:c.durable_json(state_path,initial)
        if c.canonical(hub/'ai/reminders-sync.json').read_bytes()!=raw:raise ValueError('verification_config_cas_failed')
        c.durable_json(hub/'ai/reminders-sync.json',effective);config.clear();config.update(copy.deepcopy(effective))
        return dict(ok=True,path=str(path),sha256=sha,plan=plan)

def validate(c,hub,path,sha,config,native=None):
    path=c.plan_location(hub,path);plan=read(c,path);state=read(c,path.with_name('state.json'))
    if c.digest(path.read_bytes())!=sha or plan.get('version')!=2 or plan.get('purpose')!=PURPOSE or plan.get('operation_id')!=path.parent.name or plan.get('marker')!=path.parent.name or len(plan.get('items',[]))!=1:raise ValueError('invalid_verification_plan')
    item=plan['items'][0];op=plan['operation_id'];rid=c.valid_uuid(item['reminder_id']);tid='verification-'+op
    if item.get('task_id')!=tid or item.get('project_id')!='content-system' or item.get('layout')!='project_list' or item.get('parent_id','missing') is not None or item.get('list_name')!='Система контента' or any(k in item for k in ('before_texts','after_texts','link','source_path')):raise ValueError('invalid_verification_target')
    if state.get('plan_sha256')!=sha or state.get('approved') is not True or set(state.get('items',{}))!={rid} or state['items'][rid].get('phase') not in PHASES:raise ValueError('invalid_verification_state')
    actual=read(c,hub/'ai/reminders-sync.json')
    if actual!=config:raise ValueError('config_argument_stale')
    phase=state['items'][rid]['phase']
    restored=phase=='cleaned' and c.canonical(hub/'ai/reminders-sync.json').read_text()==plan['config_before_raw']
    expected=copy.deepcopy(plan['config']);expected['project_list_verifications'][op]['plan_sha256']=sha
    if not restored and actual!=expected:raise ValueError('verification_binding_changed')
    if c.digest(c.encoded(normal(expected,op)))!=plan['config_sha256']:raise ValueError('verification_config_checksum')
    special=expected['project_list_verifications'][op]
    if special.get('approved') is not True or special.get('operation_id')!=op or special.get('marker')!=op or any(special.get(k)!=item.get(k) for k in ('task_id','reminder_id','project_id','list_id','list_name','account_id','native_group_id','layout','parent_id')):raise ValueError('verification_binding_changed')
    p,ms,binding,old=migration(c,hub,plan['migration_plan'],plan['migration_sha256'],actual)
    if any(item.get(k)!=v for k,v in binding.items()) or c.digest(c.canonical(plan['migration_plan']).with_name('state.json').read_bytes())!=plan['migration_state_sha256']:raise ValueError('verification_migration_changed')
    if json.loads(plan['config_before_raw'])!=old:raise ValueError('verification_original_config_changed')
    if runtime(c,actual)!=plan['runtime']:raise ValueError('verification_runtime_changed')
    if item['project_path']!=str(c.sync.registered(hub).get('content-system')):raise ValueError('verification_registry_changed')
    if any(b.get('list_id')==item['list_id'] for b in actual['projects'].values()):raise ValueError('verification_destination_bound')
    unbound(c,hub,actual,rid,tid,op)
    allow=c.canonical(hub/'ai/reminders-standard-allowlist.json')
    if c.digest(allow.read_bytes())!=plan['allowlist_sha256'] or item['list_name'] not in read(c,allow)['names']:raise ValueError('verification_allowlist_changed')
    boot_path=path.with_name('bootstrap.json');boot=read(c,boot_path)
    if c.digest(boot_path.read_bytes())!=plan['bootstrap_sha256'] or boot.get('phase')!='created' or boot.get('purpose')!=PURPOSE or boot.get('marker')!=op or boot.get('create_receipt',{}).get('id')!=rid or boot.get('create_args')!=dict(title=title(op),notes=notes(op),list=item['list_id']) or boot.get('runtime')!=plan['runtime'] or boot.get('config_before_raw')!=plan['config_before_raw'] or boot.get('approved') is not True or boot.get('snapshot')!=item['remote'] or boot.get('reminder_id')!=rid or boot.get('operation_id')!=op:raise ValueError('verification_bootstrap_changed')
    if not simple(item['remote'],op,rid,item['list_id'],item['list_name']):raise ValueError('verification_marker_or_snapshot_changed')
    if native is not None:c.verify_list_identity(native,item);c.full_list(native,item,rid)
    return plan,state,item,restored

def step(c,hub,path,sha,config,native,action,approve=False,token=None):
    if not approve and action!='status':raise ValueError('explicit_verification_consent_required')
    hub=c.canonical(hub);path=c.canonical(path)
    with c.locked(hub):
        plan,state,item,restored_config=validate(c,hub,path,sha,config,native);rid=item['reminder_id'];progress=state['items'][rid];phase=progress['phase']
        status=c.native_status(native,path,sha,item)
        if action=='status':return dict(ok=True,phase=phase,remote=status)
        def save(event=None):
            if event:state['events'].append(dict(stage=event,remote=copy.deepcopy(status)))
            c.durable_json(path.with_name('state.json'),state)
        if action=='restore-preview':
            if phase!='deleted' or status!=progress.get('deleted_snapshot'):raise ValueError('verification_restore_phase')
            value=dict(version=2,purpose=PURPOSE,operation_id=plan['operation_id'],plan_sha256=sha,config=copy.deepcopy(config),config_sha256=c.digest(c.canonical(hub/'ai/reminders-sync.json').read_bytes()),allowlist_sha256=plan['allowlist_sha256'],items={rid:dict(remote=status)})
            digest=c.digest(c.encoded(value));dest=c.restore_path_for(path,digest)
            if not dest.exists():c.durable_json(dest,value)
            return dict(ok=True,path=str(dest),sha256=digest)
        expected_phases={'delete':('prepared','deleting','deleted'),'restore':('deleted','restoring','restored'),'cleanup':('restored','cleanup_deleting','cleaned')}
        if action not in expected_phases:raise ValueError('invalid_verification_step')
        start,busy,done=expected_phases[action]
        if phase not in {start,busy,done}:raise ValueError('verification_step_order')
        if restored_config:raise ValueError('verification_already_closed')
        # После сохранённого результата сбой второго чтения восполняется только чтением.
        if phase==done:
            key={'delete':'deleted_snapshot','restore':'restored_snapshot','cleanup':'cleaned_snapshot'}[action]
            if status!=progress.get(key):raise ValueError('verification_completed_readback_changed')
            after_events=[e for e in state['events'] if e.get('stage')=='after_'+action]
            confirmed=[e for e in state['events'] if e.get('stage')=='confirmed_'+action]
            if not confirmed:
                if len(after_events)!=1 or after_events[0].get('remote')!=status:raise ValueError('verification_confirmation_proof_missing')
                save('confirmed_'+action)
                return dict(ok=True,phase=phase,remote=status)
            if action=='cleanup':raise ValueError('verification_cleanup_already_done')
            save('repeat_'+action);return dict(ok=True,phase=phase,remote=status)
        if not c.same_fields(status['snapshot'],item['remote']):raise ValueError('verification_snapshot_changed')
        before='deleted' if action=='restore' else 'active';after='active' if action=='restore' else 'deleted'
        if action=='restore':
            rp=c._restore_plan(path,plan,sha,token)
            if rp.get('config')!=config or rp.get('config_sha256')!=c.digest(c.canonical(hub/'ai/reminders-sync.json').read_bytes()) or rp['items'][rid]['remote']!=progress.get('deleted_snapshot'):raise ValueError('verification_restore_token_changed')
            if phase==start and status!=rp['items'][rid]['remote']:raise ValueError('verification_restore_remote_changed')
            state['restore_token']=token
        elif action=='cleanup':
            if not progress.get('deleted_snapshot') or not progress.get('restored_snapshot'):raise ValueError('verification_cleanup_proof_missing')
            if phase==start and status!=progress['restored_snapshot']:raise ValueError('verification_cleanup_remote_changed')
        elif phase==start and status['snapshot']!=item['remote']:raise ValueError('verification_initial_version_changed')
        if phase==start and status['state']!=before:raise ValueError('verification_external_mutation')
        progress['phase']=busy;save('before_'+action)
        if status['state']==before:
            arguments=dict(plan=str(path),plan_sha256=sha,id=rid,version=status['version'])
            if action=='restore':arguments.update(restore_plan=str(c.restore_path_for(path,token)),restore_sha256=token)
            native.call('hub_restore_reminder' if action=='restore' else 'hub_cancel_reminder',arguments)
        elif status['state']!=after:raise ValueError('verification_unknown_remote_state')
        status=c.native_status(native,path,sha,item)
        if status['state']!=after or not c.same_fields(status['snapshot'],item['remote']):raise ValueError('verification_readback_failed')
        c.full_list(native,item,rid)
        progress[{'delete':'deleted_snapshot','restore':'restored_snapshot','cleanup':'cleaned_snapshot'}[action]]=copy.deepcopy(status)
        progress['phase']=done;save('after_'+action)
        second=c.native_status(native,path,sha,item)
        if second!=status:raise ValueError('verification_second_readback_failed')
        save('confirmed_'+action)
        return dict(ok=True,phase=done,remote=status)

def close(c,hub,path,sha,config,native,approve=False):
    if not approve:raise ValueError('explicit_verification_consent_required')
    hub=c.canonical(hub);path=c.canonical(path)
    with c.locked(hub):
        plan,state,item,restored=validate(c,hub,path,sha,config,native)
        if state['items'][item['reminder_id']]['phase']!='cleaned':raise ValueError('verification_not_cleaned')
        cleaned=state['items'][item['reminder_id']].get('cleaned_snapshot')
        confirmed=[e for e in state.get('events',[]) if e.get('stage')=='confirmed_cleanup']
        if len(confirmed)!=1 or confirmed[0].get('remote')!=cleaned:raise ValueError('verification_cleanup_not_confirmed')
        if restored:return dict(ok=True,config_restored=True)
        observed=c.native_status(native,path,sha,item)
        if observed!=state['items'][item['reminder_id']].get('cleaned_snapshot') or observed['state']!='deleted':raise ValueError('verification_cleanup_changed')
        raw=c.canonical(hub/'ai/reminders-sync.json').read_bytes()
        if json.loads(raw)!=config:raise ValueError('verification_config_cas_failed')
        # Exact bytes, never a JSON reserialization. No task receipts or canonical task files.
        temporary=path.with_name('config-restore.tmp')
        with temporary.open('wb') as f:f.write(plan['config_before_raw'].encode());f.flush();os.fsync(f.fileno())
        if c.canonical(hub/'ai/reminders-sync.json').read_bytes()!=raw:raise ValueError('verification_config_cas_failed')
        os.replace(temporary,hub/'ai/reminders-sync.json');c.fsync_dir(hub/'ai')
        config.clear();config.update(json.loads(plan['config_before_raw']))
        return dict(ok=True,config_restored=True,config_sha256=c.digest(plan['config_before_raw']))

def witness(c,hub,path,sha,expected_journal_sha,approve=False,independent_review_accepted=False):
    """Только явное принятие родителем после независимой проверки реального журнала."""
    if not approve or not independent_review_accepted:raise ValueError('parent_and_independent_acceptance_required')
    hub=c.canonical(hub);path=c.canonical(path)
    with c.locked(hub):
        config=read(c,hub/'ai/reminders-sync.json');plan,state,item,closed=validate(c,hub,path,sha,config)
        journal=c.digest(c.canonical(path.with_name('state.json')).read_bytes())
        if expected_journal_sha!=journal or not closed:raise ValueError('verification_witness_requires_closed_exact_journal')
        progress=state['items'][item['reminder_id']];events=state.get('events',[]);index=-1
        for stage,remote_state,key in [('delete','deleted','deleted_snapshot'),('restore','active','restored_snapshot'),('cleanup','deleted','cleaned_snapshot')]:
            snapshot=progress.get(key)
            if not isinstance(snapshot,dict) or snapshot.get('state')!=remote_state or not c.same_fields(snapshot.get('snapshot',{}),item['remote']):raise ValueError('verification_witness_snapshot')
            for prefix in ('after_','confirmed_'):
                found=[(n,e) for n,e in enumerate(events) if e.get('stage')==prefix+stage]
                if len(found)!=1 or found[0][0]<=index or found[0][1].get('remote')!=snapshot:raise ValueError('verification_witness_readbacks')
                index=found[0][0]
        value=dict(protocol=2,accepted_by='parent',independent_review_accepted=True,runtime=plan['runtime'],list_id=item['list_id'],account_id=item['account_id'],group_id=item['native_group_id'],operation_id=plan['operation_id'],marker=plan['operation_id'],synthetic_uuid=item['reminder_id'],plan_sha256=sha,journal_sha256=journal)
        target=c.canonical(hub/'ai/reminders-project-list-verification.json')
        if target.exists():
            if read(c,target)!=value:raise ValueError('verification_witness_already_exists')
        else:c.durable_json(target,value)
        return dict(ok=True,path=str(target),sha256=c.digest(target.read_bytes()),pinned=False)

def pin(c,hub,expected_config_sha,expected_witness_sha,approve=False):
    if not approve:raise ValueError('parent_acceptance_required')
    hub=c.canonical(hub)
    with c.locked(hub):
        path=c.canonical(hub/'ai/reminders-sync.json');raw=path.read_bytes();config=json.loads(raw)
        proof_path=c.canonical(hub/'ai/reminders-project-list-verification.json');proof=read(c,proof_path)
        if c.digest(raw)!=expected_config_sha or c.digest(proof_path.read_bytes())!=expected_witness_sha:raise ValueError('verification_pin_cas_failed')
        if proof.get('accepted_by')!='parent' or proof.get('independent_review_accepted') is not True or runtime(c,config)!=proof.get('runtime'):raise ValueError('verification_witness_unaccepted_or_runtime')
        binding=config['projects']['content-system']
        if (binding.get('layout')!='project_list' or binding.get('parent_id','missing') is not None or binding.get('list_id')!=proof.get('list_id') or
                binding.get('account_id')!=proof.get('account_id') or binding.get('native_group_id')!=proof.get('group_id') or
                sum(b.get('list_id')==binding['list_id'] for b in config['projects'].values())!=1 or 'content-system' in c.sync.migration_pending(hub,config)):raise ValueError('verification_pin_requires_completed_migration')
        folder=c.canonical(hub/'ai/reminders-cancellations'/c.valid_uuid(proof['operation_id']))
        if c.digest(c.canonical(folder/'plan.json').read_bytes())!=proof['plan_sha256'] or c.digest(c.canonical(folder/'state.json').read_bytes())!=proof['journal_sha256']:raise ValueError('verification_witness_dependencies_changed')
        config['project_list_verification_sha256']=expected_witness_sha
        accepted(c,hub,config)
        if path.read_bytes()!=raw:raise ValueError('verification_pin_cas_failed')
        c.durable_json(path,config)
        return dict(ok=True,witness_sha256=expected_witness_sha,config_sha256=c.digest(path.read_bytes()))

def accepted(c,hub,config):
    """Постоянная проверка свидетельства не привязана к меняющимся task links."""
    path=c.canonical(hub/'ai/reminders-project-list-verification.json');proof=read(c,path)
    if config.get('project_list_verification_sha256')!=c.digest(path.read_bytes()) or proof.get('protocol')!=2 or proof.get('accepted_by')!='parent' or proof.get('independent_review_accepted') is not True or proof.get('runtime')!=runtime(c,config):raise ValueError('verification_evidence_unaccepted_or_runtime')
    if config.get('standard_allowlist_file')!=str(hub/'ai/reminders-standard-allowlist.json') or 'content-system' not in c.sync.registered(hub):raise ValueError('verification_evidence_registry_or_allowlist')
    binding=config['projects']['content-system']
    if (binding.get('layout')!='project_list' or binding.get('parent_id','missing') is not None or binding.get('list_id')!=proof.get('list_id') or
            binding.get('account_id')!=proof.get('account_id') or binding.get('native_group_id')!=proof.get('group_id') or
            sum(b.get('list_id')==binding['list_id'] for b in config['projects'].values())!=1):raise ValueError('verification_evidence_current_scope')
    op=c.valid_uuid(proof['operation_id']);folder=c.canonical(hub/'ai/reminders-cancellations'/op);plan=read(c,folder/'plan.json');state=read(c,folder/'state.json')
    if (c.digest((folder/'plan.json').read_bytes())!=proof.get('plan_sha256') or c.digest((folder/'state.json').read_bytes())!=proof.get('journal_sha256') or
            state.get('plan_sha256')!=proof['plan_sha256'] or state.get('approved') is not True or plan.get('version')!=2 or plan.get('purpose')!=PURPOSE or
            plan.get('operation_id')!=op or plan.get('marker')!=op or proof.get('marker')!=op or plan.get('runtime')!=proof['runtime'] or len(plan.get('items',[]))!=1):raise ValueError('verification_evidence_dependencies')
    item=plan['items'][0];rid=proof['synthetic_uuid'];progress=state.get('items',{}).get(rid,{})
    if item.get('reminder_id')!=rid or item.get('list_id')!=proof['list_id'] or item.get('account_id')!=proof['account_id'] or item.get('native_group_id')!=proof['group_id'] or progress.get('phase')!='cleaned':raise ValueError('verification_evidence_scope')
    if not simple(item['remote'],op,rid,proof['list_id'],'Система контента'):raise ValueError('verification_evidence_original_snapshot')
    events=state.get('events',[]);index=-1
    for stage,remote_state,key in [('delete','deleted','deleted_snapshot'),('restore','active','restored_snapshot'),('cleanup','deleted','cleaned_snapshot')]:
        remote=progress.get(key,{})
        if remote.get('state')!=remote_state or remote.get('version')!=remote.get('snapshot',{}).get('version') or not c.same_fields(remote.get('snapshot',{}),item['remote']):raise ValueError('verification_evidence_snapshot')
        for prefix in ('after_','confirmed_'):
            matches=[(n,e) for n,e in enumerate(events) if e.get('stage')==prefix+stage]
            if len(matches)!=1 or matches[0][0]<=index or matches[0][1].get('remote')!=remote:raise ValueError('verification_evidence_readbacks')
            index=matches[0][0]
    boot=read(c,folder/'bootstrap.json')
    if c.digest(c.canonical(folder/'bootstrap.json').read_bytes())!=plan['bootstrap_sha256'] or boot.get('phase')!='created' or boot.get('create_receipt',{}).get('id')!=rid or boot.get('snapshot')!=item['remote']:raise ValueError('verification_evidence_bootstrap')
    migration_path=c.canonical(plan['migration_plan']);migration_plan=read(c,migration_path);migration_state=read(c,migration_path.with_name('state.json'))
    if migration_state.get('phase')!='complete' or migration_state.get('sha256')!=plan['migration_sha256'] or migration_state.get('list_id')!=proof['list_id'] or config.get('project_list_migrations_completed',{}).get('content-system')!=plan['migration_sha256'] or 'content-system' in config.get('project_list_migrations_pending',{}):raise ValueError('verification_migration_not_completed')
    if migration_path!=hub/'ai/reminders-project-lists'/migration_plan['operation']/'plan.json' or c.digest(migration_path.read_bytes())!=plan['migration_sha256'] or c.digest(migration_plan['permission']['after'])!=plan['allowlist_sha256']:raise ValueError('verification_evidence_dependencies')
    historical_names=json.loads(migration_plan['permission']['after'])['names']
    current_names=c.allowlist(config,'project_list')[0]
    if not set(historical_names)<=set(current_names):raise ValueError('verification_evidence_permissions_removed')
    return proof
