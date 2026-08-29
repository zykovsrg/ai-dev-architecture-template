"""Local stdio entrypoint for the guarded Apple Calendar MCP."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from .eventkit_backend import EventKitBackend
from .mcp_server import build_mcp
from .policy import CalendarPolicy
from .preview import PreviewGrantStore
from .server import GuardedCalendarServer


class ConfigError(RuntimeError):
    """A configuration problem reported before any Calendar access."""


def load_allowed_calendar_ids(path: Path) -> frozenset[str]:
    """Read the allowlist; an unreadable or malformed file allows nothing."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ConfigError(f"allowlist file is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise ConfigError(f"allowlist file is not valid JSON: {path}") from error
    if not isinstance(data, dict):
        raise ConfigError("allowlist must be a JSON object")
    ids = data.get("calendar_ids", [])
    if not isinstance(ids, list) or not all(isinstance(item, str) and item for item in ids):
        raise ConfigError("calendar_ids must be a list of non-empty strings")
    return frozenset(ids)


def _required_path(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise ConfigError(f"environment variable {name} is required")
    return Path(value)


def build_server() -> GuardedCalendarServer:
    allowed = load_allowed_calendar_ids(_required_path("HUB_CALENDAR_ALLOWLIST"))
    bridge_path = _required_path("HUB_CALENDAR_BRIDGE")
    if not bridge_path.is_file():
        raise ConfigError(f"local EventKit bridge is missing: {bridge_path}")
    clock = lambda: datetime.now().astimezone()
    return GuardedCalendarServer(
        EventKitBackend(bridge_path),
        CalendarPolicy(allowed_calendar_ids=allowed),
        PreviewGrantStore(clock=clock),
        clock=clock,
    )


def main() -> None:
    try:
        guarded = build_server()
    except ConfigError as error:
        print(f"hub-calendar-policy: {error}", file=sys.stderr)
        raise SystemExit(2) from error
    build_mcp(guarded).run()


if __name__ == "__main__":
    main()
