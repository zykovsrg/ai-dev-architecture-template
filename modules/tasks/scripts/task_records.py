#!/usr/bin/env python3
"""Shared strict helpers for canonical task-record dates and records."""

import argparse
import hashlib
import importlib.util
import os
import tempfile
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

DUE_RE = re.compile(r"\s*(?:Due|due):\s*(.*?)\s*")
SCHEDULED_RE = re.compile(r"Запланировано: (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})[-–](\d{2}:\d{2})(?: \([^)]*\))?(?:\.|, .+)?\s*")
LINK_RE = re.compile(r"Событие: ([^/\s]+)/(\S+) · синхронизировано: (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})-(\d{2}:\d{2})\s*")


def _validated_span(day, start, end):
    try:
        first = datetime.strptime(f"{day} {start}", "%Y-%m-%d %H:%M")
        last = datetime.strptime(f"{day} {end}", "%Y-%m-%d %H:%M")
    except ValueError as error:
        raise ValueError("invalid_schedule") from error
    if last <= first:
        raise ValueError("invalid_schedule_range")
    return (f"{day} {start}", f"{day} {end}")


def parse_scheduled(line):
    match = SCHEDULED_RE.fullmatch(line)
    if not match:
        all_day = re.fullmatch(r"Запланировано: (\d{4}-\d{2}-\d{2}) \(весь день\)\.?\s*", line)
        if all_day:
            date.fromisoformat(all_day.group(1))
            return None
        start_only = re.fullmatch(r"Запланировано: (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})(?: \([^)]*\))?(?:\.|, .+)?\s*", line)
        if start_only:
            datetime.strptime(" ".join(start_only.groups()), "%Y-%m-%d %H:%M")
            return None
        date_only = re.fullmatch(r"Запланировано: (?:релиз )?(\d{4}-\d{2}-\d{2})\.(?: Ожидание: .+)?\s*", line)
        if date_only:
            date.fromisoformat(date_only.group(1))
            return None
        if line.startswith("Запланировано:"):
            raise ValueError("invalid_schedule")
        return None
    return _validated_span(*match.groups())


def parse_event_link(line):
    if not line.startswith("Событие:"):
        return None
    match = LINK_RE.fullmatch(line)
    if not match:
        raise ValueError("invalid_event_link")
    calendar_id, event_id, day, start, end = match.groups()
    _validated_span(day, start, end)
    return {"calendar_id": calendar_id, "event_id": event_id,
            "synced_start": f"{day} {start}", "synced_end": f"{day} {end}"}


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
    return bool(
        task_id
        and re.fullmatch(
            rf"(?:TASK-{re.escape(project_id)}-\d{{8}}-\d{{3}}|TASK-\d{{8}}-\d{{3}}|FT-\d{{8}}-\d+)",
            task_id,
        )
    )


