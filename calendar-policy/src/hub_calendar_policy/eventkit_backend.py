"""Local EventKit process boundary; it is never a network client."""

import asyncio
import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from .models import CalendarRef, ChangeRequest, EventRef


class BridgeError(RuntimeError):
    """A stable, user-safe code reported by the local bridge boundary."""


class EventKitBackend:
    """Adapter for the pinned local EventKit bridge only."""

    # The bridge is a signed bundle executable, so it is run directly. The
    # interpreter seam exists only so tests can drive a stub process.
    def __init__(self, bridge: Path, *, interpreter: Sequence[str] = ()) -> None:
        self._bridge = bridge.resolve()
        self._interpreter = tuple(interpreter)

    async def _call(self, operation: str, payload: dict[str, object] | None) -> object:
        if not self._bridge.is_file():
            raise BridgeError("LOCAL_EVENTKIT_BRIDGE_MISSING")
        try:
            process = await asyncio.create_subprocess_exec(
                *self._interpreter, str(self._bridge), operation,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except (FileNotFoundError, PermissionError) as error:
            raise BridgeError("EVENTKIT_BRIDGE_UNAVAILABLE") from error
        stdout, _ = await process.communicate(json.dumps(payload or {}).encode())
        if process.returncode != 0:
            raise BridgeError("EVENTKIT_BRIDGE_FAILED")
        return _unwrap(stdout)

    async def permission_status(self) -> str:
        result = await self._call("status", None)
        if not isinstance(result, dict) or "permission" not in result:
            raise BridgeError("EVENTKIT_BRIDGE_FAILED")
        return str(result["permission"])

    async def list_calendars(self) -> list[CalendarRef]:
        result = await self._call("calendars", None)
        return [CalendarRef.model_validate(item) for item in _as_list(result)]

    async def read_events(self, calendar_ids: set[str], start: datetime, end: datetime) -> list[EventRef]:
        result = await self._call("events", {
            "calendar_ids": sorted(calendar_ids),
            "start": start.isoformat(),
            "end": end.isoformat(),
        })
        return [EventRef.model_validate(item) for item in _as_list(result)]

    async def get_event(self, event_id: str) -> EventRef | None:
        result = await self._call("event", {"event_id": event_id})
        return None if result is None else EventRef.model_validate(result)

    async def free_slots(self, calendar_ids: set[str], start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
        events = sorted(await self.read_events(calendar_ids, start, end), key=lambda item: item.start)
        cursor: datetime = start
        slots: list[tuple[datetime, datetime]] = []
        for event in events:
            if event.start > cursor:
                slots.append((cursor, event.start))
            cursor = max(cursor, event.end)
        if cursor < end:
            slots.append((cursor, end))
        return slots

    async def create(self, request: ChangeRequest) -> EventRef:
        result = await self._call("create", request.model_dump(mode="json"))
        return EventRef.model_validate(result)

    async def update(self, event: EventRef, request: ChangeRequest, scope: str | None) -> EventRef:
        payload = request.model_dump(mode="json", exclude_none=True)
        payload["event_id"] = event.id
        payload["calendar_id"] = event.calendar_id
        payload["recurrence_scope"] = scope
        result = await self._call("update", payload)
        return EventRef.model_validate(result)

    async def delete(self, event: EventRef, scope: str | None) -> None:
        await self._call("delete", {
            "event_id": event.id,
            "calendar_id": event.calendar_id,
            "recurrence_scope": scope,
        })


def _unwrap(stdout: bytes) -> object:
    try:
        envelope = json.loads(stdout)
    except json.JSONDecodeError as error:
        raise BridgeError("EVENTKIT_BRIDGE_FAILED") from error
    if not isinstance(envelope, dict) or "ok" not in envelope:
        raise BridgeError("EVENTKIT_BRIDGE_FAILED")
    if envelope["ok"] is not True:
        raise BridgeError(_error_code(envelope.get("error")))
    return envelope.get("data")


def _error_code(value: object) -> str:
    known = {
        "CALENDAR_ACCESS_DENIED", "CALENDAR_NOT_FOUND", "EVENT_NOT_FOUND",
        "CALENDAR_MISMATCH", "INVALID_PAYLOAD", "SAVE_FAILED", "UNSUPPORTED_OPERATION",
    }
    return value if isinstance(value, str) and value in known else "EVENTKIT_BRIDGE_FAILED"


def _as_list(result: object) -> list[object]:
    if not isinstance(result, list):
        raise BridgeError("EVENTKIT_BRIDGE_FAILED")
    return result
