"""Unit tests for the loop-detection circuit breaker (2026-07-01 incident fix).

Pure-function tests for ``has_repetition_loop`` in isolation, no app/model/DB
involved. See ``tests/test_chat.py::test_chat_stops_early_on_repetition_loop``
for the full end-to-end regression pin (streamed answer actually truncated,
finish_reason recorded as ``repetition_stopped``).
"""

from __future__ import annotations

from app.services.chat_service import has_repetition_loop


def test_has_repetition_loop_detects_repeated_sentence() -> None:
    sentence = "This is a repeated sentence that is long enough to count. "
    text = sentence * 3
    assert has_repetition_loop(text) is True


def test_has_repetition_loop_detects_repeated_sentence_with_more_repeats() -> None:
    sentence = "The system keeps repeating this exact same answer forever. "
    text = sentence * 6
    assert has_repetition_loop(text) is True


def test_has_repetition_loop_false_for_varied_sentences() -> None:
    text = (
        "First point about horizontal scaling. "
        "Second point about idempotency keys. "
        "Third point about retry safety. "
    )
    assert has_repetition_loop(text) is False


def test_has_repetition_loop_ignores_short_fragments() -> None:
    # Short repeated fragments (list markers, "Yes."/"No.") are NOT loops.
    text = "Yes. Yes. Yes. Yes. "
    assert has_repetition_loop(text) is False


def test_has_repetition_loop_false_before_min_repeats() -> None:
    # Only two repeats so far - not yet a confirmed loop.
    sentence = "This is a repeated sentence that is long enough to count. "
    text = sentence * 2
    assert has_repetition_loop(text) is False


def test_has_repetition_loop_false_on_empty_text() -> None:
    assert has_repetition_loop("") is False
