"""Semantic search service: vector index, ingest, search and extractive Q&A.

The durable store of record is SQLite (``chunks`` table). For fast retrieval
the service also keeps an in-process index: a single contiguous float32 matrix
of unit-norm vectors plus an aligned list of lightweight metadata records.
Because vectors are normalised, cosine similarity is a plain matrix-vector
dot product.

All mutations (ingest / delete / rebuild) are serialised by an asyncio lock,
and each mutation atomically swaps in a fresh matrix so concurrent readers
always observe a consistent snapshot. CPU-bound embedding inference is pushed
to a worker thread so it never blocks the event loop.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import numpy as np
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models import Chunk, Document
from app.services.chunking import chunk_text
from app.services.embedding import Embedder

# Minimum cosine similarity for /ask to treat a passage as a real answer.
_ANSWER_THRESHOLD = 0.15


@dataclass(slots=True)
class ChunkMeta:
    """Metadata for one indexed vector row."""

    chunk_id: int
    document_id: int
    document_title: str
    chunk_index: int
    text: str


@dataclass(slots=True)
class ScoredChunk:
    """A chunk paired with its similarity score."""

    meta: ChunkMeta
    score: float


class SearchService:
    """In-process vector index backed by SQLite."""

    def __init__(self, embedder: Embedder, settings: Settings) -> None:
        self._embedder = embedder
        self._settings = settings
        self._lock = asyncio.Lock()
        self._vectors: np.ndarray = np.zeros(
            (0, embedder.dimension), dtype=np.float32
        )
        self._meta: list[ChunkMeta] = []

    # -- lifecycle --------------------------------------------------------

    @property
    def dimension(self) -> int:
        return self._embedder.dimension

    @property
    def size(self) -> int:
        """Number of indexed chunks currently in memory."""
        return len(self._meta)

    async def load_index(self, session: AsyncSession) -> None:
        """Rebuild the in-memory index from all persisted chunks."""
        result = await session.execute(
            select(
                Chunk.id,
                Chunk.document_id,
                Chunk.chunk_index,
                Chunk.text,
                Chunk.embedding,
                Chunk.dim,
                Document.title,
            ).join(Document, Document.id == Chunk.document_id)
        )
        rows = result.all()
        meta: list[ChunkMeta] = []
        vectors: list[np.ndarray] = []
        for cid, doc_id, idx, text, blob, dim, title in rows:
            vectors.append(np.frombuffer(blob, dtype=np.float32, count=dim))
            meta.append(
                ChunkMeta(
                    chunk_id=cid,
                    document_id=doc_id,
                    document_title=title,
                    chunk_index=idx,
                    text=text,
                )
            )
        async with self._lock:
            self._meta = meta
            self._vectors = (
                np.vstack(vectors).astype(np.float32)
                if vectors
                else np.zeros((0, self.dimension), dtype=np.float32)
            )

    # -- embedding helpers -----------------------------------------------

    async def _embed(self, texts: list[str]) -> np.ndarray:
        """Run embedding off the event loop."""
        return await run_in_threadpool(self._embedder.embed, texts)

    # -- ingest -----------------------------------------------------------

    async def ingest_document(
        self,
        session: AsyncSession,
        title: str,
        text: str,
        source: str = "user",
    ) -> tuple[Document, int]:
        """Chunk, embed and index a document. Returns (document, chunk_count).

        The document row is flushed within the caller's transaction; the
        caller is responsible for the surrounding commit. The in-memory index
        is updated only after embedding succeeds.
        """
        chunks = chunk_text(
            text,
            chunk_size=self._settings.chunk_size_words,
            overlap=self._settings.chunk_overlap_words,
        )
        if not chunks:
            raise ValueError("Document produced no chunks (empty text).")

        vectors = await self._embed(chunks)

        document = Document(title=title, text=text, source=source)
        session.add(document)
        await session.flush()  # assign document.id

        chunk_rows: list[Chunk] = []
        for idx, (chunk, vec) in enumerate(zip(chunks, vectors, strict=True)):
            row = Chunk(
                document_id=document.id,
                chunk_index=idx,
                text=chunk,
                embedding=np.ascontiguousarray(vec, dtype=np.float32).tobytes(),
                dim=int(vec.shape[0]),
            )
            session.add(row)
            chunk_rows.append(row)
        await session.flush()  # assign chunk ids

        new_meta = [
            ChunkMeta(
                chunk_id=row.id,
                document_id=document.id,
                document_title=document.title,
                chunk_index=row.chunk_index,
                text=row.text,
            )
            for row in chunk_rows
        ]
        async with self._lock:
            if self._vectors.size:
                self._vectors = np.vstack([self._vectors, vectors]).astype(
                    np.float32
                )
            else:
                self._vectors = vectors.astype(np.float32)
            self._meta.extend(new_meta)

        return document, len(chunk_rows)

    async def delete_document(
        self, session: AsyncSession, document_id: int
    ) -> bool:
        """Delete a document and drop its chunks from the index."""
        document = await session.get(Document, document_id)
        if document is None:
            return False
        await session.execute(
            sa_delete(Chunk).where(Chunk.document_id == document_id)
        )
        await session.delete(document)
        await session.flush()

        async with self._lock:
            keep = [
                i
                for i, m in enumerate(self._meta)
                if m.document_id != document_id
            ]
            self._meta = [self._meta[i] for i in keep]
            self._vectors = (
                self._vectors[keep]
                if keep
                else np.zeros((0, self.dimension), dtype=np.float32)
            )
        return True

    # -- retrieval --------------------------------------------------------

    async def search(self, query: str, limit: int) -> list[ScoredChunk]:
        """Return the top ``limit`` chunks by cosine similarity to ``query``."""
        query = query.strip()
        if not query:
            return []

        # Snapshot the index under the lock so a concurrent mutation cannot
        # desynchronise the matrix and the metadata list.
        async with self._lock:
            vectors = self._vectors
            meta = self._meta
        if len(meta) == 0:
            return []

        q = (await self._embed([query]))[0]
        scores = vectors @ q  # both sides are unit-norm => cosine similarity

        k = min(limit, len(meta))
        # argpartition for the top-k, then sort just those by score desc.
        top_idx = np.argpartition(-scores, k - 1)[:k]
        top_idx = top_idx[np.argsort(-scores[top_idx])]

        return [
            ScoredChunk(meta=meta[i], score=float(scores[i])) for i in top_idx
        ]

    async def ask(
        self, question: str, top_k: int
    ) -> tuple[bool, list[ScoredChunk]]:
        """Retrieve the best passages for an extractive answer.

        Returns (found, scored_chunks). ``found`` is False when the best
        passage does not clear the relevance threshold.
        """
        hits = await self.search(question, limit=top_k)
        if not hits or hits[0].score < _ANSWER_THRESHOLD:
            return False, hits
        return True, hits


async def count_documents(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(Document))
    return int(result.scalar_one())
