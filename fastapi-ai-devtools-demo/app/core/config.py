"""Application configuration via pydantic-settings.

All runtime configuration is read from the environment (or a local .env file).
Nothing secret is hard-coded. See .env.example for the full list of knobs.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed application settings.

    Values are loaded, in order of precedence, from: real environment
    variables, then a local ``.env`` file, then the defaults below.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- API metadata -----------------------------------------------------
    app_name: str = "AI-First Semantic Search and Q&A API"
    app_version: str = "1.0.0"
    environment: Literal["development", "production", "test"] = "development"

    # --- Security / JWT ---------------------------------------------------
    # Override this in every real deployment via the JWT_SECRET env var.
    jwt_secret: str = Field(
        default="change-me-in-production-this-is-only-a-local-default",
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # --- Database ---------------------------------------------------------
    # Async SQLAlchemy URL. Defaults to a local SQLite file via aiosqlite.
    database_url: str = "sqlite+aiosqlite:///./ai_search.db"
    # Milliseconds a SQLite connection waits on a locked database before it
    # fails (PRAGMA busy_timeout). Paired with WAL journal mode, this absorbs
    # burst-write contention (concurrent /chat logs + document writes) so a
    # contended writer retries instead of dropping the row. Ignored for
    # non-SQLite URLs (e.g. postgresql+asyncpg). (BL19)
    # ``ge=0`` rejects a negative override, which SQLite would otherwise treat
    # as "wait forever" - silently disabling the timeout and turning burst-write
    # contention into an indefinite hang.
    sqlite_busy_timeout_ms: int = Field(default=5000, ge=0)

    # --- Embedding backend ------------------------------------------------
    # "sentence-transformers" loads a real local model (default for the app).
    # "hash" is a deterministic, dependency-free embedder used by the test
    # suite so tests stay fast and never download model weights.
    embedding_backend: Literal["sentence-transformers", "hash"] = (
        "sentence-transformers"
    )
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    # Dimension used by the deterministic "hash" backend. The real model
    # reports its own dimension at load time.
    hash_embedding_dim: int = 384

    # --- Chunking ---------------------------------------------------------
    chunk_size_words: int = 90
    chunk_overlap_words: int = 20

    # --- Retrieval defaults ----------------------------------------------
    default_search_limit: int = 5
    max_search_limit: int = 50
    ask_top_k: int = 3
    chat_top_k: int = 4

    # --- Generative LLM (RAG chat) ---------------------------------------
    # The /chat endpoint streams answers from a local generative LLM served
    # through an OpenAI-COMPATIBLE API. By default that is a local Ollama
    # instance (no paid external API, no network egress). This is the
    # drop-in OpenAI seam: to use real OpenAI instead, change ONLY these
    # three env vars (OPENAI_BASE_URL, OPENAI_API_KEY, OPENAI_MODEL) - no
    # code change. See the README "Swapping in OpenAI" section.
    #
    #   Local Ollama (default):
    #     OPENAI_BASE_URL=http://localhost:11434/v1
    #     OPENAI_API_KEY=ollama            (any non-empty string; unused)
    #     OPENAI_MODEL=qwen2.5:0.5b       (tiny CPU-friendly model, ~397 MB)
    #
    #   Larger local model (better quality, slower on CPU):
    #     OPENAI_MODEL=qwen2.5:7b-instruct
    #
    #   Real OpenAI (future swap, NOT used here):
    #     OPENAI_BASE_URL=https://api.openai.com/v1
    #     OPENAI_API_KEY=sk-...            (a real key)
    #     OPENAI_MODEL=gpt-4o-mini
    # NOTE: this is the PRIMARY (GPU) model, served by the vLLM engine / GPU
    # endpoint when the training GPUs are idle. The CPU fallback is configured
    # separately below (fallback_model).
    openai_base_url: str = "http://localhost:8000/v1"
    openai_api_key: str = "openjarvis"
    openai_model: str = "qwen2.5:7b-instruct"

    # Generation controls. Low temperature keeps grounded answers faithful.
    llm_temperature: float = 0.2
    llm_max_tokens: int = 700
    # Repetition guard (2026-07-01 incident fix): a small local model can fall
    # into a degenerate loop and repeat the same sentence until it hits the
    # completion cap, burning KV-cache the whole way. vLLM's native
    # ``repetition_penalty`` (>1.0 discourages re-emitting already-seen
    # tokens) is forwarded on every generation request. 1.15 is the commonly
    # recommended value (sane range ~1.1-1.3): enough to break loops without
    # visibly hurting coherence at temperature=0.2. See app/services/
    # openjarvis_engine.py and app/services/llm_client.py.
    llm_repetition_penalty: float = 1.15
    # Seconds to wait on the LLM before giving up (CPU generation is slow).
    llm_request_timeout: float = 180.0

    # LLM backend selector, mirroring embedding_backend.
    #   "openjarvis" - run generation through the in-process OpenJarvis engine
    #                  API (vLLM engine on the GPU, Ollama engine on the CPU).
    #                  This is the production default for the demo.
    #   "openai"     - the plain OpenAI-compatible client (local Ollama / vLLM /
    #                  hosted OpenAI). A lighter alternative transport.
    #   "fake"       - deterministic, offline, network-free client used by the
    #                  test suite so tests never contact a real model.
    llm_backend: Literal["openjarvis", "openai", "fake"] = "openjarvis"

    # --- GPU-ONLY: no CPU fallback ----------------------------------------
    # This demo serves ONLY the GPU 7B. There is deliberately NO small CPU
    # fallback model: when the GPU is unavailable (serving training, or yielded)
    # the demo reports OFFLINE rather than answering with a weaker, more easily
    # jailbroken model. (Operator decision 2026-06-30: "if GPU is not online the
    # demo is not online".)

    # --- OpenJarvis engine host (used when llm_backend == "openjarvis") ----
    # The GPU (vLLM) engine endpoint OpenJarvis talks to.
    openjarvis_vllm_host: str = "http://localhost:8000"

    # --- OpenJarvis ISOLATION (hard-separate this PUBLIC demo) -------------
    # OpenJarvis derives its config/memory/traces/telemetry/learning/vault dir
    # from OPENJARVIS_HOME. We point it at a DEMO-ONLY directory so NOTHING from
    # any other OpenJarvis instance can leak into this public demo, and the demo
    # cannot pollute it. NEVER the shared ~/.openjarvis. Set before any
    # OpenJarvis import (see app.core.isolation).
    openjarvis_home: str = "/run/openjarvis-demo"
    # Fallback when /run is not writable (e.g. local dev): a dir under the app.
    openjarvis_home_fallback: str = "./.openjarvis-demo"

    # --- Self-learning (PUBLIC-SAFE, per-session, human-in-the-loop) -------
    # Logs sanitized per-request traces and derives improvement PROPOSALS. NEVER
    # auto-applies anything globally; proposals require operator approval. Traces
    # are per-session, ephemeral, capped, and store only derived metadata (never
    # raw untrusted visitor text) - so public input cannot poison persistent
    # state or leak across sessions.
    learning_enabled: bool = True
    learning_max_sessions: int = 500
    learning_max_traces_per_session: int = 50
    learning_session_ttl_seconds: float = 3600.0

    # --- GPU-idle router (per-request start gate) -------------------------
    # Before each chat request the router reads nvidia-smi (short TTL cache) to
    # decide GPU (primary 7B) vs CPU (fallback small). FAIL SAFE: any error,
    # timeout, missing tool, or ambiguity => CPU. Never assume idle.
    gpu_util_idle_pct: int = 10      # per-GPU utilization % must be below this
    gpu_mem_idle_mb: int = 1000      # per-GPU memory used (MiB) must be below this
    gpu_check_ttl_seconds: float = 12.0   # cache the idle verdict this long
    gpu_hysteresis_count: int = 2    # consecutive idle reads required to switch
                                     # TO the GPU; switching back to CPU is instant
    gpu_nvidia_smi_timeout: float = 4.0   # hard timeout on each nvidia-smi call
    gpu_nvidia_smi_path: str = "nvidia-smi"

    # Per-GPU VRAM (MiB) at/under which the GPU's memory is assumed to belong to
    # OUR OWN vLLM server. A healthy demo vLLM legitimately holds the VRAM, so the
    # per-request gate is NOT a blanket "is the GPU empty?" check (that misreads
    # our own resident model as "busy"). A NON-demo (e.g. training) process pushes
    # a card OVER this ceiling, which is how we detect foreign co-residence in a
    # namespace-robust way. NOTE: nvidia-smi reports HOST-namespace PIDs while this
    # service runs in a separate PID namespace (LXC), so PID-based attribution is
    # unreliable; the AUTHORITATIVE training-coordination signal is the yield lock
    # file (the admin endpoints / training scripts set it). Tune to the GPU: a
    # 15360 MiB T4 serving a 7B at gpu_memory_utilization~0.85 uses up to ~13 GiB,
    # so 14336 leaves headroom for our own KV cache while still catching a second
    # resident process. Set to 0 to disable the ceiling backstop (rely on the lock).
    gpu_demo_mem_ceiling_mb: int = 14336

    # --- Dynamic GPU preemption (always-on background monitor) ------------
    # Training/dev/prod has ABSOLUTE priority. A background task polls nvidia-smi;
    # if a NON-DEMO compute process appears on a GPU we are using, we DROP the GPU
    # model (release VRAM), MIGRATE any in-flight request to the CPU model, notify
    # the user mid-stream, and route all new requests to CPU until the GPU is idle.
    gpu_monitor_enabled: bool = True
    gpu_monitor_interval_seconds: float = 3.0

    # --- GPU-yield lock file (manual "get off GPU" override) --------------
    # If this file EXISTS, the GPU is treated as off-limits: every request is
    # forced to the CPU model regardless of nvidia-smi, and any in-flight GPU
    # request is migrated to CPU. The backend owns this file (the admin
    # endpoints create/remove it); the operator's training scripts may also
    # touch/rm it directly. On /run (tmpfs) it is cleared on reboot, which is
    # fine - the nvidia-smi check covers the GPU after a reboot.
    gpu_yield_lock_file: str = "/run/openjarvis/gpu_off.lock"

    # --- Admin access (internal-only GPU lock control) -------------------
    # /api/admin/* is gated PURELY by the real socket peer IP being in these
    # CIDRs (localhost + the prod/dev NAT). No bearer token. X-Forwarded-For is
    # NOT trusted. SECURITY: this is safe ONLY because the public nginx layers
    # never forward /api/admin (see README). Both conditions are required.
    admin_allowed_cidrs: str = "127.0.0.1/32,10.0.0.0/24"
    # Shared secret required (when set) on every /api/admin call via the
    # ``X-Admin-Token`` header, IN ADDITION to the peer-IP gate. Defense-in-depth
    # against an IP-gate bypass (e.g. if uvicorn is mis-run with --proxy-headers so
    # X-Forwarded-For rewrites the peer IP). STRONGLY recommended for go-live; set
    # it in the gitignored .env. Empty = token check disabled (IP gate + proxy-strip
    # only). Compared in constant time.
    admin_token: str = ""
    # Reject any /api/admin request that carries a forwarding header
    # (X-Forwarded-For / Forwarded / X-Real-IP). Legitimate internal callers reach
    # the app DIRECTLY (no proxy), so the presence of these headers means the
    # request was proxied - which both indicates the public edge did NOT strip
    # /api/admin and is the exact vector that can spoof the peer IP. Default on.
    admin_reject_forwarded: bool = True

    # --- Generation queue (bounds RAM on the public demo) -----------------
    # A global concurrency limiter + FIFO queue. Excess requests queue (and get
    # streamed a position) up to the max; beyond that they get a clean "busy".
    gen_max_concurrent: int = 2
    gen_max_queue: int = 8
    gen_request_timeout: float = 180.0
    gen_queue_poll_seconds: float = 0.5

    # --- Serving-layer thread budget -------------------------------------
    # Advisory cap forwarded to the inference layer so it cannot monopolize the
    # hub (56 threads); the serving layer (FastAPI, SSE, embeddings, queue) runs
    # UNCAPPED on the remaining threads. The hard deploy-time guarantee is a
    # cpuset/CPUAffinity on the inference process (see deploy/ + RUNBOOK).
    model_max_threads: int = 32

    # Default model id for /chat when the request does not pick one. "auto" lets
    # the router choose GPU-when-idle else CPU. Any catalog model id also works.
    default_chat_model: str = "auto"

    # --- Jailbreak / prompt-injection containment (public endpoint) -------
    # An in-house input+output guard (app.services.guard) on top of the structural
    # guarantee that NO dangerous tools are wired into the agent. The input guard
    # REFUSES clear attacks (system-prompt extraction, host/location probes, code
    # execution / exfiltration, classic injection) BEFORE any model call; the
    # output guard redacts configured sensitive tokens and refuses on a secret /
    # system-prompt leak. See app/services/guard.py for the in-house rationale.
    jailbreak_guard_enabled: bool = True
    # Comma-separated, operator-specific tokens to REDACT from model output (the
    # real public IP / hostname / provider / location words). Kept OUT of source so
    # nothing sensitive is committed; set via the GUARD_REDACT_TERMS env in the
    # gitignored .env at deploy time. The structural guarantees (no tools, sanitized
    # corpus, hardened prompt, input guard) already prevent the model from KNOWING
    # these; this is belt-and-suspenders.
    guard_redact_terms: str = ""

    # --- Mermaid server-side rendering (OFF by default = zero server exec) -
    # When True the backend may shell out to the local ``mmdc`` CLI to render the
    # model's Mermaid SOURCE to SVG. On the hardened PUBLIC deploy this stays OFF:
    # the frontend renders Mermaid client-side (mermaid.js), so the server runs NO
    # subprocess for any chat/skill request (the only exec path is removed). mmdc
    # would render TRUSTED model output (not user input), but disabling it keeps the
    # public surface exec-free. See app/services/mermaid_render.py.
    mermaid_render_enabled: bool = False

    # --- Seed corpus ------------------------------------------------------
    seed_on_startup: bool = True

    # --- CORS -------------------------------------------------------------
    # Comma-separated list of origins allowed to call the API from a browser.
    # Defaults to localhost for safe local development. Override via the
    # CORS_ALLOW_ORIGINS env var for any real or demo deployment:
    #
    #   Demo frontend on example.com:
    #     CORS_ALLOW_ORIGINS="https://chat.example.com"
    #
    #   Open public demo (any origin):
    #     CORS_ALLOW_ORIGINS="*"
    #
    #   Multiple origins:
    #     CORS_ALLOW_ORIGINS="https://chat.example.com,http://localhost:3000"
    cors_allow_origins: str = "http://localhost:8000,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse cors_allow_origins into a clean list of origins."""
        raw = self.cors_allow_origins.strip()
        if raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    @property
    def admin_allowed_cidrs_list(self) -> list[str]:
        """Parse admin_allowed_cidrs into a clean list of CIDR strings."""
        return [c.strip() for c in self.admin_allowed_cidrs.split(",") if c.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (one parse per process)."""
    return Settings()
