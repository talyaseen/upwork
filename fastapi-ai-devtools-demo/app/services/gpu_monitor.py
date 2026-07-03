"""GPU-idle monitor backed by ``nvidia-smi``.

The 2x T4 are PRODUCTION training GPUs. The demo MUST yield to them. This monitor
reads per-GPU USAGE (utilization + memory used) and decides whether the GPUs are
IDLE enough, or whether a non-demo process is co-resident. It deliberately does
NOT inspect the process/PID table: usage is all that matters, and nvidia-smi PIDs
are host-namespace (this service runs in a separate PID namespace) so they could
never be matched anyway. The authoritative yield signal is the lock file; this
usage monitor is the autonomous backstop.

Design guarantees:

- FAIL SAFE: if ``nvidia-smi`` is missing, errors, times out, or returns anything
  ambiguous, the verdict is BUSY (never idle). We never contend with training.
- TTL cache: the raw verdict is cached for a few seconds so we do not run
  ``nvidia-smi`` on every request.
- Hysteresis: switching TO the GPU requires N consecutive idle reads; switching
  BACK to the CPU (busy) is immediate. This stops flapping at the idle threshold.
- Injectable runner: the subprocess call is injected so tests can simulate idle /
  busy / error GPUs WITHOUT any real GPU (the GPU path is mocked - the T4s train).
"""

from __future__ import annotations

import logging
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from app.core.config import Settings

logger = logging.getLogger("app.gpu")

# A runner takes (argv, timeout) and returns (returncode, stdout). Injected so
# tests can fake nvidia-smi output deterministically.
SmiRunner = Callable[[list[str], float], "tuple[int, str]"]


def default_smi_runner(argv: list[str], timeout: float) -> tuple[int, str]:
    """Run ``nvidia-smi`` with a hard timeout; return (returncode, stdout)."""
    proc = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return proc.returncode, proc.stdout


@dataclass(slots=True)
class GpuSnapshot:
    """A parsed point-in-time view of the GPUs (USAGE ONLY, no process table).

    We deliberately decide "is the GPU busy?" from GPU USAGE (utilization +
    memory used), NOT from the process/PID list. Process attribution is both
    unnecessary and unreliable here: nvidia-smi reports HOST-namespace PIDs while
    this service runs in a separate PID namespace (LXC), so it can never match its
    own vLLM PIDs anyway. Usage is namespace-agnostic and is all we need.
    """

    # Per-GPU (utilization_pct, memory_used_mib).
    gpus: list[tuple[int, int]] = field(default_factory=list)


class GpuMonitor:
    """Reads nvidia-smi and answers "are the GPUs idle?" with hysteresis."""

    def __init__(
        self,
        settings: Settings,
        runner: SmiRunner | None = None,
    ) -> None:
        self._settings = settings
        self._runner = runner or default_smi_runner
        self._lock = threading.Lock()
        # TTL cache of the RAW (pre-hysteresis) idle verdict.
        self._cached_raw: bool | None = None
        self._cached_at: float = 0.0
        # Hysteresis: consecutive raw-idle reads observed so far.
        self._consecutive_idle = 0

    # -- low level -------------------------------------------------------

    def _query(self, query: str, extra: list[str]) -> tuple[int, str]:
        argv = [
            self._settings.gpu_nvidia_smi_path,
            f"--query-{query}",
            *extra,
            "--format=csv,noheader,nounits",
        ]
        return self._runner(argv, self._settings.gpu_nvidia_smi_timeout)

    def snapshot(self) -> GpuSnapshot | None:
        """Return a parsed snapshot, or ``None`` on ANY failure (=> treat busy)."""
        try:
            rc1, out1 = self._query("gpu", ["index,utilization.gpu,memory.used"])
            if rc1 != 0:
                logger.debug("nvidia-smi gpu query rc=%s", rc1)
                return None
            gpus: list[tuple[int, int]] = []
            for line in out1.strip().splitlines():
                if not line.strip():
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 3:
                    return None
                # parts = [index, util, mem_used]
                util = int(float(parts[1]))
                mem = int(float(parts[2]))
                gpus.append((util, mem))
            if not gpus:
                return None
            return GpuSnapshot(gpus=gpus)
        except (
            subprocess.TimeoutExpired,
            FileNotFoundError,
            OSError,
            ValueError,
        ) as exc:
            logger.debug("nvidia-smi snapshot failed: %s", exc)
            return None
        except Exception as exc:  # noqa: BLE001 - ANY failure => busy (fail safe)
            logger.debug("nvidia-smi snapshot unexpected failure: %s", exc)
            return None

    def _snapshot_is_idle(self, snap: GpuSnapshot) -> bool:
        """Idle iff every GPU's USAGE (util + memory) is below the thresholds."""
        for util, mem in snap.gpus:
            if util >= self._settings.gpu_util_idle_pct:
                return False
            if mem >= self._settings.gpu_mem_idle_mb:
                return False
        return True

    def _raw_idle(self) -> bool:
        """TTL-cached raw idle verdict (no hysteresis)."""
        now = time.monotonic()
        if (
            self._cached_raw is not None
            and (now - self._cached_at) < self._settings.gpu_check_ttl_seconds
        ):
            return self._cached_raw
        snap = self.snapshot()
        raw = bool(snap is not None and self._snapshot_is_idle(snap))
        self._cached_raw = raw
        self._cached_at = now
        return raw

    # -- public ----------------------------------------------------------

    def is_idle(self) -> bool:
        """Return True only after ``gpu_hysteresis_count`` consecutive idle reads.

        A single busy read immediately resets to busy. Thread-safe.
        """
        with self._lock:
            raw = self._raw_idle()
            if raw:
                self._consecutive_idle += 1
            else:
                self._consecutive_idle = 0
            return self._consecutive_idle >= self._settings.gpu_hysteresis_count

    def is_idle_cached(self) -> bool:
        """Best-effort current idle verdict for DISPLAY (TTL-cached, read-only).

        Unlike ``is_idle`` this does NOT advance the hysteresis counter, so it is
        safe to call from status endpoints without perturbing routing decisions.
        """
        with self._lock:
            return self._raw_idle()

    def foreign_over_ceiling(self, ceiling_mb: int) -> bool:
        """Check, by GPU USAGE, for a NON-demo process co-resident on a GPU.

        Returns True iff any GPU's used memory exceeds ``ceiling_mb`` - i.e. more
        VRAM is in use than our own vLLM server can account for, implying a second
        (non-demo) process is on that card. Uses a FRESH snapshot. This needs NO
        process/PID inspection: usage alone answers the question, and it is
        namespace-agnostic (nvidia-smi PIDs are host-namespace and unmatchable here).

        FAIL OPEN (return False) on ANY nvidia-smi failure: the AUTHORITATIVE yield
        signal is the lock file, and flapping the GPU off on a transient nvidia-smi
        hiccup would needlessly degrade the demo. A real GPU loss still fails over
        because the per-request gate ALSO requires a healthy vLLM. ``ceiling_mb <= 0``
        disables the backstop.
        """
        if ceiling_mb <= 0:
            return False
        snap = self.snapshot()
        if snap is None:
            return False
        return any(mem > ceiling_mb for _, mem in snap.gpus)
