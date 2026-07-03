"""Pydantic schemas for the INTERNAL-ONLY conversation-log read endpoints.

These describe the JSON returned by ``/api/admin/conversations`` (list) and
``/api/admin/conversations/{id}`` (single). Those routes are gated by the
internal gate; there is no public read path for stored conversations.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas._datetime import UtcDateTime


class ConversationRecord(BaseModel):
    """One stored /chat exchange."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: str | None = Field(
        default=None, description="Opaque client session id, if supplied."
    )
    skill: str = Field(
        description="Skill that produced the answer (qa, code-review, ...)."
    )
    model: str = Field(
        description="Model that answered, or 'guarded' when refused."
    )
    backend_tier: str = Field(
        description="Backend tier that served the exchange."
    )
    finish_reason: str = Field(
        description=(
            "How the stream ended: stop, offline, blocked, or "
            "repetition_stopped (internal loop-detection breaker fired; the "
            "client itself always sees a normal 'stop')."
        )
    )
    user_message: str = Field(description="The user's message for this turn.")
    assistant_response: str = Field(description="The assistant's full answer.")
    created_at: UtcDateTime = Field(
        description="When the exchange was stored (UTC, ISO-8601 with a 'Z' suffix)."
    )


class ConversationList(BaseModel):
    """A page of stored conversations plus paging metadata."""

    total: int = Field(description="Total stored conversations.")
    count: int = Field(description="Number of items in this page.")
    limit: int = Field(description="Page size used.")
    offset: int = Field(description="Page offset used.")
    items: list[ConversationRecord] = Field(
        description="The conversations in this page, most recent first."
    )
