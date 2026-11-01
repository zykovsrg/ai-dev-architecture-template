#!/usr/bin/env python3
"""Напоминания для ревью дня; чтение по умолчанию, граница — только finish."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import sys
import tempfile
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Europe/Kirov')
STATE = 'ai/evening-review-state.json'


def stamp(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError('Время должно содержать часовой пояс')
    return result.astimezone(TZ)


def safe(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Символическая ссылка в пути ревью')
    return path


def read_state(hub):
    path = safe(Path(hub) / STATE)
    if not path.exists():
        return None
    state = json.loads(path.read_text(encoding='utf-8'))
    if state.get('version') != 1:
        raise ValueError('Неизвестная версия состояния ревью')
    return stamp(state['last_reviewed_through']).isoformat()


def collect(native, allowed_names, required_ids=(), missing_ids=None):
    """Полные снимки только разрешённых списков, без фильтра срока выполнения."""
    listing = native.call('list_lists', {})
    lists = listing['lists']
    if (not isinstance(lists, list) or len({r['id'] for r in lists}) != len(lists)
            or listing.get('more') or listing.get('has_more')):
        raise ValueError('Некорректный список контейнеров')
    visible = {r['id'] for r in lists if r['name'] in allowed_names}
    absent = set(required_ids) - visible
    if absent:
        if missing_ids is None:
            raise ValueError('Недоступен связанный список напоминаний')
        missing_ids.extend(sorted(absent))
    rows = []
    for container in lists:
        if container['name'] not in allowed_names:
            continue
        result = native.call('find_reminders', dict(list=container['id'], include_completed=True,
                                                    detail=True, limit=500))
        batch = result.get('reminders')
        if (result.get('detail') is not True or not isinstance(batch, list)
                or type(result.get('count')) is not int or result['count'] != len(batch)
                or result.get('more') or result.get('has_more') or len(batch) >= 500):
            raise ValueError('Неполный снимок напоминаний: ' + container['id'])
        if any(r.get('list_id') != container['id'] or r.get('list') != container['name'] for r in batch):
            raise ValueError('Посторонний список в снимке напоминаний')
        rows.extend(batch)
    return rows


def prepare(rows, day, now, previous):
    """Разделить фактически завершённые и открытые задачи «сегодня»."""
    day = date.fromisoformat(day)
    upper = stamp(now)
    if upper.date() != day:
        raise ValueError('«Сегодня» требует текущую дату снимка в Europe/Kirov')
    lower = stamp(previous) if previous else datetime.combine(day, time.min, TZ)
    if lower > upper:
        raise ValueError('Граница прошлого ревью находится в будущем')
    tomorrow = datetime.combine(day + timedelta(days=1), time.min, TZ)
    done, today, warnings, seen = [], [], [], set()
    for raw in rows:
        if not all(isinstance(raw.get(k), str) and raw[k] for k in ('id', 'list_id', 'title')):
            raise ValueError('Некорректное напоминание')
        key = (raw['list_id'], raw['id'])
        if key in seen:
            raise ValueError('Повтор идентификатора напоминания')
        seen.add(key)
        completed = raw.get('completed', False)
        if type(completed) is not bool:
            raise ValueError('Неизвестный статус выполнения')
        # Не сохраняем заметки и другие поля, не нужные для разговора.
        row = {k: raw[k] for k in ('id', 'list_id', 'list', 'title', 'due', 'completed_at', 'repeat') if k in raw}
        row['completed'] = completed
        if completed:
            if not raw.get('completed_at'):
                warnings.append('Нет времени выполнения: ' + raw['id'])
                continue
            completed_at = stamp(raw['completed_at'])
            if lower < completed_at <= upper:
                done.append(row)
        elif raw.get('due'):
            due = raw['due']
            if len(due) == 10:
                due_at = datetime.combine(date.fromisoformat(due), time.min, TZ)
            else:
                due_at = datetime.fromisoformat(due)
                # Due.format нативной программы возвращает местное время без зоны.
                due_at = due_at.replace(tzinfo=TZ) if due_at.tzinfo is None else due_at.astimezone(TZ)
            if due_at < tomorrow:
                today.append(row)
    done.sort(key=lambda r: (stamp(r['completed_at']), r['id']))
    today.sort(key=lambda r: (r['due'], r['id']))
    return dict(since=lower.isoformat(), through=upper.isoformat(), previous=previous,
                first_review=previous is None, completed=done, today=today,
                complete=not warnings, warnings=warnings)


def merge(calendar, reminders, config, tasks, consumed=()):
    """Связь только по сохранённому UUID; названия не доказывают тождество."""
    links = {}
    histories = {}
    canonical = {(r['project_id'], r['task_id']): r for r in tasks}
    for pid, binding in config.get('projects', {}).items():
        for tid, link in binding.get('tasks', {}).items():
            if (pid, tid) not in canonical or not link.get('reminder_id'):
                continue
            identity = (binding['list_id'], link['reminder_id'])
            links.setdefault(identity, []).append((pid, tid))
        for rid, history in binding.get('history', {}).items():
            tid = history.get('task_id')
            if (pid, tid) not in canonical:
                continue
            live = binding.get('tasks', {}).get(tid, {})
            if history.get('project_id') != pid or history.get('original_id') != live.get('reminder_id'):
                raise ValueError('Некорректная связь истории повторений')
            histories.setdefault((binding['list_id'], rid), []).append((pid, tid))
    items = {}
    for raw in calendar['queue']:
        key = raw['review_key']
        items.setdefault(key, dict(raw, sources=['calendar']))
    for source, rows in [('completed', reminders['completed']), ('today', reminders['today'])]:
        for row in rows:
            matches = links.get((row['list_id'], row['id']), [])
            if source == 'completed':
                matches = matches + histories.get((row['list_id'], row['id']), [])
            pid, tid = matches[0] if len(matches) == 1 else (None, None)
            identity = [pid, tid] if pid else ['reminder', row['list_id'], row['id']]
            key = json.dumps(identity, ensure_ascii=False)
            item = items.setdefault(key, dict(review_key=key, project_id=pid, task_id=tid,
                                             source_path=canonical[(pid, tid)]['source_path'] if pid else None,
                                             sources=[]))
            if source not in item['sources']:
                item['sources'].append(source)
            item['reminder'] = row
            item.setdefault('reminders', []).append(row)
    return dict(calendar, **{k: v for k, v in reminders.items() if k not in ('queue',)},
                queue=[r for key, r in items.items() if key not in set(consumed)],
                review_keys=list(items))


def finish(hub, data, now):
    """Продвинуть границу атомарно, после всех ответов и полного чтения источников."""
    if (data.get('missing_lists') or data.get('complete') is not True or data.get('today_complete') is not True
            or data.get('tomorrow_complete') is not True or data.get('calendar_reviewed') is not True):
        raise ValueError('Ревью или чтение источников не завершено')
    keys, consumed = data.get('review_keys'), data.get('consumed')
    if not isinstance(keys, list) or not isinstance(consumed, list) or not set(keys) <= set(consumed):
        raise ValueError('Не все пункты ревью разобраны')
    through, finished = stamp(data['through']), stamp(now)
    if finished < through or stamp(data['since']) > through:
        raise ValueError('Неверная граница завершения')
    path = safe(Path(hub) / STATE)
    lock_path = safe(path.with_suffix('.lock'))
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        previous = read_state(hub)
        if previous != data.get('previous') or (previous and through < stamp(previous)):
            raise ValueError('Другое ревью уже изменило границу; перечитайте источники')
        state = dict(version=1, last_reviewed_through=through.isoformat(), finished_at=finished.isoformat())
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, encoding='utf-8', delete=False) as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
            handle.write('\n'); handle.flush(); os.fsync(handle.fileno())
            temporary = handle.name
        os.replace(temporary, path)
    return state


def load_reminders(hub, day, now):
    # Используем существующие ограничения доступа и нативную программу.
    from reminders_sync import Native, standard_allowlist
    config = json.loads(safe(Path(hub) / 'ai/reminders-sync.json').read_text(encoding='utf-8'))
    if config.get('enabled') is not True:
        raise ValueError('Режим напоминаний не включён')
    allowlist = json.loads(safe(standard_allowlist(config)).read_text(encoding='utf-8'))
    names = allowlist['names']
    if not isinstance(names, list) or not names or any(not isinstance(n, str) or not n for n in names):
        raise ValueError('Некорректный список разрешений')
    previous = read_state(hub)
    required = {binding['list_id'] for binding in config.get('projects', {}).values()}
    missing_ids = []
    rows = collect(Native(config), set(names), required, missing_ids)
    result = prepare(rows, day, now, previous)
    result['missing_lists'] = []
    for lid in missing_ids:
        bindings = [(pid, b) for pid, b in config['projects'].items() if b['list_id'] == lid]
        result['missing_lists'].append(dict(list_id=lid, list_name=bindings[0][1]['list_name'],
                                          project_ids=sorted(pid for pid, _ in bindings)))
    if result['missing_lists']:
        labels = ', '.join('«' + item['list_name'] + '»' for item in result['missing_lists'])
        result['clarification_question'] = 'Не найдены списки ' + labels + '. Ты удалил их намеренно?'
        result['warnings'].append('Неполный охват: не найдены связанные списки ' + labels)
        result['complete'] = False
    return result, config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['collect', 'finish'])
    parser.add_argument('--hub', required=True, type=Path)
    parser.add_argument('--day')
    parser.add_argument('--now', help='Время ISO 8601 с часовым поясом')
    args = parser.parse_args()
    now = args.now or datetime.now(TZ).isoformat()
    try:
        if args.action == 'collect':
            result, _ = load_reminders(args.hub, args.day or stamp(now).date().isoformat(), now)
        else:
            result = finish(args.hub, json.load(sys.stdin), now)
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
