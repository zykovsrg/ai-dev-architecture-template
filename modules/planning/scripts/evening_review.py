#!/usr/bin/env python3
"""Read-only input selection for an urgent-first, conversational evening review."""

import argparse
import importlib.util
import json
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

SOURCE = 'Apple Calendar / EventKit'
URGENT = 'Важно и срочно'


def local_datetime(value, timezone):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError('event timestamps must include timezone')
    return result.astimezone(timezone)


def select_events(response, day, timezone, allowed):
    if response.get('source') != SOURCE or response.get('timezone') != timezone.key:
        raise ValueError('expected guarded Calendar source and timezone')
    if not isinstance(response.get('availability_complete'), bool):
        raise ValueError('missing Calendar coverage')
    unavailable = response.get('unavailable_calendar_ids')
    if not isinstance(unavailable, list) or not set(unavailable) <= allowed:
        raise ValueError('invalid unavailable calendar IDs')
    start = datetime.combine(day, time.min, timezone)
    end = datetime.combine(day + timedelta(days=1), time.min, timezone)
    selected = {}
    for event in response['events']:
        if event['calendar_id'] not in allowed:
            raise ValueError('event calendar not allowed by metadata')
        if not isinstance(event['title'], str) or not isinstance(event['all_day'], bool):
            raise ValueError('invalid Calendar event')
        a = local_datetime(event['start'], timezone)
        b = local_datetime(event['end'], timezone)
        if b <= a:
            raise ValueError('event ends before it starts')
        if a < end and b > start:
            selected[(event['calendar_id'], event['id'], event['start'])] = event
    complete = response['availability_complete'] and not unavailable
    return sorted(selected.values(), key=lambda e: (local_datetime(e['start'], timezone), e['id'])), complete


def prepare_review(metadata, today, tomorrow, projects, tasks, day, consumed=()):
    """Return exact events and stable review keys, never outcomes or writes."""
    day = date.fromisoformat(day)
    if metadata.get('source') != SOURCE:
        raise ValueError('expected guarded Calendar metadata')
    calendars = metadata['calendars']
    allowed = {c['id'] for c in calendars}
    if len(allowed) != len(calendars):
        raise ValueError('duplicate calendar IDs')
    timezone = ZoneInfo(today['timezone'])
    if any(c.get('timezone', timezone.key) != timezone.key for c in calendars):
        raise ValueError('mixed calendar timezones')
    events, today_complete = select_events(today, day, timezone, allowed)
    future, tomorrow_complete = select_events(tomorrow, day + timedelta(days=1), timezone, allowed)
    urgent_ids = [c['id'] for c in calendars if c['name'] == URGENT]
    status = 'available' if len(urgent_ids) == 1 else ('ambiguous' if urgent_ids else 'unavailable')
    if status == 'available' and urgent_ids[0] in tomorrow['unavailable_calendar_ids']:
        status = 'unavailable'
    urgent = [e for e in future if status == 'available' and e['calendar_id'] == urgent_ids[0]]
    queue = []
    skipped = 0
    consumed = set(consumed)
    tasks = [t for t in tasks if t['project_id'] in projects]
    for event in events:
        parts = event['title'].split('/')
        project = parts[1] if len(parts) >= 3 and parts[0] and parts[1] in projects and '/'.join(parts[2:]).strip() else None
        linked = [t for t in tasks if t.get('event_link') and
                  (t['event_link']['calendar_id'], t['event_link']['event_id']) == (event['calendar_id'], event['id'])]
        if len(linked) > 1 or (linked and project and linked[0]['project_id'] != project):
            skipped += 1
            continue
        matched = linked[0] if linked else None
        if matched:
            project = matched['project_id']
        if project is None:
            skipped += 1
            continue
        if matched is None:
            exact = [t for t in tasks if t['project_id'] == project and t['title'].casefold().rstrip('.') == '/'.join(parts[2:]).casefold().rstrip('.')]
            matched = exact[0] if len(exact) == 1 else None
        # Matching task identity (or exact title fallback) groups repeated blocks,
        # while the cursor still presents one event at a time until answered.
        key = json.dumps([project, matched['task_id'] if matched else event['title'].casefold()], ensure_ascii=False)
        if key not in consumed:
            queue.append(dict(event=event, project_id=project,
                              task_id=matched['task_id'] if matched else None,
                              source_path=matched.get('source_path') if matched else None,
                              review_key=key))
    return dict(day=day.isoformat(), timezone=timezone.key, urgent_status=status,
                urgent=urgent, queue=queue, skipped=skipped,
                today_complete=today_complete, tomorrow_complete=tomorrow_complete,
                unavailable_calendar_ids=sorted(set(today['unavailable_calendar_ids'] + tomorrow['unavailable_calendar_ids'])))


