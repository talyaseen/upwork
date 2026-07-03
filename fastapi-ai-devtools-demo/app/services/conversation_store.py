"""Persistence for completed /chat exchanges.

Every completed conversational exchange (the user's message plus the assistant's
answer) is written to the ``conversations`` table so the operator has a durable,
queryable record of what the public demo was asked and how it answered.

STORE CHOICE: this uses the app's EXISTING async SQLAlchemy store. Postgres was
preferred per the brief, but this hub has no running Postgres server/cluster and
the async ``asyncpg`` driver is not installed, so the existing store is used
(SQLite via ``DATABASE_URL``). The code is storage-agnostic: pointing
``DATABASE_URL`` at a ``postgresql+asyncpg://...`` URL switches it to Postgres
with no code change (SQLAlchemy + a driver install being the only requirement).

ISOLATION: a fresh session is opened from the process-wide factory for each
write. The write is NOT tied to the request-scoped session, because /chat streams
its response and the request session's lifecycle around a StreamingResponse is
awkward; a dedicated short-lived session sidesteps that entirely.

BEST-EFFORT: persistence must NEVER break or delay a user's answer. Every write
is wrapped so a storage error is logged and swallowed, and the chat stream
continues unaffected.

INTERNAL-ONLY: the read helpers here back the ``/api/admin/conversations`` route,
which is gated by the internal gate. Nothing here is exposed to the public.
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.database import get_session_factory
from app.db.models import Conversation

logger = logging.getLogger("app.conversations")

# Defensive per-row caps so a pathological payload cannot bloat the table. The
# request layer already bounds the user message (<= 4000 chars) and generation is
# bounded by max_tokens, so these are backstops, not the primary limit.
_MAX_MESSAGE_CHARS = 8_000
_MAX_RESPONSE_CHARS = 40_000


class ConversationStore:
    """Writes and reads durable /chat conversation records.

    ``session_factory`` is injectable for tests; in production it defaults to the
    process-wide async session factory (same engine / DATABASE_URL as the app).
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._session_factory = session_factory

    def _factory(self) -> async_sessionmaker[AsyncSession]:
        return self._session_factory or get_session_factory()

    async def save(
        self,
        *,
        user_message: str,
        assistant_response: str,
        model: str,
        backend_tier: str,
        finish_reason: str,
        skill: str | None = None,
        session_id: str | None = None,
    ) -> int | None:
        """Persist one completed exchange. Returns the new row id, or None on
        failure (a failure is logged and swallowed - persistence never raises up
        into the chat stream)."""
        row = Conversation(
            session_id=(session_id or None),
            skill=(skill or "qa"),
            model=(model or "unknown"),
            backend_tier=(backend_tier or "unknown"),
            finish_reason=(finish_reason or "unknown"),
            user_message=(user_message or "")[:_MAX_MESSAGE_CHARS],
            assistant_response=(assistant_response or "")[:_MAX_RESPONSE_CHARS],
        )
        try:
            factory = self._factory()
            async with factory() as session:
                session.add(row)
                await session.commit()
                return row.id
        except Exception:  # noqa: BLE001 - persistence must never break chat
            logger.exception("Failed to persist conversation")
            return None

    async def list_recent(
        self, *, limit: int = 50, offset: int = 0
    ) -> list[Conversation]:
        """Most-recent-first page of stored conversations (internal-only)."""
        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))
        factory = self._factory()
        async with factory() as session:
            result = await session.execute(
                select(Conversation)
                .order_by(Conversation.id.desc())
                .limit(limit)
                .offset(offset)
            )
            return list(result.scalars().all())

    async def get(self, conversation_id: int) -> Conversation | None:
        """Fetch a single stored conversation by id (internal-only)."""
        factory = self._factory()
        async with factory() as session:
            return await session.get(Conversation, conversation_id)

    async def count(self) -> int:
        """Total number of stored conversations."""
        factory = self._factory()
        async with factory() as session:
            result = await session.execute(
                select(func.count()).select_from(Conversation)
            )
            return int(result.scalar_one())
