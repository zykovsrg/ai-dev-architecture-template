#!/usr/bin/env python3
"""Shared strict helpers for canonical task-record dates and records."""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

DUE_RE = re.compile(r"\s*(?:Due|due):\s*(.*?)\s*")


def read_due(lines):
    values = []
    for line in lines:
        match = DUE_RE.fullmatch(line)
        if match:
            value = match.group(1)
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError("invalid_due")
            try:
                date.fromisoformat(value)
            except ValueError as error:
                raise ValueError("invalid_due") from error
            values.append(value)
    if len(set(values)) > 1:
        raise ValueError("conflicting_due")
    return values[0] if values else None


def _due_value(line):
    match = DUE_RE.fullmatch(line)
    if not match:
        return None
    value = match.group(1)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("invalid_due")
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("invalid_due") from error
    return value


def _finish_due(values):
    if len(set(values)) > 1:
        raise ValueError("conflicting_due")
    return values[0] if values else None


def _valid_task_id(project_id, task_id):
    return task_id and (
        task_id.startswith(f"TASK-{project_id}-")
        or re.fullmatch(r"TASK-\d{8}-\d{3}|FT-\d{8}-\d+", task_id)
    )


def _read_records_lines(project_id, kind, lines, *, compact):
    if kind == "current":
        task_id = status = title = None
        due_values = []
        saw_goal = False
        for raw in lines:
            line = raw.rstrip("\r\n")
            if task_id is None and line.startswith("Task ID: "):
                task_id = line[9:]
            if status is None and line.startswith("Status: "):
                status = line[8:]
            due = _due_value(line)
            if due is not None:
                due_values.append(due)
            if line == "## Goal":
                saw_goal = True
                continue
            if saw_goal and title is None:
                if not line.strip():
                    continue
                if not line[0].isspace():
                    title = line
                saw_goal = False
                if compact:
                    break
        if status in {"empty", "backlog", None} and task_id in {None, "TASK-YYYYMMDD-NNN"}:
            return []
        if not task_id or not _valid_task_id(project_id, task_id):
            raise ValueError("invalid_current_task_id")
        if status not in {"active", "ready", "in_progress", "waiting", "blocked", "review", "paused", "done", "completed"}:
            raise ValueError("invalid_status")
        if title is None:
            raise ValueError("missing_goal")
        return [{"task_id": task_id, "title": title, "status": status, "due": _finish_due(due_values)}]

    if kind == "paused":
        records = []
        heading = task_id = status = None
        due_values = []
        metadata_done = False

        def flush_paused():
            if heading is None:
                return
            match = re.fullmatch(r"### \d{4}-\d{2}-\d{2} — (.+)", heading)
            if not match:
                return
            if not _valid_task_id(project_id, task_id) or status != "paused":
                raise ValueError("invalid_paused_record")
            records.append({"task_id": task_id, "title": match.group(1), "status": "paused", "due": _finish_due(due_values)})

        for raw in lines:
            line = raw.rstrip("\r\n")
            if line.startswith("### "):
                flush_paused()
                heading, task_id, status, due_values = line, None, None, []
                metadata_done = False
                continue
            if heading is None or (compact and metadata_done):
                continue
            if task_id is None and line.startswith("Task ID: "):
                task_id = line[9:]
                continue
            if status is None and line.startswith("Status: "):
                status = line[8:]
                continue
            due = _due_value(line)
            if due is not None:
                due_values.append(due)
                continue
            if compact and task_id is not None and status is not None and line.strip() and not line.startswith(("Priority: ", "Source: ", "Created: ")):
                metadata_done = True
        flush_paused()
        return records

    if kind != "future":
        raise ValueError("unsupported task kind")

    records = []
    heading = status = None
    due_values = []
    metadata_done = False

    def flush_future():
        if heading is None:
            return
        match = re.fullmatch(r"### (TASK-[a-z0-9-]+-\d{8}-\d{3}|FT-\d{8}-\d+) — (.+)", heading)
        if not match:
            return
        task_id, title = match.groups()
        if task_id.startswith("TASK-") and not task_id.startswith(f"TASK-{project_id}-"):
            raise ValueError("foreign_task_id")
        if status not in {"idea", "ready", "blocked", "promoted", "done", "dropped"}:
            raise ValueError("invalid_status")
        records.append({"task_id": task_id, "title": title, "status": status, "due": _finish_due(due_values)})

    for raw in lines:
        line = raw.rstrip("\r\n")
        if line.startswith("### "):
            flush_future()
            heading, status, due_values = line, None, []
            metadata_done = False
            continue
        if heading is None or (compact and metadata_done):
            continue
        if status is None and line.startswith("Status: "):
            status = line.split(": ", 1)[1]
            continue
        due = _due_value(line)
        if due is not None:
            due_values.append(due)
            continue
        if compact and status is not None and line.strip() and not line.startswith(("Priority: ", "Source: ", "Created: ")):
            metadata_done = True
    flush_future()
    return records


def read_records_lines(project_id, kind, lines):
    """Parse only compact discovery metadata from a streaming line iterator."""
    return _read_records_lines(project_id, kind, lines, compact=True)


def read_records(project_id, kind, text):
    """Parse a complete canonical record while preserving full strict validation."""
    return _read_records_lines(project_id, kind, text.splitlines(), compact=False)


def read_project_records(project_id, current_text, future_text, paused_text):
    records = []
    for kind, text in (("current", current_text), ("future", future_text), ("paused", paused_text)):
        for row in read_records(project_id, kind, text):
            records.append({**row, "source_kind": kind})
    return records


def validate_project_dates(current_text, future_text, paused_text):
    return {"current": read_due(current_text.splitlines()), "future": read_due(future_text.splitlines()), "paused": read_due(paused_text.splitlines())}


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
                due_dates = validate_project_dates(args.current_file.read_text(encoding="utf-8"), args.future_file.read_text(encoding="utf-8"), args.paused_file.read_text(encoding="utf-8"))
                print(json.dumps({"due": due_dates}, ensure_ascii=False))
                return 0
            if not args.project_id:
                raise ValueError("incomplete_project_records")
            records = read_project_records(args.project_id, args.current_file.read_text(encoding="utf-8"), args.future_file.read_text(encoding="utf-8"), args.paused_file.read_text(encoding="utf-8"))
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
