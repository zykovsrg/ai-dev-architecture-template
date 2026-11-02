#!/usr/bin/env python3
"""Проверяемый переход к приложению и отдельные квитанции принятия архивов."""
import contextlib
import copy
import fcntl
import importlib.util
import json
import re
import uuid
from pathlib import Path

KIND='reminders-authority'
MUTABLE_LINKS={'last_hub_day','last_remote_day','last_hub_title','last_remote_title','last_completed','last_open_status','last_remote_version','last_notes','last_hub_notes','last_remote_notes'}

def archive():
    spec=importlib.util.spec_from_file_location('authority_archive_historical',Path(__file__).with_name('reminders_archive.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def safe(path):return archive().safe(path)
def digest(value):return archive().digest(value)

def _folder(hub,rel):
    if not isinstance(rel,str) or not re.fullmatch(r'ai/reminders-authority/[0-9a-f-]{36}',rel):raise ValueError('authority_activation_path')
    try:uuid.UUID(rel.rsplit('/',1)[1])
    except ValueError:raise ValueError('authority_activation_path')
    return safe(Path(hub)/rel)

def _plan(path,sha256):
    path=safe(path);raw=path.read_bytes()
    if digest(raw)!=sha256:raise ValueError('authority_activation_checksum')
    plan=json.loads(raw);hub=safe(plan['hub'])
    if path!=_folder(hub,'ai/reminders-authority/'+plan['operation'])/'plan.json':raise ValueError('authority_activation_path')
    if plan.get('kind')!=KIND or plan.get('version')!=1 or plan.get('mode')!='reminders' or plan.get('deletion_policy')!='cancel' or not isinstance(plan.get('statement'),str) or not plan['statement'].strip():raise ValueError('authority_activation_intent')
    return hub,plan

def validate_activation(hub,config):
    ref=config.get('task_authority',{})
    if not isinstance(ref,dict) or ref.get('mode')!='reminders' or ref.get('deletions')!='cancel':raise ValueError('authority_activation_policy')
    folder=_folder(hub,ref.get('journal'));actual,plan=_plan(folder/'plan.json',ref.get('sha256'))
    if actual!=Path(hub):raise ValueError('authority_activation_hub')
    state=json.loads(safe(folder/'state.json').read_text())
    if state.get('phase')!='complete' or state.get('approved') is not True or state.get('plan_sha256')!=ref['sha256'] or state.get('statement')!=plan['statement']:raise ValueError('authority_activation_incomplete')
    return plan

@contextlib.contextmanager
def locked(hub,m):
    if hasattr(m,'authority_module'):
        with m.authority_module().locked(hub):yield
    else:
        with (Path(hub)/'ai/.reminders-sync.lock').open('a') as handle:
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB);yield

def _identity(binding):
    return {k:copy.deepcopy(v) for k,v in binding.items() if k not in {'tasks','history','archive','last_completed'}}

def _links(binding):
    return {tid:{k:v for k,v in link.items() if k not in MUTABLE_LINKS} for tid,link in binding.get('tasks',{}).items()}

def _context(text):
    # Только копируемые поля приложения; Due и весь остальной текст остаются историческими.
    text=re.sub(r'^(### [^\n]+? — )[^\n]*',r'\1<TITLE>',text,flags=re.M)
    text=re.sub(r'(^## Goal\n\s*\n?)[^\n]+',r'\1<TITLE>',text,count=1,flags=re.M)
    text=re.sub(r'^Status: .+$','Status: <STATE>',text,flags=re.M)
    return re.sub(r'^Запланировано:.*\n?','',text,flags=re.M)

def _permissions(config):
    paths=[config['allowlist_file']]
    if config.get('standard_allowlist_file'):paths.append(config['standard_allowlist_file'])
    paths.extend(config.get('structure',{}).get(k) for k in ('groups_allowlist_file','group_ids_allowlist_file') if config.get('structure',{}).get(k))
    return {str(safe(p)):safe(p).read_text() for p in paths}

def _scope(config,snap):
    for pid,b in config['projects'].items():
        l=snap['lists'].get(b.get('list_id'),{})
        if l.get('name')!=b.get('list_name') or b.get('account_id') and l.get('account_id')!=b['account_id']:raise ValueError('authority_activation_list_identity')
        if not b.get('archive') and b.get('native_group_id') and l.get('group_id')!=b['native_group_id']:raise ValueError('authority_activation_group_identity')
        for link in b.get('tasks',{}).values():
            row=snap['reminders'].get(link.get('reminder_id'))
            if row and (row.get('list_id')!=b['list_id'] or row.get('parent_id')!=b.get('parent_id')):raise ValueError('authority_activation_task_identity')

def _historical(hub,config,pid):
    a=archive();ref=config['projects'][pid].get('archive',{});rel=ref.get('journal','')
    if not re.fullmatch(r'ai/reminders-archives/[a-z0-9-]+',rel):raise ValueError('archive_receipt_path')
    folder=safe(Path(hub)/rel);raw=safe(folder/'plan.json').read_bytes()
    if digest(raw)!=ref.get('token'):raise ValueError('archive_receipt_checksum')
    plan=json.loads(raw);state=json.loads(safe(folder/'state.json').read_text());saved=state.get('projects',{}).get(pid)
    if state.get('phase')!='complete' or state.get('approved') is not True or not saved or saved.get('phase')!='committed' or ref.get('operation')!=plan.get('operation'):raise ValueError('archive_receipt_incomplete')
    return plan,state,saved

def _proven_link(hub,config,pid,tid,current,old):
    current=copy.deepcopy(current)
    m=archive().load_sync()
    if current.get('reminder_id')!=old.get('reminder_id'):
        lineage=config['projects'][pid].get('history',{}).get(old.get('reminder_id'))
        if lineage==dict(project_id=pid,task_id=tid,original_id=current.get('reminder_id')):
            current['reminder_id']=old['reminder_id']
    if 'external_retirement' in current and current.get('external_retirement')!=old.get('external_retirement'):
        ref=current['external_retirement'];operation=ref.get('operation','')
        if not re.fullmatch(r'[0-9a-f-]{36}',operation):raise ValueError('archive_retirement_operation')
        ext=m.external_retirement_module();_,plan,state=ext.read(Path(hub)/'ai/reminders-external-retirements'/operation/'plan.json',ref.get('plan_sha256'))
        items=[i for i in plan['items'] if (i.get('project_id'),i.get('task_id'))==(pid,tid)]
        if len(items)!=1:raise ValueError('archive_retirement_target')
        item=items[0]
        if state['phase'] not in {'committing','complete'} or state['approved'] is not True or ref!=ext.receipt(plan,ref['plan_sha256'],item) or item.get('reminder_id')!=old.get('reminder_id') or item.get('project_path')!=str(Path(hub)/'projects'/pid) or not ext.committed(config,pid,operation,ref['plan_sha256']):raise ValueError('archive_retirement_provenance')
        if {k:v for k,v in item['link'].items() if k not in MUTABLE_LINKS}!=old:raise ValueError('archive_retirement_source')
        current.pop('external_retirement')
    if 'cancellation' in current and current.get('cancellation')!=old.get('cancellation'):
        ref=current['cancellation'];operation=ref.get('operation_id','')
        if not re.fullmatch(r'[0-9a-f-]{36}',operation):raise ValueError('archive_cancellation_operation')
        cancel=m.cancellation_module();path,plan=cancel.read_plan(Path(hub),Path(hub)/'ai/reminders-cancellations'/operation/'plan.json',ref.get('plan_sha256'),require_active=False)
        state=cancel.read_state(path,plan,ref['plan_sha256']);items=[i for i in plan['items'] if (i.get('project_id'),i.get('task_id'))==(pid,tid)]
        if len(items)!=1:raise ValueError('archive_cancellation_target')
        item=items[0]
        if state['approved'] is not True or state['items'][item['reminder_id']]['phase']!='committed' or ref!=cancel.cancelled_link(item,plan,ref['plan_sha256'])['cancellation'] or item['reminder_id']!=old.get('reminder_id'):raise ValueError('archive_cancellation_provenance')
        if {k:v for k,v in item['link'].items() if k not in MUTABLE_LINKS}!=old:raise ValueError('archive_cancellation_source')
        current.pop('cancellation')
    return current

def _historical_group_path(plan,field,setting):
    if field in plan:
        value=plan[field]
    else:
        try:
            raw=plan['config_before']
            if not isinstance(raw,str):raise ValueError('snapshot_type')
            original=json.loads(raw)
            if not isinstance(original,dict) or not isinstance(original.get('structure'),dict):raise ValueError('snapshot_shape')
            value=original['structure'][setting]
        except (KeyError,TypeError,ValueError) as error:
            raise ValueError('archive_group_pin_path_unverified') from error
    if not isinstance(value,str) or not value:
        raise ValueError('archive_group_pin_path_unverified')
    try:safe(value)
    except (TypeError,ValueError) as error:raise ValueError('archive_group_pin_path_unverified') from error
    return value

def _local(hub,config,pid,plan,state,saved,strict_context=False):
    a=archive();b=config['projects'][pid];root,card,status=a.registry_entry(hub,pid)
    ids_path=_historical_group_path(plan,'group_ids_path','group_ids_allowlist_file')
    permissions_path=_historical_group_path(plan,'group_permissions_path','groups_allowlist_file')
    if config['structure']['group_ids_allowlist_file']!=ids_path or config['structure']['groups_allowlist_file']!=permissions_path:raise ValueError('archive_group_pin_path_changed')
    if root!=Path(plan['projects'][pid]['root']) or status!='archived':raise ValueError('archive_identity_changed')
    if card.read_text()!=saved['card_after']:raise ValueError('archive_card_changed')
    if a._section((Path(hub)/'ai/project-registry.md').read_text(),pid)!=saved['registry_section_after'].rstrip():raise ValueError('archive_registry_section_changed')
    if _identity(b)!=_identity(saved['binding_after']):raise ValueError('archive_binding_identity_changed')
    old=_links(saved['binding_after']);current=_links(b)
    for rid,owner in saved['binding_after'].get('history',{}).items():
        if b.get('history',{}).get(rid)!=owner:raise ValueError('archive_history_identity_changed')
    for tid,link in old.items():
        actual=current.get(tid)
        if actual is None:raise ValueError('archive_task_binding_identity_changed')
        if actual!=link and (strict_context or _proven_link(hub,config,pid,tid,actual,link)!=link):raise ValueError('archive_task_binding_identity_changed')
    if strict_context:
        if current!=old or b.get('history',{})!=saved['binding_after'].get('history',{}):raise ValueError('archive_task_binding_identity_changed')
        for name,text in saved['files_after'].items():
            if _context((root/'ai'/name).read_text())!=_context(text):raise ValueError('archive_task_context_changed')
    return root

def _pins(config,group):
    path=safe(config['structure']['group_ids_allowlist_file']);pins=json.loads(path.read_text())
    if pins.get('groups',{}).get(group['id'])!=group['name']:raise ValueError('archive_group_pin_changed')
    names=json.loads(safe(config['structure']['groups_allowlist_file']).read_text())
    if group['name'] not in names.get('names',[]):raise ValueError('archive_group_permission_changed')

def verify_group(config,group,snap):
    _pins(config,group)
    values=snap.get('groups',[])
    if isinstance(values,dict):
        if any(not isinstance(row,dict) or key!=row.get('id') for key,row in values.items()):raise ValueError('archive_native_group_shape')
        values=list(values.values())
    if (not isinstance(values,list) or any(not isinstance(row,dict) or not isinstance(row.get('id'),str) or not row['id'] for row in values)
            or len({row['id'] for row in values})!=len(values)):raise ValueError('archive_native_group_shape')
    groups=[g for g in values if g.get('id')==group['id']]
    if len(groups)!=1 or any(groups[0].get(k)!=group.get(k) for k in ('id','name','account_id')):raise ValueError('archive_native_group_changed')

def _native(config,pid,plan,state,saved,snap):
    a=archive();b=config['projects'][pid];group=state['archive_group'];verify_group(config,group,snap)
    l=snap['lists'].get(b['list_id'],{})
    if l.get('name')!=b['list_name'] or l.get('account_id')!=plan['account_id'] or l.get('group_id')!=group['id']:raise ValueError('archive_native_identity_changed')
    rows={rid:r for rid,r in snap['reminders'].items() if r.get('list_id')==b['list_id']}
    if set(rows)!=set(saved['native_after']) or set(saved['gap_ids'])&set(snap['reminders']):raise ValueError('archive_native_identity_changed')
    for rid,old in saved['native_after'].items():
        if any(rows[rid].get(k)!=old.get(k) for k in ('id','parent_id')):raise ValueError('archive_native_identity_changed')
        marker=lambda notes:[line for line in (notes or '').splitlines() if line.startswith(('Хаб:','Hub Task ID:','Hub project:','--- Hub metadata','--- /Hub metadata'))]
        if marker(rows[rid].get('notes'))!=marker(old.get('notes')):raise ValueError('archive_native_identity_changed')

def _anchor_ref(hub,config,pid):
    validate_activation(hub,config);folder=_folder(hub,config['task_authority']['journal']);state=json.loads(safe(folder/'state.json').read_text())
    return folder,state,state.get('archives',{}).get(pid)

def archive_adopted(hub,config,pid,plan,state,saved):
    if not archive().load_sync().authority_enabled(config):return False
    folder,activation,ref=_anchor_ref(hub,config,pid)
    if not ref:return False
    try:
        path=safe(Path(hub)/ref['journal'])
        if path.parent!=folder or path.name!='adoption-'+pid+'-'+config['projects'][pid]['archive']['token']+'.json':raise ValueError('path')
        raw=path.read_bytes()
        if digest(raw)!=ref['sha256']:raise ValueError('checksum')
        anchor=json.loads(raw)
        activation_plan=validate_activation(hub,config);original=activation_plan.get('archives',{}).get(pid)
        if original and original.get('ref')==config['projects'][pid]['archive'] and (original.get('saved_sha256')!=digest(saved) or original.get('state_sha256')!=digest(state)):raise ValueError('historical_baseline')
        if anchor.get('version')!=1 or anchor.get('project_id')!=pid or anchor.get('archive')!=config['projects'][pid]['archive'] or anchor.get('activation_sha256')!=config['task_authority']['sha256'] or anchor.get('approved') is not True or anchor.get('phase')!='complete':raise ValueError('identity')
        if anchor.get('binding_identity')!=_identity(saved['binding_after']) or anchor.get('archive_group')!=state['archive_group'] or anchor.get('historical_state_sha256')!=digest({k:state[k] for k in ('approved','phase','archive_group')}) or anchor.get('historical_saved_sha256')!=digest(saved):raise ValueError('history')
    except (KeyError,OSError,TypeError,ValueError) as error:raise ValueError('archive_authority_anchor_invalid: '+str(error)) from error
    _local(hub,config,pid,plan,state,saved);_pins(config,state['archive_group'])
    return True

def project_path(hub,config,pid):
    receipt=_historical(hub,config,pid)
    if not archive_adopted(hub,config,pid,*receipt):raise ValueError('archive_authority_adoption_required')
    return _local(hub,config,pid,*receipt)

def archive_group(hub,config,pid):
    receipt=_historical(hub,config,pid)
    if not archive_adopted(hub,config,pid,*receipt):raise ValueError('archive_authority_adoption_required')
    return receipt[1]['archive_group']['id']

def _anchor(hub,config,pid,plan,state,saved,activation_state=None):
    if activation_state is None:folder,activation,ref=_anchor_ref(hub,config,pid)
    else:folder=_folder(hub,config['task_authority']['journal']);activation=activation_state
    m=archive().load_sync()
    value=dict(version=1,project_id=pid,archive=copy.deepcopy(config['projects'][pid]['archive']),activation_sha256=config['task_authority']['sha256'],approved=True,phase='complete',binding_identity=_identity(saved['binding_after']),archive_group=copy.deepcopy(state['archive_group']),historical_state_sha256=digest({k:state[k] for k in ('approved','phase','archive_group')}),historical_saved_sha256=digest(saved))
    path=folder/('adoption-'+pid+'-'+config['projects'][pid]['archive']['token']+'.json')
    if path.exists() and json.loads(path.read_text())!=value:raise ValueError('archive_authority_anchor_conflict')
    if not path.exists():m.atomic_json(path,value)
    activation.setdefault('archives',{})[pid]=dict(journal=str(path.relative_to(hub)),sha256=digest(path.read_bytes()))
    m.atomic_json(folder/'state.json',activation)

def adopt_new_archive(hub,config,pid):
    plan,state,saved=_historical(hub,config,pid)
    if archive_adopted(hub,config,pid,plan,state,saved):return
    _local(hub,config,pid,plan,state,saved,True)
    _anchor(hub,config,pid,plan,state,saved)

def preview(hub,statement,native=None):
    hub=safe(hub);a=archive();m=a.load_sync()
    if not isinstance(statement,str) or not statement.strip():raise ValueError('authority_activation_intent')
    with locked(hub,m):
        config=m.load_config(hub)
        if m.authority_enabled(config):raise ValueError('authority_activation_already_selected')
        n=native or m.Native(config);snap=a.snapshot(n);_scope(config,snap);archives={}
        if a.pending_projects(hub,config):raise ValueError('authority_activation_archive_pending')
        for pid,b in config['projects'].items():
            if not b.get('archive'):continue
            plan,state,saved=_historical(hub,config,pid);_local(hub,config,pid,plan,state,saved,True);_native(config,pid,plan,state,saved,snap)
            archives[pid]=dict(ref=copy.deepcopy(b['archive']),state_sha256=digest(state),saved_sha256=digest(saved))
        plan=dict(version=1,kind=KIND,operation=str(uuid.uuid4()),hub=str(hub),mode='reminders',deletion_policy='cancel',statement=statement,config_before=(hub/'ai/reminders-sync.json').read_text(),registry_before=(hub/'ai/project-registry.md').read_text(),snapshot=snap,archives=archives,permissions=_permissions(config),initial_missing=[dict(project_id=pid,task_id=tid,reminder_id=link['reminder_id']) for pid,b in sorted(config['projects'].items()) for tid,link in sorted(b.get('tasks',{}).items()) if link.get('reminder_id') not in snap['reminders'] and not link.get('cancellation') and not link.get('external_retirement')])
        folder=hub/'ai/reminders-authority'/plan['operation'];folder.mkdir(parents=True)
        m.atomic_json(folder/'plan.json',plan);sha=digest((folder/'plan.json').read_bytes());m.atomic_json(folder/'state.json',dict(phase='preview',approved=False,plan_sha256=sha,statement=statement,archives={}))
        return dict(plan=str(folder/'plan.json'),sha256=sha,archives=list(archives))

def apply(path,sha256,approve=False,native=None):
    if not approve:raise ValueError('explicit_authority_activation_approval_required')
    hub,plan=_plan(path,sha256);folder=Path(path).parent;a=archive();m=a.load_sync()
    with locked(hub,m):
        state=json.loads(safe(folder/'state.json').read_text());target=hub/'ai/reminders-sync.json';raw=target.read_text();before=json.loads(plan['config_before']);config=copy.deepcopy(before)
        config['task_authority']=dict(mode='reminders',deletions='cancel',journal=str(folder.relative_to(hub)),sha256=sha256)
        after=json.dumps(config,ensure_ascii=False,indent=2)+'\n'
        if state.get('phase')=='complete':
            current=m.load_config(hub)
            if current.get('task_authority')!=config['task_authority']:raise ValueError('authority_activation_config_changed')
            validate_activation(hub,current)
            for pid in plan['archives']:project_path(hub,current,pid)
            return state
        if raw not in (plan['config_before'],after):raise ValueError('authority_activation_config_changed')
        if state.get('plan_sha256')!=sha256 or state.get('statement')!=plan['statement'] or state.get('phase') not in ('preview','committing'):raise ValueError('authority_activation_state')
        n=native or m.Native(before);snap=a.snapshot(n);_scope(before,snap)
        if _permissions(before)!=plan['permissions']:raise ValueError('authority_activation_permissions_changed')
        if snap!=plan['snapshot']:raise ValueError('authority_activation_snapshot_changed')
        if (hub/'ai/project-registry.md').read_text()!=plan['registry_before']:raise ValueError('authority_activation_registry_changed')
        for pid,expected in plan['archives'].items():
            p,s,saved=_historical(hub,before,pid)
            if digest(s)!=expected['state_sha256'] or digest(saved)!=expected['saved_sha256']:raise ValueError('authority_activation_archive_changed')
            _local(hub,before,pid,p,s,saved,True);_native(before,pid,p,s,saved,snap)
        state.update(phase='committing',approved=True);m.atomic_json(folder/'state.json',state)
        for pid in plan['archives']:
            p,s,saved=_historical(hub,config,pid);_anchor(hub,config,pid,p,s,saved,state)
        # Запись конфигурации предшествует завершению журнала. Повторный запуск принимает только точные before/after.
        if target.read_text()!=raw:raise ValueError('authority_activation_config_changed')
        if raw!=after:m.atomic_json(target,config)
        if target.read_text()!=after:raise ValueError('authority_activation_config_readback')
        state['phase']='complete';m.atomic_json(folder/'state.json',state)
        validate_activation(hub,m.load_config(hub))
        return json.loads((folder/'state.json').read_text())
