import asyncio
import json
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from hub_calendar_policy.eventkit_backend import EventKitBackend
from hub_calendar_policy.models import ChangeRequest, EventRef


DAY = datetime.fromisoformat("2026-09-04T00:00:00+03:00")
NEXT_DAY = datetime.fromisoformat("2026-09-05T00:00:00+03:00")
START = datetime.fromisoformat("2026-09-04T09:00:00+03:00")
END = datetime.fromisoformat("2026-09-04T10:00:00+03:00")
TITLE = "дела/поездка в киров/забрать бритву"


def create(**overrides: object) -> ChangeRequest:
    fields: dict[str, object] = {
        "action": "create",
        "calendar_id": "calendar",
        "title": TITLE,
        "start": DAY,
        "end": NEXT_DAY,
        "all_day": True,
    }
    fields.update(overrides)
    return ChangeRequest(**fields)


def test_all_day_accepts_one_whole_day() -> None:
    request = create()

    assert request.all_day is True
    assert request.start == DAY
    assert request.end == NEXT_DAY


@pytest.mark.parametrize("field", ["start", "end"])
def test_all_day_rejects_times_that_are_not_midnight(field: str) -> None:
    offset = {"start": {"start": START, "end": NEXT_DAY}, "end": {"end": END}}[field]

    with pytest.raises(ValidationError, match="must be midnight in its timezone"):
        create(**offset)


def test_all_day_requires_a_range() -> None:
    with pytest.raises(ValidationError, match="create requires title, start and end"):
        create(start=None, end=None)


def test_timed_event_still_accepts_working_hours() -> None:
    request = create(start=START, end=END, all_day=False)

    assert request.all_day is False
    assert request.start == START


def test_change_request_defaults_to_a_timed_event() -> None:
    request = ChangeRequest(action="create", calendar_id="calendar", title=TITLE, start=START, end=END)

    assert request.all_day is False


def test_event_ref_reads_all_day_from_the_bridge() -> None:
    event = EventRef.model_validate({
        "id": "event", "calendar_id": "calendar", "title": TITLE,
        "start": DAY.isoformat(), "end": NEXT_DAY.isoformat(),
        "timezone": "Europe/Moscow", "all_day": True,
    })

    assert event.all_day is True


def test_event_ref_without_all_day_is_a_timed_event() -> None:
    event = EventRef.model_validate({
        "id": "event", "calendar_id": "calendar", "title": TITLE,
        "start": START.isoformat(), "end": END.isoformat(), "timezone": "Europe/Moscow",
    })

    assert event.all_day is False


class _RecordingBackend(EventKitBackend):
    """Captures the payload that would reach the bridge, and calls nothing."""

    def __init__(self) -> None:
        super().__init__(Path("/nonexistent/bridge"))
        self.sent: list[tuple[str, dict[str, object] | None]] = []

    async def _call(self, operation: str, payload: dict[str, object] | None) -> object:
        self.sent.append((operation, payload))
        return {
            "id": "event", "calendar_id": "calendar", "title": TITLE,
            "start": DAY.isoformat(), "end": NEXT_DAY.isoformat(),
            "timezone": "Europe/Moscow", "all_day": True,
        }


def test_create_payload_carries_all_day_to_the_bridge() -> None:
    backend = _RecordingBackend()

    event = asyncio.run(backend.create(create()))

    operation, payload = backend.sent[0]
    assert operation == "create"
    assert payload is not None and payload["all_day"] is True
    assert event.all_day is True


def test_update_payload_keeps_all_day_false_instead_of_dropping_it() -> None:
    backend = _RecordingBackend()
    existing = EventRef(
        id="event", calendar_id="calendar", title=TITLE,
        start=START, end=END, timezone="Europe/Moscow",
    )
    request = ChangeRequest(
        action="update", calendar_id="calendar", event_id="event",
        title=TITLE, start=START, end=END, all_day=False,
    )

    asyncio.run(backend.update(existing, request, None))

    _, payload = backend.sent[0]
    assert payload is not None and payload["all_day"] is False


def test_preview_hash_separates_all_day_from_a_timed_change() -> None:
    timed = json.dumps(create(start=START, end=END, all_day=False).model_dump(mode="json"), sort_keys=True)
    whole_day = json.dumps(create().model_dump(mode="json"), sort_keys=True)

    assert timed != whole_day


def test_preview_shows_that_the_change_is_all_day() -> None:
    from hub_calendar_policy.models import CalendarRef
    from hub_calendar_policy.server import GuardedCalendarServer

    calendar = CalendarRef(id="calendar", name="Личный", timezone="Europe/Moscow", writable=True)

    response = GuardedCalendarServer._preview_response(
        "preview", NEXT_DAY, create(), calendar, None
    )

    assert response["all_day"] is True
