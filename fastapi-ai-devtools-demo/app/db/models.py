"""SQLAlchemy ORM models.

Four tables:
- ``users``         : registered accounts (username + bcrypt hash).
- ``documents``     : ingested documents (title + full text).
- ``chunks``        : per-document text chunks with their embedding vectors.
- ``conversations`` : durable log of every completed /chat exchange.

Embeddings are stored as raw float32 bytes (LargeBinary). On startup the
search service loads every chunk vector into an in-process NumPy matrix for
fast cosine-similarity search; SQLite is the durable store of record.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(
        String(64), default="user", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    chunks: Mapped[list[Chunk]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # float32 vector serialised with numpy.ndarray.tobytes().
    embedding: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    dim: Mapped[int] = mapped_column(Integer, nullable=False)

    document: Mapped[Document] = relationship(back_populates="chunks")


class Conversation(Base):
    """One completed /chat exchange (user turn + assistant answer).

    Written once, when a /chat stream reaches a terminal state (a normal
    completion, an offline notice, or a guard refusal). This is the durable,
    queryable record the operator asked for ("save every conversation").

    STORE: the app's existing async SQLAlchemy store backs this table. In this
    deployment that is SQLite (DATABASE_URL); the identical model runs unchanged
    against PostgreSQL by pointing DATABASE_URL at a ``postgresql+asyncpg`` URL.

    PRIVACY / ACCESS: rows are INTERNAL-ONLY. There is no public read path; the
    only read/list surface (``/api/admin/conversations``) is behind the same
    internal gate as the GPU admin routes (peer-IP allowlist + optional token,
    proxied requests rejected). Raw user text is stored deliberately (that is the
    point of a conversation log) and is never exposed to the public.
    """

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Opaque client session id (optional). Indexed so an operator can pull a
    # single visitor's thread. Null when the client did not supply one.
    session_id: Mapped[str | None] = mapped_column(
        String(64), index=True, nullable=True
    )
    # Which skill produced the answer: "qa" (grounded RAG), "code-review",
    # "mermaid", etc. Defaults to "qa" for the plain conversational path.
    skill: Mapped[str] = mapped_column(String(60), default="qa", nullable=False)
    # The generative model that answered (the served-model-name), or "guarded"
    # when the input guard refused before any model call.
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    # Which backend served it: "primary-7b-gpu", "offline", "guard", etc.
    backend_tier: Mapped[str] = mapped_column(String(40), nullable=False)
    # How the stream ended: "stop", "offline", or "blocked".
    finish_reason: Mapped[str] = mapped_column(String(20), nullable=False)
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    assistant_response: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True, nullable=False
    )
