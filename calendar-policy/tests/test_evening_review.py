import json
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from fake_backend import FakeCalendarBackend
from hub_calendar_policy.models import CalendarRef, EventRef
from hub_calendar_policy.policy import CalendarPolicy, PolicyError
from hub_calendar_policy.preview import PreviewGrantStore
from hub_calendar_policy.server import GuardedCalendarServer


ZONE = "Europe/Kirov"


def observation_id(day: str, ordinal: int, text: str) -> str:
    return sha256(f"{day}\0{ordinal}\0{text}".encode("utf-8")).hexdigest()


def write_friction_state(tmp_path: Path, day: str, entries: dict[str, object], *, format_version: int = 1) -> None:
    state = tmp_path / f"ai/tmp/workflow-friction/{day}.state.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps({"format": format_version, "entries": entries}), encoding="utf-8")


def make_server(hub: Path, permission: str = "granted") -> GuardedCalendarServer:
    start = datetime(2026, 9, 10, 9, 0, tzinfo=ZoneInfo(ZONE))
    calendar = CalendarRef(id="calendar-1", name="Work", timezone=ZONE, writable=True)
    event = EventRef(
        id="event-1", calendar_id=calendar.id, title="Planning", start=start,
        end=start + timedelta(hours=1), timezone=ZONE,
    )
    return GuardedCalendarServer(
        FakeCalendarBackend([calendar], [event], permission=permission),
        CalendarPolicy(allowed_calendar_ids=frozenset({calendar.id})),
        PreviewGrantStore(clock=lambda: start),
        hub_root=hub,
    )


@pytest.mark.asyncio
async def test_prepare_evening_review_returns_snapshot_and_pending_friction(tmp_path: Path) -> None:
    source = tmp_path / "ai/tmp/workflow-friction/2026-09-10.txt"
    source.parent.mkdir(parents=True)
    source.write_text("calendar overlap\n", encoding="utf-8")

    result = await make_server(tmp_path).prepare_evening_review("2026-09-10", ZONE)

    assert [event["title"] for event in result["events"]] == ["Planning"]
    assert Path(result["snapshot"]).is_file()
    assert result["prior_snapshots"] == []
    assert result["pending_friction"][0]["text"] == "calendar overlap"


@pytest.mark.asyncio
@pytest.mark.parametrize("disposition", ["accepted", "rejected"])
async def test_prepare_evening_review_excludes_resolved_friction(tmp_path: Path, disposition: str) -> None:
    day = "2026-09-10"
    text = "calendar overlap"
    source = tmp_path / f"ai/tmp/workflow-friction/{day}.txt"
    source.parent.mkdir(parents=True)
    source.write_text(f"{text}\n", encoding="utf-8")
    identifier = observation_id(day, 1, text)
    write_friction_state(tmp_path, day, {identifier: {"disposition": disposition, "source_sha256": "fixture"}})

    result = await make_server(tmp_path).prepare_evening_review(day, ZONE)

    assert result["pending_friction"] == []


@pytest.mark.asyncio
async def test_prepare_evening_review_keeps_other_unresolved_friction(tmp_path: Path) -> None:
    day = "2026-09-10"
    first = "calendar overlap"
    second = "late handoff"
    source = tmp_path / f"ai/tmp/workflow-friction/{day}.txt"
    source.parent.mkdir(parents=True)
    source.write_text(f"{first}\n{second}\n", encoding="utf-8")
    first_id = observation_id(day, 1, first)
    write_friction_state(tmp_path, day, {first_id: {"disposition": "accepted", "source_sha256": "fixture"}})

    result = await make_server(tmp_path).prepare_evening_review(day, ZONE)

    assert [item["text"] for item in result["pending_friction"]] == [second]
    assert result["pending_friction"][0]["id"] == observation_id(day, 2, second)


@pytest.mark.asyncio
async def test_prepare_evening_review_rejects_invalid_friction_state(tmp_path: Path) -> None:
    day = "2026-09-10"
    source = tmp_path / f"ai/tmp/workflow-friction/{day}.txt"
    source.parent.mkdir(parents=True)
    source.write_text("calendar overlap\n", encoding="utf-8")
    write_friction_state(tmp_path, day, {}, format_version=2)

    with pytest.raises(ValueError, match="invalid workflow friction state"):
        await make_server(tmp_path).prepare_evening_review(day, ZONE)


@pytest.mark.asyncio
async def test_prepare_evening_review_does_not_write_snapshot_after_permission_failure(tmp_path: Path) -> None:
    with pytest.raises(PolicyError, match="CALENDAR_PERMISSION_DENIED"):
        await make_server(tmp_path, permission="denied").prepare_evening_review("2026-09-10", ZONE)

    assert not (tmp_path / "ai/tmp/calendar-snapshots").exists()
