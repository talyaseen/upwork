"""Per-turn intent ROUTING + CONTENT-GATED artifact detection.

The frontend ships a STICKY manual skill selector, but the user's real intent
changes turn to turn: they ask for a diagram while "code-review" is still the
selected mode, mix "review this and draw it", then go back to a knowledge-base
question - all WITHOUT flipping the dropdown. Trusting the sticky selector as the
sole truth bound BOTH the system prompt AND the emitted artifact to the wrong
skill. The visible failures:

  * "give me a diagram" under a stuck code-review mode ran the REVIEWER prompt
    (so the model refused / produced a non-diagram) AND stamped that output as a
    downloadable code-review .md/.pdf.
  * A mixed "review this code and draw a diagram" turn produced ONE wrong-kind
    artifact holding both.

Fix, two halves, both here (chat_service.py wires them in):

1. ``route_intent`` classifies EACH incoming message FRESH into a skill id
   (``qa`` / ``code-review`` / ``mermaid``) with a lightweight deterministic
   heuristic. The sticky/sent skill is only a HINT/tiebreaker, never the sole
   truth, so a "draw me a diagram" turn routes to the diagram skill even while
   the selector still says code-review.

2. ``detect_artifact`` decides the artifact kind from what the model ACTUALLY
   produced (a real Mermaid diagram, a real structured review, or nothing) -
   decoupled from the skill. A refusal / empty / off-intent answer ships NO
   artifact, which kills both the refusal-as-download and the mixed-artifact
   cases.

Deterministic-first, no extra model round-trip: small, well-separated keyword and
structural signals classify the vast majority of turns correctly and the sent
skill breaks genuine ties. That is cheaper, lower-latency, and more predictable
than an LLM routing preamble on every turn, and it was live-tuned against the
real 7B (openjarvis-7b). If a future need for genuinely-ambiguous disambiguation
appears, a cheap LLM classifier can slot in behind ``route_intent`` as a final
tiebreaker without changing its callers.
"""

from __future__ import annotations

import re

from app.services.mermaid_render import extract_mermaid_source

VALID_SKILLS = frozenset({"qa", "code-review", "mermaid"})

# --- Intent signals --------------------------------------------------------

# A diagram/visual deliverable is the most SPECIFIC single ask, so its keywords
# are matched precisely. "flow" alone is NOT here (too generic - it appears in
# ordinary prose like "auth flow"); a bare "a login flow" carries no decisive
# diagram signal, so it now routes to qa (see route_intent step 4) rather than
# sticking to a previously-selected diagram mode.
_DIAGRAM_KW_RE = re.compile(
    r"\b("
    r"mermaid|diagram|flow ?chart|flow diagram|sequence diagram|class diagram|"
    r"er diagram|entity[- ]relationship|state diagram|state machine|"
    r"architecture diagram|uml|gantt|mind ?map|org chart|swimlane|graphviz"
    r")\b",
    re.IGNORECASE,
)
# Imperative verbs that, on their own, mean "produce a picture".
_DRAW_VERB_RE = re.compile(
    r"\b(draw|sketch|visuali[sz]e|illustrate)\b",
    re.IGNORECASE,
)

# A code / DevOps review ask.
_REVIEW_RE = re.compile(
    r"\b("
    r"review|audit|critique|refactor|lint|code smell|vulnerabilit|"
    r"find (?:the )?bugs?|any bugs?|security (?:issue|issues|review)|"
    r"improve this code|what'?s wrong with|check this code"
    r")\b",
    re.IGNORECASE,
)

