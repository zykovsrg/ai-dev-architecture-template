#!/usr/bin/env python3
"""Единый журналируемый исполнитель явных правок задач через «Напоминания»."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys


def sync_module():
    name = 'hub_reminders_gateway_sync'
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name('reminders_sync.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[name] = module
    return module


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def seal(value):
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')))


def durable(path, value):
    sync_module().atomic_json(path, value)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def immutable(journal):
    return {key:journal[key] for key in ('version','request','request_sha256','before','desired','binding','config_before','cancellations','intent')}


def validate_journal(path, journal):
    if (journal.get('version')!=1 or seal(journal.get('request'))!=path.stem
            or journal.get('request_sha256')!=path.stem or journal.get('plan_sha256')!=seal(immutable(journal))
            or journal.get('phase') not in {'prepared','projecting','complete'}
            or [{k:i[k] for k in ('task_id','patch','new')} for i in journal['changes']]!=journal['intent']):
        raise ValueError('gateway_journal_mismatch')


def pending_projects(hub):
    sync=sync_module(); root=sync.safe_path(Path(hub)/'ai/reminders-task-writes')
    result=set()
    if root.exists():
        for path in root.glob('*.json'):
            sync.safe_path(path)
            journal=json.loads(path.read_text()); validate_journal(path,journal)
            if journal['phase']!='complete': result.add(journal['request']['project_id'])
    return result


def rows(parser, sync, pid, texts):
    result = {}
    for kind, text in texts.items():
        parsed = parser.read_records(pid, kind, text)
        if parser.unrecognized_headings(kind, text.splitlines()):
            raise ValueError('unrecognized_heading')
        for row in parsed:
            tid = row['task_id']
            item = dict(row, kind=kind, planned_day=sync.day_in(sync.chunk(text,kind,tid)[2]))
            if tid in result:
                # Штатное продвижение сохраняет старую запись с promoted.
                if row['status']=='promoted': continue
                if result[tid]['status']!='promoted': raise ValueError('duplicate_task_id:' + tid)
            result[tid] = item
    return result


def projected(sync, pid, texts, task_id, remote, link):
    """Меняем только поля приложения в запрошенном тексте, сохраняя контекст и Due."""
    # Парсер передаётся вызывающим кодом через разобранную запись, не загружается здесь.
    row = link['_row']
    kind = row['kind']; first,last,body = sync.chunk(texts[kind],kind,task_id)
    title = remote['title']
    if not isinstance(title,str) or not title.strip() or '\n' in title or '\r' in title:
        raise ValueError('invalid_title')
    if kind=='current':
        body = re.sub(r'(^## Goal\n\s*\n?)[^\n]+',lambda m:m[1]+title,body,count=1,flags=re.M)
    else:
        body = body.replace(body.splitlines()[0],body.splitlines()[0].split(' — ',1)[0]+' — '+title,1)
    day = sync.remote_day(remote)
    if day != row['planned_day']:
        body = re.sub(r'^Запланировано:.*\n?', '', body, flags=re.M)
        if day: body = re.sub(r'(^Status: [^\n]+\n)',lambda m:m[0]+'Запланировано: '+day+'.\n',body,count=1,flags=re.M)
    repeating = bool(link.get('repeating') or remote.get('repeat'))
    completed = not repeating and bool(remote.get('completed'))
    status = row['status']
    if completed: status='done'
    elif status in {'done','completed'}: status=link.get('last_open_status') or ('active' if kind=='current' else 'ready')
    if kind=='paused' and status!='paused':
        body = re.sub(r'^Status: .+$','Status: '+status,body,count=1,flags=re.M)
        body = body.replace(body.splitlines()[0],'### '+task_id+' — '+title,1)
        existing=re.search(r'^### '+re.escape(task_id)+r' — [^\n]+\n.*?(?=^### |\Z)',texts['future'],re.M|re.S)
        if existing:
            recovered=body.rstrip()+'\n\nПрежняя запись до переноса с паузы:\n'+'\n'.join('> '+line for line in existing[0].splitlines())+'\n'
            texts['future']=texts['future'][:existing.start()]+recovered+texts['future'][existing.end():]
        else: texts['future'] += '\n'+body+'\n'
        texts[kind] = texts[kind][:first]+texts[kind][last:]
    else:
        body = re.sub(r'^Status: .+$','Status: '+status,body,count=1,flags=re.M)
        texts[kind] = texts[kind][:first]+body+texts[kind][last:]


def write_from_text(parser,hub,project_id,kind,expected_sha256,text,allow_removal=(),native=None):
    if allow_removal:
        raise ValueError('task_move_requires_batch')
    result=write_batch_from_texts(parser,hub,project_id,{kind:expected_sha256},{kind:text},native=native)
    if result.get('result')=='written':
        target=Path(result['paths'][kind]); result.update(path=str(target),sha256=digest(target.read_bytes()))
    return result


def write_batch_from_texts(parser,hub,project_id,expected_sha256,texts,native=None):
    sync=sync_module(); hub=sync.safe_path(Path(hub).resolve(strict=True))
    config=sync.load_config(hub); authority=sync.authority_module()
    if not authority.enabled(config): raise ValueError('reminders_authority_required')
    with authority.locked(hub):
        config=sync.load_config(hub); authority.validate_policy(hub,config)
        if (not texts or set(texts)!=set(expected_sha256) or not set(texts)<=set(parser.TASK_FILES)
                or any(not isinstance(t,str) for t in texts.values())
                or any(not re.fullmatch('[0-9a-f]{64}',s) for s in expected_sha256.values())):
            raise ValueError('invalid_batch_request')
        project=authority.bound_projects(hub,config).get(project_id)
        if project is None or project_id not in config['projects']: raise ValueError('unbound_project')
        paths={k:sync.safe_path(project/'ai'/name) for k,name in parser.TASK_FILES.items()}
        if any(not p.is_file() for p in paths.values()): raise ValueError('unsafe_task_path')
        request=dict(project_id=project_id,expected_sha256=expected_sha256,texts=texts)
        key=seal(request); root=sync.safe_path(hub/'ai/reminders-task-writes')
        path=sync.safe_path(root/(key+'.json'))
        actual={k:p.read_text() for k,p in paths.items()}
        config_before=copy.deepcopy(config)
        if path.exists():
            journal=json.loads(path.read_text())
            validate_journal(path,journal)
            if journal.get('request')!=request or journal.get('request_sha256')!=key:
                raise ValueError('gateway_journal_mismatch')
            original=journal['before']; desired=journal['desired']
            for k in paths:
                if not journal['cancellations'] and actual[k] not in {original[k],journal.get('projection',{}).get(k,original[k])}:
                    raise ValueError('task_file_changed')
            if journal.get('phase')=='complete' and not journal['cancellations']:
                return dict(result='written',operation=key,paths={k:str(p) for k,p in paths.items()})
        else:
            if project_id in pending_projects(hub): raise ValueError('task_write_recovery_required')
            if any(digest(actual[k])!=sha for k,sha in expected_sha256.items()): raise ValueError('task_file_changed')
            original=actual; desired={**original,**texts}
            before=rows(parser,sync,project_id,original); after=rows(parser,sync,project_id,desired)
            if set(before)-set(after): raise ValueError('task_move_requires_batch')
            binding=config['projects'][project_id]; tasks=binding.get('tasks',{})
            changes=[]; cancellations=[]
            for tid,row in after.items():
                old=before.get(tid); link=tasks.get(tid)
                if old and (old['status'] in {'dropped','promoted'} or (link and (link.get('cancellation') or link.get('external_retirement')))):
                    if row!=old: raise ValueError('terminal_task_requires_review')
                    continue
                if row['status']=='dropped' and old and old['status']!='dropped':
                    cancellations.append(tid); continue
                if not old and row['status'] in {'dropped','promoted'}: raise ValueError('invalid_new_task_status')
                # Неизменённая завершённая история не требует создания записи приложения.
                if (old and not link and old['status'] in {'done','completed'} and row == old
                        and sync.chunk(original[old['kind']],old['kind'],tid)[2]
                        == sync.chunk(desired[row['kind']],row['kind'],tid)[2]):
                    continue
                patch={}
                if old:
                    if row['title']!=old['title']: patch['title']=row['title']
                    if row['planned_day']!=old['planned_day']: patch['day']=row['planned_day']
                    completed=row['status'] in {'done','completed'}
                    if completed!=(old['status'] in {'done','completed'}): patch['completed']=completed
                    if not link or not link.get('reminder_id'): raise ValueError('unbound_existing_task')
                elif link: raise ValueError('new_task_binding_conflict')
                changes.append(dict(task_id=tid,patch=patch,new=old is None,phase='prepared'))
            if cancellations:
                if len(cancellations)!=1: raise ValueError('mixed_cancellation_requires_separate_request')
                tid=cancellations[0]; old=before[tid]
                allowed=copy.deepcopy(desired)
                a,b,body=sync.chunk(allowed[after[tid]['kind']],after[tid]['kind'],tid)
                body=re.sub(r'^Status: dropped$','Status: '+old['status'],body,count=1,flags=re.M)
                allowed[after[tid]['kind']]=allowed[after[tid]['kind']][:a]+body+allowed[after[tid]['kind']][b:]
                if allowed!=original: raise ValueError('mixed_cancellation_requires_separate_request')
            root.mkdir(exist_ok=True)
            journal=dict(version=1,request=request,request_sha256=key,before=original,desired=desired,
                         binding={k:binding.get(k) for k in ('list_id','list_name','parent_id','account_id','native_group_id')},
                         changes=changes,cancellations=cancellations,config_before=config_before,phase='prepared')
            journal['intent']=[{k:i[k] for k in ('task_id','patch','new')} for i in changes]
            journal['plan_sha256']=seal(immutable(journal))
            durable(path,journal)
        binding=config['projects'][project_id]
        if not journal['cancellations'] and config not in [journal['config_before'],journal.get('config_after')]:
            raise ValueError('gateway_config_changed')
        if journal['binding']!={k:binding.get(k) for k in journal['binding']}:
            raise ValueError('gateway_binding_changed')
        native=native or sync.Native(config)
        authority.validate_target(sync,hub,config,project_id,native)
        if journal['cancellations']:
            cancellation=sync.cancellation_module()
            if 'cancellation' not in journal:
                preview=cancellation.preview(hub,config,[(project_id,journal['cancellations'][0])],native)
                journal['cancellation']={k:preview[k] for k in ('path','sha256')}; durable(path,journal)
            receipt=journal['cancellation']
            authority.validate_target(sync,hub,config,project_id,native)
            result=cancellation.execute(hub,Path(receipt['path']),receipt['sha256'],config,native)
            if not result.get('ok'): raise ValueError('cancellation_failed')
            journal['projection']={k:p.read_text() for k,p in paths.items()}
            journal['phase']='complete'; durable(path,journal)
            return result
        before=rows(parser,sync,project_id,original); after=rows(parser,sync,project_id,desired)
        tasks=binding.setdefault('tasks',{})
        snapshots={}
        for item in journal['changes']:
            tid=item['task_id']; row=after[tid]; link=tasks.get(tid,{})
            if item['new']:
                marker='Хаб операция: '+key+':'+tid
                if item['phase']=='prepared':
                    authority.validate_target(sync,hub,config,project_id,native)
                    item['phase']='creating'; item['marker']=marker; durable(path,journal)
                    arguments=dict(title=row['title'],list=binding['list_id'],notes='Хаб: '+sync.compact_code(project_id,tid)+'\n'+marker)
                    if binding.get('parent_id'): arguments['parent_id']=binding['parent_id']
                    if row['planned_day']: arguments['due']=row['planned_day']
                    if row['status'] in {'done','completed'}: arguments['completed']=True
                    created=native.call('create_reminder',arguments)
                    item['reminder_id']=created['id']; item['phase']='written'; durable(path,journal)
                elif item['phase']=='creating':
                    found=[r for r in native.children(binding) if marker in (r.get('notes') or '').splitlines()]
                    if len(found)!=1: raise ValueError('uncertain_creation_requires_review')
                    item['reminder_id']=found[0]['id']; item['phase']='written'; durable(path,journal)
                rid=item['reminder_id']
                if link.get('reminder_id') not in {None,rid}: raise ValueError('gateway_task_binding_changed')
            else:
                rid=link.get('reminder_id')
                if not rid or (item.get('reminder_id') and item['reminder_id']!=rid): raise ValueError('gateway_task_binding_changed')
            remote=native.get(rid,binding['list_id'],binding.get('parent_id'))
            if remote.get('id')!=rid or not remote.get('version'): raise ValueError('invalid_remote_version')
            if not item['new'] and item['phase']=='prepared':
                patch=dict(item['patch'])
                if 'day' in patch: patch['due']=sync.remote_due_for_day(patch.pop('day'),remote)
                if patch:
                    authority.validate_target(sync,hub,config,project_id,native)
                item.update(phase='writing',reminder_id=rid,remote_before=remote,remote_patch=patch); durable(path,journal)
                if patch:
                    native.update(remote,patch)
                item['phase']='written'; durable(path,journal)
                remote=native.get(rid,binding['list_id'],binding.get('parent_id'))
            if item['new'] and item['phase']!='verified' and (remote['title']!=row['title']
                    or sync.remote_day(remote)!=row['planned_day'] or bool(remote.get('completed'))!=(row['status'] in {'done','completed'})):
                raise ValueError('creation_readback_failed')
            if not item['new'] and item['phase']!='verified' and any(remote.get(k)!=v for k,v in item.get('remote_patch',{}).items()):
                raise ValueError('uncertain_update_requires_review')
            item['phase']='verified'; durable(path,journal)
            snapshots[tid]=remote
        # Все изменения приложения проверены до первой записи его копии.
        projection=copy.deepcopy(desired)
        for tid,remote in snapshots.items():
            link=tasks.setdefault(tid,{}); item=next(i for i in journal['changes'] if i['task_id']==tid)
            link['reminder_id']=item['reminder_id']
            old=before.get(tid)
            if old and old['status'] not in sync.TERMINAL: link['last_open_status']=after[tid]['status'] if after[tid]['status'] not in sync.TERMINAL else old['status']
            projected(sync,project_id,projection,tid,remote,{**link,'_row':after[tid]})
            repeating=bool(link.get('repeating') or remote.get('repeat'))
            link.update(last_hub_day=sync.remote_day(remote),last_remote_day=sync.remote_day(remote),last_hub_title=remote['title'],
                        last_remote_title=remote['title'],last_completed=not repeating and bool(remote.get('completed')),repeating=repeating)
        final=rows(parser,sync,project_id,projection)
        if set(final)!=set(after): raise ValueError('projection_task_set_changed')
        previous_projection=journal.get('projection',{})
        journal['projection']=projection; journal['phase']='projecting'; durable(path,journal)
        # Запись назначения раньше источника; все удаления доказаны полным итоговым набором.
        order=sorted(paths,key=lambda k:len(parser.read_records(project_id,k,projection[k]))-len(parser.read_records(project_id,k,original[k])),reverse=True)
        for kind in order:
            current=paths[kind].read_text()
            if current==projection[kind]: continue
            if current not in {original[kind],previous_projection.get(kind,original[kind])}: raise ValueError('task_file_changed')
            removed={r['task_id'] for r in parser.read_records(project_id,kind,current)}-{r['task_id'] for r in parser.read_records(project_id,kind,projection[kind])}
            if not removed<=set(final): raise ValueError('task_id_lost')
            parser.write_task_file(hub,project_id,kind,digest(current),projection[kind],allow_removal=removed)
        # Конфигурация перечитана под общей блокировкой; чужой незаблокированный writer не затирается.
        current_config=sync.load_config(hub)
        if current_config not in [journal['config_before'],journal.get('config_after')]:
            raise ValueError('gateway_config_changed')
        journal['config_after']=config; durable(path,journal)
        sync.atomic_json(hub/'ai/reminders-sync.json',config)
        journal['phase']='complete'; durable(path,journal)
        return dict(result='written',operation=key,paths={k:str(p) for k,p in paths.items()})
