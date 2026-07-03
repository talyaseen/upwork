"""Public-safe, per-session self-learning surface.

OpenJarvis ships a learning loop (Capability-Evolver / ACE / GEPA / LoRA / GRPO)
that logs runtime traces, detects inefficiencies, and can fine-tune models. On a
PUBLIC, untrusted endpoint that full loop is a poisoning and privacy vector and
would touch the training GPUs, so we DO NOT run OpenJarvis's trainers/optimizers
here. Instead we implement the SAFE half of that idea:

- Log SANITIZED per-request traces (derived metadata ONLY - which skill, which
  backend tier, retrieved-chunk count, whether a fallback/queue happened, message
  LENGTH - never the raw visitor text). This makes poisoning and PII leakage
  impossible: there is no untrusted text to replay.
- Derive structured improvement PROPOSALS from the session's traces with simple,
  deterministic heuristics (no LLM, no GPU). Proposals are surfaced to the UI so
  the agent visibly "learns", but they are HUMAN-IN-THE-LOOP: nothing is ever
  auto-applied, and they never modify global config, models, or other sessions.
- State is PER-SESSION, ephemeral (TTL + capacity caps), and demo-scoped.

So: per-session adaptation is demonstrated; global model/weight changes from
public input are impossible; proposals are operator-approval-gated by design.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import asdict, dataclass, field

from app.core.config import Settings


@dataclass(slots=True)
class Trace:
    """A sanitized record of one request (NO raw user text)."""

    ts: float
    skill: str
    tier: str
    model: str
    retrieved: int
    grounded: bool
    had_notice: bool
    queued: bool
    message_chars: int  # length only, never the content


@dataclass(slots=True)
class Proposal:
    """A human-in-the-loop improvement proposal. NEVER auto-applied."""

    id: str
    title: str
    rationale: str
    suggested_change: str
    status: str = "proposed"  # always "proposed" here
    requires_operator_approval: bool = True


def generate_proposals(traces: list[Trace]) -> list[Proposal]:
    """Deterministic, metadata-only heuristics -> improvement proposals."""
    proposals: list[Proposal] = []
    if not traces:
        return proposals

    demo_offline = sum(1 for t in traces if t.had_notice)
    if demo_offline >= 2:
        proposals.append(
            Proposal(
                id="gpu-contention",
                title="Demo was offline for several requests this session",
                rationale=(
                    f"{demo_offline} request(s) arrived while the demo was offline "
                    "because the GPUs were serving model training (GPU-only: there "
                    "is no CPU fallback)."
                ),
                suggested_change=(
                    "Schedule training windows around demo traffic, or add a second "
                    "GPU node so the live demo stays online during training."
                ),
            )
        )

    zero_retrieval = sum(1 for t in traces if t.grounded and t.retrieved == 0)
    if zero_retrieval >= 1:
        proposals.append(
            Proposal(
                id="empty-retrieval",
                title="Some grounded questions retrieved no context",
                rationale=(
                    f"{zero_retrieval} grounded question(s) returned 0 corpus "
                    "chunks, so the answer was ungrounded."
                ),
                suggested_change=(
                    "Expand the demo corpus or lower the retrieval threshold so "
                    "these questions are grounded."
                ),
            )
        )

    if any(t.queued for t in traces):
        proposals.append(
            Proposal(
                id="queue-pressure",
                title="Requests waited in the generation queue",
                rationale="At least one request had to wait for a free slot.",
                suggested_change=(
                    "Raise GEN_MAX_CONCURRENT or add a CPU replica if waits "
                    "become common (RAM permitting)."
                ),
            )
        )

    # Repeated use of one skill -> suggest pre-loading / caching it.
    by_skill: dict[str, int] = {}
    for t in traces:
        by_skill[t.skill] = by_skill.get(t.skill, 0) + 1
    for skill, n in by_skill.items():
        if n >= 3:
            proposals.append(
                Proposal(
                    id=f"hot-skill-{skill}",
                    title=f"'{skill}' used repeatedly this session",
                    rationale=f"The '{skill}' skill was used {n} times.",
                    suggested_change=(
                        f"Pre-load / cache the '{skill}' path to reduce latency "
                        "for repeat use."
                    ),
                )
            )
    return proposals


class SessionLearningStore:
    """In-memory, per-session, ephemeral trace store + proposal surface."""

    def __init__(self, settings: Settings) -> None:
        self._max_sessions = settings.learning_max_sessions
        self._max_traces = settings.learning_max_traces_per_session
        self._ttl = settings.learning_session_ttl_seconds
        self._sessions: OrderedDict[str, list[Trace]] = OrderedDict()
        self._lock = threading.Lock()

    def _prune_locked(self, now: float) -> None:
        # Drop expired sessions, then enforce the session-count cap (LRU).
        expired = [
            sid
            for sid, traces in self._sessions.items()
            if traces and (now - traces[-1].ts) > self._ttl
        ]
        for sid in expired:
            self._sessions.pop(sid, None)
        while len(self._sessions) > self._max_sessions:
            self._sessions.popitem(last=False)

    def record(self, session_id: str, trace: Trace) -> None:
        with self._lock:
            now = trace.ts
            self._prune_locked(now)
            traces = self._sessions.get(session_id)
            if traces is None:
                traces = []
                self._sessions[session_id] = traces
            self._sessions.move_to_end(session_id)
            traces.append(trace)
            if len(traces) > self._max_traces:
                del traces[: len(traces) - self._max_traces]

    def traces(self, session_id: str) -> list[Trace]:
        with self._lock:
            return list(self._sessions.get(session_id, []))

    def proposals(self, session_id: str) -> list[Proposal]:
        return generate_proposals(self.traces(session_id))

    def summary(self, session_id: str) -> dict:
        traces = self.traces(session_id)
        proposals = generate_proposals(traces)
        return {
            "session_id": session_id,
            "observed_requests": len(traces),
            "proposals": [asdict(p) for p in proposals],
            "note": (
                "Per-session and ephemeral. Proposals are suggestions only and "
                "require operator approval; nothing is auto-applied, and no raw "
                "input is stored or shared across sessions."
            ),
        }


@dataclass(slots=True)
class LearningSummary:
    """Carried in the SSE 'learning' event so the UI can show what was learned."""

    session_id: str
    observed_requests: int
    proposals: list[dict] = field(default_factory=list)
