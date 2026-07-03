"""Mermaid source extraction + the offline SVG render seam (sync unit tests)."""

from __future__ import annotations

from app.services.mermaid_render import extract_mermaid_source, render_svg_with_mmdc


def test_extract_mermaid_source_strips_fences():
    assert extract_mermaid_source("```mermaid\nflowchart TD\nA-->B\n```") == (
        "flowchart TD\nA-->B"
    )
    assert extract_mermaid_source("flowchart LR\nX-->Y") == "flowchart LR\nX-->Y"
    assert extract_mermaid_source("  graph TD\nA-->B  ") == "graph TD\nA-->B"
    assert extract_mermaid_source("") == ""


def test_extract_mermaid_source_strips_dangling_open_fence():
    # BL16 regression: a max_tokens truncation leaves an OPENING fence with no
    # close. The old code required >= 3 fence-split parts and so returned the raw
    # text WITH the ``` marker, breaking the client render. The source must come
    # back clean, with no ``` marker anywhere.
    truncated = "```mermaid\nflowchart TD\nA-->B\nB-->C"
    result = extract_mermaid_source(truncated)
    assert result == "flowchart TD\nA-->B\nB-->C"
    assert "```" not in result

    # Same for a plain (language-less) dangling fence.
    plain = "```\ngraph LR\nX-->Y"
    assert extract_mermaid_source(plain) == "graph LR\nX-->Y"

    # A dangling fence with leading prose (len(parts) == 2 path).
    with_prose = "Here is the diagram:\n```mermaid\nflowchart TD\nA-->B"
    assert extract_mermaid_source(with_prose) == "flowchart TD\nA-->B"


def test_render_svg_returns_none_without_mmdc(monkeypatch):
    import app.services.mermaid_render as mr

    monkeypatch.setattr(mr.shutil, "which", lambda _: None)
    assert render_svg_with_mmdc("flowchart TD\nA-->B") is None
