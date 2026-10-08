#!/usr/bin/env python3
"""Morning check of open current tasks during the session scan.

`list` writes the open current tasks of active registered projects (with their
Done criteria) to the batch folder outside the Hub. `record` keeps the
scanner's per-criterion evidence for one batch. `decide` says, per task, close
(every criterion met with cited session evidence) or pause. `pause` moves one
current task into the project's `ai/paused-tasks.md` and empties
`ai/current-task.md`. No transcript text is written anywhere by this script.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from session_collect import _inside, default_batch_dir  # noqa: E402
from task_records import read_records  # noqa: E402

_spec = importlib.util.spec_from_file_location("compact_index", SCRIPTS / "read-compact-task-index.py")
_index = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_index)

OPEN = {"active", "in_progress", "ready", "review", "blocked"}
TASKS_FILE = "open-tasks.json"
CHECKS_FILE = "task-checks.json"
KEEP_META = re.compile(r"(Due|due|Запланировано|Событие|Перенесено|Stage|Priority|Source|Created):?\s")

EMPTY_CURRENT = """# Current Task

Status: empty
Stage: intake

## Goal

No active task.

## Relevant files

None yet.

## Done criteria

Define during task intake.

## Agent handoff

{handoff}
"""


def done_criteria(text):
    """Bullets of the `## Done criteria` section; continuation lines join their bullet."""
    items, inside = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.strip() == "## Done criteria"
            continue
        if not inside or not line.strip():
            continue
        bullet = re.match(r"(?:[-*]|\d+[.)])\s+(?:\[[ xX]\]\s+)?(.*)", line)
        if bullet:
            items.append(bullet.group(1).strip())
        elif items:
            items[-1] += " " + line.strip()
    return items


def open_tasks(hub, today):
    """Open current tasks of active projects; a task file changed today is today's work and is skipped."""
    hub = Path(hub).resolve()
    rows, skipped = [], []
    for project in sorted(_index.parse_registry(hub / "ai/project-registry.md"), key=lambda p: p["project_id"]):
        if project["status"] != "active":
            continue
        root = _index.registered_project_root(hub, project)
        path = _index.safe_record(root, "ai/current-task.md")
        text = path.read_text(encoding="utf-8")
        records = read_records(project["project_id"], "current", text)
        if not records or records[0]["status"] not in OPEN:
            continue
        rec = records[0]
        if datetime.fromtimestamp(path.stat().st_mtime).date().isoformat() >= today:
            skipped.append({"project": project["project_id"], "task_id": rec["task_id"]})
            continue
        rows.append({"project": project["project_id"], "task_id": rec["task_id"], "title": rec["title"],
                     "status": rec["status"], "path": str(path), "criteria": done_criteria(text)})
    return rows, skipped


