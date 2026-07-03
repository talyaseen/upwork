#!/usr/bin/env bash
# Verify the OS-sandbox confinement WITHOUT installing the unit, by launching probe
# commands under systemd-run with the SAME hardening directives as
# openjarvis-backend.service. Each probe must be DENIED (read fails), proving the
# confined runtime cannot read host files, write outside its data dir, or reach the
# network. Run on the deploy host:  sudo bash deploy/verify_sandbox.sh
#
# Exit non-zero if ANY containment check fails.
set -u
PASS=0; FAIL=0
ok(){ echo "  PASS: $1"; PASS=$((PASS+1)); }
bad(){ echo "  FAIL: $1"; FAIL=$((FAIL+1)); }

# Common hardening directives (mirror of the .service unit).
HARDEN=(
  --property=ProtectSystem=strict
  --property=ProtectHome=true
  --property=PrivateTmp=true
  --property=NoNewPrivileges=true
  --property=CapabilityBoundingSet=
  --property=RestrictNamespaces=true
  --property=RestrictSUIDSGID=true
  --property=ProtectProc=invisible
  --property=InaccessiblePaths=-/etc/openjarvis
  --property=ReadWritePaths=/var/lib/openjarvis-demo
  --property=IPAddressDeny=any
  --property=IPAddressAllow=localhost
)
RUN(){ systemd-run --quiet --wait --collect --pipe "${HARDEN[@]}" "$@" 2>&1; }

echo "[1] read /home (ProtectHome=true) must be denied"
if RUN /bin/cat /home/*/.bashrc >/dev/null 2>&1; then bad "read /home succeeded"; else ok "read /home denied"; fi

echo "[2] write outside the data dir (ProtectSystem=strict) must be denied"
if RUN /bin/sh -c 'echo x > /etc/openjarvis-probe' >/dev/null 2>&1; then bad "write /etc succeeded"; else ok "write /etc denied"; fi
if RUN /bin/sh -c 'echo x > /opt/openjarvis-probe' >/dev/null 2>&1; then bad "write /opt succeeded"; else ok "write /opt denied"; fi

echo "[3] write INSIDE the data dir must SUCCEED (the one writable path)"
mkdir -p /var/lib/openjarvis-demo 2>/dev/null
if RUN /bin/sh -c 'echo x > /var/lib/openjarvis-demo/.probe && rm -f /var/lib/openjarvis-demo/.probe' >/dev/null 2>&1; then ok "write data dir allowed"; else bad "write data dir denied (too strict)"; fi

echo "[4] network egress to a non-local host must be blocked (IPAddressDeny=any)"
if RUN /usr/bin/curl -s --max-time 5 https://example.com >/dev/null 2>&1; then bad "external egress succeeded"; else ok "external egress blocked"; fi

echo "[5] MemoryDenyWriteExecute vs the torch runtime (decide whether to enable it)"
PYBIN="${1:-/opt/openjarvis-backend/.venv/bin/python}"
if [ -x "$PYBIN" ]; then
  if systemd-run --quiet --wait --collect --pipe --property=MemoryDenyWriteExecute=true \
       "$PYBIN" -c "import torch; print('torch-ok')" 2>/dev/null | grep -q torch-ok; then
    echo "  INFO: torch imports under W^X -> you MAY enable MemoryDenyWriteExecute"
  else
    echo "  INFO: torch FAILS under W^X -> keep MemoryDenyWriteExecute DISABLED (expected)"
  fi
else
  echo "  SKIP: venv python not found at $PYBIN"
fi

echo "---- containment: PASS=$PASS FAIL=$FAIL ----"
[ "$FAIL" -eq 0 ]
