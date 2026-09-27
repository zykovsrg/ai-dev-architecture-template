#!/usr/bin/env python3
"""Plan and apply guarded updates to the local day-plan calendar context."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
import json
import os
from pathlib import Path
import sys
import tempfile
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SOURCE = "Apple Calendar / EventKit"


def calendar_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise SystemExit(f"ERROR: invalid calendar date: {value}") from error


def desired_dates(anchor: date) -> list[date]:
    return [anchor + timedelta(days=offset) for offset in range(-30, 31)]


def context_path(hub: str) -> Path:
    root = Path(hub).resolve(strict=True)
    target = root / "ai" / "tmp" / "calendar-context.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink() or target.parent.is_symlink():
        raise SystemExit("ERROR: calendar context path must not be a symlink")
    return target


def load_valid(path: Path, timezone: str, calendar_ids: list[str]) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if (
        not isinstance(data, dict)
        or data.get("schema_version") != 1
        or data.get("timezone") != timezone
        or data.get("calendar_ids") != calendar_ids
        or not isinstance(data.get("days"), dict)
    ):
        return None
    return data


def ranges_for(days: list[date]) -> list[dict[str, str]]:
    if not days:
        return []
    result: list[dict[str, str]] = []
    start = previous = days[0]
    for current in days[1:]:
        if current != previous + timedelta(days=1):
            result.append({"start": start.isoformat(), "end": (previous + timedelta(days=1)).isoformat()})
            start = current
        previous = current
    result.append({"start": start.isoformat(), "end": (previous + timedelta(days=1)).isoformat()})
    return result


def plan(args: argparse.Namespace) -> None:
    anchor = calendar_date(args.anchor)
    path = context_path(args.hub)
    calendar_ids = sorted(set(args.calendar_id))
    data = load_valid(path, args.timezone, calendar_ids)
    if data is None:
        ranges = [{"start": (anchor - timedelta(days=30)).isoformat(), "end": (anchor + timedelta(days=31)).isoformat()}]
    else:
        stored = set(data["days"])
        missing = [item for item in desired_dates(anchor) if item.isoformat() not in stored and item != anchor]
        ranges = [{"start": anchor.isoformat(), "end": (anchor + timedelta(days=1)).isoformat()}]
        ranges.extend(ranges_for(missing))
    print(json.dumps({"context": str(path), "ranges": ranges}, ensure_ascii=False, separators=(",", ":")))


def parse_event(raw: object, timezone: str, calendar_ids: set[str]) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise SystemExit("ERROR: event must be an object")
    required = ("id", "calendar_id", "title", "start", "end")
    if any(not isinstance(raw.get(key), str) or not raw[key] for key in required):
        raise SystemExit("ERROR: event is missing a required string field")
    if raw["calendar_id"] not in calendar_ids:
        raise SystemExit("ERROR: event calendar is not selected")
    try:
        start = datetime.fromisoformat(raw["start"])
        end = datetime.fromisoformat(raw["end"])
    except ValueError as error:
        raise SystemExit("ERROR: event has an invalid timestamp") from error
    if start.tzinfo is None or end.tzinfo is None or end <= start:
        raise SystemExit("ERROR: event timestamps must be aware and ordered")
    return {
        "id": raw["id"], "calendar_id": raw["calendar_id"], "title": raw["title"],
        "start": start.isoformat(), "end": end.isoformat(),
        "all_day": bool(raw.get("all_day", False)), "timezone": timezone, "source": SOURCE,
    }


def ingest(args: argparse.Namespace) -> None:
    anchor = calendar_date(args.anchor)
    range_start, range_end = calendar_date(args.start), calendar_date(args.end)
    if range_end <= range_start:
        raise SystemExit("ERROR: ingest end must be after start")
    try:
        ZoneInfo(args.timezone)
    except ZoneInfoNotFoundError as error:
        raise SystemExit("ERROR: invalid IANA timezone") from error
    payload = json.load(sys.stdin)
    if payload.get("source") != SOURCE or payload.get("timezone") != args.timezone:
        raise SystemExit("ERROR: calendar response source or timezone mismatch")
    calendar_ids = sorted(set(args.calendar_id))
    events = [parse_event(item, args.timezone, set(calendar_ids)) for item in payload.get("events", [])]
    path = context_path(args.hub)
    data = load_valid(path, args.timezone, calendar_ids) or {
        "schema_version": 1, "anchor_date": args.anchor, "timezone": args.timezone,
        "calendar_ids": calendar_ids, "days": {},
    }
    wanted = {item.isoformat() for item in desired_dates(anchor)}
    days = {key: value for key, value in data["days"].items() if key in wanted}
    fetched_at = datetime.now().astimezone().isoformat()
    cursor = range_start
    while cursor < range_end:
        local_start = datetime.combine(cursor, datetime.min.time(), ZoneInfo(args.timezone))
        local_end = datetime.combine(cursor + timedelta(days=1), datetime.min.time(), ZoneInfo(args.timezone))
        bucket = [event for event in events if datetime.fromisoformat(event["start"]) < local_end and datetime.fromisoformat(event["end"]) > local_start]
        days[cursor.isoformat()] = {"fetched_at": fetched_at, "events": bucket}
        cursor += timedelta(days=1)
    output = {"schema_version": 1, "anchor_date": args.anchor, "timezone": args.timezone, "calendar_ids": calendar_ids, "days": days}
    handle, stage_name = tempfile.mkstemp(prefix=".calendar-context.", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stage:
            json.dump(output, stage, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            stage.write("\n")
        os.replace(stage_name, path)
    finally:
        if os.path.exists(stage_name):
            os.unlink(stage_name)
    print(json.dumps({"context": str(path), "stored_days": len(days)}, ensure_ascii=False, separators=(",", ":")))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    sub = result.add_subparsers(dest="command", required=True)
    for name in ("plan", "ingest"):
        command = sub.add_parser(name)
        command.add_argument("--hub", required=True)
        command.add_argument("--anchor", required=True)
        command.add_argument("--timezone", required=True)
        command.add_argument("--calendar-id", action="append", required=True)
        if name == "ingest":
            command.add_argument("--start", required=True)
            command.add_argument("--end", required=True)
    return result


def main() -> None:
    args = parser().parse_args()
    plan(args) if args.command == "plan" else ingest(args)


if __name__ == "__main__":
    main()
