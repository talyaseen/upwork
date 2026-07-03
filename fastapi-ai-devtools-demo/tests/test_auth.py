"""Authentication flow tests."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.db.database import get_session_factory
from app.db.models import User

pytestmark = pytest.mark.asyncio


async def test_register_and_login_flow(client: AsyncClient) -> None:
    username = f"alice_{uuid.uuid4().hex[:8]}"
    password = "correct horse battery"

    reg = await client.post(
        "/auth/register", json={"username": username, "password": password}
    )
    assert reg.status_code == 201
    body = reg.json()
    assert body["username"] == username
    assert "id" in body
    assert "password" not in body and "password_hash" not in body

    login = await client.post(
        "/auth/login", data={"username": username, "password": password}
    )
    assert login.status_code == 200
    token = login.json()
    assert token["token_type"] == "bearer"
    assert token["access_token"]


async def test_duplicate_username_rejected(client: AsyncClient) -> None:
    username = f"bob_{uuid.uuid4().hex[:8]}"
    payload = {"username": username, "password": "password123"}
    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 201
    second = await client.post("/auth/register", json=payload)
    assert second.status_code == 409


async def test_duplicate_register_toctou_returns_409(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BH4 regression: two registrations that both pass the existence check and
    then collide on the unique constraint must yield a clean 409, not a raw 500.

    The check-then-insert has a TOCTOU window. We force it deterministically by
    stubbing the pre-insert lookup to always report the username as free, so the
    second insert hits the DB unique constraint (IntegrityError) exactly as a
    lost race would. Before the fix this surfaced as an uncaught 500.
    """

    async def _always_free(session, username: str):  # noqa: ANN001
        return None

    monkeypatch.setattr(
        "app.routers.auth.get_user_by_username", _always_free
    )

    username = f"race_{uuid.uuid4().hex[:8]}"
    payload = {"username": username, "password": "password123"}

    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/auth/register", json=payload)
    assert second.status_code == 409, second.text
    assert second.status_code != 500


async def test_bcrypt_offload_still_hashes_and_verifies(
    client: AsyncClient,
) -> None:
    """BM6 regression: bcrypt hashing/verify are now offloaded to a worker
    thread (asyncio.to_thread) so they don't stall the event loop. Verify the
    offload preserved correctness end to end: a registered password must hash,
    the stored hash must NOT be the plaintext, the correct password must log in,
    and a wrong password must be rejected.
    """
    username = f"eve_{uuid.uuid4().hex[:8]}"
    password = "correct horse battery staple"

    reg = await client.post(
        "/auth/register", json={"username": username, "password": password}
    )
    assert reg.status_code == 201

    # The stored credential must be a bcrypt DIGEST, never the plaintext (what
    # the docstring above asserts): read the row back and confirm the persisted
    # ``password_hash`` differs from the raw password and carries a bcrypt prefix.
    factory = get_session_factory()
    async with factory() as session:
        stored_hash = (
            await session.execute(
                select(User.password_hash).where(User.username == username)
            )
        ).scalar_one()
    assert stored_hash != password
    assert stored_hash.startswith(("$2a$", "$2b$", "$2y$"))

    good = await client.post(
        "/auth/login", data={"username": username, "password": password}
    )
    assert good.status_code == 200
    assert good.json()["access_token"]

    bad = await client.post(
        "/auth/login", data={"username": username, "password": password + "x"}
    )
    assert bad.status_code == 401


async def test_login_wrong_password(client: AsyncClient) -> None:
    username = f"carol_{uuid.uuid4().hex[:8]}"
    await client.post(
        "/auth/register",
        json={"username": username, "password": "password123"},
    )
    bad = await client.post(
        "/auth/login", data={"username": username, "password": "wrong"}
    )
    assert bad.status_code == 401


async def test_register_validation_errors(client: AsyncClient) -> None:
    # Too-short password.
    short = await client.post(
        "/auth/register", json={"username": "dave", "password": "short"}
    )
    assert short.status_code == 422
    # Invalid username characters.
    bad_user = await client.post(
        "/auth/register",
        json={"username": "has spaces!", "password": "password123"},
    )
    assert bad_user.status_code == 422


async def test_me_requires_auth(client: AsyncClient) -> None:
    unauth = await client.get("/auth/me")
    assert unauth.status_code == 401


async def test_me_returns_current_user(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert "username" in resp.json()


async def test_invalid_token_rejected(client: AsyncClient) -> None:
    resp = await client.get(
        "/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401
