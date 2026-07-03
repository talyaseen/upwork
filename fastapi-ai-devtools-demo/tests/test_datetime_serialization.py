"""Regression pin for BL15: created_at must serialize as tz-aware UTC.

SQLite drops the offset on DateTime(timezone=True) columns, so aiosqlite reads
timestamps back as NAIVE datetimes. Before the fix the API emitted an ISO string
with no 'Z'/offset and clients rendered it in local time. Every response schema
carrying created_at must now emit an explicit UTC 'Z' suffix.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.schemas.auth import UserPublic
from app.schemas.conversation import ConversationRecord
from app.schemas.document import DocumentSummary


def test_naive_created_at_serialized_as_utc_z() -> None:
    # A naive datetime is exactly what aiosqlite returns for a stored UTC value.
    naive = datetime(2026, 7, 3, 12, 30, 0)
    user = UserPublic(id=1, username="ada", created_at=naive)
    assert user.model_dump(mode="json")["created_at"] == "2026-07-03T12:30:00Z"


def test_aware_created_at_normalized_to_utc_z() -> None:
    # A non-UTC aware value is converted to UTC before serialization.
    aware = datetime(2026, 7, 3, 15, 30, 0, tzinfo=timezone(timedelta(hours=3)))
    doc = DocumentSummary(
        id=1, title="Config", source="user", created_at=aware, chunk_count=2
    )
    assert doc.model_dump(mode="json")["created_at"] == "2026-07-03T12:30:00Z"


def test_conversation_created_at_has_z_suffix() -> None:
    rec = ConversationRecord(
        id=1,
        session_id="s1",
        skill="qa",
        model="m",
        backend_tier="primary-7b-gpu",
        finish_reason="stop",
        user_message="hi",
        assistant_response="hello",
        created_at=datetime(2026, 7, 3, 0, 0, 0),
    )
    assert rec.model_dump(mode="json")["created_at"].endswith("Z")
