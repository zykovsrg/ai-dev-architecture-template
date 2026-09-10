"""Noncanonical inputs for a confirmation-gated evening review."""

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


def pending_friction(hub_root: Path, day: str) -> list[dict[str, object]]:
    source = hub_root / "ai/tmp/workflow-friction" / f"{day}.txt"
    if not source.exists():
        return []
    return [{"id": sha256(f"{day}\0{ordinal}\0{line}".encode()).hexdigest(), "ordinal": ordinal, "text": line}
            for ordinal, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1) if line]
