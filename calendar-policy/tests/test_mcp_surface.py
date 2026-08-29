from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from hub_calendar_policy.models import CalendarRef
from hub_calendar_policy.policy import CalendarPolicy
from hub_calendar_policy.preview import PreviewGrantStore
from hub_calendar_policy.mcp_server import build_mcp
from hub_calendar_policy.server import GuardedCalendarServer
from fake_backend import FakeCalendarBackend


@pytest.mark.asyncio
async def test_mcp_exposes_exactly_the_guarded_tool_set() -> None:
    now = datetime(2026, 8, 29, 12, 0, tzinfo=ZoneInfo("Europe/Kirov"))
    calendar = CalendarRef(id="calendar-1", name="Work", timezone="Europe/Kirov", writable=True)
    guarded = GuardedCalendarServer(
        FakeCalendarBackend([calendar], []),
        CalendarPolicy(allowed_calendar_ids=frozenset({calendar.id})),
        PreviewGrantStore(clock=lambda: now),
        clock=lambda: now,
    )

    mcp = build_mcp(guarded)

    assert {tool.name for tool in await mcp.list_tools()} == guarded.tool_names
