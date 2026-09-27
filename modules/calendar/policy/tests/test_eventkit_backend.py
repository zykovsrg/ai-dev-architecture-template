"""Adapter tests that drive a stub bridge process and never touch Calendar."""

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from hub_calendar_policy.backend import CalendarBackend
from hub_calendar_policy.eventkit_backend import BridgeError, EventKitBackend
from hub_calendar_policy.models import ChangeRequest, EventRef

ZONE = ZoneInfo("Europe/Kirov")

STUB = '''
import json, sys
from pathlib import Path

operation = sys.argv[1]
payload = sys.stdin.read()
Path(LOG).write_text(
    (Path(LOG).read_text() if Path(LOG).exists() else "")
    + json.dumps({"operation": operation, "payload": payload}) + "\\n"
)
sys.stdout.write(OUTPUT)
sys.exit(EXIT)
'''


def make_bridge(tmp_path: Path, output: str, exit_code: int = 0) -> tuple[EventKitBackend, Path]:
    log = tmp_path / "calls.log"
    script = tmp_path / "stub_bridge.py"
    script.write_text(
        f"LOG = {str(log)!r}\nOUTPUT = {output!r}\nEXIT = {exit_code}\n" + STUB,
        encoding="utf-8",
    )
    return EventKitBackend(script, interpreter=(sys.executable,)), log


def envelope(data: object) -> str:
    return json.dumps({"ok": True, "data": data})


def calls(log: Path) -> list[dict]:
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text().splitlines() if line]


def event_payload(event_id: str = "event-1", title: str = "Standup") -> dict:
    return {
        "id": event_id, "calendar_id": "calendar-1", "title": title,
        "start": "2026-08-29T10:00:00+03:00", "end": "2026-08-29T11:00:00+03:00",
        "timezone": "Europe/Kirov",
    }


def test_the_bridge_is_run_directly_by_default(tmp_path: Path) -> None:
    backend = EventKitBackend(tmp_path / "HubCalendarBridge")

    assert backend._interpreter == ()


def test_adapter_satisfies_the_backend_contract(tmp_path: Path) -> None:
    backend, _ = make_bridge(tmp_path, envelope(None))

    assert isinstance(backend, CalendarBackend)


@pytest.mark.asyncio
async def test_status_is_read_without_sending_a_payload(tmp_path: Path) -> None:
    backend, log = make_bridge(tmp_path, envelope({"permission": "not_determined"}))

    assert await backend.permission_status() == "not_determined"
    assert calls(log) == [{"operation": "status", "payload": "{}"}]


@pytest.mark.asyncio
async def test_calendars_are_validated_into_refs(tmp_path: Path) -> None:
    backend, _ = make_bridge(tmp_path, envelope(
        [{"id": "calendar-1", "name": "Work", "timezone": "Europe/Kirov", "writable": True}]
    ))

    calendars = await backend.list_calendars()

    assert [(item.id, item.writable) for item in calendars] == [("calendar-1", True)]


@pytest.mark.asyncio
async def test_read_events_sends_sorted_ids_and_exact_timestamps(tmp_path: Path) -> None:
    backend, log = make_bridge(tmp_path, envelope([event_payload()]))
    start = datetime(2026, 8, 29, 9, 0, 0, 500000, tzinfo=ZONE)
    end = datetime(2026, 8, 29, 18, 0, tzinfo=ZONE)

    events = await backend.read_events({"calendar-2", "calendar-1"}, start, end)

    payload = json.loads(calls(log)[0]["payload"])
    assert payload["calendar_ids"] == ["calendar-1", "calendar-2"]
    assert payload["start"] == "2026-08-29T09:00:00.500000+03:00"
    assert [item.id for item in events] == ["event-1"]


@pytest.mark.asyncio
async def test_missing_event_is_reported_as_none(tmp_path: Path) -> None:
    backend, _ = make_bridge(tmp_path, envelope(None))

    assert await backend.get_event("event-1") is None


@pytest.mark.asyncio
async def test_free_slots_are_derived_from_one_event_read(tmp_path: Path) -> None:
    backend, log = make_bridge(tmp_path, envelope([event_payload()]))
    start = datetime(2026, 8, 29, 9, 0, tzinfo=ZONE)
    end = datetime(2026, 8, 29, 12, 0, tzinfo=ZONE)

    slots = await backend.free_slots({"calendar-1"}, start, end)

    assert [call["operation"] for call in calls(log)] == ["events"]
    assert slots == [
        (start, datetime(2026, 8, 29, 10, 0, tzinfo=ZONE)),
        (datetime(2026, 8, 29, 11, 0, tzinfo=ZONE), end),
    ]


@pytest.mark.asyncio
async def test_create_returns_the_event_reported_by_the_bridge(tmp_path: Path) -> None:
    backend, log = make_bridge(tmp_path, envelope(event_payload("created-1", "работа/проект/ревью")))
    request = ChangeRequest(
        action="create", calendar_id="calendar-1", title="работа/проект/ревью",
        start=datetime(2026, 8, 29, 10, 0, tzinfo=ZONE),
        end=datetime(2026, 8, 29, 11, 0, tzinfo=ZONE),
    )

    created = await backend.create(request)

    assert (created.id, created.title) == ("created-1", "работа/проект/ревью")
    assert json.loads(calls(log)[0]["payload"])["title"] == "работа/проект/ревью"


