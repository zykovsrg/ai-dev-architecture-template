"""The only client-visible Calendar operations for the Personal AI Hub."""

from datetime import datetime
from hashlib import sha256
import json
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .backend import CalendarBackend
from .eventkit_backend import BridgeError
from .models import CalendarRef, ChangeRequest, EventRef
from .policy import CalendarPolicy, PolicyError
from .preview import PreviewGrantStore


SOURCE = "Apple Calendar / EventKit"


class GuardedCalendarServer:
    """Fail-closed facade; it has no raw upstream mutation tools."""

    tool_names = frozenset({
        "calendar_status", "list_calendar_metadata", "read_events", "find_free_slots",
        "preview_change", "cancel_preview", "apply_change",
    })

    def __init__(
        self,
        backend: CalendarBackend,
        policy: CalendarPolicy,
        previews: PreviewGrantStore,
    ) -> None:
        self._backend = backend
        self._policy = policy
        self._previews = previews

    async def calendar_status(self) -> dict[str, object]:
        return {
            "source": SOURCE,
            "permission": await self._backend.permission_status(),
            "configured_calendar_count": len(self._policy.allowed_calendar_ids),
        }

    async def list_calendar_metadata(self) -> dict[str, object]:
        calendars = await self._backend.list_calendars()
        return {
            "source": SOURCE,
            "calendars": [
                {"id": item.id, "name": item.name, "source": SOURCE, "writable": item.writable,
                 "timezone": item.timezone}
                for item in calendars if item.id in self._policy.allowed_calendar_ids
            ],
        }

    async def read_events(
        self, calendar_ids: set[str], start: datetime, end: datetime, timezone: str
    ) -> dict[str, object]:
        await self._require_permission()
        self._validate_range(start, end, timezone)
        events, unavailable = await self._read_calendar_events(calendar_ids, start, end, timezone)
        return {
            "source": SOURCE,
            "timezone": timezone,
            "events": [item.model_dump(mode="json") for item in events],
            "unavailable_calendar_ids": unavailable,
            "availability_complete": not unavailable,
        }

    async def find_free_slots(
        self, calendar_ids: set[str], start: datetime, end: datetime, timezone: str
    ) -> dict[str, object]:
        await self._require_permission()
        self._validate_range(start, end, timezone)
        events, unavailable = await self._read_calendar_events(calendar_ids, start, end, timezone)
        slots = [] if unavailable else self._free_slots(events, start, end)
        return {
            "source": SOURCE,
            "timezone": timezone,
            "slots": [{"start": left.isoformat(), "end": right.isoformat()} for left, right in slots],
            "unavailable_calendar_ids": unavailable,
            "availability_complete": not unavailable,
        }

    async def preview_change(self, request: ChangeRequest) -> dict[str, object]:
        await self._require_permission()
        calendar = await self._calendar(request.calendar_id)
        self._policy.authorize_change(calendar, request)
        event = await self._current_event(request)
        self._authorize_existing(request, event)
        grant = self._previews.issue(request, source_fingerprint=_fingerprint(event))
        return self._preview_response(grant.id, grant.expires_at, request, calendar, event)

    async def cancel_preview(self, preview_id: str) -> dict[str, str]:
        self._previews.cancel(preview_id)
        return {"result": "cancelled"}

    async def apply_change(self, preview_id: str, request: ChangeRequest) -> dict[str, object]:
        await self._require_permission()
        calendar = await self._calendar(request.calendar_id)
        self._policy.authorize_change(calendar, request)
        event = await self._current_event(request)
        self._authorize_existing(request, event)
        self._previews.consume(preview_id, request, source_fingerprint=_fingerprint(event))
        if request.action == "create":
            result = await self._backend.create(request)
        elif request.action == "update":
            assert event is not None
            result = await self._backend.update(event, request, request.recurrence_scope)
        else:
            assert event is not None
            await self._backend.delete(event, request.recurrence_scope)
            await self._confirm_deleted(event)
            result = event
        return {"source": SOURCE, "result": "applied", "event": result.model_dump(mode="json")}

    async def _confirm_deleted(self, event: EventRef) -> None:
        remaining = await self._backend.get_event(event.id, event.start)
        # EventKit can turn the last occurrence of a series into a standalone
        # event instead of removing it. That standalone event is the same single
        # occurrence, so it is removed once more as a single event.
        if remaining is not None and remaining.start == event.start and not remaining.recurring:
            await self._backend.delete(remaining, None)
            remaining = await self._backend.get_event(event.id, event.start)
        if remaining is not None and remaining.start == event.start:
            raise PolicyError("DELETE_NOT_APPLIED")

    async def _require_permission(self) -> None:
        if await self._backend.permission_status() != "granted":
            raise PolicyError("CALENDAR_PERMISSION_DENIED")

    async def _calendar(self, calendar_id: str) -> CalendarRef:
        calendar = next((item for item in await self._backend.list_calendars() if item.id == calendar_id), None)
        self._policy.authorize_calendar(calendar)
        assert calendar is not None
        return calendar

    async def _read_calendar_events(
        self, calendar_ids: set[str], start: datetime, end: datetime, timezone: str
    ) -> tuple[list[EventRef], list[str]]:
        if not calendar_ids:
            raise PolicyError("CALENDAR_ID_REQUIRED")

        # Validate the entire request before treating any configured calendar as
        # temporarily unavailable. Unknown IDs remain hard errors.
        for calendar_id in calendar_ids:
            self._policy.authorize_read(calendar_id, timezone)

        calendars = {item.id: item for item in await self._backend.list_calendars()}
        events: list[EventRef] = []
        unavailable: list[str] = []
        for calendar_id in sorted(calendar_ids):
            calendar = calendars.get(calendar_id)
            if calendar is None:
                unavailable.append(calendar_id)
                continue
            if calendar.timezone != timezone:
                raise PolicyError("CALENDAR_TIMEZONE_MISMATCH")
            try:
                events.extend(await self._backend.read_events({calendar_id}, start, end))
            except (BridgeError, PolicyError) as error:
                if str(error) not in {"CALENDAR_NOT_FOUND", "CALENDAR_UNAVAILABLE"}:
                    raise
                unavailable.append(calendar_id)
        events.sort(key=lambda item: item.start)
        return events, unavailable

    @staticmethod
    def _free_slots(
        events: list[EventRef], start: datetime, end: datetime
    ) -> list[tuple[datetime, datetime]]:
        cursor = start
        slots: list[tuple[datetime, datetime]] = []
        for event in sorted(events, key=lambda item: item.start):
            if event.start > cursor:
                slots.append((cursor, min(event.start, end)))
            cursor = max(cursor, event.end)
            if cursor >= end:
                break
        if cursor < end:
            slots.append((cursor, end))
        return slots

    async def _current_event(self, request: ChangeRequest) -> EventRef | None:
        if request.action == "create":
            return None
        assert request.event_id is not None
        event = await self._backend.get_event(request.event_id, request.occurrence_start)
        if event is None:
            raise PolicyError("EVENT_UNAVAILABLE")
        if event.calendar_id != request.calendar_id:
            raise PolicyError("CALENDAR_MISMATCH")
        # The backend resolved by identifier and start; refuse anything else,
        # so a series can never stand in for the occurrence that was named.
        if request.occurrence_start is not None and event.start != request.occurrence_start:
            raise PolicyError("OCCURRENCE_UNAVAILABLE")
        return event

    def _authorize_existing(self, request: ChangeRequest, event: EventRef | None) -> None:
        if request.action == "delete":
            assert event is not None
            self._policy.authorize_delete(event, request.recurrence_scope)
        elif request.action == "update":
            assert event is not None
            self._policy.authorize_update(event, request)

    @staticmethod
    def _validate_range(start: datetime, end: datetime, timezone: str) -> None:
        try:
            ZoneInfo(timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError("timezone must be a valid IANA timezone") from error
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("start and end must include timezone")
        if end <= start:
            raise ValueError("end must be later than start")

    @staticmethod
    def _preview_response(
        preview_id: str, expires_at: datetime, request: ChangeRequest, calendar: CalendarRef, event: EventRef | None
    ) -> dict[str, object]:
        return {
            "preview_id": preview_id,
            "expires_at": expires_at.isoformat(),
            "action": request.action,
            "calendar": {"id": calendar.id, "name": calendar.name, "timezone": calendar.timezone},
            "title": request.title if request.title is not None else (event.title if event else None),
            "start": request.start.isoformat() if request.start else (event.start.isoformat() if event else None),
            "end": request.end.isoformat() if request.end else (event.end.isoformat() if event else None),
            # A delete, or an update that leaves all_day unset, keeps the event's
            # own flag; otherwise the preview shows what the request asks for.
            "all_day": event.all_day if (event and (request.action == "delete" or request.all_day is None))
            else bool(request.all_day),
            "event_id": event.id if event else None,
            "recurrence_scope": request.recurrence_scope,
            "occurrence_start": request.occurrence_start.isoformat() if request.occurrence_start else None,
            "effect": "No change has been made. Apply requires this exact preview confirmation.",
        }


def _fingerprint(event: EventRef | None) -> str:
    payload = None if event is None else event.model_dump(mode="json")
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return sha256(canonical.encode("utf-8")).hexdigest()
