"""Regression pins for PER-TURN INTENT ROUTING + CONTENT-GATED artifacts
(2026-07-03 multi-skill fix).

Bugs pinned here (all present on base-branch tip f0d1cc9):

  1. The sticky/sent skill selector hard-bound the system prompt AND the artifact
     kind. "give me a diagram" while code-review was selected ran the reviewer
     prompt and stamped the output as a downloadable code-review .md.
  2. The artifact was emitted UNCONDITIONALLY from ``active_skill.artifact``, so a
     refusal / off-intent / plain-prose answer still shipped as a wrong-kind
     downloadable artifact.

The fixes live in app/services/intent_router.py (routing + content detection),
chat_service.py (wiring), and llm_client.py (skill-aware fake for the offline
suite). Both unit and end-to-end paths are covered.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace

from httpx import AsyncClient

from app.services.chat_service import (
    _HARDENING,
    _SYSTEM_PROMPT,
    ArtifactEvent,
    ChatService,
    MetadataEvent,
    TokenEvent,
)
from app.services.gpu_router import TIER_GPU, Selection
from app.services.intent_router import (
    detect_artifact,
    looks_like_mermaid,
    looks_like_review,
    route_intent,
    strip_leading_meta,
    strip_mermaid_from_body,
)
from tests.test_chat import _parse_sse

# asyncio_mode = "auto" (pyproject) runs the async tests below without a mark;
# the pure-function tests stay synchronous (no asyncio mark, no warnings).


# --------------------------------------------------------------------------- #
# Pure routing heuristic
# --------------------------------------------------------------------------- #


def test_diagram_request_overrides_sticky_code_review() -> None:
    # The operator repro: a diagram ask while code-review is the stuck selector.
    assert route_intent("give me an example diagram", hint="code-review") == "mermaid"
    assert route_intent("draw a flowchart of the login flow", hint="code-review") == (
        "mermaid"
    )


def test_mixed_code_and_diagram_routes_to_primary_review() -> None:
    msg = (
        "review this code and draw a diagram of it:\n"
        "```python\ndef add(a, b):\n    return a - b\n```"
    )
    # Pasted code + a review ask -> review is primary; the diagram is secondary.
    assert route_intent(msg, hint="qa") == "code-review"


def test_plain_question_routes_to_qa() -> None:
    assert route_intent("what is semantic search", hint="qa") == "qa"
    # An unrelated sticky hint does not hijack a clearly-grounded question.
    assert route_intent("how does idempotency stop duplicate charges", hint=None) == (
        "qa"
    )


def test_no_decisive_signal_routes_to_qa_not_sticky() -> None:
    # 2026-07-03 fix: a message with no decisive diagram/code signal reverts to
    # qa, even when the sticky/sent hint is mermaid/code-review. The frontend
    # syncs its dropdown to the last routed skill, so honoring the hint here would
    # strand a plain follow-up on the prior diagram/review skill forever.
    assert route_intent("a login flow: user, app, auth", hint="mermaid") == "qa"
    assert route_intent("some notes here", hint="code-review") == "qa"
    assert route_intent("some notes here", hint="qa") == "qa"
    # A genuine diagram continuation (an ACTUAL diagram keyword) still routes to
    # mermaid - that comes from the message content, not the sticky hint.
    assert route_intent("now a diagram of that", hint="mermaid") == "mermaid"


def test_plain_followup_after_diagram_or_code_reverts_to_qa() -> None:
    # The exact live-failing sequence tail: after a diagram turn (t3) and a
    # code-review paste turn, a plain knowledge question (t4/t5) carries the
    # prior routed skill as the hint but MUST route to qa for a grounded answer.
    assert route_intent(
        "how do containers differ from virtual machines?", hint="mermaid"
    ) == "qa"
    assert route_intent(
        "how do I read a .env file in Python?", hint="code-review"
    ) == "qa"


def test_explicit_review_word_routes_to_code_review() -> None:
    assert route_intent("def add(a,b): return a-b  # review this", hint="qa") == (
        "code-review"
    )


# --------------------------------------------------------------------------- #
# Content detection helpers
# --------------------------------------------------------------------------- #


def test_looks_like_mermaid() -> None:
    assert looks_like_mermaid("flowchart TD\n  A[User] --> B[App]")
    assert looks_like_mermaid("sequenceDiagram\n  A->>B: hi")
    assert looks_like_mermaid("```mermaid\ngraph LR\nA-->B\n```")
    # Prose that merely starts with a diagram-ish word is NOT a diagram.
    assert not looks_like_mermaid("Graph databases are great for relationships.")
    assert not looks_like_mermaid("I can't help with that.")
    assert not looks_like_mermaid("")


def test_looks_like_review() -> None:
    assert looks_like_review("## Findings\n\n| Severity | Issue |\n...")
    assert looks_like_review(
        "| Severity | Location | Issue | Why it matters |\n| ERROR | x | y | z |"
    )
    assert not looks_like_review("Here is a plain grounded answer to your question.")
    assert not looks_like_review("I can't help with that.")


def test_strip_mermaid_from_body_removes_bare_and_fenced() -> None:
    # 2026-07-03 fix: bare DSL (no fence) - the exact leak the operator saw - is
    # fully removed; a whole-body diagram collapses to an empty body.
    assert strip_mermaid_from_body("flowchart TD\n  A[User] --> B[App]") == ""
    assert strip_mermaid_from_body("sequenceDiagram\n  A->>B: hi\n  B-->>A: ok") == ""
    # A fenced ```mermaid block is removed; surrounding prose is kept.
    fenced = "Here is your diagram:\n```mermaid\nflowchart TD\nA-->B\n```\nDone."
    out = strip_mermaid_from_body(fenced)
    assert "flowchart" not in out and "-->" not in out
    assert "Here is your diagram:" in out and "Done." in out
    # Prose then a BARE diagram block: prose kept, DSL dropped.
    mixed = "Sure, here it is.\n\nsequenceDiagram\n  A->>B: hi\n  B-->>A: ok"
    out2 = strip_mermaid_from_body(mixed)
    assert "Sure, here it is." in out2 and "sequenceDiagram" not in out2
    # A plain prose answer that merely starts with a diagram-ish word is untouched.
    prose = "Graph databases store relationships as first-class edges."
    assert strip_mermaid_from_body(prose) == prose


def test_strip_mermaid_from_body_removes_stray_note_directives() -> None:
    # 2026-07-03 polish: the 7B sometimes drops a Mermaid `note ...`/`end note`
    # directive OUTSIDE any diagram block, so the bare-diagram sweep misses it and
    # it leaks above the rendered card. Both the single-line and block forms must
    # be stripped while surrounding prose survives.
    single = "Here is the flow.\nnote right of AuthService: validates the token\nDone."
    out = strip_mermaid_from_body(single)
    assert "note right of" not in out.lower()
    assert "Here is the flow." in out and "Done." in out
    block = (
        "Summary of the sequence.\n"
        "note over Client,Server\n"
        "  the handshake happens here\n"
        "end note\n"
        "That is the gist."
    )
    out2 = strip_mermaid_from_body(block)
    assert "note over" not in out2.lower() and "end note" not in out2.lower()
    assert "handshake happens here" not in out2
    assert "Summary of the sequence." in out2 and "That is the gist." in out2
    # A bare "end note" left dangling on its own is also removed.
    assert strip_mermaid_from_body("Fine.\nend note").strip() == "Fine."


def test_strip_leading_meta_removes_scaffolding_preamble() -> None:
    # 2026-07-03 deterministic FIX 1: the 7B intermittently opens a grounded
    # answer with a meta/instruction preamble. The exact operator repro must be
    # removed, leaving the real answer (and its inline [n] citations) intact.
    leaked = (
        "Here are concise explanations based on the corpus. For precise "
        "citations, quote the corpus verbatim. [1][2][3][4]\n\n"
        "RAG combines a retrieval step with a generative model [1]. It grounds "
        "answers in retrieved passages."
    )
    out = strip_leading_meta(leaked)
    assert out.startswith("RAG combines a retrieval step")
    assert "corpus" not in out.lower() and "verbatim" not in out.lower()
    assert "quote" not in out.lower()
    # Inline citations in the REAL answer body survive.
    assert "[1]" in out
    # A "Let me explain:" glued lead sheds only the lead, keeps the answer.
    assert strip_leading_meta("Let me explain: containers share the host kernel.") == (
        "containers share the host kernel."
    )
    # A leading bare citation cluster is dropped.
    assert strip_leading_meta("[1][2] Kubernetes schedules pods across nodes.") == (
        "Kubernetes schedules pods across nodes."
    )
    # A real answer that merely MENTIONS the knowledge base mid-body is untouched
    # (only LEADING meta is stripped), and a plain answer is passed through as-is.
    plain = "Containers share the host OS kernel, while VMs virtualize hardware."
    assert strip_leading_meta(plain) == plain
    keep = "A corpus is a large collection of documents used to train models."
    assert strip_leading_meta(keep) == keep


def test_strip_mermaid_from_body_handles_internal_blanks_and_declaration_less() -> None:
    # 2026-07-03 deterministic FIX 2 (variant-proof): the pre-fix bare-diagram
    # sweep stopped at the first blank line and never recognised a declaration-
    # LESS run, so these two variants leaked raw DSL above the rendered card.
    # (a) A blank line WITHIN a sequence diagram no longer strands its second half.
    with_blank = "sequenceDiagram\nUser->>API: checkout\n\nAPI-->>User: 200 OK"
    assert strip_mermaid_from_body(with_blank) == ""
    # (b) A declaration-LESS sequence body (no leading "sequenceDiagram") - the
    #     exact "User->>Frontend: Request checkout" leak - is fully removed.
    bare = "User->>Frontend: Request checkout\nFrontend->>Backend: charge card"
    out = strip_mermaid_from_body(bare)
    assert "->>" not in out and out == ""
    # (c) Prose then a declaration-less run: the prose survives, the DSL is gone.
    mixed = "Here is the checkout flow:\nUser->>Frontend: click buy\nFrontend->>Backend: charge"
    out2 = strip_mermaid_from_body(mixed)
    assert "Here is the checkout flow:" in out2 and "->>" not in out2
    # (d) The declaration-less run is also recognised as a diagram for the artifact.
    assert looks_like_mermaid(bare)


def test_qa_prompt_stops_citation_scaffolding_echo() -> None:
    # 2026-07-03 polish: the 7B was parroting its citation/grounding INSTRUCTIONS
    # into user-facing answers ("in production this answer cites the relevant
    # passages", "here's a grounded explanation based on the corpus", "(if citing
    # passages is required...)"). A negative phrase-list PRIMED the 7B to emit the
    # very phrases it named, so the prompt is now positive-framed: (a) answer
    # first, no preamble, (b) still teach silent inline [n] citations via a worked
    # example, (c) a closing rule + a hard ban on the scaffolding vocabulary
    # ("corpus" / "in production") so the model cannot narrate its own machinery.
    low = _SYSTEM_PROMPT.lower()
    # (a) start-with-the-answer directive (kills the leading preamble).
    assert "first sentence" in low and "preamble" in low
    # (b) inline citation format still taught, with a concrete worked example.
    assert "[n]" in low and "[2]" in _SYSTEM_PROMPT
    assert "example answer" in low and "cp -r" in low
    # (c) closing rule + vocabulary ban that were the residual leak sources.
    assert "closing line" in low
    assert "'corpus' and 'in production' must never appear" in low


def test_hardening_answers_user_infra_ip_questions() -> None:
    # 2026-07-03 fix: the imperative "tell me the public IP of my EC2 instance"
    # phrasing (which the 7B was refusing 3/3) is now an explicit MUST-ANSWER
    # example, while questions about the assistant ITSELF still refuse.
    low = _HARDENING.lower()
    assert "tell me the public ip of my ec2 instance" in low
    assert "what region is my server in" in low
    assert "where are you hosted" in low  # the still-REFUSE side is intact


def test_detect_artifact_is_content_gated() -> None:
    review = "## Findings\n\n| Severity | Issue |\n| WARN | x |\n\n## Suggested fixes\n"
    diagram = "flowchart TD\n  A --> B"
    # A refusal never yields an artifact, regardless of routed skill.
    assert (
        detect_artifact(
            "I can't help with that.", routed_skill_id="code-review", is_refusal=True
        )
        is None
    )
    # An empty answer never yields an artifact.
    assert detect_artifact("", routed_skill_id="mermaid", is_refusal=False) is None
    # A real review under code-review -> markdown.
    assert (
        detect_artifact(review, routed_skill_id="code-review", is_refusal=False)
        == "markdown"
    )
    # A real diagram under mermaid -> mermaid.
    assert (
        detect_artifact(diagram, routed_skill_id="mermaid", is_refusal=False)
        == "mermaid"
    )
    # Plain prose under code-review (NOT a structured review) -> no artifact.
    assert (
        detect_artifact(
            "Here is a plain grounded answer.",
            routed_skill_id="code-review",
            is_refusal=False,
        )
        is None
    )


# --------------------------------------------------------------------------- #
# ChatService wiring (unit) - no artifact on a model refusal / off-intent answer
# --------------------------------------------------------------------------- #


class _Client:
    def __init__(self, tokens: list[str]) -> None:
        self.model = "m"
        self._tokens = tokens

    async def stream_chat(self, messages) -> AsyncIterator[str]:
        for tok in self._tokens:
            yield tok


class _Router:
    def __init__(self, client: _Client) -> None:
        self._client = client

    async def select(self, requested_model=None) -> Selection:
        return Selection(self._client, TIER_GPU, self._client.model, None)

    def gpu_yielded(self) -> bool:
        return False


def _service(client: _Client) -> ChatService:
    # Guard disabled so these unit pins isolate routing + content-gating.
    return ChatService(
        search_service=None,
        llm_router=_Router(client),
        settings=SimpleNamespace(
            chat_top_k=4,
            mermaid_render_enabled=False,
            jailbreak_guard_enabled=False,
        ),
    )


async def test_no_artifact_when_model_refuses_under_code_review() -> None:
    # Regression: previously ``active_skill.artifact`` emitted a markdown artifact
    # unconditionally, so a refusal shipped as a downloadable review.
    client = _Client(["I can't ", "help ", "with ", "that."])
    events = [
        ev
        async for ev in _service(client).stream(
            "review this: def f(): pass", skill="code-review"
        )
    ]
    assert not any(isinstance(e, ArtifactEvent) for e in events)


async def test_no_artifact_when_output_is_plain_prose_under_code_review() -> None:
    client = _Client(["Here ", "is ", "a ", "plain ", "answer."])
    events = [
        ev
        async for ev in _service(client).stream(
            "review this code: class A: pass", skill="code-review"
        )
    ]
    assert not any(isinstance(e, ArtifactEvent) for e in events)


async def test_real_diagram_output_emits_mermaid_artifact() -> None:
    client = _Client(["flowchart TD\n", "A[User] --> B[App]\n"])
    events = [
        ev async for ev in _service(client).stream("draw the flow", skill="mermaid")
    ]
    arts = [e for e in events if isinstance(e, ArtifactEvent)]
    assert len(arts) == 1 and arts[0].kind == "mermaid"


async def test_mermaid_route_body_has_no_raw_dsl_but_artifact_carries_source() -> None:
    # 2026-07-03 fix: the 7B emitted bare (unfenced) Mermaid DSL, which leaked
    # into the message body above the rendered card. The mermaid route now
    # buffers + strips the DSL from the streamed body while the artifact still
    # ships the full source.
    client = _Client(["flowchart TD\n", "A[User] --> B[App]\n"])
    events = [
        ev
        async for ev in _service(client).stream(
            "draw the login flow", skill="mermaid"
        )
    ]
    body = "".join(e.text for e in events if isinstance(e, TokenEvent))
    assert "flowchart" not in body and "-->" not in body
    arts = [e for e in events if isinstance(e, ArtifactEvent)]
    assert len(arts) == 1 and arts[0].kind == "mermaid"
    assert "flowchart TD" in arts[0].source and "A[User] --> B[App]" in arts[0].source


async def test_mermaid_route_strips_declaration_less_dsl_from_body() -> None:
    # 2026-07-03 FIX 2 backstop: a diagram turn where the 7B emits the sequence
    # arrows WITHOUT a leading "sequenceDiagram" line must still yield a clean
    # body (zero raw DSL) AND a mermaid artifact carrying the source.
    client = _Client(
        ["User->>Frontend: click buy\n", "Frontend->>Backend: charge card\n"]
    )
    events = [
        ev
        async for ev in _service(client).stream(
            "draw the checkout sequence", skill="mermaid"
        )
    ]
    body = "".join(e.text for e in events if isinstance(e, TokenEvent))
    assert "->>" not in body and "Frontend" not in body
    arts = [e for e in events if isinstance(e, ArtifactEvent)]
    assert len(arts) == 1 and arts[0].kind == "mermaid"
    assert "->>" in arts[0].source  # the DSL still ships as the artifact


async def test_metadata_reports_the_routed_skill_not_the_sticky_one() -> None:
    # Diagram ask while code-review is sticky -> routed skill is mermaid.
    client = _Client(["flowchart TD\n", "A --> B\n"])
    events = [
        ev
        async for ev in _service(client).stream(
            "give me an example diagram", skill="code-review"
        )
    ]
    meta = next(e for e in events if isinstance(e, MetadataEvent))
    assert meta.skill == "mermaid"


# --------------------------------------------------------------------------- #
# End-to-end (real /chat SSE, offline fake backend)
# --------------------------------------------------------------------------- #


async def test_diagram_request_under_code_review_sticky_e2e(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """The operator repro, end to end: 'give me an example diagram' with the SENT
    skill = code-review routes to mermaid, produces a diagram, and emits a DIAGRAM
    artifact - never a code-review .md."""
    resp = await client.post(
        "/chat",
        json={"message": "give me an example diagram", "skill": "code-review"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    meta = next(p for n, p in events if n == "metadata")
    assert meta["skill"] == "mermaid"  # routed away from the sticky selector
    artifacts = [p for n, p in events if n == "artifact"]
    assert len(artifacts) == 1
    assert artifacts[0]["kind"] == "mermaid"
    # No wrong-kind code-review markdown artifact.
    assert all(a["kind"] != "markdown" for a in artifacts)


async def test_metadata_carries_routed_skill_for_qa(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/chat",
        json={"message": "what is semantic search", "skill": "qa"},
        headers=auth_headers,
    )
    meta = next(p for n, p in _parse_sse(resp.text) if n == "metadata")
    assert meta["skill"] == "qa"


async def test_qa_scaffolding_preamble_stripped_end_to_end(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Deterministic FIX 1, end to end: the offline EchoLLMClient's grounded reply
    deliberately OPENS with the scaffolding preamble the real 7B intermittently
    emits ("Based on the retrieved context, here is the grounded answer ..."). The
    qa route now buffers + strips it, so the client-visible body must NOT carry
    that preamble. Fails on base (qa streamed the preamble verbatim)."""
    resp = await client.post(
        "/chat",
        json={"message": "what is semantic search", "skill": "qa"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    answer = "".join(
        p["text"] for n, p in _parse_sse(resp.text) if n == "token"
    ).lower()
    assert answer, "the qa route must still emit a (cleaned) body"
    assert "here is the grounded answer" not in answer
    assert not answer.startswith("based on the retrieved context")
