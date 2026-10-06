#!/usr/bin/env python3
"""Read-only drift detection between task schedules and linked calendar events."""

import argparse
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from task_records import read_records  # noqa: E402

_spec = importlib.util.spec_from_file_location("compact_index", SCRIPTS / "read-compact-task-index.py")
_index = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_index)

CLOSED = {"done", "completed", "dropped"}
# Waiting or paused work has no schedule to keep, so passed or late blocks are not drift.
NO_SCHEDULE_CHECK = CLOSED | {"waiting", "paused"}


def collect_tasks(hub):
    hub = Path(hub).resolve()
    rows = []
    for project in sorted(_index.parse_registry(hub / "ai/project-registry.md"), key=lambda p: p["project_id"]):
        if project["status"] != "active":
            continue
        root = _index.registered_project_root(hub, project)
        for kind, relative in _index.SOURCE_FILES.items():
            path = _index.safe_record(root, relative)
            for rec in read_records(project["project_id"], kind, path.read_text(encoding="utf-8")):
                if rec["scheduled"] is None and rec["event_link"] is None:
                    continue
                rows.append({"project_id": project["project_id"], "task_id": rec["task_id"],
                             "title": rec["title"], "status": rec["status"], "source_path": str(path),
                             "scheduled": rec["scheduled"], "event_link": rec["event_link"], "due": rec["due"]})
    return rows


def _local(value, tz=None):
    dt = datetime.fromisoformat(value)
    if tz is not None:
        dt = dt.astimezone(ZoneInfo(tz))
    return dt.strftime("%Y-%m-%d %H:%M")


def _span(ev, tz=None):
    return (_local(ev["start"], tz), _local(ev["end"], tz))


def schedule_items(item, status, span, due, now):
    """Report an open task whose block already passed or lands after its deadline."""
    if status in NO_SCHEDULE_CHECK or span is None:
        return []
    # A block earlier today belongs to the evening review, not to sync.
    if span[1][:10] < now[:10]:
        return [{**item, "kind": "schedule_passed", "event": list(span)}]
    if due and span[0][:10] > due:
        return [{**item, "kind": "scheduled_after_due", "event": list(span)}]
    return []


def find_discrepancies(tasks, events, now, tz=None):
    timed = [e for e in events if not e.get("all_day")]
    by_id = defaultdict(list)
    for e in timed:
        by_id[(e["calendar_id"], e["id"])].append(e)
    competing = Counter((t["project_id"], t["title"], tuple(t["scheduled"]))
                        for t in tasks if t["scheduled"] and t["status"] not in CLOSED)
    occupied = {(t["event_link"]["calendar_id"], t["event_link"]["event_id"])
                for t in tasks if t["event_link"]}
    out = []
    for t in tasks:
        link = t["event_link"]
        item = {"project_id": t["project_id"], "task_id": t["task_id"], "source_path": t["source_path"],
                "task": list(t["scheduled"]) if t["scheduled"] else None, "event": None, "synced": None,
                "event_id": None, "calendar_id": None, "event_title": None, "due": t.get("due")}
        if link is None:
            if t["status"] in CLOSED or t["scheduled"] is None:
                continue
            key = (t["project_id"], t["title"], tuple(t["scheduled"]))
            if competing[key] != 1:
                continue
            hits = [e for e in timed if _span(e, tz) == tuple(t["scheduled"])
                    and len(by_id[(e["calendar_id"], e["id"])]) == 1
                    and not e.get("recurring", False)
                    and (e["calendar_id"], e["id"]) not in occupied
                    and e["title"].split("/", 2)[1:] == [t["project_id"], t["title"]]]
            if len(hits) == 1:
                e = hits[0]
                out.append({**item, "kind": "unlinked", "event": list(_span(e, tz)), "event_id": e["id"],
                            "calendar_id": e["calendar_id"], "event_title": e["title"]})
                item = {**item, "event_id": e["id"], "calendar_id": e["calendar_id"], "event_title": e["title"]}
            out += schedule_items(item, t["status"], tuple(t["scheduled"]), t.get("due"), now)
            continue
        synced = (link["synced_start"], link["synced_end"])
        item.update(synced=list(synced), event_id=link["event_id"], calendar_id=link["calendar_id"])
        candidates = by_id.get((link["calendar_id"], link["event_id"]), [])
        if not candidates:
            if t["status"] not in CLOSED:
                out.append({**item, "kind": "event_missing"})
            continue
        if len(candidates) > 1 or any(e.get("recurring", False) for e in candidates):
            exact = [e for e in candidates if _span(e, tz) == synced]
            if len(exact) != 1:
                out.append({**item, "kind": "event_ambiguous"})
                continue
            e = exact[0]
        else:
            e = candidates[0]
        span = _span(e, tz)
        item.update(event=list(span), event_title=e["title"])
        if t["status"] in CLOSED:
            if span[0] > now:
                out.append({**item, "kind": "closed_with_future_event"})
            continue
        sched = tuple(t["scheduled"]) if t["scheduled"] else None
        ev_moved, task_moved = span != synced, sched != synced
        if ev_moved and task_moved:
            kind = "stale_sync" if sched == span else "both_moved"
        elif ev_moved:
            kind = "calendar_moved"
        elif task_moved:
            kind = "task_moved"
        else:
            kind = None
        if kind:
            out.append({**item, "kind": kind})
        # Calendar is the source of truth for time, so check the event's span.
        out += schedule_items(item, t["status"], span, t.get("due"), now)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hub", required=True, type=Path)
    parser.add_argument("--now", required=True)
    args = parser.parse_args()
    try:
        datetime.strptime(args.now, "%Y-%m-%d %H:%M")
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    try:
        payload = json.loads(sys.stdin.read())
        events = payload["events"]
        tz = payload.get("timezone")
        result = find_discrepancies(collect_tasks(args.hub), events, args.now, tz=tz)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
