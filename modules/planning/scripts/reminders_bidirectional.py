"""Ограниченный двусторонний план и возобновляемый журнал перемещений."""
import copy
import hashlib
import json
from pathlib import Path


def merge(current, baseline, remote):
    if current == remote:
        return current, 'unchanged' if current == baseline else 'converged'
    if current == baseline:
        return remote, 'incoming'
    if remote == baseline:
        return current, 'outgoing'
    raise ValueError('structure_two_sided_conflict')


def normalized(snap):
    value=copy.deepcopy(snap)
    for row in value['reminders'].values():
        row.pop('version',None)
        row.pop('list',None)
        row.pop('subtasks',None)  # Derived summary; actual child UUID/parent relations remain in the full snapshot.
        if row.get('parent_id') is None:row.pop('parent_id',None)
    return value


def projected(snap, step):
    value=copy.deepcopy(snap)
    if step['kind']=='list':
        value['lists'][step['id']]['group_id']=step['group']
    else:
        row=value['reminders'][step['id']]
        if 'list' in step:row['list_id']=step['list']
        if 'parent_id' in step:
            row.pop('parent_id',None)
            if step['parent_id'] is not None:row['parent_id']=step['parent_id']
    return value


def plan(m, hub, config, snap, originals, verified_cancellations=None):
    effective=copy.deepcopy(config); structure=effective['structure']
    arch=hub/'ai/archiprojects.md'; registry=hub/'ai/project-registry.md'
    groups=m.load_groups(originals[arch]); cards=m.registry_cards(hub,originals[registry])
    roles=structure['list_roles']; after={}; steps=[]; items=[]; blocked=set()
    if set(structure['projects'])!=set(config['projects']):raise ValueError('missing_structure_baseline')
    inverse={}
    for native,gid in structure['native_groups'].items():
        if gid not in groups or groups[gid]['status']!='active':raise ValueError('unknown_archiproject_group')
        inverse.setdefault(gid,[]).append(native)
    resolutions=copy.deepcopy(structure.get('resolutions',{}))
    if not isinstance(resolutions,dict):raise ValueError('invalid_structure_resolutions')
    used=set(); challenges={}
    def choose(key,current,baseline,remote,lid,scope):
        if key in resolutions and (current==remote or current==baseline or remote==baseline):raise ValueError('structure_resolution_unused')
        try:return merge(current,baseline,remote)
        except ValueError:
            challenge=dict(base=baseline,hub=current,remote=remote,list_id=lid)
            related_lists={lid}
            if key.startswith('project:'):
                pid=key[8:]; related_lists.add(config['projects'][pid]['list_id'])
                related_lists.update(k for k,v in roles.items() if v.get('kind')=='subgroup' and v.get('archiproject_id')==current)
                default=structure.get('group_default_lists',{}).get(current)
                if default in roles:related_lists.add(default)
            scoped_snapshot=dict(lists={k:v for k,v in snap['lists'].items() if k in related_lists},reminders={k:v for k,v in snap['reminders'].items() if v['list_id'] in related_lists})
            related_bindings={pid:b for pid,b in config['projects'].items() if b.get('parent_id') in scoped_snapshot['reminders']}
            payload=dict(challenge=challenge,snapshot=scoped_snapshot,scope=scope,roles={k:v for k,v in roles.items() if k in related_lists},bindings=related_bindings)
            challenge['token']=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            challenges[key]=challenge
            decision=resolutions.get(key)
            if decision is None:raise
            if set(decision)!={'choice',*challenge} or {k:v for k,v in decision.items() if k!='choice'}!=challenge or decision['choice'] not in {'hub','reminders'}:
                raise ValueError('structure_resolution_stale')
            used.add(key)
            return (current,'outgoing') if decision['choice']=='hub' else (remote,'incoming')
    def consumed(key):
        if key in used:structure['resolutions'].pop(key,None)
    def target_native(gid):
        if gid in (None,'none'):return None
        live=[native for native in inverse.get(gid,[]) if native in snap.get('groups',{})]
        if len(live)!=1:raise ValueError('structure_destination_required')
        return live[0]
    def fail(exc, pids, **fields):
        blocked.update(pids)
        key='project:'+fields['project'] if 'project' in fields else 'subgroup:'+fields.get('archiproject','')
        extra={'resolution':challenges[key]} if key in challenges else {}
        items.append(dict(error=str(exc),direction='conflict',affected_projects=sorted(pids),**fields,**extra))
    # Validate every tree before any container can move.
    trees={}; currents={}; remotes={}; cancelled_by_project={}
    owners={}
    for pid,binding in config['projects'].items():
        try:
            if binding.get('archive'):
                m.archive_module(config).verify_archived(hub, config, pid, snap)
                continue
            if pid not in cards:raise ValueError('unregistered_or_inactive_project')
            card=cards[pid]; originals.setdefault(card,m.safe_path(card).read_text())
            currents[pid]=m.card_group(originals[card],pid,groups)
            baseline=structure['projects'][pid]
            if baseline['list_id']!=binding['list_id']:raise ValueError('structure_binding_baseline_mismatch')
            if any(link.get('cancellation') or link.get('external_retirement') for link in binding.get('tasks', {}).values()) and (verified_cancellations is None or pid not in verified_cancellations): raise ValueError('cancellation_readback_required')
            cancelled_by_project[pid] = (verified_cancellations or {}).get(pid, set())
            if binding.get('layout') == 'project_list':
                m.validate_project_list(pid, binding, snap, config, currents[pid], cancelled_by_project[pid])
                continue
            lid=m.validate_tree(pid,binding,snap,config,cancelled_by_project[pid])
            root=binding['parent_id']
            ids={root}|{rid for rid,row in snap['reminders'].items() if row.get('parent_id')==root}
            if any(row.get('parent_id') in ids-{root} for row in snap['reminders'].values()):raise ValueError('unsupported_structure_depth')
            if any(rid in owners for rid in ids):raise ValueError('duplicate_reminder_binding')
            owners.update({rid:pid for rid in ids}); trees[pid]=(lid,ids)
            role=roles[lid]
            if role.get('kind') not in {'direct','subgroup','project'}:raise ValueError('unconfirmed_list_role')
            remotes[pid]=role['archiproject_id'] if role['kind']=='subgroup' else m.remote_group(snap['lists'][lid],structure,groups)
            choose('project:'+pid,currents[pid],baseline['group'],remotes[pid],lid,originals[card])
        except Exception as exc:fail(exc,[pid],project=pid)
    new_groups=copy.deepcopy(groups)
    for lid,role in roles.items():
        if role.get('kind') not in {'direct','subgroup','project'}:raise ValueError('unconfirmed_list_role')
        if role['kind']!='subgroup':continue
        gid=role['archiproject_id']; affected=[]
        try:
            base=structure['subgroups'][gid]
            if gid not in groups or base['list_id']!=lid:raise ValueError('invalid_subgroup_binding')
            remote=m.remote_group(snap['lists'][lid],structure,groups); remote=None if remote=='none' else remote
            target,direction=choose('subgroup:'+gid,groups[gid]['parent'],base['parent'],remote,lid,originals[arch])
            new_groups[gid]['parent']=target; m.validate_groups(new_groups)
            if direction!='unchanged':
                affected=sorted(set(m.subgroup_scope(hub,originals[registry],groups,gid,originals))|{pid for pid,b in config['projects'].items() if snap['reminders'].get(b.get('parent_id'),{}).get('list_id')==lid})
                if any(pid in blocked for pid in affected):raise ValueError('subgroup_structure_conflict')
                if direction=='outgoing':steps.append(dict(kind='list',id=lid,group=target_native(target),projects=affected))
                if direction=='incoming':after[arch]=m.replace_parent(after.get(arch,originals[arch]),gid,target)
                items.append(dict(action='structure_subgroup_parent',archiproject=gid,parent=target,direction=direction,affected_projects=affected))
            structure['subgroups'][gid]['parent']=target
            consumed('subgroup:'+gid)
        except Exception as exc:
            new_groups[gid]=copy.deepcopy(groups.get(gid,{}))
            if not affected:affected=[pid for pid,b in structure['projects'].items() if b['group']==gid]
            fail(exc,affected or config['projects'],archiproject=gid)
    for pid,binding in effective['projects'].items():
        if pid in blocked or binding.get('layout') == 'project_list':continue
        try:
            lid,ids=trees[pid]; base=structure['projects'][pid]
            target,direction=choose('project:'+pid,currents[pid],base['group'],remotes[pid],lid,originals[cards[pid]]); destination=lid
            if cancelled_by_project.get(pid) and (lid != binding['list_id'] or direction == 'outgoing'): raise ValueError('cancellation_relocation_unsupported')
            if direction=='outgoing':
                if lid!=base['list_id']:raise ValueError('structure_destination_conflict')
                target_is_subgroup=any(role.get('kind')=='subgroup' and role.get('archiproject_id')==target for role in roles.values())
                dedicated=not target_is_subgroup and roles[lid]['kind']=='direct' and {rid for rid,row in snap['reminders'].items() if row['list_id']==lid}==ids
                if dedicated:
                    steps.append(dict(kind='list',id=lid,group=target_native(target),projects=[pid]))
                else:
                    candidates=[key for key,role in roles.items() if role.get('kind')=='subgroup' and role.get('archiproject_id')==target]
                    if not candidates:
                        default=structure.get('group_default_lists',{}).get(target)
                        if default in roles and roles[default].get('kind')=='direct' and m.remote_group(snap['lists'][default],structure,groups)==target:candidates=[default]
                    if len(candidates)!=1:raise ValueError('structure_destination_required')
                    destination=candidates[0]
                    if destination==lid:raise ValueError('structure_destination_required')
                    source_account=snap['lists'][lid].get('account_id')
                    if not source_account or source_account!=snap['lists'][destination].get('account_id'):raise ValueError('structure_account_unproven')
                    root=binding['parent_id']; children=sorted(ids-{root})
                    # Detach all children, move root, move and reattach each child.
                    for rid in children:steps.append(dict(kind='reminder',id=rid,parent_id=None,projects=[pid]))
                    steps.append(dict(kind='reminder',id=root,list=destination,projects=[pid]))
                    for rid in children:
                        steps.append(dict(kind='reminder',id=rid,list=destination,projects=[pid]))
                        steps.append(dict(kind='reminder',id=rid,parent_id=root,projects=[pid]))
            if direction=='incoming':after[cards[pid]]=m.replace_primary(originals[cards[pid]],target)
            if direction!='unchanged' or destination!=binding['list_id']:
                items.append(dict(project=pid,action='structure_project',group=target,list_id=destination,direction=direction))
            binding.update(list_id=destination,list_name=snap['lists'][destination]['name']); base.update(group=target,list_id=destination)
            consumed('project:'+pid)
        except Exception as exc:fail(exc,[pid],project=pid)
    for key in resolutions:
        if key not in used:
            if key.startswith('project:') and key[8:] in config['projects']:
                fail('structure_resolution_unused',[key[8:]],project=key[8:])
            elif key.startswith('subgroup:') and key[9:] in structure['subgroups']:
                fail('structure_resolution_unused',config['projects'],archiproject=key[9:])
            else:raise ValueError('structure_resolution_unused')
    # Verify the complete projected graph before any external action. Container moves
    # may otherwise drag a tree which another accepted operation just routed there.
    while True:
        final=snap
        for step in steps:final=projected(final,step)
        mismatched=[]
        for pid,binding in effective['projects'].items():
            if pid in blocked:continue
            if binding.get('archive'):
                m.archive_module(effective).verify_archived(hub, effective, pid, final)
                continue
            if binding.get('layout') == 'project_list':
                m.validate_project_list(pid, binding, final, effective, currents[pid], cancelled_by_project[pid])
                continue
            lid=final['reminders'][binding['parent_id']]['list_id']
            role=roles[lid]
            remote=role['archiproject_id'] if role['kind']=='subgroup' else m.remote_group(final['lists'][lid],structure,groups)
            if lid!=binding['list_id'] or remote!=structure['projects'][pid]['group']:mismatched.append(pid)
        if not mismatched:break
        component=set(mismatched); related=set()
        while True:
            previous=set(component)
            for pid in component:
                related.add(trees[pid][0]); related.add(final['reminders'][config['projects'][pid]['parent_id']]['list_id'])
            for step in steps:
                source=snap['reminders'].get(step['id'],{}).get('list_id')
                if (step['kind']=='list' and step['id'] in related) or source in related or step.get('list') in related:
                    component.update(pid for pid in step['projects'] if pid in config['projects'])
            if component==previous:break
        removed=[step for step in steps if set(step['projects'])&component]
        steps=[step for step in steps if not set(step['projects'])&component]
        affected_subgroups={roles[step['id']]['archiproject_id'] for step in removed if step['kind']=='list' and roles[step['id']]['kind']=='subgroup'}
        for pid in component:
            effective['projects'][pid]=copy.deepcopy(config['projects'][pid])
            structure['projects'][pid]=copy.deepcopy(config['structure']['projects'][pid])
            after.pop(cards[pid],None)
            key='project:'+pid
            if key in config['structure'].get('resolutions',{}):structure.setdefault('resolutions',{})[key]=copy.deepcopy(config['structure']['resolutions'][key])
        for gid in affected_subgroups:
            structure['subgroups'][gid]=copy.deepcopy(config['structure']['subgroups'][gid])
            key='subgroup:'+gid
            if key in config['structure'].get('resolutions',{}):structure.setdefault('resolutions',{})[key]=copy.deepcopy(config['structure']['resolutions'][key])
        items[:]=[item for item in items if 'error' in item or (item.get('project') not in component and item.get('archiproject') not in affected_subgroups)]
        after.pop(arch,None)
        for item in items:
            gid=item.get('archiproject')
            if item.get('action')=='structure_subgroup_parent' and item.get('direction')=='incoming':after[arch]=m.replace_parent(after.get(arch,originals[arch]),gid,structure['subgroups'][gid]['parent'])
        for pid in sorted(component):fail('structure_destination_conflict',[pid],project=pid)
    if effective!=config:after[hub/'ai/reminders-sync.json']=m.encoded(effective)
    return dict(config=effective,items=items,blocked_projects=sorted(blocked),ok=not blocked),steps,after