def _read_records_lines(project_id, kind, lines, *, compact):
    if kind == "current":
        task_id = status = title = None
        due_values = []
        scheduled = event_link = None
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
            sched = parse_scheduled(line)
            if sched is not None and scheduled is None:
                scheduled = sched
            link = parse_event_link(line)
            if link is not None:
                event_link = link
            if line == "## Goal":
                saw_goal = True
                continue
            if saw_goal and title is None:
                if not line.strip():
                    continue
                if not line[0].isspace():
                    title = line
                saw_goal = False
        if status in {"empty", "backlog", None} and task_id in {None, "TASK-YYYYMMDD-NNN"}:
            return []
        if not task_id or not _valid_task_id(project_id, task_id):
            raise ValueError("invalid_current_task_id")
        if status not in {"active", "ready", "in_progress", "waiting", "blocked", "review", "paused", "done", "completed"}:
            raise ValueError("invalid_status")
        if title is None:
            raise ValueError("missing_goal")
        return [{"task_id": task_id, "title": title, "status": status, "due": _finish_due(due_values), "scheduled": scheduled, "event_link": event_link}]

    if kind == "paused":
        records = []
        heading = task_id = status = None
        due_values = []
        scheduled = event_link = None
        metadata_done = False

        def flush_paused(scheduled, event_link):
            if heading is None:
                return
            match = re.fullmatch(r"### \d{4}-\d{2}-\d{2} — (.+)", heading)
            if not match:
                return
            if not _valid_task_id(project_id, task_id) or status != "paused":
                raise ValueError("invalid_paused_record")
            records.append({"task_id": task_id, "title": match.group(1), "status": "paused", "due": _finish_due(due_values), "scheduled": scheduled, "event_link": event_link})

        for raw in lines:
            line = raw.rstrip("\r\n")
            if line.startswith("### "):
                flush_paused(scheduled, event_link)
                heading, task_id, status, due_values, scheduled, event_link = line, None, None, [], None, None
                metadata_done = False
                continue
            if heading is None:
                continue
            due = _due_value(line)
            if due is not None:
                due_values.append(due)
                continue
            sched = parse_scheduled(line)
            if sched is not None and scheduled is None:
                scheduled = sched
            link = parse_event_link(line)
            if link is not None:
                event_link = link
            if compact and metadata_done:
                continue
            if task_id is None and line.startswith("Task ID: "):
                task_id = line[9:]
                continue
            if status is None and line.startswith("Status: "):
                status = line[8:]
                continue
            if compact and task_id is not None and status is not None and line.strip() and not line.startswith(("Priority: ", "Source: ", "Created: ", "Paused: ", "Stage: ")):
                metadata_done = True
        flush_paused(scheduled, event_link)
        return records

    if kind != "future":
        raise ValueError("unsupported task kind")

    records = []
    heading = status = None
    due_values = []
    scheduled = event_link = None
    metadata_done = False

    def flush_future(scheduled, event_link):
        if heading is None:
            return
        match = re.fullmatch(r"### (TASK-[a-z0-9-]+-\d{8}-\d{3}|FT-\d{8}-\d+) — (.+)", heading)
        if not match:
            return
        task_id, title = match.groups()
        if task_id.startswith("TASK-") and not task_id.startswith(f"TASK-{project_id}-"):
            raise ValueError("foreign_task_id")
        # Совместимость с completed, уже допустимым в текущих задачах.
        canonical_status = "done" if status == "completed" else status
        if canonical_status not in {"idea", "ready", "blocked", "promoted", "done", "dropped"}:
            raise ValueError("invalid_status")
        records.append({"task_id": task_id, "title": title, "status": canonical_status, "due": _finish_due(due_values), "scheduled": scheduled, "event_link": event_link})

    for raw in lines:
        line = raw.rstrip("\r\n")
        if line.startswith("### "):
            flush_future(scheduled, event_link)
            heading, status, due_values, scheduled, event_link = line, None, [], None, None
            metadata_done = False
            continue
        if heading is None:
            continue
        due = _due_value(line)
        if due is not None:
            due_values.append(due)
            continue
        sched = parse_scheduled(line)
        if sched is not None and scheduled is None:
            scheduled = sched
        link = parse_event_link(line)
        if link is not None:
            event_link = link
        if compact and metadata_done:
            continue
        if status is None and line.startswith("Status: "):
            status = line.split(": ", 1)[1]
            continue
        if compact and status is not None and line.strip() and not line.startswith(("Priority: ", "Source: ", "Created: ")):
            metadata_done = True
    flush_future(scheduled, event_link)
    return records


FUTURE_HEADING_RE = re.compile(r"### (?:TASK-[a-z0-9-]+-\d{8}-\d{3}|FT-\d{8}-\d+) — .+")
PAUSED_HEADING_RE = re.compile(r"### \d{4}-\d{2}-\d{2} — .+")
TEMPLATE_HEADINGS = {"### FT-YYYYMMDD-001 — Task title", "### YYYY-MM-DD — Task title"}


def unrecognized_headings(kind, lines):
    """Return (line_number, heading) for `###` headings that record parsing would skip."""
    if kind == "current":
        return []
    pattern = FUTURE_HEADING_RE if kind == "future" else PAUSED_HEADING_RE
    found = []
    for number, raw in enumerate(lines, 1):
        line = raw.rstrip("\r\n")
        if line.startswith("### ") and line not in TEMPLATE_HEADINGS and not pattern.fullmatch(line):
            found.append((number, line))
    return found


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


def read_due_per_record(lines):
    """Validate due dates inside each `###` record; return the earliest date or None.

    Future and paused files hold many records, so different records may carry
    different dates. Only one record with two different dates is a conflict.
    """
    values = []
    chunk = []
    for line in list(lines) + ["### "]:
        if line.startswith("### "):
            due = read_due(chunk)
            if due is not None:
                values.append(due)
            chunk = []
        else:
            chunk.append(line)
    return min(values) if values else None


def validate_project_dates(current_text, future_text, paused_text):
    return {
        "current": read_due(current_text.splitlines()),
        "future": read_due_per_record(future_text.splitlines()),
        "paused": read_due_per_record(paused_text.splitlines()),
    }


TASK_FILES = {"current": "current-task.md", "future": "future-tasks.md", "paused": "paused-tasks.md"}


def gateway_module():
    """Внешняя команда и проверенный resolver используют один исполнитель процесса."""
    name = 'hub_reminders_task_gateway'
    module = sys.modules.get(name)
    if module is None:
        path = Path(__file__).with_name('reminders_task_gateway.py')
        if not path.is_file():
            raise ValueError('reminders_task_gateway_missing')
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[name] = module
    return module


def reminders_mode(hub):
    path = Path(hub) / 'ai/reminders-sync.json' if hub is not None else None
    if path is None or not path.is_file():
        return False
    config = json.loads(path.read_text(encoding='utf-8'))
    if 'task_authority' not in config:
        return False
    return gateway_module().sync_module().authority_enabled(config)


