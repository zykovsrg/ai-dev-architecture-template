"""Local EventKit process boundary; it is never a network client."""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from .models import CalendarRef, ChangeRequest, EventRef


class EventKitBackend:
    """Adapter placeholder for the pinned local EventKit bridge only."""

    def __init__(self, bridge: Path) -> None:
        self._bridge = bridge.resolve()

    async def _call(self, operation: str, payload: dict[str, object]) -> object:
        if not self._bridge.is_file():
            raise RuntimeError("LOCAL_EVENTKIT_BRIDGE_MISSING")
        process = await asyncio.create_subprocess_exec(
            "swift", str(self._bridge), operation,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate(json.dumps(payload).encode())
        if process.returncode != 0:
            raise RuntimeError("EVENTKIT_BRIDGE_FAILED")
        return json.loads(stdout)

    async def permission_status(self) -> str:
        result = await self._call("status", {})
        return str(result["permission"])

    async def list_calendars(self) -> list[CalendarRef]:
        result = await self._call("calendars", {})
        return [CalendarRef.model_validate(item) for item in result]

    async def read_events(self, calendar_ids: set[str], start: datetime, end: datetime) -> list[EventRef]:
        result = await self._call("events", {"calendar_ids": sorted(calendar_ids), "start": start.isoformat(), "end": end.isoformat()})
        return [EventRef.model_validate(item) for item in result]

    async def get_event(self, event_id: str) -> EventRef | None:
        # EventKit lookup is intentionally range-free only in the local bridge.
        result = await self._call("event", {"event_id": event_id})
        return None if result is None else EventRef.model_validate(result)

    async def free_slots(self, calendar_ids: set[str], start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
        events = sorted(await self.read_events(calendar_ids, start, end), key=lambda item: item.start)
        cursor, slots = start, []
        for event in events:
            if event.start > cursor: slots.append((cursor, event.start))
            cursor = max(cursor, event.end)
        if cursor < end: slots.append((cursor, end))
        return slots