# Structural signals that the message CONTAINS pasted code (something to review).
_CODE_HINT_RE = re.compile(
    r"(?:^|\n)\s*(?:def |class |function |import |from \w+ import|#include|"
    r"public |private |protected |const |let |var |return |async def|"
    r"package |func |fn |<\?php|SELECT |CREATE TABLE)"
    r"|=>|::|\{\s*$|\}\s*$|;\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _wants_diagram(text: str) -> bool:
    return bool(_DIAGRAM_KW_RE.search(text) or _DRAW_VERB_RE.search(text))


def _wants_review(text: str) -> bool:
    return bool(_REVIEW_RE.search(text))


def _has_code_block(text: str) -> bool:
    """Conservative: a fenced block, or multi-line text with >=2 code signals.

    Deliberately strict so a single inline snippet inside an otherwise ordinary
    question (``why does `x = 1/0` throw?``) does NOT force the review path."""
    if "```" in text:
        return True
    if text.count("\n") < 2:
        return False
    return len(_CODE_HINT_RE.findall(text)) >= 2


def route_intent(message: str, hint: str | None = None) -> str:
    """Classify one message into a skill id, FRESH per turn.

    ``hint`` is the sticky/sent skill (already resolved to a valid id, or None).
    It only tips a genuinely-mixed turn that ALSO contains pasted code toward
    code-review (step 1); it is NEVER used to keep a signal-less follow-up on a
    prior diagram/review skill. A message with no decisive diagram/code signal
    always routes to ``qa`` so plain follow-up questions revert to grounded Q&A.
    Returns one of ``qa`` / ``code-review`` / ``mermaid``.
    """
    text = message or ""
    hint = hint if hint in VALID_SKILLS else None

    diagram = _wants_diagram(text)
    has_code = _has_code_block(text)
    review = _wants_review(text)

    # 1. Pasted code + a review ask -> review is the primary deliverable, even
    #    when a diagram is ALSO requested in the same message (mixed intent).
    #    Content-gating then emits the review artifact only, never a wrong-kind
    #    artifact holding both.
    if has_code and (review or hint == "code-review"):
        return "code-review"
    # 2. A clear diagram/draw ask -> mermaid (the most specific deliverable).
    #    This is what routes "give me a diagram" away from a stuck code-review
    #    selector.
    if diagram:
        return "mermaid"
    # 3. An explicit review ask, or pasted code with no other intent -> review.
    if review or has_code:
        return "code-review"
    # 4. No decisive diagram/code signal in THIS message -> qa (the neutral
    #    default). We deliberately do NOT fall back to the sticky/sent skill.
    #    The frontend now syncs its dropdown to the LAST routed skill, so a plain
    #    follow-up question ("how do containers differ from VMs?") carries a
    #    mermaid/code-review hint - honoring it here would strand the user on the
    #    prior diagram/review skill forever, never reverting to Q&A. Classifying
    #    fresh from the current message content and defaulting to qa lets every
    #    plain question get a real grounded answer with history carried.
    return "qa"


# --- Content-gated artifact detection --------------------------------------

# The first line of a Mermaid diagram declares its type. Matched precisely so a
# prose answer that merely STARTS with "Graph databases ..." is not mistaken for
# a diagram.
_MERMAID_FIRST_RE = re.compile(
    r"^(?:graph|flowchart)\s+(?:tb|td|bt|rl|lr)\b"
    r"|^(?:sequencediagram|classdiagram|erdiagram|statediagram(?:-v2)?|gantt|"
    r"pie|journey|gitgraph|mindmap|timeline|quadrantchart|requirementdiagram|"
    r"c4context|block-beta|sankey-beta|xychart-beta|flowchart-elk)\b",
    re.IGNORECASE,
)


# A ```mermaid (or ```mmd) opening fence, matched on a stripped line.
_MERMAID_FENCE_OPEN_RE = re.compile(r"^`{3,}\s*(?:mermaid|mmd)\b", re.IGNORECASE)

# A stray Mermaid diagram DIRECTIVE line the 7B sometimes emits OUTSIDE a
# recognized diagram block (so the bare-diagram sweep above never picks it up),
# e.g. a lone "note right of AuthService: token check" or a "note over A,B" ...
# "end note" pair left hanging in the prose above the rendered card. These are
# only diagram syntax, never useful prose, so strip them when a diagram is
# present (this function is only called on a mermaid-artifact turn).
_MERMAID_NOTE_OPEN_RE = re.compile(
    r"^note\s+(?:right of|left of|over)\b", re.IGNORECASE
)
_MERMAID_NOTE_END_RE = re.compile(r"^end\s+note$", re.IGNORECASE)

# A STRONG Mermaid edge/arrow that a node id sits on either side of. Distinctive
# enough that it (almost) never appears in ordinary prose or code, so it lets the
# stripper recognise a declaration-LESS diagram body (the 7B sometimes emits the
# arrows with NO leading ``sequenceDiagram`` / ``flowchart`` line). The required
# node token on BOTH sides deliberately excludes an HTML comment close (``<!-- x
# -->``): the ``-->`` there is followed by end-of-line, not a node, so it does
# NOT match. Bare ``->`` (common in C / Rust / PHP prose) is intentionally NOT
# here - only the two-plus-char Mermaid forms.
_MERMAID_STRONG_EDGE_RE = re.compile(
    r"[\w\])}>\"']\s*(?:-->>|->>|<<--|-->|--x|-\.->|==+>|~~>)\s*[\w\[({>\"'|]",
)
# A line whose FIRST token is a Mermaid keyword (sequence/flow directives). Used
# only to CONTINUE a run already anchored on a declaration or a strong edge, so a
# prose line that merely starts with "End " / "Class " never starts a strip.
_MERMAID_KEYWORD_LINE_RE = re.compile(
    r"^(?:participant|actor|note\b|loop\b|alt\b|opt\b|par\b|and\b|else\b|end\b|"
    r"rect\b|activate\b|deactivate\b|subgraph\b|class\b|state\b|direction\b|"
    r"section\b|title\b|link\b|click\b|style\b|linkstyle\b)",
    re.IGNORECASE,
)


def _is_dsl_body_line(line: str) -> bool:
    """True if a line looks like Mermaid diagram body (edge, keyword, or class
    assignment). Only used to CONTINUE / cross-blank an already-anchored block."""
    s = line.strip()
    if not s:
        return False
    return bool(
        _MERMAID_STRONG_EDGE_RE.search(s)
        or _MERMAID_KEYWORD_LINE_RE.match(s)
        or ":::" in s
    )


def _consume_diagram_block(
    lines: list[str], i: int, n: int, *, strict: bool
) -> int:
    """Advance ``i`` past a contiguous Mermaid diagram body starting at ``i``.

    A single (or few) blank line(s) WITHIN the diagram are crossed only when the
    next non-blank line is still DSL - so a real sequence diagram split by a blank
    line no longer leaks its second half (the pre-fix ``while lines[i].strip()``
    stopped dead at the first blank).

    ``strict`` gates whether a NON-blank line must itself look like DSL to be
    swallowed. After a real declaration line (``flowchart TD`` ...) we are certain
    it is a diagram, so ``strict=False`` swallows every contiguous non-blank line
    (matching the original behaviour for node-only lines like ``A[User]``). For a
    declaration-LESS run anchored only on a strong edge we use ``strict=True`` so
    we stop at the first line that is clearly prose, never eating a real sentence.
    """
    while i < n:
        s = lines[i].strip()
        if not s:
            j = i
            while j < n and not lines[j].strip():
                j += 1
            if j < n and _is_dsl_body_line(lines[j]):
                i = j
                continue
            break
        if strict and not (_is_dsl_body_line(lines[i]) or _MERMAID_FIRST_RE.match(s)):
            break
        i += 1
    return i


def strip_mermaid_from_body(body: str) -> str:
    """Remove Mermaid diagram DSL from an assistant message body.

    When a diagram turn also renders the source as a downloadable card, the raw
    DSL in the prose is duplicative. This drops EVERY form the 7B emits:

      * a fenced ```mermaid ... ``` block (as the frontend already strips),
      * a BARE diagram block - a Mermaid declaration line (``flowchart TD`` /
        ``sequenceDiagram`` / ...) plus its diagram body, now tolerant of blank
        lines that sit inside the diagram,
      * a declaration-LESS DSL run - a stretch of strong-edge lines (``User->>
        Frontend: ...`` / ``A-->B``) the model emitted with NO declaration line
        above them, which the previous sweep missed entirely, and
      * a stray ``note ...`` / ``end note`` directive left outside any block.

    Surrounding prose, other code fences, and tables are left intact; blank-line
    runs left behind by a removal are collapsed so the prose keeps its shape.
    """
    if not (body or "").strip():
        return ""
    lines = body.split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        stripped = lines[i].strip()
        # (a) fenced ```mermaid ... ``` block: swallow through the closing fence.
        if _MERMAID_FENCE_OPEN_RE.match(stripped):
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                i += 1
            i += 1  # consume the closing fence line (if present)
            continue
        # (b) bare diagram: a Mermaid declaration line + its (blank-tolerant) body.
        if _MERMAID_FIRST_RE.match(stripped):
            i = _consume_diagram_block(lines, i + 1, n, strict=False)
            continue
        # (c) stray note directive: a lone "note right of X: ..." single line, or
        #     a "note over A,B" ... "end note" pair the model dropped outside any
        #     diagram block. Swallow the opener (through a matching "end note" when
        #     it is a multi-line block) and any bare "end note" that stands alone.
        if _MERMAID_NOTE_OPEN_RE.match(stripped):
            has_inline_text = ":" in stripped
            i += 1
            if not has_inline_text:
                # Block form: consume the note body through its "end note".
                while i < n and not _MERMAID_NOTE_END_RE.match(lines[i].strip()):
                    i += 1
                i += 1  # consume the "end note" line (if present)
            continue
        if _MERMAID_NOTE_END_RE.match(stripped):
            i += 1
            continue
        # (d) declaration-LESS DSL run: a strong Mermaid edge line the model
        #     emitted with no ``sequenceDiagram`` / ``flowchart`` line above it.
        #     Anchor on the strong edge, then swallow the contiguous DSL run.
        if _MERMAID_STRONG_EDGE_RE.search(stripped):
            i = _consume_diagram_block(lines, i, n, strict=True)
            continue
        out.append(lines[i])
        i += 1
    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(out))
    return cleaned.strip()


