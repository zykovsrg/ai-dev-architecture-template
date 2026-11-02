"""Устойчивая очередь спорных правил и точные решения пользователя."""
from __future__ import annotations
import argparse
import copy
from datetime import date, datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import re
from contextlib import contextmanager

import session_rules as rules
from session_collect import registry, save_json

QUEUE='ai/learning/case-review-queue.json'
REASONS={'review_reject','review_uncertain','missing_evidence','standing','scope','relation','observation'}


def _safe(hub,relative):
    path=hub/relative
    for p in [path,*path.parents]:
        if p.is_symlink():raise ValueError('unsafe queue/catalog path')
        if p==hub:break
    return path


def _load(hub):
    p=_safe(hub,QUEUE)
    data=json.loads(p.read_text()) if p.exists() else {'format':1,'items':[]}
    if data.get('format')!=1 or not isinstance(data.get('items'),list):raise ValueError('invalid queue')
    ids=[i['id'] for i in data['items']]
    if len(ids)!=len(set(ids)):raise ValueError('duplicate queue id')
    return data


@contextmanager
def _lock(hub):
    path=_safe(hub,QUEUE+'.lock');path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a') as f:
        fcntl.flock(f,fcntl.LOCK_EX)
        yield


def _text(value):
    if not isinstance(value,str) or not value.strip() or len(value)>200 or '\n' in value or rules.looks_personal(value):
        raise ValueError('unsafe proposed rule text')
    return value


