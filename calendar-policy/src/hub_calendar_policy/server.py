"""The only client-visible Calendar operations for the Personal AI Hub."""

from collections.abc import Callable
from datetime import datetime
from hashlib import sha256
import json
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .backend import CalendarBackend
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
        *,
        clock: Callable[[], datetime],
    ) -> None:
        self._backend = backend
        self._policy = policy
        self._previews = previews
        self._clock = clock

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
                for item in calendars
            ],
        }

    async def read_events(
        self, calendar_ids: set[str], start: datetime, end: datetime, timezone: str
    ) -> dict[str, object]:
        await self._require_permission()
        self._validate_range(start, end, timezone)
        await self._authorize_calendar_ids(calendar_ids, timezone)
        events = await self._backend.read_events(calendar_ids, start, end)
        return {"source": SOURCE, "timezone": timezone, "events": [item.model_dump(mode="json") for item in events]}

    async def find_free_slots(
        self, calendar_ids: set[str], start: datetime, end: datetime, timezone: str
    ) -> dict[str, object]:
        await self._require_permission()
        self._validate_range(start, end, timezone)
        await self._authorize_calendar_ids(calendar_ids, timezone)
        slots = await self._backend.free_slots(calendar_ids, start, end)
        return {"source": SOURCE, "timezone": timezone, "slots": [{"start": left.isoformat(), "end": right.isoformat()} for left, right in slots]}

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
            result = event
        return {"source": SOURCE, "result": "applied", "event": result.model_dump(mode="json")}

    async def _require_permission(self) -> None:
        if await self._backend.permission_status() != "granted":
            raise PolicyError("CALENDAR_PERMISSION_DENIED")

    async def _calendar(self, calendar_id: str) -> CalendarRef:
        calendar = next((item for item in await self._backend.list_calendars() if item.id == calendar_id), None)
        self._policy.authorize_calendar(calendar)
        assert calendar is not None
        return calendar

    async def _authorize_calendar_ids(self, calendar_ids: set[str], timezone: str) -> None:
        if not calendar_ids:
            raise PolicyError("CALENDAR_ID_REQUIRED")
        for calendar_id in calendar_ids:
            calendar = await self._calendar(calendar_id)
            if calendar.timezone != timezone:
                raise PolicyError("CALENDAR_TIMEZONE_MISMATCH")
            self._policy.authorize_read(calendar_id, timezone)

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
            self._policy.authorize_delete(event, request.recurrence_scope, self._now())
        elif request.action == "update":
            assert event is not None
            self._policy.authorize_update(event, request, self._now())

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

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("clock must return a timezone-aware datetime")
        return now

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
            "event_id": event.id if event else None,
            "recurrence_scope": request.recurrence_scope,
            "occurrence_start": request.occurrence_start.isoformat() if request.occurrence_start else None,
            "effect": "No change has been made. Apply requires this exact preview confirmation.",
        }


def _fingerprint(event: EventRef | None) -> str:
    payload = None if event is None else event.model_dump(mode="json")
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return sha256(canonical.encode("utf-8")).hexdigest()
