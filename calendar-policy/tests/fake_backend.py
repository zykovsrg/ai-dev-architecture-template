from datetime import datetime, timedelta

from hub_calendar_policy.models import CalendarRef, ChangeRequest, EventRef


class FakeCalendarBackend:
    def __init__(self, calendars: list[CalendarRef], events: list[EventRef], permission: str = "granted") -> None:
        self.calendars = {calendar.id: calendar for calendar in calendars}
        self.events = {event.id: event for event in events}
        self.permission = permission
        self.writes: list[tuple[str, str | None, str | None]] = []

    async def permission_status(self) -> str:
        return self.permission

    async def list_calendars(self) -> list[CalendarRef]:
        return list(self.calendars.values())

    async def read_events(self, calendar_ids: set[str], start: datetime, end: datetime) -> list[EventRef]:
        return [
            event for event in self.events.values()
            if event.calendar_id in calendar_ids and event.start < end and event.end > start
        ]

    async def get_event(self, event_id: str) -> EventRef | None:
        return self.events.get(event_id)

    async def create(self, request: ChangeRequest) -> EventRef:
        assert request.start is not None and request.end is not None and request.title is not None
        event = EventRef(
            id=f"created-{len(self.writes) + 1}", calendar_id=request.calendar_id,
            title=request.title, start=request.start, end=request.end,
            timezone=self.calendars[request.calendar_id].timezone,
        )
        self.events[event.id] = event
        self.writes.append(("create", None, None))
        return event

    async def update(self, event: EventRef, request: ChangeRequest, scope: str | None) -> EventRef:
        updated = event.model_copy(update={
            "title": request.title or event.title,
            "start": request.start or event.start,
            "end": request.end or event.end,
        })
        self.events[event.id] = updated
        self.writes.append(("update", event.id, scope))
        return updated

    async def delete(self, event: EventRef, scope: str | None) -> None:
        del self.events[event.id]
        self.writes.append(("delete", event.id, scope))

    async def free_slots(self, calendar_ids: set[str], start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
        events = await self.read_events(calendar_ids, start, end)
        cursor = start
        slots: list[tuple[datetime, datetime]] = []
        for event in sorted(events, key=lambda item: item.start):
            if event.start > cursor:
                slots.append((cursor, event.start))
            cursor = max(cursor, event.end)
        if cursor < end:
            slots.append((cursor, end))
        return slots
