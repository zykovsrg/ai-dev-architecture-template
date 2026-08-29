"""Strict authorization rules independent of EventKit and MCP transport."""

from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

from .models import CalendarRef, ChangeRequest, EventRef, _require_timezone


class PolicyError(RuntimeError):
    """A stable, user-safe denial code."""


class CalendarPolicy(BaseModel):
    """Allows only explicitly selected calendar identifiers; no defaults."""

    model_config = ConfigDict(frozen=True)

    allowed_calendar_ids: frozenset[str] = Field(default_factory=frozenset)

    def authorize_calendar(self, calendar: CalendarRef | None) -> None:
        if calendar is None:
            raise PolicyError("CALENDAR_UNAVAILABLE")
        if calendar.id not in self.allowed_calendar_ids:
            raise PolicyError("CALENDAR_NOT_ALLOWED")

    def authorize_read(self, calendar_id: str, timezone: str) -> None:
        _require_timezone(timezone)
        if calendar_id not in self.allowed_calendar_ids:
            raise PolicyError("CALENDAR_NOT_ALLOWED")

    def authorize_change(self, calendar: CalendarRef | None, request: ChangeRequest) -> None:
        self.authorize_calendar(calendar)
        assert calendar is not None
        if calendar.id != request.calendar_id:
            raise PolicyError("CALENDAR_MISMATCH")
        if not calendar.writable:
            raise PolicyError("CALENDAR_READ_ONLY")

    def authorize_delete(
        self, event: EventRef, scope: str | None, now: datetime
    ) -> None:
        self.authorize_read(event.calendar_id, event.timezone)
        if self._is_past(event, now):
            raise PolicyError("PAST_EVENT_DELETE_DENIED")
        if scope not in {None, "this", "future"}:
            raise PolicyError("INVALID_RECURRENCE_SCOPE")

    def authorize_update(
        self, original: EventRef, request: ChangeRequest, now: datetime
    ) -> None:
        self.authorize_read(original.calendar_id, original.timezone)
        if request.action != "update" or request.event_id != original.id:
            raise PolicyError("EVENT_MISMATCH")
        if request.calendar_id != original.calendar_id:
            raise PolicyError("CALENDAR_MISMATCH")
        if self._is_past(original, now):
            raise PolicyError("PAST_EVENT_MUTATION_DENIED")

    @staticmethod
    def _is_past(event: EventRef, now: datetime) -> bool:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("now must include timezone")
        calendar_zone = ZoneInfo(event.timezone)
        return event.end.astimezone(calendar_zone) <= now.astimezone(calendar_zone)