def looks_like_mermaid(text: str) -> bool:
    """True if ``text`` actually contains Mermaid diagram source.

    Accepts a fenced ```mermaid block, raw source whose first non-empty line is a
    valid Mermaid diagram declaration (the diagram skill is prompted to emit
    fence-less source), OR a declaration-LESS body carrying two or more strong
    Mermaid edge lines (``User->>Frontend: ...`` / ``A-->B``) - the variant the
    7B sometimes emits with no leading declaration, so the artifact is still
    produced and the body still gets stripped. A single stray arrow in prose is
    not enough (a real diagram has multiple edges), so this stays off ordinary
    text."""
    if "```mermaid" in (text or "").lower():
        return True
    src = extract_mermaid_source(text)
    src_lines = src.splitlines()
    first = next((ln.strip() for ln in src_lines if ln.strip()), "")
    if _MERMAID_FIRST_RE.match(first):
        return True
    strong = sum(
        1 for ln in src_lines if _MERMAID_STRONG_EDGE_RE.search(ln.strip())
    )
    return strong >= 2


def looks_like_review(text: str) -> bool:
    """True if ``text`` is a real STRUCTURED code review (not a refusal/prose).

    Keyed on the code-review skill's Markdown contract: the ``## Findings`` /
    ``## Suggested fixes`` sections, or a findings table with a Severity column.
    """
    low = (text or "").lower()
    if "## findings" in low or "## suggested fix" in low:
        return True
    if (
        "severity" in low
        and low.count("|") >= 4
        and ("issue" in low or "why it matters" in low or "location" in low)
    ):
        return True
    return False


