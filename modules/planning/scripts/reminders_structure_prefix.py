"""Временный контекст чтения квитанций после доказанного префикса переносов списков.

Вызывающий код предварительно проверяет свидетельство журнала и локальные файлы.
Никакие права, задачи, базовые значения или квитанции здесь не меняются.
"""
import copy


def verification_config(config,initial,steps,snapshot):
    seen=set();lists=copy.deepcopy(initial['lists']);matches=[]
    for step in steps:
        if (set(step)!={'kind','id','group','projects'} or step['kind']!='list' or step['id'] in seen or
                step['id'] not in lists or step['group']==lists[step['id']]['group_id']):
            raise ValueError('structure_prefix_list_only')
        seen.add(step['id'])
    for index in range(len(steps)+1):
        if lists==snapshot['lists'] and initial['groups']==snapshot['groups']:matches.append(index)
        if index<len(steps):lists[steps[index]['id']]['group_id']=steps[index]['group']
    if len(matches)!=1:raise ValueError('structure_prefix_unproven')
    projected=copy.deepcopy(config)
    for pid,binding in projected['projects'].items():
        lid=binding['list_id']
        if snapshot['lists'][lid]['group_id']==initial['lists'][lid]['group_id']:continue
        if (binding.get('archive') or any('cancellation' in link or 'external_retirement' in link for link in binding.get('tasks',{}).values()) or
                any('absence_receipt' in entry or 'confirmation_receipt' in entry for entry in binding.get('history',{}).values())):
            raise ValueError('structure_prefix_receipt_project_move')
        binding['native_group_id']=snapshot['lists'][lid]['group_id']
    return projected,matches[0]



def _safe(path):
    from pathlib import Path
    path=Path(path)
    if not path.is_absolute() or '..' in path.parts or path!=path.resolve() or any(p.is_symlink() for p in [path,*path.parents]):
        raise ValueError('structure_read_context_changed')
    return path


def _text(path):
    return _safe(path).read_bytes().decode('utf-8')


def _attestation(source):
    import hashlib,json
    value={key:source[key] for key in ('config','originals','snapshot')}
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def _encoded(value):
    import json
    return json.dumps(value,ensure_ascii=False,indent=2)+'\n'


def _metadata(value,template):
    result={}
    for key,fields in (('lists',('id','name','group_id','account_id')),('groups',('id','name','account_id'))):
        rows=value[key]
        if isinstance(rows,list):
            rows={row['id']:row for row in rows}
            if len(rows)!=len(value[key]):raise ValueError('structure_read_context_changed')
        if not isinstance(rows,dict) or set(rows)!=set(template[key]):raise ValueError('structure_read_context_changed')
        result[key]={rid:{field:row.get(field) for field in fields if field in template[key][rid]} for rid,row in rows.items()}
    return result


class _ReadContext:
    __slots__=('_raw','_seal')
    def __init__(self,payload):
        import hashlib,json
        raw=json.dumps(payload,ensure_ascii=False).encode()
        object.__setattr__(self,'_raw',raw);object.__setattr__(self,'_seal',hashlib.sha256(raw).hexdigest())
    def __setattr__(self,name,value):raise AttributeError('structure_read_context_immutable')


def _source_valid(payload):
    import json
    source=payload['source'];current=json.loads(payload['config_raw']);digest=_attestation(source)
    pinned=copy.deepcopy(source['config']);pinned['structure']['outgoing_intent_sha256']=digest
    if (source.get('version')!=2 or source.get('status')!='pending' or current['structure'].get('outgoing_intent_sha256')!=digest or
            payload['config_raw'] not in ( _encoded(pinned),source['files'].get('ai/reminders-sync.json'))):
        raise ValueError('structure_read_context_unattested')
    if set(payload['guards'])!=set(source['originals']):raise ValueError('structure_read_context_changed')


def _captured_unchanged(payload):
    from pathlib import Path
    hub=_safe(payload['hub'])
    try:
        if _text(hub/'ai/reminders-sync.json')!=payload['config_raw'] or _text(hub/payload['journal'])!=payload['journal_raw']:
            raise ValueError('structure_read_context_changed')
        for name,raw in payload['guards'].items():
            rel=Path(name)
            if rel.is_absolute() or '..' in rel.parts or _text(hub/rel)!=raw:raise ValueError('structure_read_context_changed')
    except OSError as exc:raise ValueError('structure_read_context_changed') from exc


def create_read_context(hub,source,snapshot):
    """Только после проверки вызывающим кодом свидетельства, файлов и допустимой пары."""
    import json
    from pathlib import Path
    hub=_safe(hub);raw=_text(hub/'ai/reminders-sync.json');config=json.loads(raw)
    journal=Path(source['config']['structure']['journal_file'])
    if journal.is_absolute() or journal.parent!=Path('ai'):raise ValueError('structure_read_context_changed')
    journal_raw=_text(hub/journal)
    if _attestation(source)!=config['structure'].get('outgoing_intent_sha256'):raise ValueError('structure_read_context_unattested')
    shape=_metadata(snapshot,source['snapshot'])
    _,prefix=verification_config(source['config'],source['snapshot'],source['steps'],shape)
    if prefix:
        for binding in source['config']['projects'].values():
            refusals=set(binding.get('retired_parent_cleanup',{}).get('restore_refusal_ids',[]))
            for entry in binding.get('history',{}).values():
                link=binding.get('tasks',{}).get(entry.get('task_id'),{})
                if 'absence_receipt' in entry and 'cancellation' in link and entry.get('original_id')==link.get('reminder_id') and link.get('reminder_id') in refusals:
                    raise ValueError('structure_read_context_composition_unsupported')
    guards={}
    for name,before in source['originals'].items():
        rel=Path(name)
        if rel.is_absolute() or '..' in rel.parts:raise ValueError('structure_read_context_changed')
        current=_text(hub/rel)
        allowed=(before,source['files'].get(name,before),raw if name=='ai/reminders-sync.json' else before)
        if current not in allowed:raise ValueError('structure_read_context_changed')
        guards[name]=current
    payload=dict(hub=str(hub),source=copy.deepcopy(source),config_raw=raw,journal=str(journal),journal_raw=journal_raw,guards=guards,metadata=shape,prefix=prefix)
    _source_valid(payload);_captured_unchanged(payload)
    return _ReadContext(payload)


def validate_read_context(context,hub,config_raw,metadata):
    """Проверяет настоящую metadata и все сохранённые байты; возвращает только группы."""
    import hashlib,json
    if type(context) is not _ReadContext or hashlib.sha256(context._raw).hexdigest()!=context._seal:
        raise ValueError('structure_read_context_changed')
    payload=json.loads(context._raw)
    if payload['hub']!=str(_safe(hub)) or payload['config_raw']!=config_raw:raise ValueError('structure_read_context_changed')
    _source_valid(payload);_captured_unchanged(payload)
    source=payload['source'];shape=_metadata(metadata,source['snapshot'])
    projected,prefix=verification_config(source['config'],source['snapshot'],source['steps'],shape)
    if shape!=payload['metadata'] or prefix!=payload['prefix']:raise ValueError('structure_read_context_changed')
    return {pid:binding['native_group_id'] for pid,binding in projected['projects'].items()
            if shape['lists'][binding['list_id']]['group_id']!=source['snapshot']['lists'][binding['list_id']]['group_id']}
