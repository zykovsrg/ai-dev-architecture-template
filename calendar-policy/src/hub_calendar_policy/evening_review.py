"""Noncanonical inputs for a confirmation-gated evening review."""

import json
import os
import re
import stat
import tempfile
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

from .models import EventRef


def _inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _cache_directory(hub_root: Path, name: str, *, create: bool = False) -> Path:
    hub = Path(hub_root).resolve(strict=True)
    current = hub
    for part in ("ai", "tmp", name):
        current = current / part
        if current.is_symlink():
            raise ValueError(f"{name} cache path must not contain symlinks")
        if current.exists():
            if not current.is_dir():
                raise ValueError(f"{name} cache path must contain directories only")
        elif create:
            try:
                current.mkdir()
            except FileExistsError:
                if current.is_symlink():
                    raise ValueError(f"{name} cache path must not contain symlinks")
                if not current.is_dir():
                    raise ValueError(f"{name} cache path must contain directories only")
    if not _inside(current.resolve(strict=False), hub):
        raise ValueError(f"{name} cache must stay inside Hub")
    return current


def _regular_cache_file(directory: Path, name: str, label: str) -> Path:
    root = directory.resolve(strict=False)
    path = directory / name
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symlink")
    if not _inside(path.resolve(strict=False), root):
        raise ValueError(f"{label} must stay inside its cache directory")
    if path.exists() and not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError(f"{label} must be a regular file")
    return path


def _validate_day(day: str) -> None:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise ValueError("day must be YYYY-MM-DD")


def day_bounds(day: str, timezone: str) -> tuple[datetime, datetime]:
    start = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=ZoneInfo(timezone))
    return start, start + timedelta(days=1)


def write_snapshot(hub_root: Path, day: str, events: list[EventRef]) -> Path:
    _validate_day(day)
    directory = _cache_directory(hub_root, "calendar-snapshots", create=True)
    fd, name = tempfile.mkstemp(prefix=f"{day}-", suffix=".txt", dir=directory)
    snapshot = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("".join(
                f"{event.start:%H:%M}|{event.end:%H:%M}|{event.title}|{event.calendar_id}\n"
                for event in events
            ))
    except Exception:
        snapshot.unlink(missing_ok=True)
        raise
    return snapshot


def prior_snapshots(hub_root: Path, day: str) -> list[str]:
    _validate_day(day)
    directory = _cache_directory(hub_root, "calendar-snapshots")
    if not directory.exists():
        return []
    snapshots = []
    for path in sorted(directory.glob(f"{day}-*.txt")):
        safe = _regular_cache_file(directory, path.name, "calendar snapshot")
        snapshots.append(str(safe))
    return snapshots


def friction_state(hub_root: Path, day: str) -> dict[str, object]:
    _validate_day(day)
    directory = _cache_directory(hub_root, "workflow-friction")
    path = _regular_cache_file(directory, f"{day}.state.json", "workflow friction state")
    if not path.exists():
        return {"format": 1, "entries": {}}
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("format") != 1 or not isinstance(state.get("entries"), dict):
        raise ValueError("invalid workflow friction state")
    return state


def pending_friction(hub_root: Path, day: str) -> list[dict[str, object]]:
    _validate_day(day)
    directory = _cache_directory(hub_root, "workflow-friction")
    source = _regular_cache_file(directory, f"{day}.txt", "workflow friction source")
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
