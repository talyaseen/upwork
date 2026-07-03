"""Pydantic v2 schemas for authentication."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas._datetime import UtcDateTime


class UserCreate(BaseModel):
    """Registration payload."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"username": "ada", "password": "s3cure-pass"}
        }
    )

    username: str = Field(
        min_length=3,
        max_length=64,
        pattern=r"^[A-Za-z0-9_.-]+$",
        description="Unique account handle (letters, digits, _ . - only).",
    )
    # Upper bound keeps the bcrypt 72-byte limit meaningful and avoids
    # accepting pathologically long inputs.
    password: str = Field(
        min_length=8,
        max_length=72,
        description="Plaintext password, 8-72 characters.",
    )


class UserPublic(BaseModel):
    """Public view of a user (never exposes the password hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    created_at: UtcDateTime


class Token(BaseModel):
    """OAuth2 bearer token response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
            }
        }
    )

    access_token: str
    token_type: str = "bearer"
