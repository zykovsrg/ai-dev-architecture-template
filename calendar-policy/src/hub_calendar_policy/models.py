"""Immutable, validated values accepted by the Calendar policy layer."""

import re
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, model_validator


_CATEGORY_PATTERN = re.compile(r"^[a-zа-яё0-9-]+$")


def _require_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, TypeError) as error:
        raise ValueError("timezone must be a valid IANA timezone") from error
    return value


def _require_aware(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include timezone")
    return value


def _require_midnight(value: datetime, field_name: str) -> datetime:
    # An all-day event is a whole number of days in its own timezone, so both
    # bounds must sit on midnight there; anything else is a timed event.
    if (value.hour, value.minute, value.second, value.microsecond) != (0, 0, 0, 0):
        raise ValueError(f"{field_name} must be midnight in its timezone for an all-day event")
    return value


class CalendarRef(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    timezone: str
    writable: bool

    @model_validator(mode="after")
    def validate_timezone(self) -> "CalendarRef":
        _require_timezone(self.timezone)
        return self


class EventRef(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    id: str = Field(min_length=1)
    calendar_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    start: datetime
    end: datetime
    timezone: str
    all_day: bool = False

    @model_validator(mode="after")
    def validate_times(self) -> "EventRef":
        _require_timezone(self.timezone)
        _require_aware(self.start, "start")
        _require_aware(self.end, "end")
        if self.end <= self.start:
            raise ValueError("end must be later than start")
        return self


class ChangeRequest(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    action: Literal["create", "update", "delete"]
    calendar_id: str = Field(min_length=1)
    title: str | None = Field(default=None, min_length=1)
    event_id: str | None = Field(default=None, min_length=1)
    start: datetime | None = None
    end: datetime | None = None
    all_day: bool = False
    recurring: bool = False
    recurrence_scope: Literal["this", "future"] | None = None
    occurrence_start: datetime | None = None

    @model_validator(mode="after")
    def validate_request(self) -> "ChangeRequest":
        if self.title is not None:
            parts = self.title.split("/")
            if (
                len(parts) != 3
                or any(not part or part != part.strip() for part in parts)
                or self.title != self.title.lower()
                or not _CATEGORY_PATTERN.fullmatch(parts[0])
            ):
                raise ValueError("title must use lowercase category/project/task")
        if self.action in {"update", "delete"} and self.event_id is None:
            raise ValueError("event_id is required for update and delete")
        if self.action == "create" and (self.title is None or self.start is None):
            raise ValueError("create requires title, start and end")
        if self.recurring and self.recurrence_scope is None:
            raise ValueError("recurrence_scope is required for recurring events")
        # Every occurrence of a series shares one identifier, so a recurring
        # write must also name which occurrence it starts from.
        if self.recurring and self.action in {"update", "delete"}:
            if self.occurrence_start is None:
                raise ValueError("occurrence_start is required for recurring changes")
            _require_aware(self.occurrence_start, "occurrence_start")
        if (self.start is None) != (self.end is None):
            raise ValueError("start and end must be supplied together")
        if self.start is not None and self.end is not None:
            _require_aware(self.start, "start")
            _require_aware(self.end, "end")
            if self.end <= self.start:
                raise ValueError("end must be later than start")
        if self.all_day:
            if self.start is None or self.end is None:
                raise ValueError("all-day changes require start and end")
            _require_midnight(self.start, "start")
            _require_midnight(self.end, "end")
        return self
