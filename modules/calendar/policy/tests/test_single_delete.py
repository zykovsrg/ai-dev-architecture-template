import asyncio
from datetime import datetime

import pytest

from hub_calendar_policy.models import CalendarRef, ChangeRequest, EventRef
from hub_calendar_policy.policy import CalendarPolicy, PolicyError
from hub_calendar_policy.preview import PreviewGrantStore
from hub_calendar_policy.server import GuardedCalendarServer


CALENDAR = "calendar"
START = datetime.fromisoformat("2026-10-04T07:15:00+03:00")
END = datetime.fromisoformat("2026-10-04T07:30:00+03:00")


def event(*, recurring: bool) -> EventRef:
    return EventRef(
        id="event", calendar_id=CALENDAR, title="дела/спорт", start=START, end=END,
        timezone="Europe/Moscow", recurring=recurring,
    )


class _Backend:
    """Holds one event; `leftovers` lists what each delete leaves behind."""

    def __init__(self, current: EventRef | None, leftovers: list[EventRef | None]) -> None:
        self.current = current
        self.leftovers = leftovers
        self.deletes: list[tuple[bool, str | None]] = []

    async def permission_status(self) -> str:
        return "granted"

    async def list_calendars(self) -> list[CalendarRef]:
        return [CalendarRef(id=CALENDAR, name="calendar", writable=True, timezone="Europe/Moscow")]

    async def get_event(self, event_id: str, occurrence_start: datetime | None = None) -> EventRef | None:
        return self.current

    async def delete(self, target: EventRef, scope: str | None) -> None:
        self.deletes.append((target.recurring, scope))
        self.current = self.leftovers.pop(0)


def server(backend: _Backend) -> GuardedCalendarServer:
    return GuardedCalendarServer(
        backend,  # type: ignore[arg-type]
        CalendarPolicy(allowed_calendar_ids=frozenset({CALENDAR})),
        PreviewGrantStore(clock=lambda: START),
    )


def delete(**overrides: object) -> ChangeRequest:
    fields: dict[str, object] = {"action": "delete", "calendar_id": CALENDAR, "event_id": "event"}
    fields.update(overrides)
    return ChangeRequest(**fields)


async def apply(backend: _Backend, request: ChangeRequest) -> dict[str, object]:
    guarded = server(backend)
    preview = await guarded.preview_change(request)
    return await guarded.apply_change(str(preview["preview_id"]), request)


def occurrence(**overrides: object) -> ChangeRequest:
    return delete(recurring=True, recurrence_scope="this", occurrence_start=START, **overrides)


def test_series_delete_is_refused() -> None:
    backend = _Backend(event(recurring=True), [])
    request = delete(recurring=True, recurrence_scope="future", occurrence_start=START)

    with pytest.raises(PolicyError, match="SERIES_DELETE_FORBIDDEN"):
        asyncio.run(server(backend).preview_change(request))


def test_recurring_event_needs_the_this_scope() -> None:
    backend = _Backend(event(recurring=True), [])

    with pytest.raises(PolicyError, match="OCCURRENCE_REQUIRED"):
        asyncio.run(server(backend).preview_change(delete()))


def test_occurrence_delete_succeeds_when_it_is_gone() -> None:
    backend = _Backend(event(recurring=True), [None])

    result = asyncio.run(apply(backend, occurrence()))

    assert result["result"] == "applied"
    assert backend.deletes == [(True, "this")]


def test_last_occurrence_left_standalone_is_removed_as_a_single_event() -> None:
    backend = _Backend(event(recurring=True), [event(recurring=False), None])

    result = asyncio.run(apply(backend, occurrence()))

    assert result["result"] == "applied"
    assert backend.deletes == [(True, "this"), (False, None)]


def test_delete_that_leaves_the_event_reports_failure() -> None:
    backend = _Backend(event(recurring=True), [event(recurring=True)])

    with pytest.raises(PolicyError, match="DELETE_NOT_APPLIED"):
        asyncio.run(apply(backend, occurrence()))
    assert backend.deletes == [(True, "this")]
