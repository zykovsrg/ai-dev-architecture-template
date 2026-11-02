#!/usr/bin/env python3
"""Обратимый архив project_list. Любая запись требует принятого точного плана."""
import argparse, copy, datetime, fcntl, hashlib, importlib.util, json, re, uuid
import contextlib
from pathlib import Path

FIELDS = ('id', 'title', 'notes', 'due', 'repeat', 'parent_id')
TERMINAL = {'done', 'completed', 'dropped', 'promoted'}

def safe(p):
    p=Path(p)
    if not p.is_absolute() or '..' in p.parts or any(x.is_symlink() for x in [p,*p.parents]):
        raise ValueError('unsafe_archive_path')
    return p

def digest(value):
    if not isinstance(value,bytes): value=json.dumps(value,ensure_ascii=False,sort_keys=True).encode()
    return hashlib.sha256(value).hexdigest()

def load_sync():
    spec=importlib.util.spec_from_file_location('archive_sync',Path(__file__).with_name('reminders_sync.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def authority_archive():
    spec=importlib.util.spec_from_file_location('archive_authority_helper',Path(__file__).with_name('reminders_authority_archive.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

@contextlib.contextmanager
def archive_lock(hub,m):
    if hasattr(m,'sync_lock'):
        with m.sync_lock(hub):yield
    else:
        with (Path(hub)/'ai/.reminders-sync.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);yield

def registry_entry(hub,pid):
    text=safe(Path(hub)/'ai/project-registry.md').read_text()
    hits=re.findall(r'^## '+re.escape(pid)+r'\n(.*?)(?=^## |\Z)',text,re.M|re.S)
    if len(hits)!=1:raise ValueError('archive_registry_identity')
    def field(k):
        values=re.findall('^'+re.escape(k)+r': (.+)$',hits[0],re.M)
        if len(values)!=1:raise ValueError('archive_registry_field')
        return values[0]
    root=safe(field('Path'));card=safe(Path(hub)/field('Card'))
    if root.parent!=Path(hub)/'projects' or card!=Path(hub)/'ai/project-cards'/(pid+'.md'):
        raise ValueError('archive_registry_path')
    return root,card,field('Status')

def protected(row):
    out={k:row.get(k) for k in FIELDS}
    out['notes']=row.get('notes') or ''
    out['completed']=bool(row.get('completed'))
    return out

def snapshot(native,lists=None):
    meta=native.call('list_lists',{})
    if not isinstance(meta,dict) or meta.get('error') or meta.get('errors') or meta.get('more') or meta.get('has_more') or not isinstance(meta.get('lists'),list) or not isinstance(meta.get('groups',[]),list):raise ValueError('archive_incomplete_metadata')
    if len({r['id'] for r in meta['lists']})!=len(meta['lists']):raise ValueError('archive_duplicate_list_uuid')
    selected=meta['lists'] if lists is None else [r for r in meta['lists'] if r['id'] in lists]
    rows={}
    for l in selected:
        data=native.call('find_reminders',dict(list=l['id'],include_completed=True,limit=500))
        records=data['reminders']
        if data.get('more') or data.get('has_more') or data.get('count',len(records))!=len(records) or len(records)!=l['total']:
            raise ValueError('archive_incomplete_snapshot')
        for row in records:
            if row['id'] in rows:raise ValueError('archive_duplicate_uuid')
            rows[row['id']]=dict(row,list_id=l['id'])
    return dict(lists={r['id']:r for r in meta['lists']},reminders=rows,groups=meta.get('groups',[]))

def pending_projects(hub,config):
    return set(config.get('archive_pending',{}).get('projects',[]))

def module():
    return load_sync()

def read_receipt(hub,config,pid):
    selected=load_sync().authority_enabled(config)
    ref=config['projects'][pid].get('archive')
    if not ref:return None
    rel=ref.get('journal','')
    if not re.fullmatch(r'ai/reminders-archives/[a-z0-9-]+',rel):raise ValueError('archive_receipt_path')
    folder=safe(Path(hub)/rel)
    plan=json.loads((folder/'plan.json').read_text())
    if digest((folder/'plan.json').read_bytes())!=ref.get('token'):raise ValueError('archive_receipt_checksum')
    state=json.loads((folder/'state.json').read_text())
    saved=state.get('projects',{}).get(pid)
    if state.get('phase')!='complete' or not state.get('approved') or not saved or saved.get('phase')!='committed' or ref.get('operation')!=plan['operation']:
        raise ValueError('archive_receipt_incomplete')
    adopted=authority_archive().archive_adopted(hub,config,pid,plan,state,saved) if selected else False
    binding=copy.deepcopy(config['projects'][pid]);binding.pop('archive',None)
    if not adopted and binding!=saved['binding_after']:raise ValueError('archive_binding_changed')
    root,card,status=registry_entry(hub,pid)
    if status!='archived' or re.findall(r'^Status: (.+)$',card.read_text(),re.M)!=['archived']:
        raise ValueError('archive_status_conflict')
    if card.read_text()!=saved['card_after']:
        raise ValueError('archive_card_changed')
    registry=(Path(hub)/'ai/project-registry.md').read_text()
    section=re.search(r'^## '+re.escape(pid)+r'\n.*?(?=^## |\Z)',registry,re.M|re.S)
    if not section or section[0].rstrip()!=saved['registry_section_after'].rstrip():
        raise ValueError('archive_registry_section_changed')
    if not adopted:
        for kind,text in saved['files_after'].items():
            if (root/'ai'/kind).read_text()!=text:raise ValueError('archive_task_file_changed')
    return plan,state,saved

def verify_archived(hub,config,pid,snap):
    receipt=read_receipt(hub,config,pid)
    if receipt is None:return False
    plan,state,saved=receipt;b=config['projects'][pid];l=snap['lists'].get(b['list_id'],{})
    if l.get('name')!=b['list_name'] or l.get('group_id')!=state['archive_group']['id'] or l.get('account_id')!=plan['account_id']:
        raise ValueError('archive_native_identity_changed')
    if authority_archive().archive_adopted(hub,config,pid,plan,state,saved):
        authority_archive().verify_group(config,state['archive_group'],snap)
        for rid,old in saved['native_after'].items():
            row=snap['reminders'].get(rid)
            if row and (row.get('list_id')!=b['list_id'] or row.get('parent_id')!=old.get('parent_id')):raise ValueError('archive_native_identity_changed')
        return True
    actual={rid:protected(r) for rid,r in snap['reminders'].items() if r.get('list_id')==b['list_id']}
    if actual!=saved['native_after'] or set(saved['gap_ids'])&set(snap['reminders']):
        raise ValueError('archive_native_content_changed')
    return True

def verify_current(hub,config,pid,native):
    if not config['projects'][pid].get('archive'):return False
    if not hasattr(native,'_archive_snapshot'):native._archive_snapshot=snapshot(native)
    return verify_archived(hub,config,pid,native._archive_snapshot)

def replace_status(text,old,new):
    if re.findall(r'^Status: (.+)$',text,re.M)!=[old]:raise ValueError('archive_status_changed')
    return re.sub(r'^Status: '+re.escape(old)+r'$', 'Status: '+new,text,flags=re.M)

def set_registry_status(text,pid,old,new):
    pat=r'(^## '+re.escape(pid)+r'\n)(.*?)(?=^## |\Z)'
    matches=list(re.finditer(pat,text,re.M|re.S))
    if len(matches)!=1:raise ValueError('archive_registry_identity')
    hit=matches[0];body=replace_status(hit[2],old,new)
    return text[:hit.start()]+hit[1]+body+text[hit.end():]

def preview(hub,pids,native=None):
    hub=safe(hub);m=load_sync();c=m.load_config(hub);native=native or m.Native(c)
    if m.authority_enabled(c):authority_archive().validate_activation(hub,c)
    if pending_projects(hub,c):raise ValueError('archive_recovery_required')
    snap=snapshot(native);accounts=set();projects={}
    for pid in pids:
        root,card,status=registry_entry(hub,pid);b=c['projects'][pid]
        if status!='active' or b.get('layout')!='project_list' or b.get('archive'):
            raise ValueError('archive_requires_active_project_list')
        if re.findall(r'^Status: (.+)$',card.read_text(),re.M)!=['active']:raise ValueError('archive_card_status')
        l=snap['lists'].get(b['list_id'],{})
        if l.get('name')!=b['list_name'] or l.get('group_id')!=b['native_group_id'] or l.get('account_id')!=b['account_id']:
            raise ValueError('archive_source_identity')
        accounts.add(l['account_id']);rows={rid:r for rid,r in snap['reminders'].items() if r['list_id']==b['list_id']}
        known={t['reminder_id'] for t in b.get('tasks',{}).values()}|set(b.get('history',{}))
        if set(rows)-known:raise ValueError('archive_foreign_or_unbound_tasks')
        gap=known-set(rows)
        if gap&set(snap['reminders']):raise ValueError('archive_bound_task_in_foreign_list')
        hp=m.HubProject(hub,pid)
        if any(r.get('repeat') for r in rows.values()) or any(t.get('repeating') for t in b.get('tasks',{}).values()):
            raise ValueError('archive_repeating_requires_separate_decision')
        if any(r['status'] not in TERMINAL and r['kind']!='future' for r in hp.rows().values()):
            raise ValueError('archive_nonfuture_open_task_requires_review')
        projects[pid]=dict(binding=copy.deepcopy(b),files={n:(root/'ai'/n).read_text() for n in m.NAMES.values()},
            card_path=str(card.relative_to(hub)),card=card.read_text(),root=str(root),
            native_before={rid:copy.deepcopy(r) for rid,r in rows.items()},gap_ids=sorted(gap),
            open_tasks=[r['task_id'] for r in hp.rows().values() if r['status'] not in TERMINAL])
    if len(accounts)!=1:raise ValueError('archive_account_ambiguous')
    groups=[g for g in snap['groups'] if g['name']=='Архив']
    if len(groups)>1 or groups and groups[0]['account_id']!=next(iter(accounts)):raise ValueError('archive_group_conflict')
    gp=safe(c['structure']['groups_allowlist_file']);pin=safe(c['structure']['group_ids_allowlist_file'])
    plan=dict(version=1,operation=str(uuid.uuid4()),hub=str(hub),account_id=next(iter(accounts)),projects=projects,
        config_before=(hub/'ai/reminders-sync.json').read_text(),registry_before=(hub/'ai/project-registry.md').read_text(),
        group_permissions_path=str(gp),group_permissions_before=gp.read_text(),group_ids_path=str(pin),group_ids_before=pin.read_text(),
        archive_group=groups[0] if groups else None,confirmation='Пользователь подтвердил готовность всех выбранных проектов. Отсутствие UUID не считается выполнением в приложении.')
    folder=hub/'ai/reminders-archives'/plan['operation'];folder.mkdir(parents=True)
    m.atomic_json(folder/'plan.json',plan);m.atomic_json(folder/'state.json',dict(phase='preview',projects={}))
    return dict(plan=str(folder/'plan.json'),sha256=digest((folder/'plan.json').read_bytes()),
        projects={pid:dict(list_id=v['binding']['list_id'],open_tasks=v['open_tasks'],preserved_preexisting_gap=v['gap_ids']) for pid,v in projects.items()},
        create_group=not bool(groups),archive_group_name='Архив')

def _settle_config(hub,m,folder,state):
    intent=state.get('config_intent')
    if not intent:return
    target=Path(hub)/'ai/reminders-sync.json';actual=target.read_text()
    if actual not in [intent['before'],intent['after']]:raise ValueError('archive_config_changed')
    if actual==intent['before']:m.atomic_json(target,json.loads(intent['after']))
    if target.read_text()!=intent['after']:raise ValueError('archive_config_readback')
    state['config_expected']=intent['after'];state.pop('config_intent')
    m.atomic_json(folder/'state.json',state)

def _config_write(hub,m,folder,state,c,default):
    target=Path(hub)/'ai/reminders-sync.json';before=state.get('config_expected',default)
    if target.read_text()!=before:raise ValueError('archive_config_changed')
    after=json.dumps(c,ensure_ascii=False,indent=2)+'\n'
    state['config_intent']=dict(before=before,after=after)
    m.atomic_json(folder/'state.json',state)
    _settle_config(hub,m,folder,state)

def _section(text,pid):
    hit=re.search(r'^## '+re.escape(pid)+r'\n.*?(?=^## |\Z)',text,re.M|re.S)
    if not hit:raise ValueError('archive_registry_identity')
    return hit[0].rstrip()

def apply(path,token,approve=False,native=None):
    if not approve:raise ValueError('explicit_approval_required')
    path=safe(path)
    if digest(path.read_bytes())!=token:raise ValueError('archive_plan_changed')
    plan=json.loads(path.read_text());hub=safe(plan['hub']);m=load_sync();folder=path.parent
    with archive_lock(hub,m):
        m.load_config(hub)  # Неверный выбранный режим не разрешает восстановительную запись конфигурации.
        state=json.loads((folder/'state.json').read_text())
        def save():m.atomic_json(folder/'state.json',state)
        if state['phase']=='complete':
            c=m.load_config(hub);n=native or m.Native(c);snap=snapshot(n)
            for pid in plan['projects']:
                if m.authority_enabled(c):authority_archive().adopt_new_archive(hub,c,pid)
                if not verify_archived(hub,c,pid,snap):raise ValueError('archive_restored_requires_new_plan')
            return state
        _settle_config(hub,m,folder,state)
        expected=state.get('config_expected',plan['config_before'])
        if (hub/'ai/reminders-sync.json').read_text()!=expected:raise ValueError('archive_config_changed')
        c=m.load_config(hub);n=native or m.Native(c)
        if m.authority_enabled(c):authority_archive().validate_activation(hub,c)
        def config_save():
            _config_write(hub,m,folder,state,c,plan['config_before'])
        if state['phase']=='preview':
            if (hub/'ai/project-registry.md').read_text()!=plan['registry_before']:raise ValueError('archive_registry_changed')
            for pid,v in plan['projects'].items():
                if any((Path(v['root'])/'ai'/name).read_text()!=text for name,text in v['files'].items()) or (hub/v['card_path']).read_text()!=v['card']:
                    raise ValueError('archive_local_changed')
            c['archive_pending']=dict(operation=plan['operation'],projects=list(plan['projects']))
            state.update(phase='permissions',approved=True);config_save()
        gp=safe(plan['group_permissions_path']);pin=safe(plan['group_ids_path'])
        names=json.loads(plan['group_permissions_before']);after=copy.deepcopy(names)
        if 'Архив' not in after['names']:after['names'].append('Архив')
        if json.loads(gp.read_text()) not in [names,after]:raise ValueError('archive_group_permissions_changed')
        m.atomic_json(gp,after)
        if 'archive_group' not in state:
            if state['phase']=='group_intent':raise ValueError('archive_group_creation_uncertain_requires_review')
            meta=n.call('list_lists',{});groups=[g for g in meta.get('groups',[]) if g['name']=='Архив']
            if plan['archive_group']:
                if len(groups)!=1 or groups[0]['id']!=plan['archive_group']['id']:raise ValueError('archive_group_changed')
            elif groups and not (state.get('phase')=='group_created' and state.get('group_create_result')):raise ValueError('archive_group_appeared_concurrently')
            elif not groups:
                state['phase']='group_intent';save()
                result=n.call('manage_group',dict(action='create',group='Архив'))
                state['group_create_result']=result;state['phase']='group_created';save()
                groups=[g for g in n.call('list_lists',{}).get('groups',[]) if g['name']=='Архив']
            created=state.get('group_create_result')
            if created:
                returned=created.get('group',created)
                if len(groups)!=1 or groups[0]['id']!=returned.get('id'):raise ValueError('archive_created_group_identity_changed')
            if len(groups)!=1 or groups[0].get('account_id')!=plan['account_id']:raise ValueError('archive_group_account')
            state['archive_group']=groups[0];state['phase']='projects';save()
        gid=state['archive_group']['id'];pins=json.loads(plan['group_ids_before']);newpins=copy.deepcopy(pins)
        if gid in newpins['groups'] and newpins['groups'][gid]!='Архив':raise ValueError('archive_group_pin_conflict')
        newpins['groups'][gid]='Архив'
        if json.loads(pin.read_text()) not in [pins,newpins]:raise ValueError('archive_group_pins_changed')
        m.atomic_json(pin,newpins)
        for pid,v in plan['projects'].items():
            project=state['projects'].setdefault(pid,dict(phase='tasks',completed_intents={}))
            if project['phase']=='committed':continue
            b=c['projects'][pid]
            if b!=v['binding']:raise ValueError('archive_project_binding_changed')
            root=Path(v['root']);fresh=snapshot(n)
            if set(v['gap_ids'])&set(fresh['reminders']):raise ValueError('archive_gap_reappeared')
            l=fresh['lists'][b['list_id']]
            if l['name']!=b['list_name'] or l['account_id']!=plan['account_id'] or l['group_id'] not in [b['native_group_id'],gid]:
                raise ValueError('archive_list_changed')
            before=v['native_before'];actual={rid:r for rid,r in fresh['reminders'].items() if r['list_id']==b['list_id']}
            if set(actual)!=set(before):raise ValueError('archive_task_set_changed')
            for rid,original in before.items():
                expectedrow=protected(original);now=actual[rid]
                if rid not in project['completed_intents'] and project['phase']=='tasks' and now.get('version')!=original.get('version'):
                    raise ValueError('archive_task_version_changed')
                if rid in project['completed_intents']:expectedrow['completed']=True
                if protected(now)!=expectedrow:
                    if rid in project['completed_intents'] and protected(now)==protected(original) and now.get('version')==original.get('version'):
                        n.update(now, {'completed':True})
                        now=n.get(rid,b['list_id'])
                    else:raise ValueError('archive_task_changed')
                if not original.get('completed'):
                    if rid not in project['completed_intents']:
                        project['completed_intents'][rid]=True;save()
                        n.update(now,{'completed':True})
                    check=n.get(rid,b['list_id'])
                    if protected(check)!=expectedrow|{'completed':True}:raise ValueError('archive_completion_readback')
            if project['phase']=='tasks':
                hp=m.HubProject(hub,pid);afterfiles=dict(hp.texts)
                if {m.NAMES[k]:t for k,t in hp.texts.items()}!=v['files']:raise ValueError('archive_task_file_changed')
                for tid in v['open_tasks']:
                    row=hp.rows()[tid];a,z,body=m.chunk(afterfiles['future'],'future',tid)
                    body=re.sub(r'^Status: .+$','Status: done',body,flags=re.M)
                    body += '\nГотовность подтверждена пользователем 2026-10-28 при архивировании проекта; фактическая дата релиза и URL не сообщены. Прежний контекст сохранён как история.\n'
                    afterfiles['future']=afterfiles['future'][:a]+body+afterfiles['future'][z:]
                project['files_after']={m.NAMES[k]:t for k,t in afterfiles.items()};project['phase']='files_intent';save()
            if project['phase']=='files_intent':
                target=root/'ai/future-tasks.md';current=target.read_text();wanted=project['files_after']['future-tasks.md']
                if current!=wanted:
                    if current!=v['files']['future-tasks.md']:raise ValueError('archive_local_concurrent_edit')
                    if m.authority_enabled(c):
                        m.parser_for(hub).write_task_file(hub,pid,'future',digest(current.encode()),wanted)
                    else:
                        import subprocess
                        result=subprocess.run(['python3',str(hub/'scripts/task_records.py'),'write','--hub',str(hub),'--project-id',pid,'--kind','future','--expected-sha256',digest(current.encode())],input=wanted,text=True,capture_output=True)
                        if result.returncode:raise ValueError('archive_task_write_failed: '+result.stdout+result.stderr)
                project['phase']='move_intent';save()
            current=n.call('list_lists',{});l=next(r for r in current['lists'] if r['id']==b['list_id'])
            if l['group_id']==b['native_group_id']:
                n.call('manage_list',dict(action='update',list=b['list_id'],group=gid,expected_group_id=b['native_group_id']))
            elif l['group_id']!=gid:raise ValueError('archive_group_concurrent_edit')
            final=snapshot(n);l=final['lists'][b['list_id']]
            if set(v['gap_ids'])&set(final['reminders']):raise ValueError('archive_gap_reappeared')
            if l['group_id']!=gid or l['account_id']!=plan['account_id'] or l['name']!=b['list_name']:raise ValueError('archive_move_readback')
            if any((root/'ai'/name).read_text()!=text for name,text in project['files_after'].items()):
                raise ValueError('archive_local_concurrent_edit')
            project['native_after']={rid:protected(r) for rid,r in final['reminders'].items() if r['list_id']==b['list_id']}
            expectedrows={rid:protected(r)|{'completed':True} for rid,r in before.items()}
            if project['native_after']!=expectedrows:raise ValueError('archive_content_after_move')
            project['gap_ids']=v['gap_ids'];project['phase']='metadata_intent';save()
            registry=hub/'ai/project-registry.md';text=registry.read_text()
            status=registry_entry(hub,pid)[2]
            original_section=_section(plan['registry_before'],pid)
            allowed_section=_section(set_registry_status(plan['registry_before'],pid,'active','archived'),pid)
            if _section(text,pid) not in [original_section,allowed_section]:raise ValueError('archive_registry_concurrent_edit')
            if status=='active':
                if registry.read_text()!=text:raise ValueError('archive_registry_concurrent_edit')
                registry.write_text(set_registry_status(text,pid,'active','archived'))
            elif status!='archived':raise ValueError('archive_status_concurrent_edit')
            card=hub/v['card_path'];text=card.read_text()
            if text==v['card']:card.write_text(replace_status(text,'active','archived'))
            elif text!=replace_status(v['card'],'active','archived'):raise ValueError('archive_card_concurrent_edit')
            for tid,link in b['tasks'].items():
                if link['reminder_id'] in project['native_after']:link['last_completed']=True
            project['card_after']=card.read_text()
            project['registry_section_after']=re.search(r'^## '+re.escape(pid)+r'\n.*?(?=^## |\Z)',registry.read_text(),re.M|re.S)[0]
            project['binding_after']=copy.deepcopy(b)
            b['archive']=dict(journal=str(folder.relative_to(hub)),token=token,operation=plan['operation'])
            project['phase']='committed';config_save()
        c.pop('archive_pending',None);config_save();state['phase']='complete';save()
        if m.authority_enabled(c):
            for pid in plan['projects']:authority_archive().adopt_new_archive(hub,c,pid)
        return state

def restore_preview(hub,pid,native=None):
    m=load_sync();c=m.load_config(hub);n=native or m.Native(c)
    if m.authority_enabled(c):
        authority_archive().validate_activation(hub,c)
        raise ValueError('authority_restore_requires_new_plan')
    if hasattr(n,'_archive_snapshot'):del n._archive_snapshot
    verify_current(hub,c,pid,n)
    plan,state,saved=read_receipt(hub,c,pid);original=plan['projects'][pid]
    return dict(project=pid,list_id=original['binding']['list_id'],from_group=state['archive_group']['id'],
        to_group=original['binding']['native_group_id'],gap_ids_preserved=saved['gap_ids'],
        warning='Возвращается исходное состояние, включая прежние missing. Отсутствующие UUID не воссоздаются.',
        token=digest(dict(config=c,receipt=state,project=pid,native_snapshot=n._archive_snapshot)),journal=config_journal(c,pid))

def config_journal(c,pid):return c['projects'][pid]['archive']['journal']

def restore(hub,pid,token,approve=False,native=None):
    if not approve:raise ValueError('explicit_restore_approval_required')
    m=load_sync();hub=safe(hub);c=m.load_config(hub);n=native or m.Native(c)
    if m.authority_enabled(c):
        authority_archive().validate_activation(hub,c)
        raise ValueError('authority_restore_requires_new_plan')
    if not c['projects'][pid].get('archive'):
        # Последняя запись конфигурации могла завершиться раньше записи журнала.
        matches=[]
        for candidate in (hub/'ai/reminders-archives').glob('*/state.json'):
            savedstate=json.loads(candidate.read_text())
            recovered=savedstate.get('projects',{}).get(pid,{})
            if recovered.get('restore',{}).get('token')==token:matches.append((candidate.parent,savedstate))
        if len(matches)!=1:raise ValueError('archive_restore_receipt_missing')
        folder,state=matches[0]
        with archive_lock(hub,m):
            _settle_config(hub,m,folder,state)
            plan=json.loads((folder/'plan.json').read_text());original=plan['projects'][pid]
            if digest((folder/'plan.json').read_bytes())!=state['projects'][pid]['restore']['plan_token'] or not state.get('approved'):
                raise ValueError('archive_restore_receipt_checksum')
            c=m.load_config(hub)
            if c['projects'][pid]!=original['binding'] or state['projects'][pid].get('phase')!='restored':
                raise ValueError('archive_restore_binding_changed')
            root,card,status=registry_entry(hub,pid)
            if status!='active' or card.read_text()!=original['card'] or _section((hub/'ai/project-registry.md').read_text(),pid)!=_section(plan['registry_before'],pid):
                raise ValueError('archive_restore_local_changed')
            if any((root/'ai'/name).read_text()!=text for name,text in original['files'].items()):raise ValueError('archive_restore_local_changed')
            final=snapshot(n,{original['binding']['list_id']});l=final['lists'][original['binding']['list_id']]
            if l['name']!=original['binding']['list_name'] or l['account_id']!=plan['account_id'] or l['group_id']!=original['binding']['native_group_id'] or {rid:protected(row) for rid,row in final['reminders'].items()if row['list_id']==l['id']}!={rid:protected(row)for rid,row in original['native_before'].items()}:
                raise ValueError('archive_restore_native_changed')
            return dict(project=pid,status='active',already_active=True,gap_ids_preserved=state['projects'][pid]['gap_ids'])
    ref=c['projects'][pid]['archive'];folder=safe(hub/ref['journal'])
    plan=json.loads((folder/'plan.json').read_text())
    if digest((folder/'plan.json').read_bytes())!=ref['token']:raise ValueError('archive_receipt_checksum')
    with archive_lock(hub,m):
        state=json.loads((folder/'state.json').read_text())
        _settle_config(hub,m,folder,state);c=m.load_config(hub)
        saved=state['projects'][pid];original=plan['projects'][pid];root=Path(original['root'])
        def save():m.atomic_json(folder/'state.json',state)
        def cfg():_config_write(hub,m,folder,state,c,state.get('config_expected',(hub/'ai/reminders-sync.json').read_text()))
        if not saved.get('restore'):
            view=restore_preview(hub,pid,n)
            if view['token']!=token:raise ValueError('archive_restore_preview_stale')
            saved['restore']=dict(token=token,plan_token=ref['token'],phase='started',group_intent=False,tasks={},files={},card_intent=False,registry_intent=False)
            save()
            c['archive_pending']=dict(operation=plan['operation'],projects=[pid]);cfg()
        recovery=saved['restore']
        if recovery['token']!=token:raise ValueError('archive_restore_token_changed')
        b=c['projects'][pid]
        snap=snapshot(n,{b['list_id']});l=snap['lists'][b['list_id']]
        if l['name']!=b['list_name'] or l['account_id']!=plan['account_id']:raise ValueError('archive_restore_native_identity')
        current={rid:protected(row)for rid,row in snap['reminders'].items()if row['list_id']==b['list_id']}
        expected=copy.deepcopy(saved['native_after'])
        for rid in recovery['tasks']:
            if current.get(rid)==protected(original['native_before'][rid]):expected[rid]=current[rid]
        if current!=expected:raise ValueError('archive_restore_native_content_changed')
        if l['group_id']==state['archive_group']['id']:
            recovery['group_intent']=True;save()
            n.call('manage_list',dict(action='update',list=b['list_id'],group=original['binding']['native_group_id'],expected_group_id=state['archive_group']['id']))
        elif not recovery['group_intent'] or l['group_id']!=original['binding']['native_group_id']:
            raise ValueError('archive_restore_group_changed')
        for rid,row in original['native_before'].items():
            if row.get('completed'):continue
            actual=n.get(rid,b['list_id']);before=saved['native_after'][rid];after=protected(row)
            if protected(actual)==after and rid in recovery['tasks']:continue
            if protected(actual)!=before:raise ValueError('archive_restore_task_changed')
            recovery['tasks'][rid]=True;save();n.update(actual,{'completed':False})
            if protected(n.get(rid,b['list_id']))!=after:raise ValueError('archive_restore_task_readback')
        # Проверка собственных before/after непосредственно перед каждой локальной записью.
        import subprocess
        for name,text in original['files'].items():
            target=root/'ai'/name;actual=target.read_text();expected=saved['files_after'][name]
            if actual==text and recovery['files'].get(name):continue
            if actual!=expected:raise ValueError('archive_restore_local_changed')
            recovery['files'][name]=True;save()
            if actual!=text:
                result=subprocess.run(['python3',str(hub/'scripts/task_records.py'),'write','--hub',str(hub),'--project-id',pid,'--kind',{v:k for k,v in m.NAMES.items()}[name],'--expected-sha256',digest(actual.encode())],input=text,text=True,capture_output=True)
                if result.returncode:raise ValueError('archive_restore_task_write')
        card=hub/original['card_path'];actual=card.read_text()
        if not(actual==original['card'] and recovery['card_intent']):
            if actual!=saved['card_after']:raise ValueError('archive_restore_card_changed')
            recovery['card_intent']=True;save()
            if card.read_text()!=actual:raise ValueError('archive_restore_card_changed')
            card.write_text(original['card'])
        registry=hub/'ai/project-registry.md';actual=registry.read_text();section=_section(actual,pid)
        desired=_section(plan['registry_before'],pid)
        if not(section==desired and recovery['registry_intent']):
            if section!=saved['registry_section_after'].rstrip():raise ValueError('archive_restore_registry_changed')
            recovery['registry_intent']=True;save()
            if registry.read_text()!=actual:raise ValueError('archive_restore_registry_changed')
            registry.write_text(set_registry_status(actual,pid,'archived','active'))
        final=snapshot(n,{b['list_id']});l=final['lists'][b['list_id']]
        if l['group_id']!=original['binding']['native_group_id'] or {rid:protected(row)for rid,row in final['reminders'].items()if row['list_id']==b['list_id']}!={rid:protected(row)for rid,row in original['native_before'].items()}:
            raise ValueError('archive_restore_readback')
        if any((root/'ai'/name).read_text()!=text for name,text in original['files'].items()):raise ValueError('archive_restore_local_readback')
        recovery['phase']='data_restored';saved['phase']='restored';save()
        c['projects'][pid]=original['binding'];c.pop('archive_pending',None);cfg()
        return dict(project=pid,status='active',gap_ids_preserved=saved['gap_ids'])

def main():
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('command',choices=['preview','apply','restore-preview','restore'])
    cli.add_argument('--hub',required=True);cli.add_argument('--project',action='append',default=[]);cli.add_argument('--plan');cli.add_argument('--sha256');cli.add_argument('--approve',action='store_true')
    args=cli.parse_args();hub=safe(args.hub)
    try:
        if args.command=='preview':result=preview(hub,args.project)
        elif args.command=='apply':result=apply(args.plan,args.sha256,args.approve)
        elif args.command=='restore-preview':result=restore_preview(hub,args.project[0])
        else:result=restore(hub,args.project[0],args.sha256,args.approve)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except Exception as e:
        print(json.dumps(dict(ok=False,error=str(e)),ensure_ascii=False));return 1
if __name__=='__main__':raise SystemExit(main())
