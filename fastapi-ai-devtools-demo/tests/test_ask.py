"""Extractive Q&A endpoint tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_ask_returns_extractive_answer_with_citations(
    client: AsyncClient, internal_client: AsyncClient
) -> None:
    # Ingest a document with a distinctive, easily-matched passage so the
    # deterministic hash embedder reliably retrieves it.
    answer_text = (
        "The capital widget threshold for the snarfblat module is "
        "exactly fortytwo units per cycle."
    )
    await internal_client.post(
        "/documents",
        json={"title": "Widget Spec", "text": answer_text},
    )

    resp = await client.post(
        "/ask",
        json={
            "question": (
                "capital widget threshold snarfblat module fortytwo units"
            )
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is True
    assert data["answer"]  # non-empty
    assert data["citations"]
    # Extractive: the answer is drawn verbatim from a cited passage.
    assert data["answer"] == data["citations"][0]["text"]


async def test_ask_no_match_returns_not_found(client: AsyncClient) -> None:
    # A query of pure noise that shares no tokens with any seed passage.
    resp = await client.post(
        "/ask",
        json={"question": "zzqqxx vvbbnn wwkkjj noisetokenxyz"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is False
    assert data["citations"] == []


async def test_ask_validation_error(client: AsyncClient) -> None:
    resp = await client.post("/ask", json={"question": ""})
    assert resp.status_code == 422


async def test_ask_respects_top_k(client: AsyncClient) -> None:
    resp = await client.post(
        "/ask",
        json={"question": "semantic search embeddings vectors", "top_k": 1},
    )
    assert resp.status_code == 200
    data = resp.json()
    if data["found"]:
        assert len(data["citations"]) <= 1
