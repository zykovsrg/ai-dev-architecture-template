from datetime import datetime

import pytest
from pydantic import ValidationError

from hub_calendar_policy.models import ChangeRequest


START = datetime.fromisoformat("2026-09-01T09:00:00+03:00")
END = datetime.fromisoformat("2026-09-01T10:00:00+03:00")


def create(title: str) -> ChangeRequest:
    return ChangeRequest(
        action="create",
        calendar_id="calendar",
        title=title,
        start=START,
        end=END,
    )


@pytest.mark.parametrize(
    "title",
    [
        "дела/поездка в киров/забрать бритву",
        "новая-категория/проект 2/сделать задачу",
    ],
)
def test_create_accepts_standard_title(title: str) -> None:
    assert create(title).title == title


@pytest.mark.parametrize(
    "title",
    [
        "дела/забрать бритву",
        "дела/проект/задача/ещё",
        "дела/Поездка/забрать бритву",
        "дела /проект/задача",
        "дела/проект /задача",
    ],
)
def test_create_rejects_non_standard_title(title: str) -> None:
    with pytest.raises(
        ValidationError, match="title must use lowercase category/project/task"
    ):
        create(title)


def test_update_without_title_remains_valid() -> None:
    request = ChangeRequest(action="update", calendar_id="calendar", event_id="event")

    assert request.title is None


def test_update_rejects_non_standard_replacement_title() -> None:
    with pytest.raises(
        ValidationError, match="title must use lowercase category/project/task"
    ):
        ChangeRequest(
            action="update",
            calendar_id="calendar",
            event_id="event",
            title="поезд Москва → Киров",
        )
