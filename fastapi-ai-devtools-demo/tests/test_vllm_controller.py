"""VllmController: FULL PROCESS EXIT on yield (VRAM hygiene)."""

from __future__ import annotations

import os
import subprocess
import sys
import time

from app.services.openjarvis_engine import VllmController


def test_stop_no_attached_process_is_recorded_noop():
    ctl = VllmController()
    assert ctl.is_running() is False
    ctl.mark_started()
    assert ctl.is_running() is True
    ctl.stop()
    assert ctl.stop_calls == 1
    assert ctl.is_running() is False


def test_stop_full_process_exit_kills_process_group():
    # A real child process in its OWN process group (as a launched vLLM would be).
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        start_new_session=True,  # new pgroup, so killpg targets it cleanly
    )
    ctl = VllmController()
    ctl.attach(proc)
    assert ctl.is_running() is True

    ctl.stop()  # must FULLY terminate the process (not pause it)

    # Give the OS a moment to reap.
    for _ in range(50):
        if proc.poll() is not None:
            break
        time.sleep(0.05)
    assert proc.poll() is not None, "vLLM process must be fully terminated on yield"
    assert ctl.is_running() is False
    assert ctl.stop_calls == 1
    # The pid is gone (no lingering CUDA context / resident VRAM).
    try:
        os.kill(proc.pid, 0)
        alive = True
    except OSError:
        alive = False
    assert alive is False
