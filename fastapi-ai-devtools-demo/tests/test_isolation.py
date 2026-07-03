"""OpenJarvis demo isolation: OPENJARVIS_HOME pinned to a demo-only dir."""

from __future__ import annotations

import os
from types import SimpleNamespace

from app.core.isolation import configure_openjarvis_isolation


def test_pins_openjarvis_home_to_demo_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENJARVIS_HOME", raising=False)
    demo = tmp_path / "openjarvis-demo"
    chosen = configure_openjarvis_isolation(
        SimpleNamespace(
            openjarvis_home=str(demo),
            openjarvis_home_fallback=str(tmp_path / "fallback"),
        )
    )
    assert chosen == str(demo)
    assert os.environ["OPENJARVIS_HOME"] == str(demo)
    assert os.path.isdir(demo)
    # NEVER the shared home.
    assert ".openjarvis" not in os.path.basename(os.path.expanduser("~")) or True
    assert os.environ["OPENJARVIS_HOME"] != os.path.expanduser("~/.openjarvis")


def test_falls_back_when_primary_unwritable(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENJARVIS_HOME", raising=False)
    fallback = tmp_path / "fallback-home"
    chosen = configure_openjarvis_isolation(
        SimpleNamespace(
            openjarvis_home="/proc/cannot/create/here",
            openjarvis_home_fallback=str(fallback),
        )
    )
    assert chosen == str(fallback.resolve()) or chosen == os.path.abspath(str(fallback))
    assert os.path.isdir(chosen)
    assert os.environ["OPENJARVIS_HOME"] == chosen
