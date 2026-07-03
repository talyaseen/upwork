"""Pydantic v2 schemas for documents."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas._datetime import UtcDateTime


class DocumentCreate(BaseModel):
    """Payload for ingesting a new document."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Twelve-Factor Configuration",
                "text": (
                    "Store configuration in the environment. Keep secrets "
                    "out of source control and inject them at deploy time so "
                    "the same build artifact runs in every environment."
                ),
            }
        }
    )

    title: str = Field(min_length=1, max_length=512)
    text: str = Field(
        min_length=1,
        max_length=200_000,
        description="Full document body. It is chunked and embedded on ingest.",
    )


class DocumentSummary(BaseModel):
    """List/summary view of a document (no full body)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    source: str
    created_at: UtcDateTime
    chunk_count: int = Field(
        description="Number of chunks this document was split into."
    )


class DocumentDetail(BaseModel):
    """Full document view, including body text."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    text: str
    source: str
    created_at: UtcDateTime
    chunk_count: int


class DocumentList(BaseModel):
    """Paginated list of document summaries."""

    total: int = Field(description="Total documents matching the query.")
    limit: int
    offset: int
    items: list[DocumentSummary]


class IngestResult(BaseModel):
    """Result of ingesting a document."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    chunk_count: int
    message: str = "Document ingested and indexed."
