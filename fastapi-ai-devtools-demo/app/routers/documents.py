"""Document ingestion and CRUD routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import func, select

from app.core.dependencies import DbSession, SearchDep
from app.core.internal_gate import require_internal
from app.db.models import Chunk, Document
from app.schemas.document import (
    DocumentCreate,
    DocumentDetail,
    DocumentList,
    DocumentSummary,
    IngestResult,
)

router = APIRouter(prefix="/documents", tags=["documents"])


async def _chunk_count(session: DbSession, document_id: int) -> int:
    result = await session.execute(
        select(func.count())
        .select_from(Chunk)
        .where(Chunk.document_id == document_id)
    )
    return int(result.scalar_one())


@router.post(
    "",
    response_model=IngestResult,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest and index a document (internal only)",
    description=(
        "Submit a title and body. The text is split into overlapping chunks, "
        "each chunk is embedded with the local model, and the vectors are "
        "added to the shared search index that the public /search and /ask "
        "serve. Because this write mutates the corpus every visitor sees, it is "
        "INTERNAL-ONLY: restricted to the operator/curator network (peer-IP "
        "allowlist + admin token), NEVER reachable by public/self-registered "
        "users. The public demo therefore runs on the curated seed corpus only."
    ),
    dependencies=[Depends(require_internal)],
)
async def ingest_document(
    payload: DocumentCreate,
    session: DbSession,
    search: SearchDep,
) -> IngestResult:
    document, chunk_count = await search.ingest_document(
        session, title=payload.title, text=payload.text, source="user"
    )
    return IngestResult(
        id=document.id, title=document.title, chunk_count=chunk_count
    )


@router.get(
    "",
    response_model=DocumentList,
    summary="List documents (paginated)",
    description="Return document summaries ordered by newest first.",
)
async def list_documents(
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DocumentList:
    total_result = await session.execute(
        select(func.count()).select_from(Document)
    )
    total = int(total_result.scalar_one())

    result = await session.execute(
        select(
            Document.id,
            Document.title,
            Document.source,
            Document.created_at,
            func.count(Chunk.id).label("chunk_count"),
        )
        .outerjoin(Chunk, Chunk.document_id == Document.id)
        .group_by(Document.id)
        .order_by(Document.id.desc())
        .limit(limit)
        .offset(offset)
    )
    items = [
        DocumentSummary(
            id=row.id,
            title=row.title,
            source=row.source,
            created_at=row.created_at,
            chunk_count=int(row.chunk_count),
        )
        for row in result.all()
    ]
    return DocumentList(total=total, limit=limit, offset=offset, items=items)


@router.get(
    "/{document_id}",
    response_model=DocumentDetail,
    summary="Fetch a single document",
)
async def get_document(
    session: DbSession,
    document_id: Annotated[int, Path(ge=1)],
) -> DocumentDetail:
    document = await session.get(Document, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    count = await _chunk_count(session, document_id)
    return DocumentDetail(
        id=document.id,
        title=document.title,
        text=document.text,
        source=document.source,
        created_at=document.created_at,
        chunk_count=count,
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete a document and its chunks (internal only)",
    description="Remove a document from the store and the shared search index. "
    "INTERNAL-ONLY: restricted to the operator/curator network (peer-IP "
    "allowlist + admin token), never reachable by public/self-registered users.",
    dependencies=[Depends(require_internal)],
)
async def delete_document(
    session: DbSession,
    search: SearchDep,
    document_id: Annotated[int, Path(ge=1)],
) -> None:
    deleted = await search.delete_document(session, document_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