def _record_ids(project_id, kind, text):
    return {record["task_id"] for record in read_records(project_id, kind, text) if record["task_id"]}


def _lost_task_ids(project_dir, project_id, kind, before, text):
    """Идентификаторы, которые новый текст убирает и которых нет в других файлах задач."""
    try:
        old_ids = _record_ids(project_id, kind, before.decode("utf-8"))
    except ValueError:
        return set()
    lost = old_ids - _record_ids(project_id, kind, text)
    for other, filename in TASK_FILES.items():
        path = project_dir / "ai" / filename
        if other != kind and lost and path.is_file():
            lost -= _record_ids(project_id, other, path.read_text(encoding="utf-8"))
    return lost


def write_task_file(hub, project_id, kind, expected_sha256, text, allow_removal=()):
    """Проверить весь новый текст до замены зарегистрированного файла задач."""
    if hub is None or not project_id or not kind or not expected_sha256:
        raise ValueError("incomplete_write_request")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ValueError("invalid_expected_sha256")
    hub = hub.resolve(strict=True)
    section = None
    paths = []
    for line in (hub / "ai/project-registry.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
        elif section == project_id and line.startswith("Path: "):
            paths.append(Path(line[6:].strip()))
    adopted = None
    if reminders_mode(hub):
        sync = gateway_module().sync_module()
        config = sync.load_config(hub)
        authority = sync.authority_module()
        authority.validate_policy(hub, config)
        adopted = authority.bound_projects(hub, config).get(project_id)
        if adopted is None:
            raise ValueError('unbound_project')
    if adopted is None and len(paths) != 1:
        raise ValueError("unregistered_project")
    project = adopted or paths[0]
    root = hub / "projects"
    if (root.is_symlink() or project.is_symlink() or not project.is_absolute()
            or (adopted is None and project.resolve(strict=True).parent != root.resolve(strict=True))):
        raise ValueError("unsafe_task_path")
    project = project.resolve(strict=True)
    filename = TASK_FILES[kind]
    target = project / "ai" / filename
    if target.parent.is_symlink() or target.is_symlink() or not target.is_file():
        raise ValueError("unsafe_task_path")
    before = target.read_bytes()
    if hashlib.sha256(before).hexdigest() != expected_sha256:
        raise ValueError("task_file_changed")
    read_records(project_id, kind, text)
    if unrecognized_headings(kind, text.splitlines()):
        raise ValueError("unrecognized_heading")
    lost = _lost_task_ids(project, project_id, kind, before, text) - set(allow_removal)
    if lost:
        raise ValueError("task_id_lost:" + ",".join(sorted(lost)))
    staged = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".task-record-", delete=False) as stream:
            staged = Path(stream.name)
            os.fchmod(stream.fileno(), target.stat().st_mode & 0o777)
            stream.write(text.encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        if target.is_symlink() or target.parent.is_symlink() or target.read_bytes() != before:
            raise ValueError("task_file_changed")
        os.replace(staged, target)
    finally:
        if staged is not None and staged.exists():
            staged.unlink()
    return {"result": "written", "path": str(target), "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", nargs="?", choices=("read", "write", "write-batch"), default="read")
    parser.add_argument("--hub", type=Path)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--file", type=Path)
    parser.add_argument("--current-file", type=Path)
    parser.add_argument("--future-file", type=Path)
    parser.add_argument("--paused-file", type=Path)
    parser.add_argument("--validate-project-dates", action="store_true")
    parser.add_argument("--project-id")
    parser.add_argument("--kind", choices=("current", "future", "paused"))
    parser.add_argument("--strict-headings", action="store_true")
    parser.add_argument("--allow-removal", action="append", default=[])
    args = parser.parse_args()
    try:
        if args.action in {"write", "write-batch"}:
            if args.file or args.current_file or args.future_file or args.paused_file:
                raise ValueError("write_target_is_derived_from_registry")
            if args.action == 'write-batch':
                if not reminders_mode(args.hub):
                    raise ValueError('batch_requires_reminders_authority')
                value = json.load(sys.stdin)
                result = gateway_module().write_batch_from_texts(sys.modules[__name__], args.hub, args.project_id,
                                                               value['expected_sha256'], value['texts'])
            elif reminders_mode(args.hub):
                result = gateway_module().write_from_text(sys.modules[__name__], args.hub, args.project_id, args.kind,
                                                         args.expected_sha256, sys.stdin.read(), args.allow_removal)
            else:
                result = write_task_file(args.hub, args.project_id, args.kind, args.expected_sha256, sys.stdin.read(), args.allow_removal)
            print(json.dumps(result, ensure_ascii=False))
            return 0
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
            if args.strict_headings:
                skipped = unrecognized_headings(args.kind, text.splitlines())
                for number, heading in skipped:
                    print(f"unrecognized_heading:{number}: {heading}", file=sys.stderr)
                if skipped:
                    return 2
            return 0
        due = read_due(text.splitlines())
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps({"due": due}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
