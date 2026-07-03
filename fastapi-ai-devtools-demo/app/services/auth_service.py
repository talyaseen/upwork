"""User registration and authentication service."""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.db.models import User


async def get_user_by_username(
    session: AsyncSession, username: str
) -> User | None:
    result = await session.execute(
        select(User).where(User.username == username)
    )
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession, username: str, password: str
) -> User:
    """Create a new user. Caller must ensure the username is free."""
    # bcrypt is CPU-bound (~250ms). Offload it to a thread so hashing never
    # stalls the event loop (which would freeze in-flight SSE streams). (BM6)
    password_hash = await asyncio.to_thread(hash_password, password)
    user = User(username=username, password_hash=password_hash)
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def authenticate(
    session: AsyncSession, username: str, password: str
) -> User | None:
    """Return the user if the credentials are valid, else None."""
    user = await get_user_by_username(session, username)
    if user is None:
        return None
    # bcrypt verify is CPU-bound (~250ms); offload it off the event loop. (BM6)
    ok = await asyncio.to_thread(verify_password, password, user.password_hash)
    if not ok:
        return None
    return user
