"""Document CRUD and pagination tests.

Document WRITES (POST/DELETE) are internal-only (curator surface): they mutate
the shared corpus the public /search and /ask serve, so they go through the
``internal_client`` (peer 127.0.0.1). READS (GET) stay public and use ``client``.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

LONG_TEXT = " ".join(f"word{i}" for i in range(400))


async def test_ingest_blocked_for_public_caller(client: AsyncClient) -> None:
    # A public (non-internal) caller cannot write to the shared corpus, even
    # with a well-formed body: the internal gate refuses before the handler.
    resp = await client.post(
        "/documents", json={"title": "T", "text": "some body text here"}
    )
    assert resp.status_code == 403


async def test_ingest_and_get_document(
    internal_client: AsyncClient, client: AsyncClient
) -> None:
    resp = await internal_client.post(
        "/documents",
        json={"title": "My Note", "text": LONG_TEXT},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "My Note"
    # 400 words with size 90 / overlap 20 => multiple chunks.
    assert body["chunk_count"] > 1

    doc_id = body["id"]
    got = await client.get(f"/documents/{doc_id}")
    assert got.status_code == 200
    detail = got.json()
    assert detail["id"] == doc_id
    assert detail["text"] == LONG_TEXT
    assert detail["chunk_count"] == body["chunk_count"]


async def test_get_missing_document_404(client: AsyncClient) -> None:
    resp = await client.get("/documents/999999")
    assert resp.status_code == 404


async def test_list_pagination(
    internal_client: AsyncClient, client: AsyncClient
) -> None:
    # Seed corpus already loaded; add a couple more via the internal curator.
    for i in range(3):
        await internal_client.post(
            "/documents",
            json={"title": f"Extra {i}", "text": f"body number {i} here"},
        )

    page = await client.get("/documents", params={"limit": 5, "offset": 0})
    assert page.status_code == 200
    data = page.json()
    assert data["limit"] == 5
    assert data["offset"] == 0
    assert len(data["items"]) == 5
    assert data["total"] >= 17  # 14 seed + 3 extra

    page2 = await client.get("/documents", params={"limit": 5, "offset": 5})
    assert page2.status_code == 200
    ids_page1 = {item["id"] for item in data["items"]}
    ids_page2 = {item["id"] for item in page2.json()["items"]}
    assert ids_page1.isdisjoint(ids_page2)


async def test_pagination_validation(client: AsyncClient) -> None:
    bad = await client.get("/documents", params={"limit": 0})
    assert bad.status_code == 422
    bad2 = await client.get("/documents", params={"offset": -1})
    assert bad2.status_code == 422


async def test_delete_document(
    internal_client: AsyncClient, client: AsyncClient
) -> None:
    created = await internal_client.post(
        "/documents",
        json={"title": "Throwaway", "text": "to be deleted soon"},
    )
    doc_id = created.json()["id"]

    # Delete is internal-only: a public caller is refused.
    public = await client.delete(f"/documents/{doc_id}")
    assert public.status_code == 403

    deleted = await internal_client.delete(f"/documents/{doc_id}")
    assert deleted.status_code == 204

    gone = await client.get(f"/documents/{doc_id}")
    assert gone.status_code == 404

    # Deleting again is a 404.
    again = await internal_client.delete(f"/documents/{doc_id}")
    assert again.status_code == 404


async def test_ingest_validation_error(internal_client: AsyncClient) -> None:
    resp = await internal_client.post(
        "/documents",
        json={"title": "", "text": ""},
    )
    assert resp.status_code == 422
