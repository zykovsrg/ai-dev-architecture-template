"""Immutable, validated values accepted by the Calendar policy layer."""

from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    recurring: bool = False
    recurrence_scope: Literal["this", "future"] | None = None

    @model_validator(mode="after")
    def validate_request(self) -> "ChangeRequest":
        if self.action in {"update", "delete"} and self.event_id is None:
            raise ValueError("event_id is required for update and delete")
        if self.recurring and self.recurrence_scope is None:
            raise ValueError("recurrence_scope is required for recurring events")
        if (self.start is None) != (self.end is None):
            raise ValueError("start and end must be supplied together")
        if self.start is not None and self.end is not None:
            _require_aware(self.start, "start")
            _require_aware(self.end, "end")
            if self.end <= self.start:
                raise ValueError("end must be later than start")
        return self
