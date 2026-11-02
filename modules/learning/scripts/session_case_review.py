"""Независимый смысловой допуск случаев; исходные ответы остаются вне Хаба."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import subprocess

from session_rules import load_reply, validate_parts
from session_case_queue import enqueue

# Признак повторяемости необходим, но сам по себе не доказывает постоянное указание.
PERSISTENCE = re.compile(r'\b(?:всегда|никогда|впредь|отныне|на будущее|постоянно|запомни|кажд\w*|всяк\w*|'
                         r'всех|всем|все|по умолчанию|в дальнейшем|больше не|'
                         r'always|never|every|from now on|by default|remember)\b', re.I)


def proposals(payload, reply):
    rules = {r['id']: r for r in payload['rules']}
    sources = {p['part_id']: p['text'] for p in payload['parts']}
    out = []
    for part in reply['parts']:
        for n, case in enumerate(part['cases']):
            known = rules.get(case['rule'], {})
            target = case.get('text') if case['rule'] == 'new' else known.get('text')
            if not target or part['part_id'] not in sources:
                raise ValueError('case review: unknown target rule or source')
            out.append(dict(case_id=f"{part['part_id']}:{n}", part_id=part['part_id'],
                            case=case, target_rule=target,
                            target_kind=case.get('kind') if case['rule'] == 'new' else known.get('kind')))
    return out


def role_evidence(text, quote, wanted_role):
    """Цитата должна находиться целиком в диапазоне заданного автора."""
    if not isinstance(quote, str) or not quote.strip() or len(quote) > 2000:
        return False
    header, _, body = text.partition('\n\n')
    role = 'USER' if 'Role at part start: USER' in header else 'ASSISTANT'
    spans = re.split(r'(?m)^(USER|ASSISTANT): ', body)
    if role == wanted_role and quote in spans[0]:
        return True
    return any(spans[n] == wanted_role and quote in spans[n+1]
               for n in range(1, len(spans)-1, 2))


def user_evidence(text, quote):
    return role_evidence(text, quote, 'USER')


def review_schema(items):
    fields = dict(case_id={'type': 'string', 'enum': [p['case_id'] for p in items]},
                  verdict={'enum': ['accept', 'reject', 'uncertain']},
                  persistence={'enum': ['standing', 'observation', 'once', 'unknown']},
                  relation={'enum': ['same', 'opposite', 'new', 'unrelated', 'unknown']},
                  scope={'enum': ['global', 'project', 'unknown']},
                  evidence_kind={'enum': ['user_preference', 'repaired_agent_error', 'none']},
                  evidence_quote={'type': 'string'}, reason={'type': 'string'})
    return dict(type='object', additionalProperties=False, required=['reviews'], properties={
        'reviews': dict(type='array', minItems=len(items), maxItems=len(items), items={
            'type': 'object', 'additionalProperties': False, 'required': list(fields), 'properties': fields})})


def apply_reviews(payload, reply, review):
    items = proposals(payload, reply)
    decisions = review.get('reviews', [])
    keys = [d.get('case_id') for d in decisions]
    if len(keys) != len(items) or len(set(keys)) != len(keys) or set(keys) != {p['case_id'] for p in items}:
        raise ValueError('case review coverage mismatch')
    sources = {p['part_id']: p['text'] for p in payload['parts']}
    kept = set()
    disputes = []
    for item, decision in [(p, next(d for d in decisions if d['case_id'] == p['case_id'])) for p in items]:
        verdict = decision.get('verdict')
        if verdict not in ('accept', 'reject', 'uncertain') or not str(decision.get('reason', '')).strip():
            raise ValueError('case review: invalid verdict or reason')
        case = item['case']
        issue = 'review_' + verdict if verdict != 'accept' else None
        quote = decision.get('evidence_quote')
        repaired = (item.get('target_kind') == 'agent-habit' and case['effect'] == 'confirm'
                    and decision.get('evidence_kind') == 'repaired_agent_error'
                    and decision.get('persistence') == 'observation')
        has_evidence = (role_evidence(sources[item['part_id']], quote, 'ASSISTANT') if repaired
                        else decision.get('evidence_kind') == 'user_preference'
                        and user_evidence(sources[item['part_id']], quote))
        if issue is None and not has_evidence:
            issue = 'missing_evidence'
        if case['effect'] == 'explicit':
            if decision.get('persistence') != 'standing' or not PERSISTENCE.search(quote):
                issue = issue or 'standing'
            if decision.get('scope') != case.get('scope'):
                issue = issue or 'scope'
        elif decision.get('persistence') not in ('standing', 'observation'):
            issue = issue or 'observation'
        expected = 'new' if case['rule'] == 'new' else ('opposite' if case['effect'] == 'contradict' else 'same')
        if decision.get('relation') != expected or (case['rule'] == 'new' and case['effect'] == 'contradict'):
            issue = issue or 'relation'
        if issue is not None:
            disputes.append(dict(case_id=item['case_id'],part_id=item['part_id'],text=item['target_rule'],
                                 kind=item['target_kind'],rule=case['rule'],original_effect=case['effect'],
                                 project=case.get('project'),scope=decision.get('scope') if decision.get('scope') in ('global','project') else case.get('scope'),
                                 reason=issue))
            continue
        kept.add(item['case_id'])
    checked = copy.deepcopy(reply)
    for part in checked['parts']:
        had_cases = bool(part['cases'])
        part['cases'] = [c for n, c in enumerate(part['cases']) if f"{part['part_id']}:{n}" in kept]
        if had_cases and not part['cases']:
            part['empty_reason'] = 'Спорные кандидаты ожидают решения пользователя в отдельной очереди; исходный ответ и причины сохранены.'
    checked['disputed_cases'] = disputes
    return checked


def review_cases(hub, folder, batch, payload, raw_reply, executable):
    """Новый контекст проверяет случаи; не извлекает заново и не исправляет ответ модели."""
    items = proposals(payload, raw_reply)
    if not items:
        return folder / 'reply.json'
    installed = hub / 'ai/skills/hub-session-scan/resources/case-review.md'
    local = Path(__file__).resolve().parents[1] / 'skills/hub-session-scan/resources/case-review.md'
    instruction = (installed if installed.is_file() else local).read_text(encoding='utf-8')
    used = {p['part_id'] for p in items}
    data = dict(candidates=items, parts=[p for p in payload['parts'] if p['part_id'] in used])
    prompt = '[hub-session-scan]\n'+instruction+'\n<untrusted_session_data>\n'+json.dumps(data, ensure_ascii=False)+'\n</untrusted_session_data>'
    schema = folder/'case-review-schema.json'
    schema.write_text(json.dumps(review_schema(items), ensure_ascii=False), encoding='utf-8')
    (folder/'case-review-input.txt').write_text(prompt, encoding='utf-8')
    output = folder/'case-review.json'
    command = [str(executable), 'exec', '-m', 'gpt-6-luna', '-c', 'model_reasoning_effort=low',
               '-s', 'read-only', '--skip-git-repo-check', '--ephemeral', '-C', str(folder),
               '--output-schema', str(schema), '-o', str(output), '-']
    with (folder/'case-review.log').open('w', encoding='utf-8') as log:
        result = subprocess.run(command, input=prompt, text=True, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise ValueError(f'case review failed ({result.returncode}); preserved output: {folder}')
    try:
        decisions = json.loads(output.read_text(encoding='utf-8'))
        checked = apply_reviews(payload, raw_reply, decisions)
        validate_parts(batch, checked)
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        raise ValueError(f'invalid case review; preserved output: {folder}; {error}') from error
    target = folder/'verified-reply.json'
    target.write_text(json.dumps(checked, ensure_ascii=False), encoding='utf-8')
    enqueue(hub, batch, checked['disputed_cases'])
    return target
