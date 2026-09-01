from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from fake_backend import FakeCalendarBackend
from hub_calendar_policy.models import CalendarRef, ChangeRequest, EventRef
from hub_calendar_policy.policy import CalendarPolicy, PolicyError
from hub_calendar_policy.preview import PreviewGrantStore
from hub_calendar_policy.server import GuardedCalendarServer


ZONE = "Europe/Kirov"


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 8, 29, 12, 0, tzinfo=ZoneInfo(ZONE))


@pytest.fixture
def calendar() -> CalendarRef:
    return CalendarRef(id="calendar-1", name="Work", timezone=ZONE, writable=True)


@pytest.fixture
def event(now: datetime) -> EventRef:
    return EventRef(id="event-1", calendar_id="calendar-1", title="Planning", start=now + timedelta(hours=1), end=now + timedelta(hours=2), timezone=ZONE)


@pytest.fixture
def backend(calendar: CalendarRef, event: EventRef) -> FakeCalendarBackend:
    return FakeCalendarBackend([calendar], [event])


@pytest.fixture
def server(backend: FakeCalendarBackend, now: datetime) -> GuardedCalendarServer:
    return GuardedCalendarServer(
        backend=backend,
        policy=CalendarPolicy(allowed_calendar_ids=frozenset({"calendar-1"})),
        previews=PreviewGrantStore(clock=lambda: now, token_factory=lambda: "preview-1"),
        clock=lambda: now,
    )


def create_request(now: datetime) -> ChangeRequest:
    return ChangeRequest(action="create", calendar_id="calendar-1", title="работа/проект/новая встреча", start=now + timedelta(hours=3), end=now + timedelta(hours=4))


def test_exposes_only_safe_tools(server: GuardedCalendarServer) -> None:
    assert server.tool_names == frozenset({"calendar_status", "list_calendar_metadata", "read_events", "find_free_slots", "preview_change", "cancel_preview", "apply_change"})


@pytest.mark.asyncio
async def test_permission_denied_blocks_read(calendar: CalendarRef, event: EventRef, now: datetime) -> None:
    backend = FakeCalendarBackend([calendar], [event], permission="denied")
    server = GuardedCalendarServer(backend, CalendarPolicy(allowed_calendar_ids=frozenset({calendar.id})), PreviewGrantStore(clock=lambda: now), clock=lambda: now)
    with pytest.raises(PolicyError, match="CALENDAR_PERMISSION_DENIED"):
        await server.read_events({calendar.id}, now, now + timedelta(days=1), ZONE)


@pytest.mark.asyncio
async def test_unavailable_calendar_is_denied(server: GuardedCalendarServer, now: datetime) -> None:
    with pytest.raises(PolicyError, match="CALENDAR_UNAVAILABLE"):
        await server.read_events({"missing"}, now, now + timedelta(days=1), ZONE)


@pytest.mark.asyncio
async def test_wrong_timezone_is_denied(server: GuardedCalendarServer, now: datetime) -> None:
    with pytest.raises(ValueError, match="timezone"):
        await server.read_events({"calendar-1"}, now, now + timedelta(days=1), "Mars/Olympus")


@pytest.mark.asyncio
async def test_read_only_calendar_cannot_be_previewed(now: datetime) -> None:
    calendar = CalendarRef(id="calendar-1", name="Read only", timezone=ZONE, writable=False)
    backend = FakeCalendarBackend([calendar], [])
    server = GuardedCalendarServer(backend, CalendarPolicy(allowed_calendar_ids=frozenset({calendar.id})), PreviewGrantStore(clock=lambda: now), clock=lambda: now)
    with pytest.raises(PolicyError, match="CALENDAR_READ_ONLY"):
        await server.preview_change(create_request(now))


@pytest.mark.asyncio
async def test_create_runs_only_after_confirmation(server: GuardedCalendarServer, backend: FakeCalendarBackend, now: datetime) -> None:
    request = create_request(now)
    preview = await server.preview_change(request)
    assert backend.writes == []
    await server.apply_change(preview["preview_id"], request)
    assert backend.writes == [("create", None, None)]


@pytest.mark.asyncio
async def test_update_runs_only_after_confirmation(server: GuardedCalendarServer, backend: FakeCalendarBackend, now: datetime) -> None:
    request = ChangeRequest(action="update", calendar_id="calendar-1", event_id="event-1", title="работа/проект/изменённая задача")
    preview = await server.preview_change(request)
    await server.apply_change(preview["preview_id"], request)
    assert backend.writes == [("update", "event-1", None)]


@pytest.mark.asyncio
async def test_past_event_delete_is_rejected(server: GuardedCalendarServer, backend: FakeCalendarBackend, now: datetime) -> None:
    backend.events["event-1"] = EventRef(id="event-1", calendar_id="calendar-1", title="Past", start=now - timedelta(hours=2), end=now, timezone=ZONE)
    request = ChangeRequest(action="delete", calendar_id="calendar-1", event_id="event-1")
    with pytest.raises(PolicyError, match="PAST_EVENT_DELETE_DENIED"):
        await server.preview_change(request)


@pytest.mark.asyncio
async def test_future_event_delete_runs_after_confirmation(server: GuardedCalendarServer, backend: FakeCalendarBackend) -> None:
    request = ChangeRequest(action="delete", calendar_id="calendar-1", event_id="event-1")
    preview = await server.preview_change(request)
    await server.apply_change(preview["preview_id"], request)
    assert backend.writes == [("delete", "event-1", None)]


@pytest.mark.asyncio
@pytest.mark.parametrize("scope", ["this", "future"])
async def test_recurring_scope_is_explicit_and_preserved(server: GuardedCalendarServer, backend: FakeCalendarBackend, event: EventRef, scope: str) -> None:
    request = ChangeRequest(
        action="delete", calendar_id="calendar-1", event_id="event-1",
        recurring=True, recurrence_scope=scope, occurrence_start=event.start,
    )
    preview = await server.preview_change(request)
    assert preview["recurrence_scope"] == scope
    assert preview["occurrence_start"] == event.start.isoformat()
    await server.apply_change(preview["preview_id"], request)
    assert backend.writes == [("delete", "event-1", scope)]
    assert backend.lookups == [("event-1", event.start), ("event-1", event.start)]


@pytest.mark.asyncio
async def test_a_recurring_change_must_name_its_occurrence() -> None:
    with pytest.raises(ValueError, match="occurrence_start is required"):
        ChangeRequest(
            action="delete", calendar_id="calendar-1", event_id="event-1",
            recurring=True, recurrence_scope="this",
        )


@pytest.mark.asyncio
async def test_a_series_may_not_stand_in_for_the_named_occurrence(
    server: GuardedCalendarServer, event: EventRef
) -> None:
    # The backend answered with a different instance than the one requested.
    request = ChangeRequest(
        action="delete", calendar_id="calendar-1", event_id="event-1",
        recurring=True, recurrence_scope="this",
        occurrence_start=event.start + timedelta(days=7),
    )

    with pytest.raises(PolicyError, match="EVENT_UNAVAILABLE"):
        await server.preview_change(request)


@pytest.mark.asyncio
async def test_cancelled_preview_never_writes(server: GuardedCalendarServer, backend: FakeCalendarBackend, now: datetime) -> None:
    request = create_request(now)
    preview = await server.preview_change(request)
    await server.cancel_preview(preview["preview_id"])
    with pytest.raises(Exception, match="PREVIEW_CANCELLED"):
        await server.apply_change(preview["preview_id"], request)
    assert backend.writes == []
