"""Semantic search and extractive Q&A routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.core.config import get_settings
from app.core.dependencies import SearchDep
from app.core.sanitize import escape_html
from app.schemas.search import (
    AskRequest,
    AskResponse,
    Citation,
    SearchHit,
    SearchResponse,
)

router = APIRouter(tags=["search"])


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Semantic search over the corpus",
    description=(
        "Embed the query with the local model and return the most similar "
        "chunks ranked by cosine similarity. Matches by meaning, not just "
        "keywords, so a query can surface relevant passages that share no "
        "exact words. Open to all callers."
    ),
)
async def search(
    search_service: SearchDep,
    q: Annotated[
        str,
        Query(
            min_length=1,
            max_length=2000,
            description="Natural-language search query.",
            examples=["how should configuration be managed"],
        ),
    ],
    limit: Annotated[
        int | None,
        Query(ge=1, le=50, description="Max results (defaults to server config)."),
    ] = None,
) -> SearchResponse:
    settings = get_settings()
    effective_limit = limit or settings.default_search_limit
    hits = await search_service.search(q, limit=effective_limit)
    # HTML-escape corpus-derived text on OUTPUT so a browser client can never
    # execute markup that round-tripped through the corpus (stored-XSS defence).
    results = [
        SearchHit(
            document_id=h.meta.document_id,
            document_title=escape_html(h.meta.document_title),
            chunk_id=h.meta.chunk_id,
            chunk_index=h.meta.chunk_index,
            text=escape_html(h.meta.text),
            score=round(h.score, 6),
        )
        for h in hits
    ]
    return SearchResponse(query=q, count=len(results), results=results)


@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Ask a question (extractive answer)",
    description=(
        "Retrieve the most relevant passages and return the best one verbatim "
        "as an extractive answer, with citations to its source documents. No "
        "generative model is involved, so every answer is grounded in and "
        "traceable to the indexed corpus."
    ),
)
async def ask(
    payload: AskRequest,
    search_service: SearchDep,
) -> AskResponse:
    settings = get_settings()
    top_k = payload.top_k or settings.ask_top_k
    found, hits = await search_service.ask(payload.question, top_k=top_k)

    # HTML-escape corpus-derived text on OUTPUT (stored-XSS defence). The answer
    # is drawn from the same escaped passage as citation[0], so they stay equal.
    citations = [
        Citation(
            document_id=h.meta.document_id,
            document_title=escape_html(h.meta.document_title),
            chunk_id=h.meta.chunk_id,
            text=escape_html(h.meta.text),
            score=round(h.score, 6),
        )
        for h in hits
    ]

    if found:
        answer = escape_html(hits[0].meta.text)
    else:
        answer = (
            "No passage in the knowledge base was relevant enough to answer "
            "this question confidently."
        )

    return AskResponse(
        question=payload.question,
        answer=answer,
        found=found,
        citations=citations if found else [],
    )