def detect_artifact(
    full_text: str, *, routed_skill_id: str, is_refusal: bool
) -> str | None:
    """Decide the downloadable artifact kind from the ACTUAL model output.

    Returns ``"mermaid"``, ``"markdown"``, or ``None``. A refusal / empty answer
    never yields an artifact. Otherwise the kind follows the content: a real
    diagram -> ``mermaid``; a real structured review -> ``markdown``. The routed
    skill only sets the PREFERENCE when both (or neither) content signals apply,
    so the artifact can never contradict what the model produced.
    """
    if is_refusal or not (full_text or "").strip():
        return None
    has_mermaid = looks_like_mermaid(full_text)
    has_review = looks_like_review(full_text)
    if routed_skill_id == "mermaid":
        return "mermaid" if has_mermaid else None
    if routed_skill_id == "code-review":
        if has_review:
            return "markdown"
        return "mermaid" if has_mermaid else None
    # qa / default: only a genuine diagram block warrants an artifact; a plain
    # grounded answer ships as text with citations, no artifact.
    return "mermaid" if has_mermaid else None


# --- Leading scaffolding-preamble strip (deterministic FIX 1) ----------------
#
# Despite the anti-scaffolding system-prompt rewrite, the safety-tuned 7B STILL
# intermittently (~1 in 2) opens a grounded answer with a meta/instruction
# preamble it should never surface, e.g.:
#
#   "Here are concise explanations based on the corpus. For precise citations,
#    quote the corpus verbatim. [1][2][3][4]"   <-- then the real answer.
#
# A prompt can NUDGE but cannot DETERMINISTICALLY beat the non-determinism, so
# this is a post-generation strip: on a buffered answer, drop the LEADING
# meta/instruction sentence(s) (a preamble that talks about the knowledge base /
# citations / how the response is produced, quotes-verbatim instructions, "here
# are ... explanations", "in production ...", or a bare leading ``[n]`` cluster)
# up to the FIRST genuine content segment, then keep everything from there on.
#
# Only the LEADING run is examined and we STOP at the first non-meta segment, so
# a real answer that merely MENTIONS "corpus"/"citation" mid-body is untouched.
# A fail-safe returns the original text if stripping would empty it (never blank
# out a real answer). Inline ``[n]`` citations inside the kept body are preserved.

