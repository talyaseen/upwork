"""Shared tz-aware datetime serialization for API response schemas.

The ORM stores timestamps as ``DateTime(timezone=True)`` with a UTC default, but
SQLite does not persist the offset, so aiosqlite reads them back as NAIVE
datetimes. Serialised as-is they emit an ISO string with no ``Z``/offset, and
clients then render them in the browser's local time zone (BL15). ``UtcDateTime``
coerces every API timestamp to an explicit UTC ISO-8601 string ending in ``Z``.

Naive values are ASSUMED to be UTC (that is how they were written); aware values
are converted to UTC. Serialization only applies in JSON mode, so Python-mode
``model_dump()`` still yields ``datetime`` objects for internal callers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import PlainSerializer


def to_utc_iso(value: datetime) -> str:
    """Render a datetime as a UTC ISO-8601 string with a trailing ``Z``."""
    aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return aware.isoformat().replace("+00:00", "Z")


UtcDateTime = Annotated[
    datetime,
    PlainSerializer(to_utc_iso, return_type=str, when_used="json"),
]