@pytest.mark.asyncio
async def test_update_uses_a_single_bridge_call_and_returns_its_event(tmp_path: Path) -> None:
    backend, log = make_bridge(tmp_path, envelope(event_payload(title="работа/проект/новое имя")))
    original = EventRef.model_validate(event_payload())
    request = ChangeRequest(
        action="update", calendar_id="calendar-1", event_id="event-1", title="работа/проект/новое имя",
    )

    updated = await backend.update(original, request, None)

    assert [call["operation"] for call in calls(log)] == ["update"]
    assert updated.title == "работа/проект/новое имя"
    payload = json.loads(calls(log)[0]["payload"])
    assert payload["event_id"] == "event-1"
    assert payload["calendar_id"] == "calendar-1"
    assert payload["recurrence_scope"] is None
    assert "occurrence_start" not in payload


@pytest.mark.asyncio
async def test_delete_identifies_the_event_and_its_calendar(tmp_path: Path) -> None:
    backend, log = make_bridge(tmp_path, envelope(event_payload()))
    original = EventRef.model_validate(event_payload())

    assert await backend.delete(original, None) is None

    payload = json.loads(calls(log)[0]["payload"])
    assert payload == {
        "event_id": "event-1", "calendar_id": "calendar-1", "recurrence_scope": None,
    }


@pytest.mark.asyncio
async def test_recurring_delete_passes_its_occurrence_to_the_bridge(tmp_path: Path) -> None:
    backend, log = make_bridge(tmp_path, envelope(event_payload()))
    original = EventRef.model_validate(event_payload())

    assert await backend.delete(original, "this") is None

    payload = json.loads(calls(log)[0]["payload"])
    assert payload["occurrence_start"] == "2026-08-29T10:00:00+03:00"


@pytest.mark.asyncio
async def test_a_named_occurrence_is_passed_to_the_bridge(tmp_path: Path) -> None:
    backend, log = make_bridge(tmp_path, envelope(event_payload()))
    occurrence = datetime(2026, 9, 5, 10, 0, tzinfo=ZONE)

    await backend.get_event("event-1", occurrence)

    payload = json.loads(calls(log)[0]["payload"])
    assert payload == {"event_id": "event-1", "occurrence_start": "2026-09-05T10:00:00+03:00"}


@pytest.mark.asyncio
async def test_an_unnamed_occurrence_leaves_the_lookup_alone(tmp_path: Path) -> None:
    backend, log = make_bridge(tmp_path, envelope(event_payload()))

    await backend.get_event("event-1")

    assert json.loads(calls(log)[0]["payload"]) == {"event_id": "event-1"}


@pytest.mark.asyncio
async def test_known_bridge_denial_keeps_its_own_code(tmp_path: Path) -> None:
    backend, _ = make_bridge(tmp_path, json.dumps({"ok": False, "error": "CALENDAR_ACCESS_DENIED"}))

    with pytest.raises(BridgeError, match="CALENDAR_ACCESS_DENIED"):
        await backend.list_calendars()


@pytest.mark.asyncio
async def test_unknown_bridge_error_is_reduced_to_a_generic_code(tmp_path: Path) -> None:
    backend, _ = make_bridge(tmp_path, json.dumps({"ok": False, "error": "something odd"}))

    with pytest.raises(BridgeError, match="EVENTKIT_BRIDGE_FAILED"):
        await backend.list_calendars()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("output", "exit_code"),
    [("not json", 0), (json.dumps({"data": []}), 0), (envelope([]), 1), ("", 0)],
)
async def test_unusable_bridge_output_fails_closed(tmp_path: Path, output: str, exit_code: int) -> None:
    backend, _ = make_bridge(tmp_path, output, exit_code)

    with pytest.raises(BridgeError, match="EVENTKIT_BRIDGE_FAILED"):
        await backend.list_calendars()


@pytest.mark.asyncio
async def test_non_list_payload_where_a_list_is_required_fails_closed(tmp_path: Path) -> None:
    backend, _ = make_bridge(tmp_path, envelope({"id": "calendar-1"}))

    with pytest.raises(BridgeError, match="EVENTKIT_BRIDGE_FAILED"):
        await backend.list_calendars()


@pytest.mark.asyncio
async def test_a_missing_bridge_file_is_refused_before_any_process_starts(tmp_path: Path) -> None:
    backend = EventKitBackend(tmp_path / "absent.swift", interpreter=(sys.executable,))

    with pytest.raises(BridgeError, match="LOCAL_EVENTKIT_BRIDGE_MISSING"):
        await backend.permission_status()


@pytest.mark.asyncio
async def test_a_missing_interpreter_is_reported_as_an_unavailable_bridge(tmp_path: Path) -> None:
    backend, _ = make_bridge(tmp_path, envelope(None))
    backend = EventKitBackend(
        tmp_path / "stub_bridge.py", interpreter=(str(tmp_path / "no-such-interpreter"),)
    )

    with pytest.raises(BridgeError, match="EVENTKIT_BRIDGE_UNAVAILABLE"):
        await backend.permission_status()
