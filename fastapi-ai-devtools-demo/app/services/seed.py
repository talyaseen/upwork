"""Seed the corpus on first startup."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.corpus.seed_data import SEED_DOCUMENTS
from app.services.search_service import SearchService, count_documents

logger = logging.getLogger("app.seed")


async def seed_corpus_if_empty(
    session: AsyncSession, search: SearchService
) -> int:
    """Ingest the built-in corpus when the database has no documents.

    Returns the number of documents ingested (0 if the corpus already
    contained data).
    """
    existing = await count_documents(session)
    if existing > 0:
        logger.info("Corpus already populated (%d documents); skipping seed.",
                    existing)
        return 0

    ingested = 0
    for doc in SEED_DOCUMENTS:
        await search.ingest_document(
            session,
            title=doc["title"],
            text=doc["text"],
            source="seed",
        )
        ingested += 1
    await session.commit()
    logger.info("Seeded %d documents into the corpus.", ingested)
    return ingested
