#!/usr/bin/env python3
"""Одно явно согласованное переназначение существующей ready-задачи."""
import argparse
import copy
import datetime
import importlib.util
import json
from pathlib import Path
import re
import uuid


def module(name):
    spec=importlib.util.spec_from_file_location('task_reassignment_'+name,Path(__file__).with_name(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


pl=module('reminders_project_lists')
sync=pl.load_sync()
KIND='task_reassignment'
PHASES={'preview','intent','native','canonical_dest','canonical_source','binding','verified','complete'}


def read(path,digest):
    path=pl.safe(path);raw=path.read_bytes().decode('utf-8')
    if pl.sha(raw)!=digest:raise ValueError('reassignment_plan_checksum_mismatch')
    plan=json.loads(raw);hub=pl.safe(plan['hub'])
    if (plan.get('kind')!=KIND or plan.get('version')!=1 or not pl.valid_uuid(plan.get('operation')) or
            path!=hub/'ai/reminders-task-reassignments'/plan['operation']/'plan.json'):
        raise ValueError('invalid_reassignment_plan')
    state=json.loads(pl.safe(path.with_name('state.json')).read_bytes().decode('utf-8'))
    if (state.get('sha256')!=digest or type(state.get('approved')) is not bool or state.get('phase') not in PHASES or
            state['phase']!='preview' and not state['approved']):raise ValueError('invalid_reassignment_state')
    return path,plan,state


def pending_projects(hub,config,ignore_operation=None):
    """Только файлы: потерянная отметка не снимает блокировку участников."""
    result=set();root=pl.safe(Path(hub)/'ai/reminders-task-reassignments')
    if not root.exists():return result
    try:
        for folder in root.iterdir():
            if folder.name==ignore_operation:continue
            path=pl.safe(folder/'plan.json');digest=pl.sha(path.read_bytes());_,plan,state=read(path,digest)
            if state['phase']!='preview' and (state['phase']!='complete' or
                    config.get('task_reassignments_completed',{}).get(plan['operation'])!=digest):result.update(plan['projects'])
    except (ValueError,OSError,KeyError,TypeError):result.update(config['projects'])
    return result


def snapshot_files(hub,config):
    paths=[hub/'ai/project-registry.md',pl.safe(config['allowlist_file']),pl.safe(sync.standard_allowlist(config))]
    groups=config.get('structure',{}).get('groups_allowlist_file')
    if groups:paths.append(pl.safe(groups))
    return {str(p):p.read_bytes().decode('utf-8') for p in paths}


def exact_fields(row):
    return {k:v for k,v in row.items() if k!='version' and not (k=='parent_id' and v is None)}


def metadata(native):
    result=pl.metadata(native)
    if result.get('error') or result.get('errors') or result.get('more') or result.get('has_more'):raise ValueError('reassignment_metadata_error')
    for kind in ('lists','groups'):
        for row in result[kind]:
            if not pl.valid_uuid(row['id']) or not pl.valid_uuid(row['account_id']):raise ValueError('invalid_reassignment_metadata_uuid')
    return {k:[{a:b for a,b in row.items() if a not in ('total','open')} for row in result[k]] for k in ('lists','groups')}


def observe(native,lids):
    pl.reset_cache(native)
    return {lid:pl.rows(native,lid) for lid in sorted(set(lids))}


def binding_guards(config,target,meta,permissions):
    source,dest=target['source_project'],target['destination_project'];s=config['projects'][source];d=config['projects'][dest]
    if source==dest or d.get('layout')!='project_list' or d.get('parent_id') is not None:raise ValueError('destination_project_list_required')
    roles=config['structure']['list_roles'];role=roles.get(d['list_id'])
    if role!={'kind':'project','project_id':dest} or sum(b['list_id']==d['list_id'] for b in config['projects'].values())!=1:raise ValueError('destination_exclusive_role_required')
    retired=d.get('retired_parent')
    if not isinstance(retired,dict) or not pl.valid_uuid(retired.get('list_id')) or not isinstance(retired.get('snapshot'),dict):raise ValueError('destination_retired_parent_required')
    if (retired.get('id')!=retired['snapshot'].get('id') or retired['snapshot'].get('list_id')!=retired['list_id'] or
            retired['snapshot'].get('parent_id') is not None or retired['snapshot'].get('subtasks')):raise ValueError('invalid_retired_parent')
    old=next((r for r in meta['lists'] if r['id']==retired['list_id']),None)
    if old is None and d.get('retired_parent_cleanup'):
        spec=importlib.util.spec_from_file_location('reassignment_old_list_cleanup',Path(__file__).with_name('reminders_old_list_cleanup.py'))
        cleanup=importlib.util.module_from_spec(spec);spec.loader.exec_module(cleanup)
        cleanup.retired_parent_cleaned(None,d);raise ValueError('reassignment_retired_source_removed_by_cleanup')
    new=next((r for r in meta['lists'] if r['id']==d['list_id']),None)
    group=next((r for r in meta['groups'] if r['id']==d.get('native_group_id')),None)
    if (not old or not new or not group or old.get('shared',False) is not False or new.get('shared',False) is not False or
            new['name']!=d['list_name'] or old['account_id']!=new['account_id'] or
            group['account_id']!=new['account_id'] or new['account_id']!=d.get('account_id') or
            new.get('group_id')!=group['id'] or old.get('group_id')!=group['id']):raise ValueError('reassignment_account_group_or_sharing_conflict')
    if any(x['name'] not in permissions and x['id'] not in permissions for x in (old,new)):raise ValueError('reassignment_permission_required')
    if (config['structure']['projects'].get(dest,{}).get('list_id')!=d['list_id'] or
            config['structure'].get('native_groups',{}).get(group['id'])!=config['structure']['projects'][dest].get('group')):raise ValueError('reassignment_structure_conflict')
    link=s['tasks'][target['task_id']]
    known={'reminder_id','notes_owner','last_hub_day','last_remote_day','last_hub_title','last_remote_title','last_completed','repeating'}
    if set(link)-known:raise ValueError('reassignment_unknown_link_metadata_unsupported')
    reference_config=copy.deepcopy(config);reference_config['projects'][source]['tasks'].pop(target['task_id'])
    if target['task_id'] in pl.encoded(reference_config):raise ValueError('reassignment_external_config_reference_unsupported')
    if (link.get('reminder_id')!=target['reminder_id'] or any(k.startswith('pending_') or k in {'cancellation','external_retirement','task_reassignment'} for k in link)):
        raise ValueError('reassignment_target_binding_changed')
    for pid,b in config['projects'].items():
        for tid,t in b.get('tasks',{}).items():
            if t.get('reminder_id')==target['reminder_id'] and (pid,tid)!=(source,target['task_id']):raise ValueError('reassignment_duplicate_uuid')
        for h in b.get('history',{}).values():
            if h.get('original_id')==target['reminder_id'] or (h.get('project_id')==source and h.get('task_id')==target['task_id']):raise ValueError('reassignment_selected_recurrence_history')
    return s,d,link,retired


def new_id(hub,dest,config):
    hp=sync.HubProject(hub,dest);prefix='TASK-'+dest+'-'+datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).strftime('%Y%m%d')+'-'
    used=set(hp.rows()) | set(config['projects'][dest].get('tasks',{}))
    used.update(h.get('task_id') for h in config['projects'][dest].get('history',{}).values())
    for index in range(1,1000):
        tid=prefix+f'{index:03}'
        if tid not in used and hp.parser._valid_task_id(dest,tid):return tid
    raise ValueError('reassignment_task_ids_exhausted')


def canonical_plan(hub,target,tid):
    projects={};source=target['source_project'];dest=target['destination_project'];old=target['task_id']
    hp=sync.HubProject(hub,source);row=hp.rows().get(old)
    if not row or row['kind']!='future' or row['status']!='ready':raise ValueError('reassignment_requires_future_ready')
    if row.get('scheduled') is not None or row.get('event_link') is not None:raise ValueError('reassignment_calendar_reference_unsupported')
    first,last,block=sync.chunk(hp.texts['future'],'future',old)
    content=block.replace('### '+old+' — ','',1)
    if re.search(r'\b(?:TASK-(?:[a-z0-9-]+-)?\d{8}-\d{3}|FT-\d{8}-\d+)\b',content):raise ValueError('reassignment_task_reference_unsupported')
    if re.search(r'(?im)^\s*(?:calendar\b|calendar[ _-]|event[ _-]?id\b|календар|depends\b|dependency\b|завис|blocked\b|after[ _-]task\b)',block):raise ValueError('reassignment_external_reference_unsupported')
    # Любая ссылка на выбранный ID вне самого переносимого блока требует решения человека.
    for pid in (source,dest):
        current=sync.HubProject(hub,pid);before=copy.deepcopy(current.texts)
        if any(current.paths[k].read_bytes()!=v.encode() for k,v in before.items()):raise ValueError('reassignment_unsupported_canonical_encoding')
        for kind,text in before.items():
            selected=text[:first]+text[last:] if pid==source and kind=='future' else text
            if old in selected:raise ValueError('reassignment_task_references_unsupported')
        projects[pid]=dict(before=before,after=copy.deepcopy(before))
    allowed={'Status','Project','Due','Priority','Source','Created','Stage'}
    for field in re.findall(r'^([A-Za-z][A-Za-z0-9_ -]*):',block,re.M):
        if field not in allowed:raise ValueError('reassignment_unknown_canonical_field_unsupported')
    changed=block.replace('### '+old+' — ', '### '+tid+' — ',1)
    # Только точное служебное поле проекта. Пользовательский текст не редактируется.
    changed=re.sub(r'^Project: '+re.escape(source)+r'$', 'Project: '+dest,changed,flags=re.M)
    if re.search(r'^Project: (?!'+re.escape(dest)+r'$)',changed,re.M):raise ValueError('reassignment_ambiguous_project_field')
    projects[source]['after']['future']=hp.texts['future'][:first]+hp.texts['future'][last:]
    projects[dest]['after']['future']+='\n'+changed
    for pid,item in projects.items():
        p=sync.HubProject(hub,pid)
        for kind,text in item['after'].items():
            p.parser.read_records(pid,kind,text)
            if p.parser.unrecognized_headings(kind,text.splitlines()):raise ValueError('reassignment_unrecognized_heading')
    newrow=dict(row,project_id=dest,task_id=tid,TaskID=tid)
    return projects,row,block,newrow


def notes_plan(remote,row,newrow,link,config,hub):
    notes=remote.get('notes') or ''
    old=(row['project_id'],row['task_id'])
    owner=link.get('notes_owner')
    if isinstance(owner,dict) and 'line' in owner:raise ValueError('legacy_notes_ownership_unsupported')
    if sync.creation_identity(remote,sync.compact_identities(config))!=old:raise ValueError('reassignment_marker_ownership_required')
    # Только compact marker с доказанной старой парой. Legacy-блоки не угадываем.
    marker='Хаб: '+sync.compact_code(*old)
    if len(re.findall(r'(?m)^'+re.escape(marker)+r'$',notes))!=1 or '--- Hub metadata ---' in notes:raise ValueError('reassignment_exact_compact_marker_required')
    if re.search(r'(?m)^Крайний срок: ',notes) and not link.get('notes_owner'):raise ValueError('notes_ownership_conflict')
    # Валидируем прежнее владение existing managed_notes до замены старой идентичности.
    oldrow=dict(row,project_label=sync.project_label(hub,row['project_id'],config['projects'][row['project_id']]))
    notes,validated_owner=sync.managed_notes(notes,oldrow,link,repeating=True)
    newmarker='Хаб: '+sync.compact_code(newrow['project_id'],newrow['task_id'])
    notes=re.sub(r'(?m)^'+re.escape(marker)+r'$',lambda _:newmarker,notes,count=1)
    newrow=dict(newrow,project_label=sync.project_label(hub,newrow['project_id'],config['projects'][newrow['project_id']]))
    return sync.managed_notes(notes,newrow,{'notes_owner':validated_owner},repeating=True)


def preview(hub,target,user_intent,native=None):
    hub=pl.safe(hub)
    if (not isinstance(target,dict) or set(target)!={'source_project','task_id','reminder_id','destination_project'} or
            not pl.valid_uuid(target['reminder_id'])):raise ValueError('invalid_reassignment_target')
    if (not isinstance(user_intent,dict) or user_intent.get('confirmed') is not True or user_intent.get('target')!=target or
            not isinstance(user_intent.get('statement'),str) or not user_intent['statement'].strip()):raise ValueError('exact_user_reassignment_intent_required')
    with pl.locked(hub):
        config,_=pl.config_read(hub);raw=(hub/'ai/reminders-sync.json').read_bytes().decode('utf-8')
        if json.loads(raw)!=config:raise ValueError('reassignment_config_snapshot_conflict')
        registered=sync.registered(hub);pids=[target['source_project'],target['destination_project']]
        if any(p not in registered or p not in config['projects'] for p in pids):raise ValueError('unregistered_reassignment_project')
        for pid in pids:pl.ensure_no_pending(hub,config,pid)
        files=snapshot_files(hub,config);names=json.loads(files[sync.standard_allowlist(config)])['names']
        native=native or sync.Native(config);meta=metadata(native)
        s,d,link,retired=binding_guards(config,target,meta,names)
        tid=new_id(hub,target['destination_project'],config);projects,row,block,newrow=canonical_plan(hub,target,tid)
        before=observe(native,[retired['list_id'],d['list_id']]);remote=before[retired['list_id']].get(target['reminder_id'])
        if (not remote or remote.get('parent_id') is not None or remote.get('subtasks') or remote.get('completed',False) is not False or
                remote.get('list')!=next(x['name'] for x in meta['lists'] if x['id']==retired['list_id']) or
                any(x.get('parent_id')==remote['id'] for values in before.values() for x in values.values())):raise ValueError('reassignment_remote_root_required')
        if before[retired['list_id']].get(retired['id'])!=retired['snapshot']:raise ValueError('retired_parent_changed')
        repeat=remote.get('repeat')
        if repeat is not None and (not isinstance(repeat,dict) or repeat.get('frequency') not in {'daily','weekly','monthly','yearly'} or type(repeat.get('interval',1)) is not int or repeat.get('interval',1)<1):raise ValueError('reassignment_unsupported_recurrence')
        notes,owner=notes_plan(remote,row,newrow,link,config,hub)
        after=copy.deepcopy(remote);after.update(list=d['list_name'],list_id=d['list_id'],parent_id=None,notes=notes)
        if metadata(native)!=meta:raise ValueError('reassignment_metadata_changed')
        plan=dict(version=1,kind=KIND,operation=str(uuid.uuid4()),hub=str(hub),target=target,user_intent=user_intent,projects=projects,
                  config_raw=raw,config=config,files=files,metadata=meta,native_before=before,remote_before=remote,remote_after=after,
                  new_task_id=tid,new_notes_owner=owner,original_block=block,original_row=row,original_link=link)
        root=pl.safe(hub/'ai/reminders-task-reassignments');root.mkdir(exist_ok=True);folder=root/plan['operation'];folder.mkdir()
        path=folder/'plan.json';data=pl.encoded(plan);pl.durable(path,data,True);digest=pl.sha(data)
        pl.durable(folder/'state.json',pl.encoded(dict(sha256=digest,phase='preview',approved=False)),True)
        return dict(plan=str(path),sha256=digest,new_task_id=tid)


def documents(plan,digest):
    before=plan['config_raw'];intent=copy.deepcopy(plan['config']);pids=plan['projects']
    for pid in pids:intent.setdefault('project_list_migrations_pending',{})[pid]=digest
    bound=copy.deepcopy(intent);t=plan['target'];source=t['source_project'];dest=t['destination_project']
    link=bound['projects'][source]['tasks'].pop(t['task_id']);link['notes_owner']=plan['new_notes_owner']
    link['task_reassignment']={'operation':plan['operation'],'plan_sha256':digest}
    bound['projects'][dest]['tasks'][plan['new_task_id']]=link
    bound.setdefault('task_reassignments_completed',{})[plan['operation']]=digest
    final=copy.deepcopy(bound)
    for pid in pids:final['project_list_migrations_pending'].pop(pid)
    return [before,pl.encoded(intent),pl.encoded(bound),pl.encoded(final)]


def verify_canonical(hub,plan):
    for pid,item in plan['projects'].items():
        hp=sync.HubProject(hub,pid)
        for kind,text in hp.texts.items():
            if hp.paths[kind].read_bytes() not in (item['before'][kind].encode(),item['after'][kind].encode()):raise ValueError('reassignment_canonical_snapshot_conflict')


def verify_remote(native,plan,allow_after):
    if metadata(native)!=plan['metadata']:raise ValueError('reassignment_remote_metadata_changed')
    observed=observe(native,plan['native_before']);rid=plan['target']['reminder_id'];before=plan['remote_before'];after=plan['remote_after']
    matches=[]
    for lid,rows in observed.items():
        if rid in rows:matches.append(rows[rid])
    if len(matches)!=1:raise ValueError('reassignment_remote_identity_changed')
    current=matches[0]
    old=current==before
    own_after=allow_after and exact_fields(current)==exact_fields(after) and current.get('version')!=before['version']
    if not old and not own_after:raise ValueError('reassignment_remote_changed')
    expected=copy.deepcopy(plan['native_before'])
    if own_after:
        del expected[before['list_id']][rid];expected[after['list_id']][rid]=current
    if observed!=expected:raise ValueError('reassignment_remote_neighbors_changed')
    return current,own_after


def apply(path,digest,approve=False,native=None):
    if not approve:raise ValueError('explicit_reassignment_approval_required')
    path,plan,state=read(path,digest);hub=pl.safe(plan['hub']);configs=documents(plan,digest)
    def save(phase):
        state.update(phase=phase,approved=True);pl.durable(path.with_name('state.json'),pl.encoded(state))
    with pl.locked(hub):
        for name,text in plan['files'].items():
            if pl.safe(name).read_bytes().decode('utf-8')!=text:raise ValueError('reassignment_permission_or_registry_changed')
        config_path=hub/'ai/reminders-sync.json';raw=config_path.read_bytes().decode('utf-8')
        if raw not in configs:raise ValueError('reassignment_config_snapshot_conflict')
        # Preview cannot resume from somebody else's supposedly completed document.
        if state['phase']=='preview' and raw!=configs[0]:raise ValueError('reassignment_unapproved_config_changed')
        clean=json.loads(raw)
        for pid in plan['projects']:
            if clean.get('project_list_migrations_pending',{}).get(pid)==digest:clean['project_list_migrations_pending'].pop(pid)
        blocked=pl.pending_projects(hub,clean,ignore_reassignment=plan['operation'])
        cancellation=sync.cancellation_module()
        if cancellation:blocked.update(cancellation.pending_projects(hub,clean))
        blocked.update(sync.structure_module().pending_structure_projects(hub,clean))
        if set(plan['projects']) & blocked:raise ValueError('reassignment_other_operation_pending')
        verify_canonical(hub,plan)
        if state['phase']=='preview' and any(sync.HubProject(hub,pid).texts!=item['before'] for pid,item in plan['projects'].items()):raise ValueError('reassignment_canonical_changed')
        native=native or sync.Native(json.loads(raw));remote,own_after=verify_remote(native,plan,state['phase'] not in {'preview','intent'})
        if state['phase']=='complete':
            if raw!=configs[3] or not own_after or any(sync.HubProject(hub,pid).texts!=item['after'] for pid,item in plan['projects'].items()):raise ValueError('reassignment_completed_readback_conflict')
            return dict(phase='complete',reminder_id=remote['id'],task_id=plan['new_task_id'])
        if state['phase']=='preview':save('intent')
        if raw==configs[0]:
            if config_path.read_bytes().decode('utf-8')!=raw:raise ValueError('reassignment_config_cas_conflict')
            verify_canonical(hub,plan)
            pl.durable(config_path,configs[1]);raw=configs[1]
        # Известный собственный результат допускается только после WAL native.
        if not own_after:
            if raw!=configs[1] or any(sync.HubProject(hub,pid).texts!=item['before'] for pid,item in plan['projects'].items()):raise ValueError('reassignment_native_reverted')
            save('native')
            native.call('update_reminder',dict(id=remote['id'],version=remote['version'],list=plan['remote_after']['list_id'],parent_id=None,notes=plan['remote_after']['notes']))
            remote,own_after=verify_remote(native,plan,True)
            if not own_after:raise ValueError('reassignment_native_update_unconfirmed')
        for phase,pid in [('canonical_dest',plan['target']['destination_project']),('canonical_source',plan['target']['source_project'])]:
            hp=sync.HubProject(hub,pid);item=plan['projects'][pid]
            if hp.texts!=item['after']:
                verify_canonical(hub,plan);save(phase);hp.save(item['after'],allow_removal=[plan['target']['task_id']] if phase=='canonical_source' else ())
                if sync.HubProject(hub,pid).texts!=item['after']:raise ValueError('reassignment_canonical_readback_failed')
        if raw==configs[1]:
            save('binding')
            if config_path.read_bytes().decode('utf-8')!=raw:raise ValueError('reassignment_config_cas_conflict')
            pl.durable(config_path,configs[2]);raw=configs[2]
        # Квитанция хранит прежнее происхождение отдельно от recurrence history.
        receipt=path.with_name('receipt.json');expected=pl.encoded(dict(kind=KIND,operation=plan['operation'],plan_sha256=digest,
                    target=plan['target'],new_task_id=plan['new_task_id'],original_block=plan['original_block'],original_link=plan['original_link']))
        if receipt.exists():
            if receipt.read_bytes().decode('utf-8')!=expected:raise ValueError('reassignment_receipt_conflict')
        else:pl.durable(receipt,expected,True)
        verify_canonical(hub,plan);_,own_after=verify_remote(native,plan,True)
        if not own_after or any(sync.HubProject(hub,pid).texts!=item['after'] for pid,item in plan['projects'].items()):raise ValueError('reassignment_final_readback_failed')
        if config_path.read_bytes().decode('utf-8')!=raw or raw not in configs[2:]:raise ValueError('reassignment_config_readback_conflict')
        save('verified')
        if config_path.read_bytes().decode('utf-8')!=raw:raise ValueError('reassignment_final_config_cas_conflict')
        if raw==configs[2]:pl.durable(config_path,configs[3])
        if config_path.read_bytes().decode('utf-8')!=configs[3]:raise ValueError('reassignment_final_config_readback_failed')
        save('complete')
        return dict(phase='complete',reminder_id=remote['id'],task_id=plan['new_task_id'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('preview');p.add_argument('--hub',required=True);p.add_argument('--target-json',required=True);p.add_argument('--intent-json',required=True)
    for command in ('apply','status'):
        p=sub.add_parser(command);p.add_argument('--plan',required=True);p.add_argument('--sha256',required=True)
        if command=='apply':p.add_argument('--approve',action='store_true')
    args=parser.parse_args()
    if args.command=='preview':result=preview(Path(args.hub),json.loads(args.target_json),json.loads(args.intent_json))
    elif args.command=='apply':result=apply(args.plan,args.sha256,args.approve)
    else:
        _,plan,state=read(args.plan,args.sha256);result=dict(state=state,pending=sorted(pending_projects(Path(plan['hub']),sync.load_config(Path(plan['hub'])))))
    print(pl.encoded(result),end='')
if __name__=='__main__':main()
