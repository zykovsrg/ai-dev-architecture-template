"""In-memory, single-use approvals for exact Calendar changes."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
import json
import secrets

from pydantic import BaseModel, ConfigDict, Field

from .models import ChangeRequest


class PreviewError(RuntimeError):
    """A stable denial code for a preview grant."""


class PreviewGrant(BaseModel):
    """Public non-sensitive reference to one preview."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    expires_at: datetime


@dataclass
class _StoredGrant:
    payload_hash: str
    source_fingerprint: str
    expires_at: datetime
    state: str = "active"


class PreviewGrantStore:
    """Keeps approvals only in memory and binds each to exact input and source."""

    def __init__(
        self,
        *,
        clock: Callable[[], datetime],
        token_factory: Callable[[], str] = lambda: secrets.token_urlsafe(32),
    ) -> None:
        self._clock = clock
        self._token_factory = token_factory
        self._grants: dict[str, _StoredGrant] = {}

    def issue(self, request: ChangeRequest, *, source_fingerprint: str) -> PreviewGrant:
        now = self._now()
        grant_id = self._token_factory()
        if not grant_id or grant_id in self._grants:
            raise PreviewError("PREVIEW_ID_COLLISION")
        expires_at = now + timedelta(seconds=600)
        self._grants[grant_id] = _StoredGrant(
            payload_hash=_payload_hash(request),
            source_fingerprint=source_fingerprint,
            expires_at=expires_at,
        )
        return PreviewGrant(id=grant_id, expires_at=expires_at)

    def cancel(self, grant_id: str) -> None:
        grant = self._get(grant_id)
        if grant.state == "used":
            raise PreviewError("PREVIEW_ALREADY_USED")
        grant.state = "cancelled"

    def consume(
        self, grant_id: str, request: ChangeRequest, *, source_fingerprint: str
    ) -> None:
        grant = self._get(grant_id)
        if grant.state == "cancelled":
            raise PreviewError("PREVIEW_CANCELLED")
        if grant.state == "used":
            raise PreviewError("PREVIEW_ALREADY_USED")
        if self._now() >= grant.expires_at:
            grant.state = "expired"
            raise PreviewError("PREVIEW_EXPIRED")
        if _payload_hash(request) != grant.payload_hash:
            raise PreviewError("PREVIEW_PAYLOAD_MISMATCH")
        if source_fingerprint != grant.source_fingerprint:
            raise PreviewError("PREVIEW_SOURCE_CHANGED")
        grant.state = "used"

    def _get(self, grant_id: str) -> _StoredGrant:
        grant = self._grants.get(grant_id)
        if grant is None:
            raise PreviewError("PREVIEW_NOT_FOUND")
        return grant

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("clock must return a timezone-aware datetime")
        return now


def _payload_hash(request: ChangeRequest) -> str:
    canonical = json.dumps(
        request.model_dump(mode="json"),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return sha256(canonical.encode("utf-8")).hexdigest()
