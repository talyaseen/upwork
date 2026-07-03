"""Semantic search endpoint tests (offline hash embedder)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_search_returns_ranked_results(client: AsyncClient) -> None:
    resp = await client.get(
        "/search", params={"q": "configuration environment variables"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "configuration environment variables"
    assert data["count"] >= 1
    assert data["count"] == len(data["results"])

    scores = [hit["score"] for hit in data["results"]]
    # Results must be sorted by score descending.
    assert scores == sorted(scores, reverse=True)

    first = data["results"][0]
    for key in (
        "document_id",
        "document_title",
        "chunk_id",
        "chunk_index",
        "text",
        "score",
    ):
        assert key in first
    assert -1.0001 <= first["score"] <= 1.0001


async def test_search_respects_limit(client: AsyncClient) -> None:
    resp = await client.get("/search", params={"q": "caching", "limit": 2})
    assert resp.status_code == 200
    assert len(resp.json()["results"]) <= 2


async def test_search_requires_query(client: AsyncClient) -> None:
    resp = await client.get("/search")
    assert resp.status_code == 422


async def test_search_limit_validation(client: AsyncClient) -> None:
    too_big = await client.get("/search", params={"q": "x", "limit": 999})
    assert too_big.status_code == 422


async def test_newly_ingested_document_is_searchable(
    client: AsyncClient, internal_client: AsyncClient
) -> None:
    marker = "zylophonics quantumly snarfblat"
    await internal_client.post(
        "/documents",
        json={
            "title": "Unique Marker Doc",
            "text": f"This passage mentions {marker} as a rare phrase.",
        },
    )
    resp = await client.get("/search", params={"q": marker, "limit": 1})
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert results
    assert results[0]["document_title"] == "Unique Marker Doc"
