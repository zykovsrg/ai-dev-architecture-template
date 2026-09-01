from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from hub_calendar_policy.models import CalendarRef, ChangeRequest, EventRef
from hub_calendar_policy.policy import CalendarPolicy, PolicyError


ZONE = "Europe/Kirov"


@pytest.fixture
def clock() -> datetime:
    return datetime(2026, 8, 29, 12, 0, tzinfo=ZoneInfo(ZONE))


@pytest.fixture
def allowed_calendar() -> CalendarRef:
    return CalendarRef(id="calendar-1", name="Work", timezone=ZONE, writable=True)


@pytest.fixture
def policy() -> CalendarPolicy:
    return CalendarPolicy(allowed_calendar_ids=frozenset({"calendar-1"}))


@pytest.fixture
def past_event(clock: datetime) -> EventRef:
    return EventRef(
        id="event-past",
        calendar_id="calendar-1",
        title="Finished",
        start=clock - timedelta(hours=2),
        end=clock,
        timezone=ZONE,
    )


def test_empty_allowlist_denies_read() -> None:
    policy = CalendarPolicy(allowed_calendar_ids=frozenset())

    with pytest.raises(PolicyError, match="CALENDAR_NOT_ALLOWED"):
        policy.authorize_read("calendar-1", ZONE)


def test_unavailable_calendar_is_denied(policy: CalendarPolicy) -> None:
    with pytest.raises(PolicyError, match="CALENDAR_UNAVAILABLE"):
        policy.authorize_calendar(None)


def test_read_only_calendar_is_denied_for_change(policy: CalendarPolicy) -> None:
    calendar = CalendarRef(id="calendar-1", name="Read only", timezone=ZONE, writable=False)
    request = ChangeRequest(
        action="create", calendar_id="calendar-1", title="работа/проект/ревью",
        start=datetime(2026, 8, 29, 10, 0, tzinfo=ZoneInfo(ZONE)),
        end=datetime(2026, 8, 29, 11, 0, tzinfo=ZoneInfo(ZONE)),
    )

    with pytest.raises(PolicyError, match="CALENDAR_READ_ONLY"):
        policy.authorize_change(calendar, request)


def test_unauthorized_calendar_is_denied(allowed_calendar: CalendarRef) -> None:
    policy = CalendarPolicy(allowed_calendar_ids=frozenset({"calendar-2"}))

    with pytest.raises(PolicyError, match="CALENDAR_NOT_ALLOWED"):
        policy.authorize_calendar(allowed_calendar)


def test_invalid_timezone_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone"):
        CalendarRef(id="calendar-1", name="Work", timezone="Mars/Olympus", writable=True)


def test_allowed_read_is_returned(policy: CalendarPolicy, allowed_calendar: CalendarRef) -> None:
    assert policy.authorize_read(allowed_calendar.id, allowed_calendar.timezone) is None


def test_past_delete_is_allowed_for_an_authorized_calendar(
    clock: datetime, policy: CalendarPolicy, past_event: EventRef
) -> None:
    assert policy.authorize_delete(past_event, scope=None) is None


def test_future_delete_is_allowed(clock: datetime, policy: CalendarPolicy) -> None:
    event = EventRef(
        id="event-future",
        calendar_id="calendar-1",
        title="Planned",
        start=clock + timedelta(hours=1),
        end=clock + timedelta(hours=2),
        timezone=ZONE,
    )

    assert policy.authorize_delete(event, scope=None) is None


def test_moving_a_past_event_is_allowed_for_an_authorized_calendar(
    clock: datetime, policy: CalendarPolicy, past_event: EventRef
) -> None:
    request = ChangeRequest(
        action="update",
        calendar_id="calendar-1",
        event_id=past_event.id,
        start=clock + timedelta(days=1),
        end=clock + timedelta(days=1, hours=1),
    )

    assert policy.authorize_update(past_event, request) is None


def test_recurrence_scope_must_be_explicit_for_series() -> None:
    with pytest.raises(ValueError, match="recurrence_scope"):
        ChangeRequest(
            action="delete",
            calendar_id="calendar-1",
            event_id="event-series",
            recurring=True,
        )
