"""Word-window text chunking with overlap.

A simple, language-agnostic splitter: it breaks text into windows of
``chunk_size`` words with ``overlap`` words shared between neighbours so that
sentences spanning a boundary remain retrievable. Good enough for a demo
corpus and easy to reason about; swap in a sentence-aware splitter later
without touching the rest of the pipeline.
"""

from __future__ import annotations


def chunk_text(
    text: str,
    chunk_size: int = 90,
    overlap: int = 20,
) -> list[str]:
    """Split ``text`` into overlapping word windows.

    Returns a list of non-empty chunk strings. A document shorter than one
    window yields a single chunk.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be in [0, chunk_size)")

    words = text.split()
    if not words:
        return []
    if len(words) <= chunk_size:
        return [" ".join(words)]

    step = chunk_size - overlap
    chunks: list[str] = []
    for start in range(0, len(words), step):
        window = words[start : start + chunk_size]
        if not window:
            break
        chunks.append(" ".join(window))
        if start + chunk_size >= len(words):
            break
    return chunks
