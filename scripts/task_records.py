#!/usr/bin/env python3
"""Shared strict helpers for canonical task-record dates."""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path


def read_due(lines):
    values = []
    for line in lines:
        match = re.fullmatch(r"\s*(?:Due|due):\s*(.*?)\s*", line)
        if match:
            value = match.group(1)
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError("invalid_due")
            date.fromisoformat(value)
            values.append(value)
    if len(set(values)) > 1:
        raise ValueError("conflicting_due")
    return values[0] if values else None


def read_records(project_id, kind, text):
    if kind == "current":
        lines = text.splitlines()
        task_id = next((line[9:] for line in lines if line.startswith("Task ID: ")), None)
        status = next((line[8:] for line in lines if line.startswith("Status: ")), None)
        if status in {"empty", "backlog", None} and task_id in {None, "TASK-YYYYMMDD-NNN"}:
            return []
        if not task_id or not (task_id.startswith(f"TASK-{project_id}-") or re.fullmatch(r"TASK-\d{8}-\d{3}|FT-\d{8}-\d+", task_id)):
            raise ValueError("invalid_current_task_id")
        if status not in {"active", "ready", "in_progress", "waiting", "blocked", "review", "paused", "done", "completed"}:
            raise ValueError("invalid_status")
        goal = re.search(r"^## Goal\s*$\n(?:\s*\n)*(\S[^\n]*)", text, re.M)
        if not goal:
            raise ValueError("missing_goal")
        return [{"task_id": task_id, "title": goal.group(1), "status": status, "due": read_due(lines)}]
    if kind == "paused":
        records = []
        for block in re.split(r"(?=^### )", text, flags=re.M):
            heading = re.match(r"^### \d{4}-\d{2}-\d{2} — (.+)$", block, re.M)
            if not heading:
                continue
            task_id = re.search(r"^Task ID: (.+)$", block, re.M)
            status = re.search(r"^Status: (.+)$", block, re.M)
            valid_id = task_id and (task_id.group(1).startswith(f"TASK-{project_id}-") or re.fullmatch(r"TASK-\d{8}-\d{3}|FT-\d{8}-\d+", task_id.group(1)))
            if not valid_id or not status or status.group(1) != "paused":
                raise ValueError("invalid_paused_record")
            records.append({"task_id": task_id.group(1), "title": heading.group(1), "status": "paused", "due": read_due(block.splitlines())})
        return records
    if kind != "future":
        raise ValueError("unsupported task kind")
    records = []
    heading = None
    body = []
    def flush():
        if heading is None:
            return
        match = re.fullmatch(r"### (TASK-[a-z0-9-]+-\d{8}-\d{3}|FT-\d{8}-\d+) — (.+)", heading)
        if not match:
            return
        task_id, title = match.groups()
        if task_id.startswith("TASK-") and not task_id.startswith(f"TASK-{project_id}-"):
            raise ValueError("foreign_task_id")
        status = next((line.split(": ", 1)[1] for line in body if line.startswith("Status: ")), None)
        if status not in {"idea", "ready", "blocked", "promoted", "done", "dropped"}:
            raise ValueError("invalid_status")
        records.append({"task_id": task_id, "title": title, "status": status, "due": read_due(body)})
    for line in text.splitlines():
        if line.startswith("### "):
            flush()
            heading, body = line, []
        elif heading is not None:
            body.append(line)
    flush()
    return records


def validate_project_dates(current_text, future_text, paused_text):
    return {
        "current": read_due(current_text.splitlines()),
        "future": read_due(future_text.splitlines()),
        "paused": read_due(paused_text.splitlines()),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("read", nargs="?")
    parser.add_argument("--file", type=Path)
    parser.add_argument("--current-file", type=Path)
    parser.add_argument("--future-file", type=Path)
    parser.add_argument("--paused-file", type=Path)
    parser.add_argument("--validate-project-dates", action="store_true")
    parser.add_argument("--project-id")
    parser.add_argument("--kind", choices=("current", "future", "paused"))
    args = parser.parse_args()
    try:
        if args.current_file or args.future_file or args.paused_file:
            if not (args.current_file and args.future_file and args.paused_file):
                raise ValueError("incomplete_project_records")
            if args.validate_project_dates:
                due_dates = validate_project_dates(
                    args.current_file.read_text(encoding="utf-8"),
                    args.future_file.read_text(encoding="utf-8"),
                    args.paused_file.read_text(encoding="utf-8"),
                )
                print(json.dumps({"due": due_dates}, ensure_ascii=False))
                return 0
            if not args.project_id:
                raise ValueError("incomplete_project_records")
            records = read_project_records(
                args.project_id,
                args.current_file.read_text(encoding="utf-8"),
                args.future_file.read_text(encoding="utf-8"),
                args.paused_file.read_text(encoding="utf-8"),
            )
            print(json.dumps({"records": records}, ensure_ascii=False))
            return 0
        if not args.file:
            raise ValueError("missing_file")
        text = args.file.read_text(encoding="utf-8")
        if args.project_id and args.kind:
            print(json.dumps({"records": read_records(args.project_id, args.kind, text)}, ensure_ascii=False))
            return 0
        due = read_due(text.splitlines())
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps({"due": due}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