def prepare_sync(window, day, timezone, allowed, hub, now):
    """Run the mandatory [D-30, D+31) task/Calendar sync check (read-only)."""
    start = local_datetime(window['start'], timezone)
    end = local_datetime(window['end'], timezone)
    if start > datetime.combine(day - timedelta(days=30), time.min, timezone) or \
            end < datetime.combine(day + timedelta(days=31), time.min, timezone):
        raise ValueError('sync_window must cover [D-30, D+31)')
    response = window['response']
    if response.get('source') != SOURCE or response.get('timezone') != timezone.key:
        raise ValueError('expected guarded Calendar source and timezone in sync_window')
    unavailable = response.get('unavailable_calendar_ids')
    if not isinstance(response.get('availability_complete'), bool) or not isinstance(unavailable, list):
        raise ValueError('missing Calendar coverage in sync_window')
    if any(e['calendar_id'] not in allowed for e in response['events']):
        raise ValueError('sync_window event calendar not allowed by metadata')
    if not response['availability_complete'] or unavailable:
        return dict(status='incomplete', items=[], unavailable_calendar_ids=sorted(unavailable))
    spec = importlib.util.spec_from_file_location('review_calendar_sync', Path(__file__).resolve().parent / 'calendar_task_sync.py')
    sync = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sync)
    items = sync.find_discrepancies(sync.collect_tasks(hub), response['events'], now, tz=timezone.key)
    return dict(status='complete', items=items)


def canonical_inputs(hub):
    """Reuse canonical registry/path guards in source and installed layouts."""
    scripts = Path(__file__).resolve().parent
    task_scripts = scripts if (scripts / 'read-compact-task-index.py').is_file() else scripts.parents[1] / 'tasks/scripts'
    sys.path.insert(0, str(task_scripts))
    spec = importlib.util.spec_from_file_location('review_compact_index', task_scripts / 'read-compact-task-index.py')
    index = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(index)
    from task_records import read_records
    # Discovery first: this also reports unrecognized task heading warnings.
    rows = index.build_index(hub)
    projects, tasks = set(), []
    for project in index.parse_registry(hub / 'ai/project-registry.md'):
        if project['status'] != 'active':
            continue
        root = index.registered_project_root(hub, project)
        projects.add(project['project_id'])
        # Link identity is absent from the compact index; read only canonical
        # records selected by discovery to recover that required detail.
        discovered_paths = {r['source_path'] for r in rows if r['project_id'] == project['project_id']}
        for kind, relative in index.SOURCE_FILES.items():
            path = index.safe_record(root, relative)
            if str(path) not in discovered_paths:
                continue
            for record in read_records(project['project_id'], kind, path.read_text(encoding='utf-8')):
                tasks.append(dict(record, project_id=project['project_id'], source_path=str(path)))
    return projects, tasks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hub', required=True, type=Path)
    parser.add_argument('--day', required=True)
    parser.add_argument('--now', help='YYYY-MM-DD HH:MM in the calendar timezone; defaults to the current time')
    args = parser.parse_args()
    try:
        data = json.load(sys.stdin)
        projects, tasks = canonical_inputs(args.hub.resolve())
        consumed = data.get('consumed', [])
        # The first run of a review must include the month window: the sync
        # check is part of the review, not an optional step to remember.
        if not consumed and 'sync_window' not in data:
            raise ValueError('sync_window is required on the first run: pass the guarded [D-30, D+31) read_events response')
        output = prepare_review(data['metadata'], data['today'], data['tomorrow'], projects, tasks,
                                args.day, consumed)
        if 'sync_window' in data:
            timezone = ZoneInfo(output['timezone'])
            now = args.now or datetime.now(timezone).strftime('%Y-%m-%d %H:%M')
            datetime.strptime(now, '%Y-%m-%d %H:%M')
            allowed = {c['id'] for c in data['metadata']['calendars']}
            output['sync'] = prepare_sync(data['sync_window'], date.fromisoformat(args.day), timezone,
                                          allowed, args.hub.resolve(), now)
        else:
            output['sync'] = dict(status='done-earlier-this-review')
        print(json.dumps(output, ensure_ascii=False))
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
