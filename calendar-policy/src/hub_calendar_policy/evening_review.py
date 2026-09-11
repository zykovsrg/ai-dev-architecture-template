"""Noncanonical inputs for a confirmation-gated evening review."""

import json
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

from .models import EventRef


def day_bounds(day: str, timezone: str) -> tuple[datetime, datetime]:
    start = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=ZoneInfo(timezone))
    return start, start + timedelta(days=1)


def write_snapshot(hub_root: Path, day: str, events: list[EventRef]) -> Path:
    directory = hub_root / "ai/tmp/calendar-snapshots"
    directory.mkdir(parents=True, exist_ok=True)
    snapshot = directory / f"{day}-{len(list(directory.glob(f'{day}-*.txt'))):04d}.txt"
    snapshot.write_text("".join(f"{event.start:%H:%M}|{event.end:%H:%M}|{event.title}|{event.calendar_id}\n" for event in events), encoding="utf-8")
    return snapshot


def prior_snapshots(hub_root: Path, day: str) -> list[str]:
    directory = hub_root / "ai/tmp/calendar-snapshots"
    return [str(path) for path in sorted(directory.glob(f"{day}-*.txt"))] if directory.exists() else []


def friction_state(hub_root: Path, day: str) -> dict[str, object]:
    path = hub_root / "ai/tmp/workflow-friction" / f"{day}.state.json"
    if not path.exists():
        return {"format": 1, "entries": {}}
    if path.is_symlink():
        raise ValueError("workflow friction state must not be a symlink")
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("format") != 1 or not isinstance(state.get("entries"), dict):
        raise ValueError("invalid workflow friction state")
    return state


def pending_friction(hub_root: Path, day: str) -> list[dict[str, object]]:
    source = hub_root / "ai/tmp/workflow-friction" / f"{day}.txt"
    if not source.exists():
        return []
    state = friction_state(hub_root, day)
    entries = []
    for ordinal, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        identifier = sha256(f"{day}\0{ordinal}\0{line}".encode()).hexdigest()
        if state["entries"].get(identifier, {}).get("disposition", "pending") == "pending":
            entries.append({"id": identifier, "ordinal": ordinal, "text": line})
    return entries
