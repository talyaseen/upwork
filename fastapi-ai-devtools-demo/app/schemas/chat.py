"""Pydantic v2 schemas for the conversational RAG /chat endpoint.

The response itself is an SSE (text/event-stream) byte stream, not a JSON
body, so the schemas here describe the REQUEST plus the JSON shapes carried
inside each SSE event. See ``app/routers/chat.py`` for the exact event order.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.search import Citation


class ChatMessage(BaseModel):
    """One prior turn in the conversation (for multi-turn context)."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    """A user message plus optional prior turns and a retrieval override."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": (
                    "I'm getting duplicate charges when my service restarts "
                    "- what's going on and how do I make it scale safely?"
                ),
                "history": [],
                "top_k": 4,
                "model": "auto",
            }
        }
    )

    message: str = Field(
        min_length=1,
        max_length=4000,
        description="The user's current message.",
    )
    model: str | None = Field(
        default=None,
        max_length=120,
        description=(
            "Which model to answer with (see GET /models). Use 'auto' (or omit) "
            "to let the server pick the GPU model when the GPU is idle. This "
            "demo is GPU-only: when the GPU is busy serving training the demo is "
            "offline (there is no CPU fallback). Unknown ids fall back to 'auto'."
        ),
    )
    skill: str | None = Field(
        default=None,
        max_length=60,
        description=(
            "Which skill to use (see GET /skills): 'qa' (default, grounded RAG), "
            "'code-review' (review a pasted snippet), or 'mermaid' (NL -> "
            "diagram). Unknown ids fall back to 'qa'."
        ),
    )
    session_id: str | None = Field(
        default=None,
        max_length=64,
        description=(
            "Optional opaque session id. When set, the demo logs sanitized "
            "per-session traces and streams a 'learning' event with improvement "
            "proposals (see GET /learning/{session_id}). Per-session and "
            "ephemeral; no raw text is stored."
        ),
    )
    history: list[ChatMessage] = Field(
        default_factory=list,
        max_length=20,
        description=(
            "Prior conversation turns, oldest first, so the assistant can "
            "answer follow-ups in context. Omit or send [] for a fresh chat."
        ),
    )
    top_k: int | None = Field(
        default=None,
        ge=1,
        le=10,
        description=(
            "How many corpus chunks to retrieve as grounding context "
            "(defaults to server config)."
        ),
    )


# --- Documentation-only models describing the SSE event payloads ----------
# These are not returned as a JSON body; they document the JSON carried in the
# ``data:`` field of each Server-Sent Event so the contract is discoverable.


class ChatMetadataEvent(BaseModel):
    """Leading ``event: metadata`` payload (sent once, before any tokens)."""

    model: str = Field(description="The generative model that produced the answer.")
    retrieved: int = Field(description="Number of corpus chunks retrieved.")
    backend_tier: str = Field(
        default="unknown",
        description="Which backend served this answer: 'primary-7b-gpu' when the "
        "GPU is serving, or 'offline' when the GPU is unavailable (no CPU "
        "fallback). 'guard' when the request was refused by the safety guard.",
    )
    notice: str | None = Field(
        default=None,
        description="Set when the demo is offline (GPU serving training).",
    )
    skill: str = Field(
        default="qa",
        description=(
            "The skill the per-turn intent router routed this message to "
            "('qa' / 'code-review' / 'mermaid'). May differ from the sticky "
            "selector the client sent; the UI can reflect the mode that ran."
        ),
    )
    citations: list[Citation] = Field(
        description="The retrieved source passages grounding the answer."
    )


class ChatQueueEvent(BaseModel):
    """A ``event: queue`` payload, sent while the request waits for a slot."""

    position: int = Field(description="1-based position in the generation queue.")
    status: str = Field(default="waiting", description="Always 'waiting'.")


class ChatNoticeEvent(BaseModel):
    """A ``event: notice`` payload (e.g. the demo went offline: GPU yielded)."""

    message: str = Field(description="Human-readable notice for the UI.")
    model: str = Field(description="The model now serving the request.")
    backend_tier: str = Field(description="The backend now serving the request.")


class ChatBusyEvent(BaseModel):
    """A ``event: busy`` payload, sent when the queue is full."""

    message: str = Field(description="Why the request was rejected.")
    retry_after_seconds: int = Field(
        default=5, description="Suggested wait before retrying."
    )


class ChatArtifactEvent(BaseModel):
    """A ``event: artifact`` payload (e.g. a Mermaid diagram from the diagram skill).

    Sent once, after the tokens and before ``done``, when a skill produces a
    non-text artifact. For the ``mermaid`` skill, ``source`` is the Mermaid code
    (always present) and ``svg`` is a downloadable rendered image when local
    rendering is enabled (otherwise ``null`` - the client can render ``source``).
    """

    kind: str = Field(description="Artifact kind, e.g. 'mermaid'.")
    format: str = Field(
        description="'svg' when rendered, else 'mermaid' (source only)."
    )
    source: str = Field(description="The artifact source (e.g. Mermaid code).")
    svg: str | None = Field(
        default=None, description="Rendered, downloadable SVG when available."
    )


class ChatTokenEvent(BaseModel):
    """A streamed ``event: token`` payload (sent many times)."""

    text: str = Field(description="An incremental fragment of the answer.")


class ChatDoneEvent(BaseModel):
    """Terminal ``event: done`` payload (sent once, after the last token)."""

    finish_reason: str = Field(
        default="stop", description="Why generation stopped."
    )