def _load(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def record(folder, batch, reply):
    """Keep valid evidence for open tasks from one scanner reply; return (kept, dropped)."""
    tasks = {(t["project"], t["task_id"]): t for t in _load(folder / TASKS_FILE, {"tasks": []})["tasks"]}
    sessions = {s["id"] for s in batch.get("sessions", [])}
    checks = _load(folder / CHECKS_FILE, [])
    items = reply.get("tasks", []) if isinstance(reply, dict) else []
    kept = dropped = 0
    for item in items:
        task = tasks.get((item.get("project"), item.get("task_id")))
        if task is None:
            dropped += 1
            continue
        for crit in item.get("criteria", []):
            n, ev, sid = crit.get("n"), crit.get("evidence"), crit.get("session")
            if (crit.get("met") is True and isinstance(n, int) and 1 <= n <= len(task["criteria"])
                    and sid in sessions and isinstance(ev, str) and ev.strip()):
                checks.append({"project": task["project"], "task_id": task["task_id"], "n": n,
                               "session": sid, "evidence": ev.strip()})
                kept += 1
            else:
                dropped += 1
        note = item.get("note")
        if isinstance(note, str) and note.strip():
            checks.append({"project": task["project"], "task_id": task["task_id"], "note": note.strip()})
    (folder / CHECKS_FILE).write_text(json.dumps(checks, ensure_ascii=False, indent=1), encoding="utf-8")
    return kept, dropped


def decide(folder):
    tasks = _load(folder / TASKS_FILE, {"tasks": []})["tasks"]
    checks = _load(folder / CHECKS_FILE, [])
    out = []
    for t in tasks:
        mine = [c for c in checks if c["project"] == t["project"] and c["task_id"] == t["task_id"]]
        evidence = {}
        for c in mine:
            if "n" in c:
                evidence.setdefault(c["n"], c)
        met = [evidence[n] for n in sorted(evidence)]
        total = len(t["criteria"])
        action = "close" if total and len(evidence) == total else "pause"
        out.append({"project": t["project"], "task_id": t["task_id"], "title": t["title"], "action": action,
                    "criteria": total, "met": met, "notes": [c["note"] for c in mine if "note" in c]})
    return out


def pause(hub, project_id, task_id, today):
    """Move the open current task to the top of `## Paused tasks` and empty current-task.md."""
    hub = Path(hub).resolve()
    project = next((p for p in _index.parse_registry(hub / "ai/project-registry.md")
                    if p["project_id"] == project_id and p["status"] == "active"), None)
    if project is None:
        raise ValueError(f"not an active registered project: {project_id}")
    root = _index.registered_project_root(hub, project)
    current = _index.safe_record(root, "ai/current-task.md")
    paused = _index.safe_record(root, "ai/paused-tasks.md")
    text = current.read_text(encoding="utf-8")
    records = read_records(project_id, "current", text)
    if not records or records[0]["task_id"] != task_id or records[0]["status"] not in OPEN:
        raise ValueError(f"current task is not open task {task_id}")
    rec = records[0]
    lines = text.splitlines()
    first_section = next((i for i, line in enumerate(lines) if line.startswith("## ")), len(lines))
    meta = [line for line in lines[:first_section] if KEEP_META.match(line)]
    body = [("##" + line) if line.startswith("## ") else line for line in lines[first_section:]]
    entry = [f"### {today} — {rec['title']}", "", f"Task ID: {task_id}", "", "Status: paused", ""]
    entry += meta + ([""] if meta else [])
    entry += ["Why paused:", "", f"Утренняя проверка {today}: критерии готовности не подтверждены, задача поставлена на паузу.",
              "", "Current state:", "", f"Статус до паузы: {rec['status']}. Полная запись задачи ниже.", "",
              "Resume criteria:", "", "Пользователь продолжает эту задачу.", ""]
    entry += [line.rstrip() for line in body]
    block = "\n".join(entry).rstrip() + "\n"
    old = paused.read_text(encoding="utf-8")
    marker = re.search(r"^## Paused tasks[ \t]*\n", old, re.M)
    if marker:
        new = old[:marker.end()] + "\n" + block + "\n" + old[marker.end():].lstrip("\n")
    else:
        new = old.rstrip("\n") + "\n\n## Paused tasks\n\n" + block
    paused.write_text(new.rstrip("\n") + "\n", encoding="utf-8")
    handoff = f"Задача {task_id} поставлена на паузу утренней проверкой {today}; запись — ai/paused-tasks.md."
    current.write_text(EMPTY_CURRENT.format(handoff=handoff), encoding="utf-8")
    return {"project": project_id, "task_id": task_id, "paused": str(paused), "current": str(current)}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--hub", required=True, type=Path)
    parser.add_argument("--dir", type=Path, default=None, help="batch folder outside the Hub")
    parser.add_argument("--today", default=date.today().isoformat())
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    rec = sub.add_parser("record")
    rec.add_argument("--batch", required=True, type=Path)
    rec.add_argument("--cases", required=True, type=Path)
    sub.add_parser("decide")
    pa = sub.add_parser("pause")
    pa.add_argument("--project", required=True)
    pa.add_argument("--task-id", required=True)
    args = parser.parse_args(argv)
    hub = args.hub.resolve()
    folder = (args.dir or default_batch_dir()).resolve()
    if _inside(folder, hub):
        raise SystemExit("ERROR: the batch folder must be outside the Hub")
    try:
        if args.cmd == "list":
            rows, skipped = open_tasks(hub, args.today)
            folder.mkdir(parents=True, exist_ok=True)
            (folder / TASKS_FILE).write_text(json.dumps({"tasks": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
            (folder / CHECKS_FILE).write_text("[]", encoding="utf-8")
            print(json.dumps({"open": len(rows), "skipped_today": skipped, "file": str(folder / TASKS_FILE)},
                             ensure_ascii=False))
        elif args.cmd == "record":
            from session_rules import load_reply
            reply = load_reply(args.cases.read_text(encoding="utf-8"))
            batch = json.loads(args.batch.read_text(encoding="utf-8"))
            kept, dropped = record(folder, batch, reply)
            print(json.dumps({"kept": kept, "dropped": dropped}))
        elif args.cmd == "decide":
            print(json.dumps(decide(folder), ensure_ascii=False, indent=1))
        else:
            print(json.dumps(pause(hub, args.project, args.task_id, args.today), ensure_ascii=False))
    except (OSError, ValueError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
