"""
Smoke test: spin up a temporary uvicorn server, exercise /chat with the
real local Ollama qwen2.5:0.5b model, measure first-token latency, then
cleanly terminate the server.

Run from the project root:
    python smoke_test_chat.py

Exits 0 on success, non-zero on failure.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

PORT = 18765  # Ephemeral port, avoids clashing with any running service
BASE = f"http://127.0.0.1:{PORT}"
TIMEOUT_STARTUP = 40   # seconds to wait for the server to become healthy
TIMEOUT_CHAT    = 90   # hard budget for the whole /chat SSE response

def wait_for_ready(deadline: float) -> bool:
    """Poll /health until the server is ready or the deadline passes."""
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE}/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def post_json(path: str, body: dict, token: str | None = None) -> dict:
    data = json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main() -> int:
    db_file = tempfile.mktemp(suffix=".db", prefix="smoke_")

    env = os.environ.copy()
    # Use hash embedder for fast startup (no model download needed during smoke)
    env["EMBEDDING_BACKEND"] = "hash"
    env["HASH_EMBEDDING_DIM"] = "384"
    # Real Ollama model - this is the point of the smoke test
    env["LLM_BACKEND"] = "openai"
    env["OPENAI_BASE_URL"] = "http://localhost:11434/v1"
    env["OPENAI_API_KEY"] = "ollama"
    env["OPENAI_MODEL"] = "qwen2.5:0.5b"
    env["LLM_REQUEST_TIMEOUT"] = "60.0"
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_file}"
    env["JWT_SECRET"] = "smoke-test-only-do-not-reuse"
    env["SEED_ON_STARTUP"] = "true"
    # Localhost-only CORS for this ephemeral server
    env["CORS_ALLOW_ORIGINS"] = f"http://127.0.0.1:{PORT}"

    venv_python = Path(__file__).parent / ".venv" / "bin" / "python"
    cmd = [
        str(venv_python), "-m", "uvicorn", "app.main:app",
        "--host", "127.0.0.1",
        "--port", str(PORT),
        "--log-level", "warning",
    ]

    print(f"[smoke] Starting uvicorn on port {PORT} ...")
    proc = subprocess.Popen(
        cmd,
        cwd=str(Path(__file__).parent),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    try:
        deadline = time.time() + TIMEOUT_STARTUP
        if not wait_for_ready(deadline):
            output = proc.stdout.read().decode(errors="replace") if proc.stdout else ""
            print(f"[smoke] FAIL: server did not become ready within {TIMEOUT_STARTUP}s")
            print(output[-2000:])
            return 1
        print("[smoke] Server ready.")

        # Register + login (OAuth2 form-encoded login)
        import urllib.parse
        print("[smoke] Registering test user ...")
        post_json("/auth/register", {"username": "smokeuser", "password": "smokepass123"})
        form_data = urllib.parse.urlencode({"username": "smokeuser", "password": "smokepass123"}).encode()
        login_req = urllib.request.Request(
            f"{BASE}/auth/login",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(login_req, timeout=15) as r:
            token = json.loads(r.read())["access_token"]
        print(f"[smoke] Token obtained (len={len(token)}).")

        # /chat SSE request - measure first-token latency
        print("[smoke] Sending /chat request (real Ollama qwen2.5:0.5b) ...")
        chat_body = json.dumps({
            "message": "What is semantic search?",
            "history": [],
        }).encode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Accept": "text/event-stream",
        }
        req = urllib.request.Request(f"{BASE}/chat", data=chat_body, headers=headers)

        t_send = time.monotonic()
        t_first_token: float | None = None
        events_received = []
        error_event: str | None = None

        with urllib.request.urlopen(req, timeout=TIMEOUT_CHAT) as resp:
            buf = b""
            deadline_chat = time.monotonic() + TIMEOUT_CHAT
            while time.monotonic() < deadline_chat:
                chunk = resp.read(256)
                if not chunk:
                    break
                buf += chunk
                # Parse SSE lines
                while b"\n\n" in buf:
                    frame, buf = buf.split(b"\n\n", 1)
                    lines = frame.decode(errors="replace").splitlines()
                    ev_type = "message"
                    ev_data = ""
                    for ln in lines:
                        if ln.startswith("event: "):
                            ev_type = ln[7:].strip()
                        elif ln.startswith("data: "):
                            ev_data = ln[6:].strip()
                    events_received.append((ev_type, ev_data))
                    if ev_type == "token" and t_first_token is None:
                        t_first_token = time.monotonic()
                    if ev_type == "error":
                        error_event = ev_data
                    if ev_type == "done":
                        break
                else:
                    continue
                break

        elapsed_first = (t_first_token - t_send) if t_first_token else None
        token_count = sum(1 for e in events_received if e[0] == "token")

        if error_event:
            print(f"[smoke] FAIL: received SSE error event: {error_event}")
            return 1

        if t_first_token is None or token_count == 0:
            print(f"[smoke] FAIL: no token events received. Events: {events_received[:5]}")
            return 1

        print(f"[smoke] PASS")
        print(f"  First-token latency : {elapsed_first:.2f}s")
        print(f"  Token events        : {token_count}")
        event_types = [e[0] for e in events_received]
        print(f"  Event sequence      : {event_types[:10]}")
        return 0

    finally:
        print("[smoke] Terminating server ...")
        try:
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=8)
        except Exception:
            proc.kill()
        # Clean up temp DB
        try:
            os.unlink(db_file)
        except Exception:
            pass
        print("[smoke] Server stopped.")


if __name__ == "__main__":
    sys.exit(main())