# Split off the first "segment": text up to (and including) the first sentence
# terminator followed by whitespace/end, a colon followed by whitespace, or a
# newline. The colon boundary lets "Let me explain: <real answer>" shed only the
# "Let me explain:" lead and keep the answer.
_LEADING_SEG_RE = re.compile(
    r"^(.*?(?:[.!?][)\]\"']*(?=\s|$)|:(?=\s)|\n))(.*)$",
    re.DOTALL,
)

# A leading segment is META when it describes the response / knowledge base /
# citations or instructs about the model's own behaviour, rather than answering.
# Each pattern keys on a behaviour/instruction phrase (not a bare topical word)
# so a real sentence like "A corpus is a collection of documents" is NOT matched.
_META_SEG_RES = (
    re.compile(
        r"\bhere\s+(?:are|is|'s)\b.*\b(?:answer|answers|explanation|explanations"
        r"|response|responses|summary|overview|breakdown)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bbased on\b.*\b(?:corpus|knowledge base|retrieved|passages?|sources?"
        r"|documents?|context|provided information)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bfor\s+(?:precise|accurate|exact|proper|specific)\b.*\bcitation",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:quote|cite|citing|quoting)\b.*\b(?:corpus|passages?|sources?"
        r"|documents?|verbatim|directly)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bverbatim\b", re.IGNORECASE),
    re.compile(
        r"\bin production\b.*\b(?:answer|generated|retriev|corpus|passages?"
        r"|response|demo|cite|cites|citing|source)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\baccording to the\s+(?:corpus|knowledge base|passages?|sources?"
        r"|documents?|retrieved)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bfrom the\s+(?:corpus|knowledge base|retrieved|passages?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bthe\s+(?:retrieved|following|provided|supporting)\b.*\b(?:passages?"
        r"|corpus|context|sources?|documents?|answer|explanation)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bto\s+(?:answer|address)\s+(?:your|this|the)\s+"
        r"(?:question|query|request)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:i'?ll|i\s+will|let\s+me|i\s+can|i\s+shall)\s+(?:now\s+)?"
        r"(?:answer|explain|provide|summari[sz]e|walk|give|help|describe|break)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bas\s+an?\s+(?:ai|assistant|language\s+model|helpful\s+assistant)\b",
        re.IGNORECASE,
    ),
    # A leading segment that is ONLY a citation cluster / punctuation (has a [n]).
    re.compile(r"^[\s\[\]\d,;.\-]*\[\d+\][\s\[\]\d,;.\-]*$"),
)


def _is_meta_segment(seg: str) -> bool:
    s = seg.strip()
    if not s:
        return False
    return any(r.search(s) for r in _META_SEG_RES)


def _next_leading_segment(s: str) -> tuple[str, str]:
    m = _LEADING_SEG_RE.match(s)
    if not m:
        return s, ""
    return m.group(1), m.group(2)


def strip_leading_meta(text: str) -> str:
    """Drop a LEADING scaffolding/meta preamble from an assistant answer.

    Removes leading meta/instruction segments (see module notes) up to the first
    genuine content segment, then keeps the remainder verbatim. Never empties a
    real answer: if every leading segment is meta and nothing genuine remains, the
    original text is returned unchanged."""
    original = text or ""
    if not original.strip():
        return original
    remaining = original
    for _ in range(12):  # bounded: a real preamble is at most a few segments
        lead = remaining.lstrip()
        if not lead:
            break
        seg, rest = _next_leading_segment(lead)
        if seg and _is_meta_segment(seg):
            remaining = rest
            continue
        remaining = lead
        break
    # Trim a leading citation cluster ("[1][2] ...") glued to the first real
    # content line - the model sometimes front-loads the source markers.
    result = re.sub(r"^(?:\[\d+\][\s,;]*)+", "", remaining.lstrip()).strip()
    return result if result else original.strip()
