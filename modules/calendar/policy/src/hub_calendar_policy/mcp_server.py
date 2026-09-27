"""stdio MCP registration for the seven guarded Calendar tools only."""

from datetime import datetime

from fastmcp import FastMCP

from .models import ChangeRequest
from .server import GuardedCalendarServer


def build_mcp(guarded: GuardedCalendarServer) -> FastMCP:
    mcp = FastMCP(
        "Personal AI Hub Apple Calendar",
        instructions=(
            "Read only explicitly selected calendars. Every change requires a fresh "
            "preview and its one-time confirmation."
        ),
    )

    @mcp.tool(name="calendar_status")
    async def calendar_status() -> dict[str, object]:
        return await guarded.calendar_status()

    @mcp.tool(name="list_calendar_metadata")
    async def list_calendar_metadata() -> dict[str, object]:
        return await guarded.list_calendar_metadata()

    @mcp.tool(name="read_events")
    async def read_events(calendar_ids: list[str], start: str, end: str, timezone: str) -> dict[str, object]:
        return await guarded.read_events(set(calendar_ids), _parse_datetime(start), _parse_datetime(end), timezone)

    @mcp.tool(name="find_free_slots")
    async def find_free_slots(calendar_ids: list[str], start: str, end: str, timezone: str) -> dict[str, object]:
        return await guarded.find_free_slots(set(calendar_ids), _parse_datetime(start), _parse_datetime(end), timezone)

    @mcp.tool(name="preview_change")
    async def preview_change(request: ChangeRequest) -> dict[str, object]:
        return await guarded.preview_change(request)

    @mcp.tool(name="cancel_preview")
    async def cancel_preview(preview_id: str) -> dict[str, str]:
        return await guarded.cancel_preview(preview_id)

    @mcp.tool(name="apply_change")
    async def apply_change(preview_id: str, request: ChangeRequest) -> dict[str, object]:
        return await guarded.apply_change(preview_id, request)

    return mcp


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("datetime must include timezone")
    return parsed