def enqueue(hub,batch,disputes):
    hub=Path(hub).resolve()
    if not disputes:return {'added':0}
    entries={e['part_id']:e for e in batch['sessions']}
    active={pid for pid,e in registry(hub).items() if e.get('status')=='active'}
    prepared=[]
    for d in disputes:
        e=entries.get(d['part_id'])
        if not e or not re.fullmatch(re.escape(e['part_id'])+r':\d+',d['case_id']):raise ValueError('queue source mismatch')
        text=_text(d['text'])
        if d.get('kind') not in rules.KINDS or d.get('reason') not in REASONS:raise ValueError('invalid disputed rule')
        project=d.get('project') if d.get('project') in active else e['project']
        if project!='hub' and project not in active:raise ValueError('inactive disputed project')
        scope=d.get('scope') or ('global' if project=='hub' else 'project')
        if scope not in ('global','project'):raise ValueError('invalid disputed scope')
        source={k:e[k] for k in ('tool','id','source_sha256')}
        identity=dict(source=source,text=text,scope=scope,project=project)
        qid='Q-'+hashlib.sha256(json.dumps(identity,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]
        prepared.append(dict(id=qid,status='pending',text=text,kind=d['kind'],scope=scope,project=project,
                             target_rule=d['rule'],original_effect=d['original_effect'],reason=d['reason'],
                             source=source,part_id=d['part_id'],case_id=d['case_id'],
                             history=[{'event':'pending','at':datetime.now(timezone.utc).isoformat()}]))
    with _lock(hub):
        data=_load(hub);known={i['id'] for i in data['items']};added=0
        for item in prepared:
            if item['id'] not in known:data['items'].append(item);known.add(item['id']);added+=1
        if added:save_json(_safe(hub,QUEUE),data)
    return {'added':added}


def pending(hub):
    data=_load(Path(hub).resolve());items=[i for i in data['items'] if i['status']=='pending']
    item=copy.deepcopy(items[0]) if items else None
    question=None
    if item:
        area='Общее правило' if item['scope']=='global' else 'Правило проекта '+item['project']
        question=area+': «'+item['text']+'». Сохранить это как постоянное правило?'
        if item['scope']=='project' and item['project']=='hub':
            question='Предложение: «'+item['text']+'». Сохранить как общее правило или для конкретного проекта?'
    return {'pending_count':len(items),'item':item,'question':question}


def resolve(hub,qid,decision,approved_text=None,scope=None,project=None):
    hub=Path(hub).resolve()
    if decision not in ('accept','reject'):raise ValueError('invalid user decision')
    with _lock(hub):
        data=_load(hub);matches=[i for i in data['items'] if i['id']==qid]
        if len(matches)!=1:raise ValueError('unknown queue id')
        item=matches[0]
        if item['status']!='pending':
            if item['status']!=('accepted' if decision=='accept' else 'rejected'):raise ValueError('decision already recorded')
            return {'id':qid,'status':item['status'],'already_resolved':True}
        now=datetime.now(timezone.utc).isoformat();today=date.today()
        if decision=='accept':
            text=_text(approved_text if approved_text is not None else item['text'])
            chosen_scope=scope or item['scope'];project=project or item['project']
            if chosen_scope not in ('global','project'):raise ValueError('invalid approved scope')
            if chosen_scope=='project' and (project=='hub' or registry(hub).get(project,{}).get('status')!='active'):
                raise ValueError('a concrete active project is required')
            path=_safe(hub,rules.CATALOG);before=path.read_bytes() if path.exists() else None
            catalog=rules.load_catalog(hub)
            existing=next((r for r in catalog['rules'] if any(c.get('decision_id')==qid for c in r['cases'])),None)
            if existing:
                confirmed=next(c for c in existing['cases'] if c.get('decision_id')==qid)
                if existing['text']!=text or confirmed.get('approved_scope')!=chosen_scope or confirmed.get('approved_project')!=project:raise ValueError('retry differs from recorded confirmation')
                rule=existing
            else:
                target=next((r for r in catalog['rules'] if r['id']==item['target_rule']),None)
                if target and target['text']!=item['text']:raise ValueError('target rule changed; preview decision again')
                def compatible(r):
                    if chosen_scope=='global':return True
                    positive={c['project'] for c in r['cases'] if c['effect']!='contradict'}
                    return r.get('explicit_scope')!='global' and positive <= {project}
                rule=next((r for r in catalog['rules'] if r['status']=='active' and r['text']==text and compatible(r)),None)
                if rule is None and rules.duplicates_standing(text,rules.standing_instructions(hub)):
                    item['already_standing']=True
                else:
                    if rule is None:
                        rule=dict(id=f"R-{catalog['next_id']}",text=text,kind=item['kind'],status='active',
                                  explicit_scope=None,merged_into=None,created=today.isoformat(),cases=[],history=[])
                        catalog['next_id']+=1;catalog['rules'].append(rule)
                    rule['explicit_scope']=chosen_scope if rule.get('explicit_scope')!='global' else 'global'
                    rule['cases'].append(dict(effect='explicit',project=project if chosen_scope=='project' else 'hub',
                                              tool='user',session='decision:'+qid,date=today.isoformat(),decision_id=qid,approved_scope=chosen_scope,approved_project=project,
                                              note='Пользователь подтвердил показанный текст как постоянное правило.'))
                    rule['history'].append(dict(date=today.isoformat(),event='user_confirmed',detail=qid))
                    if (path.read_bytes() if path.exists() else None)!=before:raise ValueError('catalog changed during confirmation')
                    save_json(path,catalog)
            if rule is not None:
                rules.write_render(hub,catalog,today)
                item['saved_rule']=rule['id']
            item['approved_text']=text;item['approved_scope']=chosen_scope;item['approved_project']=project
        item['status']='accepted' if decision=='accept' else 'rejected'
        item['history'].append({'event':item['status'],'at':now,'source':'Прямой ответ пользователя об этом предложении.'})
        save_json(_safe(hub,QUEUE),data)
        return {'id':qid,'status':item['status'],'rule':item.get('saved_rule'),'already_standing':item.get('already_standing',False)}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--hub',type=Path,required=True)
    sub=parser.add_subparsers(dest='command',required=True);sub.add_parser('pending')
    decide=sub.add_parser('resolve');decide.add_argument('--id',required=True)
    decide.add_argument('--decision',choices=['accept','reject'],required=True)
    decide.add_argument('--text');decide.add_argument('--scope',choices=['global','project']);decide.add_argument('--project')
    args=parser.parse_args()
    try:
        result=pending(args.hub) if args.command=='pending' else resolve(args.hub,args.id,args.decision,args.text,args.scope,args.project)
    except (ValueError,OSError) as error:raise SystemExit('ERROR: '+str(error))
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
