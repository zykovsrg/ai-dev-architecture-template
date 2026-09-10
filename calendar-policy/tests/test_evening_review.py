from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from fake_backend import FakeCalendarBackend
from hub_calendar_policy.models import CalendarRef, EventRef
from hub_calendar_policy.policy import CalendarPolicy, PolicyError
from hub_calendar_policy.preview import PreviewGrantStore
from hub_calendar_policy.server import GuardedCalendarServer


ZONE = "Europe/Kirov"


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
async def test_prepare_evening_review_does_not_write_snapshot_after_permission_failure(tmp_path: Path) -> None:
    with pytest.raises(PolicyError, match="CALENDAR_PERMISSION_DENIED"):
        await make_server(tmp_path, permission="denied").prepare_evening_review("2026-09-10", ZONE)

    assert not (tmp_path / "ai/tmp/calendar-snapshots").exists()
