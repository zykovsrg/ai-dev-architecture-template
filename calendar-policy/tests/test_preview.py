from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from hub_calendar_policy.models import ChangeRequest
from hub_calendar_policy.preview import PreviewError, PreviewGrantStore


ZONE = ZoneInfo("Europe/Kirov")


class MutableClock:
    def __init__(self) -> None:
        self.value = datetime(2026, 8, 29, 12, 0, tzinfo=ZONE)

    def now(self) -> datetime:
        return self.value


@pytest.fixture
def clock() -> MutableClock:
    return MutableClock()


@pytest.fixture
def change_request() -> ChangeRequest:
    return ChangeRequest(
        action="update",
        calendar_id="calendar-1",
        event_id="event-1",
        title="Review",
    )


@pytest.fixture
def store(clock: MutableClock) -> PreviewGrantStore:
    return PreviewGrantStore(clock=clock.now, token_factory=lambda: "grant-1")


def test_preview_is_single_use(store: PreviewGrantStore, change_request: ChangeRequest) -> None:
    grant = store.issue(change_request, source_fingerprint="before")

    store.consume(grant.id, change_request, source_fingerprint="before")

    with pytest.raises(PreviewError, match="PREVIEW_ALREADY_USED"):
        store.consume(grant.id, change_request, source_fingerprint="before")


def test_preview_expires_after_ten_minutes(
    store: PreviewGrantStore, clock: MutableClock, change_request: ChangeRequest
) -> None:
    grant = store.issue(change_request, source_fingerprint="before")
    clock.value += timedelta(seconds=600)

    with pytest.raises(PreviewError, match="PREVIEW_EXPIRED"):
        store.consume(grant.id, change_request, source_fingerprint="before")


def test_cancelled_preview_cannot_be_applied(
    store: PreviewGrantStore, change_request: ChangeRequest
) -> None:
    grant = store.issue(change_request, source_fingerprint="before")
    store.cancel(grant.id)

    with pytest.raises(PreviewError, match="PREVIEW_CANCELLED"):
        store.consume(grant.id, change_request, source_fingerprint="before")


def test_preview_is_bound_to_exact_payload(
    store: PreviewGrantStore, change_request: ChangeRequest
) -> None:
    grant = store.issue(change_request, source_fingerprint="before")
    changed_request = change_request.model_copy(update={"title": "Different title"})

    with pytest.raises(PreviewError, match="PREVIEW_PAYLOAD_MISMATCH"):
        store.consume(grant.id, changed_request, source_fingerprint="before")


def test_preview_is_bound_to_current_event_fingerprint(
    store: PreviewGrantStore, change_request: ChangeRequest
) -> None:
    grant = store.issue(change_request, source_fingerprint="before")

    with pytest.raises(PreviewError, match="PREVIEW_SOURCE_CHANGED"):
        store.consume(grant.id, change_request, source_fingerprint="after")


def test_restart_loses_all_unapplied_previews(
    clock: MutableClock, change_request: ChangeRequest
) -> None:
    first_store = PreviewGrantStore(clock=clock.now, token_factory=lambda: "grant-1")
    grant = first_store.issue(change_request, source_fingerprint="before")
    restarted_store = PreviewGrantStore(clock=clock.now, token_factory=lambda: "grant-2")

    with pytest.raises(PreviewError, match="PREVIEW_NOT_FOUND"):
        restarted_store.consume(grant.id, change_request, source_fingerprint="before")


def test_two_previews_never_authorize_each_other(
    clock: MutableClock, change_request: ChangeRequest
) -> None:
    tokens = iter(["grant-1", "grant-2"])
    store = PreviewGrantStore(clock=clock.now, token_factory=lambda: next(tokens))
    other_request = change_request.model_copy(update={"title": "Other review"})
    first = store.issue(change_request, source_fingerprint="before")
    second = store.issue(other_request, source_fingerprint="before")

    with pytest.raises(PreviewError, match="PREVIEW_PAYLOAD_MISMATCH"):
        store.consume(first.id, other_request, source_fingerprint="before")

    store.consume(second.id, other_request, source_fingerprint="before")
