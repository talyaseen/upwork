"""Self-learning store + proposal heuristics (sync unit tests)."""

from __future__ import annotations

import time
from types import SimpleNamespace

from app.services.learning import (
    SessionLearningStore,
    Trace,
    generate_proposals,
)


def _settings(**over):
    base = dict(
        learning_max_sessions=100,
        learning_max_traces_per_session=10,
        learning_session_ttl_seconds=3600.0,
    )
    base.update(over)
    return SimpleNamespace(**base)


def _trace(**over) -> Trace:
    base = dict(
        ts=time.time(),
        skill="qa",
        tier="primary-7b-gpu",
        model="qwen2.5:7b-instruct",
        retrieved=3,
        grounded=True,
        had_notice=False,
        queued=False,
        message_chars=20,
    )
    base.update(over)
    return Trace(**base)


def test_no_proposals_for_empty_history():
    assert generate_proposals([]) == []


def test_gpu_contention_proposal():
    traces = [_trace(had_notice=True), _trace(had_notice=True)]
    assert "gpu-contention" in {p.id for p in generate_proposals(traces)}


def test_empty_retrieval_proposal():
    ids = {p.id for p in generate_proposals([_trace(grounded=True, retrieved=0)])}
    assert "empty-retrieval" in ids


def test_queue_pressure_proposal():
    assert "queue-pressure" in {
        p.id for p in generate_proposals([_trace(queued=True)])
    }


def test_hot_skill_proposal():
    traces = [_trace(skill="mermaid") for _ in range(3)]
    assert "hot-skill-mermaid" in {p.id for p in generate_proposals(traces)}


def test_proposals_are_never_auto_applied():
    traces = [_trace(had_notice=True), _trace(had_notice=True, queued=True)]
    proposals = generate_proposals(traces)
    assert proposals  # something was proposed
    for p in proposals:
        assert p.status == "proposed"
        assert p.requires_operator_approval is True


def test_store_is_per_session_isolated():
    store = SessionLearningStore(_settings())
    store.record("a", _trace(skill="qa"))
    store.record("b", _trace(skill="mermaid"))
    assert store.traces("a")[0].skill == "qa"
    assert store.traces("b")[0].skill == "mermaid"
    summ = store.summary("unknown")
    assert summ["observed_requests"] == 0 and summ["proposals"] == []


def test_store_caps_traces_per_session():
    store = SessionLearningStore(_settings(learning_max_traces_per_session=3))
    for _ in range(6):
        store.record("s", _trace())
    assert len(store.traces("s")) == 3


def test_store_expires_old_sessions():
    store = SessionLearningStore(_settings(learning_session_ttl_seconds=0.0))
    store.record("old", _trace(ts=time.time() - 10))
    store.record("new", _trace())
    assert store.traces("old") == []


def test_trace_stores_no_raw_text():
    fields = set(Trace.__dataclass_fields__)
    assert "message" not in fields and "text" not in fields
    assert "message_chars" in fields
