"""Pydantic v2 schemas for semantic search and extractive Q&A."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SearchHit(BaseModel):
    """A single ranked chunk returned by semantic search."""

    document_id: int
    document_title: str
    chunk_id: int
    chunk_index: int
    text: str
    score: float = Field(
        description="Cosine similarity in [-1, 1]; higher is more relevant."
    )


class SearchResponse(BaseModel):
    """Ranked semantic-search results for a query."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "how should configuration be managed",
                "count": 1,
                "results": [
                    {
                        "document_id": 1,
                        "document_title": "Twelve-Factor Configuration",
                        "chunk_id": 3,
                        "chunk_index": 0,
                        "text": "Store configuration in the environment...",
                        "score": 0.62,
                    }
                ],
            }
        }
    )

    query: str
    count: int
    results: list[SearchHit]


class AskRequest(BaseModel):
    """Question payload for extractive Q&A."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"question": "Where should configuration be stored?"}
        }
    )

    question: str = Field(min_length=1, max_length=2000)
    top_k: int | None = Field(
        default=None,
        ge=1,
        le=10,
        description="How many passages to consider (defaults to server config).",
    )


class Citation(BaseModel):
    """A source passage supporting an extractive answer."""

    document_id: int
    document_title: str
    chunk_id: int
    text: str
    score: float


class AskResponse(BaseModel):
    """Extractive answer with source citations.

    The answer is the most relevant passage(s) drawn verbatim from the
    indexed corpus. There is no generative model in the loop, so every
    answer is fully grounded in and traceable to its citations.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "Where should configuration be stored?",
                "answer": "Store configuration in the environment...",
                "found": True,
                "citations": [
                    {
                        "document_id": 1,
                        "document_title": "Twelve-Factor Configuration",
                        "chunk_id": 3,
                        "text": "Store configuration in the environment...",
                        "score": 0.62,
                    }
                ],
            }
        }
    )

    question: str
    answer: str
    found: bool = Field(
        description="False when no passage clears the relevance threshold."
    )
    citations: list[Citation]
