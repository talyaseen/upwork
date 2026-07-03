"""Regression pin for BL19: SQLite connections must use WAL + a busy timeout.

The default rollback journal serialises writers, so under burst writes a second
concurrent writer hits "database is locked" and the row is silently dropped. WAL
plus PRAGMA busy_timeout make contended writes retry instead of failing. Without
the fix in ``app.db.database`` the journal mode is the default ("delete") and
this test fails.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.db import database as db_module


def test_negative_sqlite_busy_timeout_is_rejected():
    # A negative busy_timeout silently disables the timeout in SQLite (it waits
    # forever), turning burst-write contention into an indefinite hang. The
    # ``ge=0`` bound must reject it up front. Zero (disable, but explicit) is OK.
    with pytest.raises(ValidationError):
        Settings(sqlite_busy_timeout_ms=-1)
    assert Settings(sqlite_busy_timeout_ms=0).sqlite_busy_timeout_ms == 0


@pytest.mark.asyncio
async def test_sqlite_connection_uses_wal_and_busy_timeout(tmp_path, monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'pragma.db'}"
    )
    monkeypatch.setenv("SQLITE_BUSY_TIMEOUT_MS", "7000")
    get_settings.cache_clear()
    db_module._engine = None
    db_module._session_factory = None
    try:
        engine = db_module.get_engine()
        async with engine.connect() as conn:
            journal = (await conn.execute(text("PRAGMA journal_mode"))).scalar()
            busy = (await conn.execute(text("PRAGMA busy_timeout"))).scalar()
        assert str(journal).lower() == "wal"
        assert int(busy) == 7000
    finally:
        await db_module.dispose_db()
        get_settings.cache_clear()
