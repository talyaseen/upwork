"""Regression pins for the two live red-team web-integrity findings.

Finding #23 (RAG corpus poisoning): a self-registered visitor could POST into
the SHARED global corpus that the public /search + /ask serve to everyone. The
fix makes document writes internal-only, so a self-registered user is refused
(403) and cannot poison the corpus everyone sees.

Finding #26 (stored-XSS round-trip): injected <script> / <img onerror=...> text
was returned VERBATIM (unsanitized) from /search, /ask and /chat. The fix
HTML-escapes all corpus-derived text on output, so markup comes back inert.

These tests FAIL on the pre-fix code (write returns 201 / output returns raw
markup) and PASS after the fix.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.db.database import get_session_factory

pytestmark = pytest.mark.asyncio

_MARK = "qzxwmarker7788"
_XSS_TEXT = f'{_MARK} <script>alert("xss-{_MARK}")</script> {_MARK} payload {_MARK}'
_XSS_TITLE = f'<img src=x onerror=alert(1)> {_MARK}'


async def _ingest_direct(app: FastAPI, title: str, text: str) -> None:
    """Insert a document straight into the shared corpus + live index.

    Bypasses the (now internal-only) HTTP write path so the stored-XSS pin can
    stage a poisoned corpus entry and assert how it comes back OUT on the public
    read endpoints, independent of the write-authz change.
    """
    factory = get_session_factory()
    async with factory() as session:
        await app.state.search_service.ingest_document(
            session, title=title, text=text, source="user"
        )
        await session.commit()


# --- Finding #23: open corpus poisoning --------------------------------------


async def test_self_registered_user_cannot_poison_shared_corpus(
    client: AsyncClient,
) -> None:
    # A visitor registers and logs in (a valid bearer token) - exactly the
    # red-team's path. On the pre-fix code this POST returned 201 and the doc
    # surfaced via the public /search + /ask to every other visitor.
    username = f"rt_{uuid.uuid4().hex[:10]}"
    password = "supersecret123"
    reg = await client.post(
        "/auth/register", json={"username": username, "password": password}
    )
    assert reg.status_code == 201, reg.text
    login = await client.post(
        "/auth/login", data={"username": username, "password": password}
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    poison_marker = "poisonmarker_zz9931"
    resp = await client.post(
        "/documents",
        json={"title": "Poison", "text": f"totally {poison_marker} bogus"},
        headers=headers,
    )
    # The shared corpus is no longer publicly writable: refused.
    assert resp.status_code == 403

    # And nothing the visitor tried to inject surfaces on the public corpus.
    hit = await client.get("/search", params={"q": poison_marker})
    assert all(
        poison_marker not in r["text"] for r in hit.json()["results"]
    )


# --- Finding #26: stored-XSS / unsanitized round-trip ------------------------


async def test_search_escapes_injected_html(
    app: FastAPI, client: AsyncClient
) -> None:
    await _ingest_direct(app, _XSS_TITLE, _XSS_TEXT)

    resp = await client.get("/search", params={"q": _MARK, "limit": 3})
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert results, "poisoned chunk should be retrievable"
    blob = "".join(r["text"] + r["document_title"] for r in results)
    # Raw active markup must NOT come back; the escaped (inert) form MUST. Once
    # the angle brackets are escaped the tag cannot execute, so residual inert
    # substrings like "onerror=" are harmless text.
    assert "<script>" not in blob
    assert "<img" not in blob
    assert "&lt;script&gt;" in blob
    assert "&lt;img" in blob


async def test_ask_escapes_injected_html(
    app: FastAPI, client: AsyncClient
) -> None:
    await _ingest_direct(app, "Benign Title", _XSS_TEXT)

    resp = await client.post("/ask", json={"question": _MARK})
    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is True
    assert "<script>" not in data["answer"]
    assert "&lt;script&gt;" in data["answer"]
    # The extractive answer is drawn from the (escaped) cited passage.
    assert data["answer"] == data["citations"][0]["text"]
