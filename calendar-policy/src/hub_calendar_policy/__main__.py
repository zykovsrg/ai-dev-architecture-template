"""Local stdio entrypoint for the guarded Apple Calendar MCP."""

import json
import os
from datetime import datetime
from pathlib import Path

from .eventkit_backend import EventKitBackend
from .mcp_server import build_mcp
from .policy import CalendarPolicy
from .preview import PreviewGrantStore
from .server import GuardedCalendarServer


def main() -> None:
    allowlist_path = Path(os.environ["HUB_CALENDAR_ALLOWLIST"])
    bridge_path = Path(os.environ["HUB_CALENDAR_BRIDGE"])
    data = json.loads(allowlist_path.read_text(encoding="utf-8"))
    allowed = frozenset(data.get("calendar_ids", []))
    backend = EventKitBackend(bridge_path)
    guarded = GuardedCalendarServer(
        backend, CalendarPolicy(allowed_calendar_ids=allowed),
        PreviewGrantStore(clock=lambda: datetime.now().astimezone()),
        clock=lambda: datetime.now().astimezone(),
    )
    build_mcp(guarded).run()


if __name__ == "__main__":
    main()
