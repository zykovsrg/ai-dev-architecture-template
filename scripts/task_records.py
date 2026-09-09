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
    if kind != "future":
        raise ValueError("only future records are supported by this reader version")
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("read", nargs="?")
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--project-id")
    parser.add_argument("--kind", choices=("future",))
    args = parser.parse_args()
    try:
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
