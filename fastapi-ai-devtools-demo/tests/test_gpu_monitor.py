"""GpuMonitor unit tests - nvidia-smi parsing, fail-safe, TTL, hysteresis.

The GPU path is MOCKED (the real T4s are training): a fake nvidia-smi runner
feeds deterministic CSV so we exercise idle / busy / error / hysteresis / VRAM-
ceiling behaviour without any real GPU. Decisions are by GPU USAGE only (no
process/PID inspection).
"""

from __future__ import annotations

from types import SimpleNamespace

from app.services.gpu_monitor import GpuMonitor


def _settings(**over):
    base = dict(
        gpu_nvidia_smi_path="nvidia-smi",
        gpu_nvidia_smi_timeout=4.0,
        gpu_util_idle_pct=10,
        gpu_mem_idle_mb=1000,
        gpu_check_ttl_seconds=12.0,
        gpu_hysteresis_count=2,
    )
    base.update(over)
    return SimpleNamespace(**base)


def _runner(gpu_csv: str, rc: int = 0, exc=None):
    def run(argv, timeout):
        if exc is not None:
            raise exc
        return (rc, gpu_csv)

    return run


def test_idle_when_all_gpus_below_thresholds():
    mon = GpuMonitor(_settings(gpu_hysteresis_count=1), _runner("0, 5, 100\n1, 0, 50"))
    assert mon.is_idle() is True


def test_busy_when_utilization_high():
    mon = GpuMonitor(_settings(gpu_hysteresis_count=1), _runner("0, 80, 100"))
    assert mon.is_idle() is False


def test_busy_when_memory_high():
    mon = GpuMonitor(_settings(gpu_hysteresis_count=1), _runner("0, 1, 4000"))
    assert mon.is_idle() is False


def test_fail_safe_on_nonzero_returncode():
    mon = GpuMonitor(_settings(gpu_hysteresis_count=1), _runner("", rc=1))
    assert mon.is_idle() is False


def test_fail_safe_when_nvidia_smi_missing():
    mon = GpuMonitor(
        _settings(gpu_hysteresis_count=1),
        _runner("", exc=FileNotFoundError("nvidia-smi")),
    )
    assert mon.is_idle() is False


def test_fail_safe_on_garbage_output():
    mon = GpuMonitor(_settings(gpu_hysteresis_count=1), _runner("not,enough"))
    assert mon.is_idle() is False


def test_hysteresis_requires_consecutive_idle_reads():
    # ttl=0 so each call re-reads; toggle output via a mutable cell.
    cell = {"gpu": "0, 1, 50"}

    def run(argv, timeout):
        is_gpu = any(a.startswith("--query-gpu") for a in argv)
        return (0, cell["gpu"] if is_gpu else "")

    mon = GpuMonitor(
        _settings(gpu_hysteresis_count=2, gpu_check_ttl_seconds=0.0), run
    )
    assert mon.is_idle() is False  # streak 1, not yet
    assert mon.is_idle() is True   # streak 2 -> idle
    # A single busy read flips immediately back to busy.
    cell["gpu"] = "0, 95, 50"
    assert mon.is_idle() is False


def test_ttl_cache_avoids_reprobing():
    calls = {"n": 0}

    def run(argv, timeout):
        is_gpu = any(a.startswith("--query-gpu") for a in argv)
        if is_gpu:
            calls["n"] += 1
        return (0, "0, 1, 50" if is_gpu else "")

    mon = GpuMonitor(_settings(gpu_hysteresis_count=1, gpu_check_ttl_seconds=60.0), run)
    mon.is_idle()
    mon.is_idle()
    assert calls["n"] == 1  # second verdict came from the TTL cache


def test_foreign_over_ceiling_detects_co_resident():
    # Our own vLLM (~9 GiB/card) stays under the ceiling -> NOT foreign. This is
    # the namespace-robust check the router/preemptor use (no PID matching).
    mon = GpuMonitor(_settings(), _runner("0, 50, 9000\n1, 50, 9000"))
    assert mon.foreign_over_ceiling(14336) is False
    # A second resident process pushes a card over the ceiling -> foreign.
    mon2 = GpuMonitor(_settings(), _runner("0, 50, 15000\n1, 50, 9000"))
    assert mon2.foreign_over_ceiling(14336) is True


def test_foreign_over_ceiling_fail_open_on_error():
    # FAIL OPEN: the lock file is the authoritative yield signal; a transient
    # nvidia-smi error must not flap the GPU off.
    mon = GpuMonitor(_settings(), _runner("", exc=OSError("boom")))
    assert mon.foreign_over_ceiling(14336) is False


def test_foreign_over_ceiling_disabled_when_zero():
    mon = GpuMonitor(_settings(), _runner("0, 99, 15000"))
    assert mon.foreign_over_ceiling(0) is False