def attestation(config,originals,snapshot):
    payload=dict(config=config,originals=originals,snapshot=snapshot)
    return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def reconcile(m, hub, config, apply=False, native=None):
    migrating = m.migration_pending(hub, config)
    if migrating:
        return dict(config=copy.deepcopy(config), items=[dict(project=pid, error='migration_recovery_required') for pid in sorted(migrating)], blocked_projects=sorted(migrating), ok=False)
    result=dict(config=copy.deepcopy(config),items=[],blocked_projects=[],ok=True)
    try:
        hub=m.safe_path(Path(hub).absolute()); structure=config['structure']; roles=structure['list_roles']
        relative=Path(structure['journal_file'])
        if relative.is_absolute() or '..' in relative.parts or relative.parent!=Path('ai') or relative.name in {'reminders-sync.json','archiprojects.md','project-registry.md'}:raise ValueError('unsafe_journal_path')
        journal=m.safe_path(hub/relative); config_path=hub/'ai/reminders-sync.json'
        pending=json.loads(journal.read_text()) if journal.exists() else None
        active=structure.get('outgoing_intent_sha256'); completed=structure.get('outgoing_completed_sha256')
        unfinished=bool(active and active!=completed)
        if unfinished and not pending:raise ValueError('structure_recovery_journal_missing')
        if active and active==completed and pending and {'config','originals','snapshot'}<=set(pending):
            if attestation(pending['config'],pending['originals'],pending['snapshot'])!=active:raise ValueError('structure_intent_unattested')
            pending=None  # Only the trusted completion receipt makes historical status cosmetic.
        recovering=bool(pending and (unfinished or pending.get('status')!='complete' or pending.get('version')==2))
        if recovering and pending.get('version')!=2:
            if unfinished:raise ValueError('unsafe_structure_journal')
            # Existing local-only recovery keeps its original whitelist.
            return m.reconcile_structure_legacy(hub,config,apply,native)
        native=native or m.StructureNative(config)
        allow_path=m.safe_path(m.standard_allowlist(config)); group_path=m.safe_path(structure['groups_allowlist_file'])
        pin=m.safe_path(structure['group_ids_allowlist_file']) if structure.get('group_ids_allowlist_file') else None
        allow=json.loads(allow_path.read_text()); names=set(allow.get('names',[]) if isinstance(allow,dict) else allow)
        group_fields={'include_groups':True} if m.cancellation_sync_module().authority_enabled(config) else {}
        def read():
            snap=m.snapshot(native,roles,names,detailed=True,**group_fields)
            # Восстановление нормализует версии активных переносов, но прежний родитель неизменяем.
            m.retired_parent_ids(config,snap)
            return snap
        verified_cancellations = {pid: m.verified_cancelled_ids(hub, pid, binding, config, native) for pid, binding in config['projects'].items() if not binding.get('archive')}
        if recovering:
            if not apply:raise ValueError('structure_recovery_required')
            expected_keys={'version','status','config','originals','snapshot','steps','files','guards'}
            if set(pending)!=expected_keys:raise ValueError('unsafe_structure_journal')
            original_config=pending['config']
            digest=attestation(original_config,pending['originals'],pending['snapshot'])
            if config['structure'].get('outgoing_intent_sha256')!=digest:raise ValueError('structure_intent_unattested')
            old_view=m.nonstructural_config(original_config); current_view=m.nonstructural_config(config)
            old_view['structure'].pop('resolutions',None); current_view['structure'].pop('resolutions',None)
            old_view['structure'].pop('outgoing_intent_sha256',None); current_view['structure'].pop('outgoing_intent_sha256',None)
            if old_view!=current_view:raise ValueError('structure_recovery_config_mismatch')
            allowed={config_path,hub/'ai/archiprojects.md',hub/'ai/project-registry.md',allow_path,group_path}
            if pin:allowed.add(pin)
            # Card paths come only from the current trusted registry.
            registry_text=(hub/'ai/project-registry.md').read_text()
            allowed.update(m.registry_cards(hub,registry_text).values())
            import re
            for card_relative in re.findall(r'^Card: (.+)$',registry_text,re.M):
                card=m.safe_path(hub/card_relative)
                if card.parent!=hub/'ai/project-cards':raise ValueError('unsafe_structure_journal')
                allowed.add(card)
            originals={m.safe_path(hub/rel):text for rel,text in pending['originals'].items()}
            if not set(originals)<=allowed:raise ValueError('unsafe_structure_journal')
            required={config_path,hub/'ai/archiprojects.md',hub/'ai/project-registry.md',allow_path,group_path}
            if pin:required.add(pin)
            if not required<=set(originals):raise ValueError('unsafe_structure_journal')
            result,steps,after=plan(m,hub,original_config,pending['snapshot'],originals,verified_cancellations)
            result['config']['structure']['outgoing_intent_sha256']=digest
            after[config_path]=m.encoded(result['config'])
            pinned_before=copy.deepcopy(original_config); pinned_before['structure']['outgoing_intent_sha256']=digest
            pinned_text=m.encoded(pinned_before)
            files={str(p.relative_to(hub)):text for p,text in after.items()}
            guards={str(p.relative_to(hub)):text for p,text in originals.items() if p not in after}
            if pending['steps']!=steps or pending['files']!=files or pending['guards']!=guards:raise ValueError('unsafe_structure_journal')
            if config not in (original_config,pinned_before,result['config']):raise ValueError('structure_recovery_config_mismatch')
            first=pending['snapshot']
        else:
            if json.loads(config_path.read_text())!=config:raise ValueError('structure_config_changed')
            paths=[config_path,hub/'ai/archiprojects.md',hub/'ai/project-registry.md',allow_path,group_path]
            if pin:paths.append(pin)
            originals={m.safe_path(p):m.safe_path(p).read_text() for p in paths}
            shallow=m.snapshot(native,roles,names,detailed=False,detailed_ids=m.retired_parent_read_ids(config),**group_fields)
            fast_result,fast_steps,fast_after=plan(m,hub,config,shallow,originals,verified_cancellations)
            fast_items=fast_result['items']
            if not structure.get('resolutions') and not fast_steps and not fast_after and all(item.get('error')=='missing_bound_child' and 'resolution' not in item for item in fast_items):
                return fast_result
            first=read(); result,steps,after=plan(m,hub,config,first,originals,verified_cancellations)
            if not apply:return result
            if not steps and not after:return result
            digest=attestation(config,{str(p.relative_to(hub)):text for p,text in originals.items()},first)
            result['config']['structure']['outgoing_intent_sha256']=digest
            after[config_path]=m.encoded(result['config'])
            pinned_before=copy.deepcopy(config); pinned_before['structure']['outgoing_intent_sha256']=digest
            pinned_text=m.encoded(pinned_before)
            files={str(p.relative_to(hub)):text for p,text in after.items()}
            guards={str(p.relative_to(hub)):text for p,text in originals.items() if p not in after}
            m.fresh_reads()
            if read()!=first:raise ValueError('structure_snapshot_changed')
            for p,text in originals.items():
                if p.read_text()!=text:raise ValueError('structure_file_changed')
            pending=dict(version=2,status='pending',config=copy.deepcopy(config),originals={str(p.relative_to(hub)):text for p,text in originals.items()},snapshot=first,steps=steps,files=files,guards=guards)
            m.atomic_write(journal,m.encoded(pending))
            m.atomic_write(config_path,pinned_text)
        def guard():
            for p,before in originals.items():
                actual=m.safe_path(p).read_text()
                if actual not in (before,pinned_text if p==config_path else before,after.get(p,before)):raise ValueError('structure_recovery_guard_changed')
        states=[first]
        for step in steps:states.append(projected(states[-1],step))
        actual=read(); matches=[i for i,state in enumerate(states) if normalized(actual)==normalized(state)]
        if not matches:raise ValueError('structure_recovery_third_state')
        local_advanced=any(path.read_text()==text and text!=originals[path] and (path!=config_path or text!=pinned_text) for path,text in after.items())
        if local_advanced and normalized(actual)!=normalized(states[-1]):raise ValueError('structure_recovery_third_state')
        start=max(matches)
        for index in range(start,len(steps)):
            guard(); m.fresh_reads(); fresh=read()
            if fresh!=actual:raise ValueError('structure_snapshot_changed')
            guard()  # Recheck local intent after all fresh native reads, immediately before the write.
            step=steps[index]
            if step['kind']=='list':
                native.call('manage_list',dict(action='update',list=step['id'],group=step['group'],expected_group_id=fresh['lists'][step['id']]['group_id']))
            else:
                row=fresh['reminders'][step['id']]
                args=dict(id=step['id'],version=row['version'])
                args.update({key:step[key] for key in ('list','parent_id') if key in step})
                native.call('update_reminder',args)
            actual=read()
            if normalized(actual)!=normalized(states[index+1]):raise ValueError('structure_readback_failed')
        guard()
        if normalized(read())!=normalized(states[-1]):raise ValueError('structure_readback_failed')
        for path,text in after.items():
            guard()
            if path.read_text()!=text:m.atomic_write(path,text)
        guard()
        if normalized(read())!=normalized(states[-1]):raise ValueError('structure_readback_failed')
        guard()  # Final local proof follows the last native read, before the trusted receipt.
        if any(path.read_text()!=text for path,text in after.items()):raise ValueError('structure_local_readback_failed')
        completed_config=copy.deepcopy(result['config'])
        completed_config['structure']['outgoing_completed_sha256']=digest
        m.atomic_write(config_path,m.encoded(completed_config))  # Receipt follows all native/local final checks.
        result['config']=completed_config
        pending['status']='complete'; m.atomic_write(journal,m.encoded(pending))
        return result
    except Exception as exc:
        return dict(config=copy.deepcopy(config),items=result['items']+[dict(project='*',error=str(exc),direction='conflict')],blocked_projects=sorted(config['projects']),ok=False)
