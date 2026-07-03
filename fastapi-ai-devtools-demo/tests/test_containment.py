"""Structural containment: the agent's capability surface + zero code execution.

Proves at the APP layer that the agent can ONLY do the three prompt-only skills,
that the code-review feature NEVER executes the code it reviews (static, text-only
analysis), that the mermaid server-side renderer is OFF by default (no subprocess),
and that the code-review input is treated as TEXT (never opened as a file path).
The OS layer (systemd sandbox) is delivered separately in deploy/.
"""

from __future__ import annotations

import builtins
import os
import pathlib
import subprocess
from collections.abc import AsyncIterator
from types import SimpleNamespace

from app.services.chat_service import ArtifactEvent, ChatService, TokenEvent
from app.services.gpu_router import TIER_GPU, Selection
from app.services.skills import SkillRegistry

ALLOWLIST = {"qa", "code-review", "mermaid"}

# The ONLY OpenJarvis modules the app is permitted to import: the two local
# inference engines and the plain message dataclasses. NO agent, tool registry,
# interpreter, skills runtime, web, MCP, or messaging channel.
ALLOWED_OJ_IMPORTS = {
    "openjarvis.engine.ollama",
    "openjarvis.engine.openai_compat_engines",
    "openjarvis.core.types",
}


def test_skill_surface_is_exactly_the_allowlist():
    ids = {s.id for s in SkillRegistry.default().skills}
    assert ids == ALLOWLIST, f"unexpected skill surface: {ids}"
    # Every enabled skill is PROMPT-ONLY: it carries a text system_prompt (or uses
    # the default grounded prompt) and exposes no executor / tool object.
    for s in SkillRegistry.default().skills:
        assert s.system_prompt is None or isinstance(s.system_prompt, str)
        assert not hasattr(s, "tool")
        assert not hasattr(s, "executor")


def test_app_only_imports_safe_openjarvis_modules():
    app_dir = pathlib.Path(__file__).resolve().parent.parent / "app"
    bad: list[str] = []
    for py in app_dir.rglob("*.py"):
        for line in py.read_text(encoding="utf-8").splitlines():
            t = line.strip()
            if t.startswith(("import openjarvis", "from openjarvis")):
                # Normalize "from openjarvis.x.y import Z" -> "openjarvis.x.y".
                mod = t.split()[1]
                if mod not in ALLOWED_OJ_IMPORTS:
                    bad.append(f"{py.name}: {t}")
    assert not bad, f"disallowed OpenJarvis imports (possible dangerous tools): {bad}"


# --- helpers ----------------------------------------------------------------

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


def _service(tokens, **settings_kw):
    settings = SimpleNamespace(chat_top_k=4, **settings_kw)
    return ChatService(
        search_service=None, llm_router=_Router(_Client(tokens)), settings=settings
    )


async def test_code_review_never_executes_reviewed_code(monkeypatch):
    """The code-review path must do ZERO process spawning / exec, even when the
    pasted code is itself a shell/exec call."""
    calls = {"n": 0}

    def boom(*a, **k):  # any exec attempt -> record + raise
        calls["n"] += 1
        raise AssertionError("code-review must NEVER spawn a process")

    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(subprocess, "Popen", boom)
    monkeypatch.setattr(os, "system", boom)

    service = _service(["## Findings\n", "| ERROR | x | bug | ... |\n"])
    malicious = "import os\nos.system('touch /tmp/pwned')  # review this"
    events = [
        ev async for ev in service.stream(malicious, skill="code-review")
    ]
    assert calls["n"] == 0
    assert any(isinstance(e, TokenEvent) for e in events)
    art = next(e for e in events if isinstance(e, ArtifactEvent))
    assert art.kind == "markdown"  # review returned as text, code never ran
    assert not os.path.exists("/tmp/pwned")


async def test_mermaid_render_off_by_default_spawns_no_subprocess(monkeypatch):
    calls = {"n": 0}

    def boom(*a, **k):
        calls["n"] += 1
        raise AssertionError("mermaid render must be OFF by default")

    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(subprocess, "Popen", boom)
    # No mermaid_render_enabled flag => default OFF.
    service = _service(["flowchart TD\n", "A-->B\n"])
    events = [ev async for ev in service.stream("draw", skill="mermaid")]
    assert calls["n"] == 0
    art = next(e for e in events if isinstance(e, ArtifactEvent))
    assert art.svg is None  # source-only; client renders


async def test_code_review_input_is_text_not_a_filepath(monkeypatch):
    """A path-looking message under code-review must be treated as TEXT - the
    service must NOT open or read it (no filesystem access from the agent)."""
    opened: list[str] = []
    real_open = builtins.open

    def tracking_open(path, *a, **k):
        opened.append(str(path))
        return real_open(path, *a, **k)

    monkeypatch.setattr(builtins, "open", tracking_open)
    service = _service(["## Findings\n", "nothing to do\n"])
    events = [
        ev
        async for ev in service.stream(
            "review this: /etc/passwd", skill="code-review"
        )
    ]
    assert any(isinstance(e, TokenEvent) for e in events)
    # The sensitive path was never opened by the request path.
    assert not any("/etc/passwd" in p for p in opened)
