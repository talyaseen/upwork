"""Mermaid diagram skill: artifact emission, SVG render seam, source extraction."""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest

from app.services.chat_service import ArtifactEvent, ChatService, TokenEvent
from app.services.gpu_router import TIER_GPU, Selection

pytestmark = pytest.mark.asyncio


class _Client:
    def __init__(self, tokens: list[str]) -> None:
        self.model = "m"
        self._tokens = tokens

    async def stream_chat(self, messages) -> AsyncIterator[str]:
        for tok in self._tokens:
            yield tok


class _Router:
    def __init__(self, client: _Client) -> None:
        self._client = client

    async def select(self, requested_model=None) -> Selection:
        return Selection(self._client, TIER_GPU, self._client.model, None)

    def gpu_yielded(self) -> bool:
        return False


def _service(client: _Client, renderer) -> ChatService:
    return ChatService(
        search_service=None,
        llm_router=_Router(client),
        settings=SimpleNamespace(chat_top_k=4, mermaid_render_enabled=True),
        mermaid_renderer=renderer,
    )


async def test_mermaid_skill_emits_artifact_with_rendered_svg():
    client = _Client(["```mermaid\n", "flowchart TD\n", "A-->B\n", "```"])
    service = _service(client, renderer=lambda s: f"<svg>{s}</svg>")

    events = [
        ev async for ev in service.stream("draw a flow", skill="mermaid")
    ]
    artifacts = [e for e in events if isinstance(e, ArtifactEvent)]
    assert len(artifacts) == 1
    art = artifacts[0]
    assert art.kind == "mermaid"
    # The code fence is stripped; the diagram source is clean.
    assert "flowchart TD" in art.source and "A-->B" in art.source
    assert "```" not in art.source
    assert art.svg == f"<svg>{art.source}</svg>"
    assert art.fmt == "svg"
    # 2026-07-03 fix: the raw diagram DSL is NOT streamed into the body (it would
    # duplicate the rendered card); it ships only as the artifact source.
    body = "".join(e.text for e in events if isinstance(e, TokenEvent))
    assert "flowchart" not in body and "A-->B" not in body and "```" not in body


async def test_mermaid_artifact_source_only_when_no_renderer():
    client = _Client(["sequenceDiagram\n", "A->>B: hi\n"])
    service = _service(client, renderer=lambda s: None)  # render unavailable

    events = [
        ev async for ev in service.stream("draw a sequence diagram", skill="mermaid")
    ]
    art = next(e for e in events if isinstance(e, ArtifactEvent))
    assert art.svg is None
    assert art.fmt == "mermaid"
    assert "sequenceDiagram" in art.source


async def test_qa_skill_emits_no_artifact():
    client = _Client(["hello"])
    # qa is grounded; search_service is required, so use a stub that returns [].
    service = ChatService(
        search_service=SimpleNamespace(search=_empty_search),
        llm_router=_Router(client),
        settings=SimpleNamespace(chat_top_k=4),
    )
    events = [ev async for ev in service.stream("hi", skill="qa")]
    assert not any(isinstance(e, ArtifactEvent) for e in events)


async def _empty_search(query, limit):
    return []
