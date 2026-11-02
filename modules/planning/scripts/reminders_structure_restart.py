#!/usr/bin/env python3
"""Новый проверенный снимок прерванного переноса списков; приложение только читается.

preview сохраняет неизменяемый план. apply PLAN --sha256 SHA записывает сначала
журнал, затем закрепление намерения. После сбоя повторяют тот же apply. Обычная
сверка самостоятельно проверяет новый журнал и продолжает оставшиеся переносы.
Поля и базовые значения задач эта команда не записывает.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import uuid


def _module(name):
    spec=importlib.util.spec_from_file_location('structure_restart_'+name,Path(__file__).with_name(name+'.py'))
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

sync=_module('reminders_sync')
m=_module('reminders_structure')
b=_module('reminders_bidirectional')
prefix_context=m.structure_prefix_module()
LIMIT=33_554_432
JOURNAL_KEYS={'version','status','config','originals','snapshot','steps','files','guards'}
PLAN_KEYS={'version','kind','operation','hub','before_config','before_journal','after_config','after_journal','snapshot','prefix'}


def _path(path):
    path=m.safe_path(Path(path))
    if path!=path.resolve():raise ValueError('unsafe_structure_restart_path')
    return path


def _text(path):
    path=_path(path)
    if path.stat().st_size>LIMIT:raise ValueError('structure_restart_file_too_large')
    raw=path.read_bytes()
    if len(raw)>LIMIT:raise ValueError('structure_restart_file_too_large')
    return raw.decode('utf-8')


class ReadOnly:
    def __init__(self,native):self.native=native
    def call(self,tool,args):
        if tool not in {'list_lists','find_reminders','get_reminder','hub_cancel_status','hub_cancel_capabilities'}:
            raise ValueError('structure_restart_read_only')
        return self.native.call(tool,args)
    def cancellation_status(self,args):
        if hasattr(self.native,'cancellation_status'):return self.native.cancellation_status(args)
        return self.call('hub_cancel_status',args)


def _source(hub,raw):
    j=json.loads(raw)
    if not isinstance(j,dict) or set(j)!=JOURNAL_KEYS or j['version']!=2 or j['status']!='pending':
        raise ValueError('structure_restart_pending_v2_required')
    config=j['config']; structure=config['structure']; rel=Path(structure['journal_file'])
    if rel.is_absolute() or rel.parent!=Path('ai') or rel.name in {'reminders-sync.json','archiprojects.md','project-registry.md'}:
        raise ValueError('unsafe_structure_restart_journal')
    journal=_path(hub/rel)
    if not structure.get('enabled') or not structure.get('bidirectional'):raise ValueError('structure_restart_bidirectional_required')
    if m.migration_pending(hub,config):raise ValueError('migration_recovery_required')
    required={hub/'ai/reminders-sync.json',hub/'ai/archiprojects.md',hub/'ai/project-registry.md',_path(m.standard_allowlist(config)),_path(structure['groups_allowlist_file'])}
    if structure.get('group_ids_allowlist_file'):required.add(_path(structure['group_ids_allowlist_file']))
    originals={}
    for name,text in j['originals'].items():
        rel=Path(name)
        if rel.is_absolute() or '..' in rel.parts:raise ValueError('unsafe_structure_restart_original')
        path=_path(hub/rel)
        if not isinstance(text,str):raise ValueError('invalid_structure_restart_original')
        originals[path]=text
    if not required<=set(originals):raise ValueError('structure_restart_missing_guards')
    allowed=set(required)
    registry=originals[hub/'ai/project-registry.md']
    allowed.update(m.registry_cards(hub,registry).values())
    for name in re.findall(r'^Card: (.+)$',registry,re.M):
        card=_path(hub/name)
        if card.parent!=hub/'ai/project-cards':raise ValueError('unsafe_structure_restart_original')
        allowed.add(card)
    if not set(originals)<=allowed or not set(j['files'])<=set(j['originals']):raise ValueError('unsafe_structure_restart_original')
    if json.loads(originals[hub/'ai/reminders-sync.json'])!=config:raise ValueError('structure_restart_source_config_changed')
    if j['guards']!={name:text for name,text in j['originals'].items() if name not in j['files']}:
        raise ValueError('structure_restart_missing_guards')
    digest=b.attestation(config,j['originals'],j['snapshot'])
    pinned=copy.deepcopy(config);pinned['structure']['outgoing_intent_sha256']=digest
    if pinned['structure'].get('outgoing_completed_sha256')==digest:raise ValueError('structure_restart_already_complete')
    seen=set()
    if not j['steps']:raise ValueError('structure_restart_list_only')
    for step in j['steps']:
        if (set(step)!={'kind','id','group','projects'} or step['kind']!='list' or step['id'] in seen or
                step['id'] not in j['snapshot']['lists'] or step['group']==j['snapshot']['lists'][step['id']]['group_id']):
            raise ValueError('structure_restart_list_only')
        seen.add(step['id'])
    return j,journal,originals,m.encoded(pinned)


def _guards(hub,j):
    for name,text in j['originals'].items():
        if name!='ai/reminders-sync.json' and _text(hub/name)!=text:raise ValueError('structure_restart_guard_changed')


def _fresh(config,native):
    m.fresh_reads()
    allow=json.loads(_text(m.standard_allowlist(config)))
    names=set(allow.get('names',[]) if isinstance(allow,dict) else allow)
    snap=m.snapshot(native,config['structure']['list_roles'],names,detailed=True,include_groups=True)
    m.retired_parent_ids(config,snap)
    return snap


def _seed(j,snapshot):
    initial=j['snapshot'];state=initial;matches=[]
    for index in range(len(j['steps'])+1):
        if state['lists']==snapshot['lists'] and state['groups']==snapshot['groups']:matches.append(index)
        if index<len(j['steps']):state=b.projected(state,j['steps'][index])
    if len(matches)!=1:raise ValueError('structure_restart_unknown_prefix')
    for rid in set(initial['reminders'])&set(snapshot['reminders']):
        old=initial['reminders'][rid];new=snapshot['reminders'][rid]
        if (old.get('list_id'),old.get('parent_id'))!=(new.get('list_id'),new.get('parent_id')):
            raise ValueError('structure_restart_task_moved')
    seed=copy.deepcopy(snapshot);seed['lists']=copy.deepcopy(initial['lists']);seed['groups']=copy.deepcopy(initial['groups'])
    return matches[0],seed


def _derive(hub,j,originals,snapshot,native):
    prefix,seed=_seed(j,snapshot);config=j['config']
    proof_config,prefix=prefix_context.verification_config(config,j['snapshot'],j['steps'],snapshot)
    read_context=None
    if prefix:
        context_source=j
        current=json.loads(_text(hub/'ai/reminders-sync.json'))
        if b.attestation(j['config'],j['originals'],j['snapshot'])!=current['structure'].get('outgoing_intent_sha256'):
            # apply уже проверил точную after/after пару того же неизменяемого плана.
            context_source=json.loads(_text(hub/j['config']['structure']['journal_file']))
        read_context=prefix_context.create_read_context(hub,context_source,snapshot)
    verified={pid:m.verified_cancelled_ids(hub,pid,binding,proof_config,native,**(dict(read_context=read_context) if read_context is not None else {})) for pid,binding in proof_config['projects'].items() if not binding.get('archive')}
    result,steps,after=b.plan(m,hub,config,seed,copy.deepcopy(originals),verified)
    if not result['ok']:raise ValueError('structure_restart_plan_blocked: '+m.encoded(result['items']))
    digest=b.attestation(config,j['originals'],seed)
    result['config']['structure']['outgoing_intent_sha256']=digest
    after[hub/'ai/reminders-sync.json']=m.encoded(result['config'])
    files={str(path.relative_to(hub)):text for path,text in after.items()}
    guards={name:text for name,text in j['originals'].items() if name not in files}
    if steps!=j['steps'] or set(files)!=set(j['files']) or guards!=j['guards']:raise ValueError('structure_restart_intent_changed')
    for name,text in files.items():
        if name=='ai/reminders-sync.json':
            view=json.loads(text);expected=json.loads(j['files'][name])
            view['structure']['outgoing_intent_sha256']=expected['structure']['outgoing_intent_sha256']
            if m.encoded(view)!=j['files'][name]:raise ValueError('structure_restart_intent_changed')
        elif text!=j['files'][name]:raise ValueError('structure_restart_intent_changed')
    new=dict(version=2,status='pending',config=copy.deepcopy(config),originals=copy.deepcopy(j['originals']),snapshot=seed,steps=steps,files=files,guards=guards)
    pinned=copy.deepcopy(config);pinned['structure']['outgoing_intent_sha256']=digest
    return prefix,m.encoded(new),m.encoded(pinned)


def _pair(hub,journal,before_config,before_journal,after_config,after_journal):
    config=_text(hub/'ai/reminders-sync.json');saved=_text(journal)
    if (saved,config) not in {(before_journal,before_config),(after_journal,before_config),(after_journal,after_config)}:
        raise ValueError('structure_restart_pair_changed')
    return saved,config


def _publish(hub,plan):
    root=_path(hub/'ai/reminders-structure-restarts');root.mkdir(exist_ok=True)
    directory=root/plan['operation'];directory.mkdir()
    path=directory/'plan.json';raw=m.encoded(plan).encode()
    if len(raw)>LIMIT:raise ValueError('structure_restart_file_too_large')
    with path.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    for saved_directory in (directory,root,root.parent):
        fd=os.open(saved_directory,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    return dict(ok=True,plan=str(path),sha256=hashlib.sha256(raw).hexdigest(),prefix=plan['prefix'])


def preview(hub,native=None):
    hub=_path(Path(hub).absolute())
    with sync.authority_module().locked(hub):
        config=sync.load_config(hub);journal=_path(hub/config['structure']['journal_file']);raw=_text(journal)
        j,journal,originals,before_config=_source(hub,raw)
        if _text(hub/'ai/reminders-sync.json')!=before_config:raise ValueError('structure_restart_pair_changed')
        _guards(hub,j)
        native=ReadOnly(native or m.StructureNative(config))
        snapshot=_fresh(j['config'],native)
        prefix,after_journal,after_config=_derive(hub,j,originals,snapshot,native)
        if _fresh(j['config'],native)!=snapshot:raise ValueError('structure_restart_snapshot_changed')
        _guards(hub,j)
        if _text(journal)!=raw or _text(hub/'ai/reminders-sync.json')!=before_config:raise ValueError('structure_restart_pair_changed')
        plan=dict(version=1,kind='list_prefix_restart',operation=str(uuid.uuid4()),hub=str(hub),before_config=before_config,before_journal=raw,after_config=after_config,after_journal=after_journal,snapshot=snapshot,prefix=prefix)
        return _publish(hub,plan)


def _read_plan(path,digest):
    path=_path(Path(path).absolute());raw=_text(path).encode()
    if not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest) or hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('structure_restart_checksum_changed')
    plan=json.loads(raw)
    if not isinstance(plan,dict) or set(plan)!=PLAN_KEYS or plan['version']!=1 or plan['kind']!='list_prefix_restart':raise ValueError('structure_restart_plan_changed')
    hub=_path(plan['hub'])
    if str(uuid.UUID(plan['operation']))!=plan['operation'] or path!=hub/'ai/reminders-structure-restarts'/plan['operation']/'plan.json':raise ValueError('unsafe_structure_restart_plan')
    return plan,hub


def apply(path,sha256,native=None):
    plan,hub=_read_plan(path,sha256)
    with sync.authority_module().locked(hub):
        j,journal,originals,before_config=_source(hub,plan['before_journal'])
        if before_config!=plan['before_config']:raise ValueError('structure_restart_plan_changed')
        _pair(hub,journal,plan['before_config'],plan['before_journal'],plan['after_config'],plan['after_journal'])
        _guards(hub,j)
        native=ReadOnly(native or m.StructureNative(j['config']))
        if _fresh(j['config'],native)!=plan['snapshot']:raise ValueError('structure_restart_snapshot_changed')
        derived=_derive(hub,j,originals,plan['snapshot'],native)
        if derived!=(plan['prefix'],plan['after_journal'],plan['after_config']):raise ValueError('structure_restart_plan_changed')
        # Расчёт может читать много свидетельств. Снимок и файлы проверяем ПОСЛЕ него.
        if _fresh(j['config'],native)!=plan['snapshot']:raise ValueError('structure_restart_snapshot_changed')
        _guards(hub,j)
        saved,config=_pair(hub,journal,plan['before_config'],plan['before_journal'],plan['after_config'],plan['after_journal'])
        if saved!=plan['after_journal']:m.atomic_write(journal,plan['after_journal'])
        _guards(hub,j)
        saved,config=_pair(hub,journal,plan['before_config'],plan['before_journal'],plan['after_config'],plan['after_journal'])
        if config!=plan['after_config']:m.atomic_write(hub/'ai/reminders-sync.json',plan['after_config'])
        _guards(hub,j)
        if (_text(journal),_text(hub/'ai/reminders-sync.json'))!=(plan['after_journal'],plan['after_config']):raise ValueError('structure_restart_local_readback_failed')
        return dict(ok=True,applied=True,prefix=plan['prefix'],remaining=len(j['steps'])-plan['prefix'],native_writes=0)


def main():
    cli=argparse.ArgumentParser(description=__doc__);sub=cli.add_subparsers(dest='command',required=True)
    p=sub.add_parser('preview');p.add_argument('--hub',required=True)
    p=sub.add_parser('apply');p.add_argument('plan');p.add_argument('--sha256',required=True)
    args=cli.parse_args()
    try:
        result=preview(args.hub) if args.command=='preview' else apply(args.plan,args.sha256)
        print(m.encoded(result),end='');return 0
    except Exception as exc:print(m.encoded(dict(ok=False,error=str(exc))),end='');return 1

if __name__=='__main__':raise SystemExit(main())
