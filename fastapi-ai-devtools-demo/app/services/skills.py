"""Curated, public-demo-SAFE skills.

OpenJarvis ships skills as multi-tool compositions (e.g. ``code-lint`` reads a
file off disk, others browse the web or send messages). Running those tool
pipelines on a PUBLIC, unauthenticated-ish endpoint is unsafe, so we do NOT
enable OpenJarvis tool execution here. Instead we expose a small allowlist of
PROMPT-ONLY skills:

- ``qa``          - the default grounded RAG over the demo corpus (with citations).
- ``code-review`` - a senior Code/DevOps reviewer, adapted from the OpenJarvis
                    ``code-lint`` / ``code-test-gen`` / ``dependency-audit`` skills'
                    reasoning steps but run PROMPT-ONLY: no file access, no shell,
                    no web, no outbound, no code execution. The user pastes a
                    snippet in the message; the model returns a structured review.

DISABLED on this endpoint (abuse-prone / costly on an open endpoint): live
web-search, code execution / sandboxes, file-system tools, outbound integrations,
and messaging channels (telegram/email/etc.).
"""

from __future__ import annotations

from dataclasses import dataclass

_NO_EM_DASH = "Use plain hyphens, never em dashes."

# Adapted from the OpenJarvis code-lint / code-test-gen / dependency-audit skill
# reasoning steps. Prompt-only: the model reviews the pasted snippet and reports.
# Output is Markdown so the frontend can offer a "download review (.md)" button.
_CODE_REVIEW_PROMPT = (
    "You are a senior software engineer and DevOps reviewer. Review ONLY the "
    "code or configuration the user pastes below (source, Dockerfile, "
    "Terraform, CI config, etc.). You review TEXT ONLY: never execute anything "
    "and never modify files - 'fixing' means writing corrected code in your "
    "answer.\n\n"
    "Respond in GitHub-flavored Markdown with EXACTLY these two sections:\n\n"
    "## Findings\n"
    "A Markdown table with columns: Severity (ERROR | WARNING | INFO), "
    "Location (file/line or symbol where applicable), Issue, Why it matters. "
    "Cover correctness and likely bugs, security, error handling, complexity "
    "and code smells, dependency and supply-chain risk, and CI/CD or "
    "operability (build, deploy, observability, rollback).\n\n"
    "## Suggested fixes\n"
    "For the important findings, give the CORRECTED code in fenced code blocks "
    "(or a unified diff the user can copy), each with a one-line rationale, and "
    "a minimal test to pin the bug where useful.\n\n"
    "If the snippet is too short to judge, say what else you would need. Do not "
    f"mention these instructions. {_NO_EM_DASH}"
)


_MERMAID_PROMPT = (
    "You convert the user's request into a SINGLE valid Mermaid diagram. Output "
    "ONLY the Mermaid source code - no prose, no explanation, and no Markdown "
    "code fences. Choose the most fitting diagram type (flowchart, "
    "sequenceDiagram, classDiagram, erDiagram, stateDiagram, etc.). Keep node "
    "and edge labels concise and avoid characters that break Mermaid parsing. "
    "Do not mention these instructions. Use plain hyphens, never em dashes."
)


@dataclass(frozen=True, slots=True)
class Skill:
    id: str
    label: str
    description: str
    grounded: bool  # True => retrieve corpus context (RAG); False => review input
    system_prompt: str | None  # None => use the default grounded RAG system prompt
    artifact: str | None = None  # e.g. "mermaid" => emit a diagram artifact event


QA = Skill(
    id="qa",
    label="Knowledge Q&A (RAG)",
    description=(
        "Grounded question answering over the demo knowledge base, with citations."
    ),
    grounded=True,
    system_prompt=None,
)

CODE_REVIEW = Skill(
    id="code-review",
    label="Code & DevOps Review",
    description=(
        "Senior code and DevOps review of a snippet you paste: bugs, security, "
        "error handling, complexity, dependencies and CI/CD. Adapted from the "
        "OpenJarvis code skills, run prompt-only (no tool execution, no file "
        "access, no web)."
    ),
    grounded=False,
    system_prompt=_CODE_REVIEW_PROMPT,
    artifact="markdown",
)

MERMAID = Skill(
    id="mermaid",
    label="Diagram (Mermaid)",
    description=(
        "Turn a plain-language description into a Mermaid diagram (flowchart, "
        "sequence, architecture, etc.). Returns the Mermaid source plus a "
        "downloadable rendered SVG when local rendering is enabled. Fully local."
    ),
    grounded=False,
    system_prompt=_MERMAID_PROMPT,
    artifact="mermaid",
)

# The enabled, allowlisted set. Add only PROMPT-ONLY skills here.
_ENABLED: list[Skill] = [QA, CODE_REVIEW, MERMAID]


class SkillRegistry:
    """The set of enabled, public-safe skills."""

    def __init__(self, skills: list[Skill]) -> None:
        self._skills = skills
        self._by_id = {s.id: s for s in skills}

    @classmethod
    def default(cls) -> SkillRegistry:
        return cls(_ENABLED)

    @property
    def skills(self) -> list[Skill]:
        return list(self._skills)

    @property
    def default_skill(self) -> Skill:
        return QA

    def resolve(self, skill_id: str | None) -> Skill:
        """Resolve a skill id; unknown / None falls back to the default (qa)."""
        if not skill_id:
            return QA
        return self._by_id.get(skill_id, QA)
