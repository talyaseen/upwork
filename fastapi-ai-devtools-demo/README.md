# AI-First Semantic Search, Q&A and RAG Chat API

A production-style FastAPI backend that does semantic search, extractive
question answering and **conversational, grounded (RAG) chat** over a document
corpus, powered entirely by **local AI models**. There is no paid external API
anywhere in the system: the embedding model runs in-process on CPU and the
generative model runs locally via Ollama, so the service is fully
self-contained and free to operate.

The generative `/chat` endpoint is built around a deliberate **OpenAI seam**:
it talks to the model through the OpenAI-compatible chat-completions wire
format, so switching from the local model to hosted OpenAI is a three
environment-variable change with no code edit (see "Swapping in OpenAI" below).

The auto-generated Swagger UI at `/docs` is the centerpiece. Every endpoint is
documented with a summary, description, example payload and tag.

## What it does

- Splits documents into overlapping chunks and embeds each chunk into a dense
  vector with a local sentence-transformer.
- Stores vectors and metadata in SQLite and keeps an in-memory index for fast
  cosine-similarity retrieval.
- Ranks results by meaning, not keyword overlap, so a query like "how should
  configuration be managed" surfaces a passage about environment variables
  even with no exact word match.
- Answers questions extractively: `/ask` returns the most relevant passage
  verbatim with source citations. No generative model is involved, so every
  answer is grounded in and traceable to the corpus (no hallucination).
- Answers questions conversationally: `/chat` retrieves the relevant passages
  and has a **local generative LLM** compose a fluent, cited, multi-turn answer
  (retrieval-augmented generation), STREAMED token by token over Server-Sent
  Events. The model is grounded in the retrieved context and instructed to say
  when the context does not cover the question.
- Ships with a built-in seed corpus of original notes on software
  architecture, AI engineering and DevOps, so search, Q&A and chat work
  immediately on first boot.

## Stack

- Python 3.11+, FastAPI, Pydantic v2, pydantic-settings
- Async SQLAlchemy 2.0 with aiosqlite (SQLite store of record)
- JWT auth (PyJWT) with bcrypt password hashing, OAuth2 bearer flow
- NumPy for the vector index (normalised vectors, cosine = dot product)
- sentence-transformers (all-MiniLM-L6-v2) for local embeddings
- Ollama (qwen2.5:0.5b) for the local generative LLM, reached through
  the `openai` SDK pointed at its OpenAI-compatible endpoint
- Server-Sent Events (text/event-stream) for token streaming
- pytest + httpx + asgi-lifespan for the async test suite
- Docker (slim CPU base, single uvicorn worker)

## The AI approach

- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`, loaded once at
  startup and run on CPU. Weights download to a local cache on first run; after
  that there are zero network calls and zero external API dependencies.
- Retrieval: query and chunks share the same embedding space; relevance is
  cosine similarity. Vectors are L2-normalised at ingest, so the whole index
  is scored against a query with a single matrix multiplication.
- Q&A is extractive: the top passage is returned as-is with citations. This is
  intentional - it keeps the system local, free and free of hallucination.
- Chat is generative RAG: the same retriever selects the top-k relevant chunks,
  those chunks are placed in a grounded system prompt, and a local instruction
  model composes the answer using only that context. The model is told to cite
  its sources inline and to say plainly when the context does not cover the
  question, which keeps generative fluency without untethered hallucination.
- Model inference runs in a worker thread (`run_in_threadpool`) so it never
  blocks the async event loop.

## Conversational RAG chat (`/chat`)

`POST /chat` is the conversational, grounded layer. It is JWT-protected and
streams its response as Server-Sent Events.

Flow per request: embed the user message, retrieve the top-k corpus chunks via
the existing semantic search, build a grounded RAG prompt (a system message
carrying the numbered context plus the prior conversation turns), call the
local LLM through its OpenAI-compatible API, and stream the generated tokens
back to the client. The retrieved passages are returned as citations.

### Request body

```json
{
  "message": "I'm getting duplicate charges when my service restarts - what's going on and how do I make it scale safely?",
  "history": [
    { "role": "user", "content": "earlier user turn" },
    { "role": "assistant", "content": "earlier assistant turn" }
  ],
  "top_k": 4
}
```

- `message` (required) - the user's current message.
- `history` (optional) - prior turns, oldest first, so follow-ups are answered
  in context. Omit or send `[]` for a fresh conversation.
- `top_k` (optional) - how many corpus chunks to retrieve (defaults to
  `CHAT_TOP_K`).

### Response: Server-Sent Events (`text/event-stream`)

Events (the `queue` and `notice` events are conditional):

```
event: queue          (0+ times, only while waiting for a free slot)
data: {"position": 2, "status": "waiting"}

event: metadata        (exactly once)
data: {"model": "<served-model-name>", "retrieved": 4, "backend_tier": "primary-7b-gpu",
       "notice": null, "citations": [ { ...Citation }, ... ]}

event: notice          (0+ times: the demo went offline - GPU reclaimed by training)
data: {"message": "The GPU is serving training right now, so the demo is offline.",
       "model": "<served-model-name>", "backend_tier": "offline"}

event: token           (many)
data: {"text": "Based "}

event: done            (exactly once)
data: {"finish_reason": "stop"}
```

- `queue` is emitted only when the request has to wait for a concurrency slot;
  under free capacity it never appears. `position` is the 1-based queue place.
- `metadata` carries the active `model`, the retrieved-chunk count, the full
  **citation list**, and **`backend_tier`** (`primary-7b-gpu` when the GPU is
  serving, or `offline` when the GPU is busy with training - this demo is
  GPU-only, there is no CPU fallback) so the UI can show which engine answered.
  `notice` is set when the demo went offline.
- `notice` events announce that the demo went offline: either the GPU was
  already busy at start time, or training DYNAMICALLY reclaimed the GPU
  mid-stream ("GPU reclaimed by training"). There is no CPU fallback, so the
  answer stops rather than continuing on a weaker model.
- Each `token` event carries an incremental `text` fragment; concatenate in order.
- `artifact` (0 or 1, before `done`) carries a skill's downloadable output. The
  `mermaid` skill emits `{"kind":"mermaid","format":"svg"|"mermaid","source":"<mermaid code>","svg":"<svg>"|null}`
  (`source` always present; `svg` when local rendering is enabled, else render
  `source` client-side). The `code-review` skill emits
  `{"kind":"markdown","format":"markdown","source":"<full review .md>","svg":null}`
  (findings table + suggested fixes) for a "download review (.md)" button.
- `learning` (0 or 1, before `done`, only when the request sent a `session_id`)
  carries `{"session_id","observed_requests","proposals":[...]}` - what the agent
  learned this session and proposes (advisory; never auto-applied).
- The terminal `done` event closes the stream with a `finish_reason` (`stop`,
  `error`, or `busy`).
- If the queue is full, a single `busy` event is emitted, then `done` with
  `finish_reason: "busy"`. If the LLM is unreachable, an `error` event precedes
  `done` with `finish_reason: "error"`.

**Frontend (Flutter) note:** the metadata gained `backend_tier` + `notice`, and
new event types may appear: `queue` (show "waiting, position N"), `notice` (show
the "demo offline - GPU serving training" banner), `busy` (show "try again
shortly"), and `artifact` (render
the Mermaid `source`, and offer a download button - use the `svg` when present,
otherwise download the `.mmd` source). All are additive; a client that ignores
unknown events still works. Optional request fields `model` (see `GET /models`)
and `skill` (see `GET /skills`) were added; for the `mermaid` skill set
`skill: "mermaid"` and put the diagram description in `message`.

### curl example

```bash
# Get a token first
TOKEN=$(curl -s -X POST localhost:8000/auth/login \
  -d "username=USER&password=PASS" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -N -X POST localhost:8000/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I stop duplicate charges and scale safely?"}'
```

`-N` disables curl buffering so you see the tokens stream in.

## OpenJarvis engine, GPU-yield router and dynamic preemption

The generative layer runs on the [OpenJarvis](https://github.com/open-jarvis/OpenJarvis)
engine API (in-process), with FastAPI as the public orchestration layer. The
small CPU model is served by the OpenJarvis **Ollama** engine; the GPU 7B model
by the OpenJarvis **vLLM** engine. We use the in-process engine API (not
`jarvis serve`) because the GPU guardrail needs explicit, per-request control
over which engine serves and the ability to drop the GPU engine on demand.

**GPU-yield router (the 2x T4 are production training GPUs; the demo yields).**

- Per request, a short-TTL-cached `nvidia-smi` read (per-GPU utilization, memory,
  running compute processes) decides GPU vs CPU. The GPU 7B is used only when the
  GPU is genuinely idle AND the vLLM engine is healthy; otherwise the small CPU
  model serves, pinned off the GPU (`CUDA_VISIBLE_DEVICES=""`).
- **Fail safe:** any `nvidia-smi` error, timeout, missing tool, or ambiguity
  resolves to the CPU model. We never assume idle and never contend with training.
- Hysteresis (N consecutive idle reads to switch to the GPU; instant switch back
  to CPU) prevents flapping. The active backend is surfaced as `backend_tier`.

**Dynamic mid-stream preemption.** An always-on background monitor polls
`nvidia-smi`. If a non-demo (training/dev/prod) process appears on a GPU we are
using, it instantly: (1) routes all new requests to CPU, (2) drops the GPU model
and releases its VRAM (stops our vLLM server), and (3) migrates any in-flight
request to the CPU model, notifying the user mid-stream via a `notice` event.
New requests stay on CPU until the GPU has been idle again for the hysteresis
window. Training always has absolute priority.

**Model selection.** `GET /models` returns the curated set: a GPU 7B option and
small CPU options. The `/chat` `model` field picks one; a GPU model chosen while
the GPU is busy auto-falls back to a CPU model with a `notice`. `auto` (default)
picks the GPU when idle, else CPU.

**Generation queue (bounds RAM).** A global concurrency limiter
(`GEN_MAX_CONCURRENT`, default 2) plus a bounded FIFO queue (`GEN_MAX_QUEUE`).
Waiting requests are streamed their queue `position`; when the queue is full the
request gets a clean `busy`.

**Skills (public-safe, prompt-only).** `GET /skills` lists the enabled skills:
`qa` (grounded RAG, default), `code-review` (a senior Code/DevOps reviewer
adapted from the OpenJarvis `code-lint` / `code-test-gen` / `dependency-audit`
skills; returns a structured findings table + suggested fixes as a downloadable
Markdown artifact), and `mermaid` (natural language -> a Mermaid diagram; returns
the Mermaid source plus a downloadable rendered SVG when local rendering is enabled).
All run **prompt-only**: OpenJarvis tool execution, file access, web-search, code
execution, and outbound/messaging integrations are **disabled** here. To render
downloadable SVGs install the Mermaid CLI locally (`npm i -g
@mermaid-js/mermaid-cli`); it renders fully offline (no network at request time).
Without it, the `source` is returned for client-side rendering.

**Thread cap.** `MODEL_MAX_THREADS` (default 32) caps ONLY the LLM inference
(Ollama `num_thread` / `OLLAMA_NUM_THREAD`); the serving layer (FastAPI, SSE,
embeddings, queue) runs uncapped on the box's remaining threads. The hard
guarantee is a cpuset on the Ollama process - see the RUNBOOK below.

**Safety.** Local models only; no paid external API is ever contacted. The GPU
path is exercised in tests with MOCKED `nvidia-smi` + mocked vLLM health (no real
GPU inference is started); only the CPU path is run for real.

### Install OpenJarvis (for the `openjarvis` backend)

```bash
# Clone alongside the app and install editable (no heavy deps needed for the
# engine path: httpx + openai already satisfy it).
git clone https://github.com/open-jarvis/OpenJarvis ../openjarvis
uv pip install --no-deps -e ../openjarvis    # or: pip install --no-deps -e ../openjarvis
```

No Rust/maturin build is required for the engine API used here. Set
`LLM_BACKEND=openjarvis` (the default). For a quick local run without OpenJarvis,
set `LLM_BACKEND=openai` to use the plain OpenAI-compatible transport against the
same Ollama/vLLM endpoints.

### RUNBOOK: hard thread cap (deploy)

Cap ONLY the Ollama inference process to <=32 threads; leave the serving layer
free. With systemd:

```ini
# /etc/systemd/system/ollama.service.d/override.conf
[Service]
AllowedCPUs=0-31
Environment=OLLAMA_NUM_THREAD=32
```

Or ad-hoc: `taskset -c 0-31 ollama serve` with `OLLAMA_NUM_THREAD=32`. Do NOT
cpuset the FastAPI/uvicorn process.

### GPU-yield control: lock file + admin endpoints

Beyond the automatic nvidia-smi guardrail, a **lock file** is a manual "get off
the GPU" override. If `GPU_YIELD_LOCK_FILE` (default `/run/openjarvis/gpu_off.lock`)
exists, every request is forced to CPU regardless of nvidia-smi, and any in-flight
GPU request is migrated to CPU (the background monitor watches the lock on its
poll cadence). The lock file is the single source of truth; the maintainer's
training scripts may `touch`/`rm` it directly, and the backend owns it via the
admin endpoints.

Provision the directory with systemd so the app user can write it:

```ini
# the backend service unit
[Service]
RuntimeDirectory=openjarvis        # creates /run/openjarvis (tmpfs, app-writable)
```

**Admin endpoints (internal-only, no token):**

```bash
curl -X POST http://<internal-host>:8000/api/admin/gpu/lock     # force CPU
curl -X POST http://<internal-host>:8000/api/admin/gpu/unlock   # allow GPU again
curl       http://<internal-host>:8000/api/admin/gpu            # status
```

Access is gated PURELY by the REAL socket peer IP being in `ADMIN_ALLOWED_CIDRS`
(default `127.0.0.1/32,10.0.0.0/24` = localhost + the prod/dev NAT). There is no
token; the network is the trust boundary. `X-Forwarded-For` is deliberately NOT
trusted. `unlock` only clears the MANUAL override - the nvidia-smi check and
training-process detection still force CPU whenever the GPU is actually busy, so a
stray `unlock` can never contend with active training.

> **SECURITY - both conditions are required.** `/api/admin` is safe only because
> (a) the app allows it only from localhost + `10.0.0.0/24` by real peer IP, AND
> (b) the public reverse-proxy layers NEVER forward `/api/admin` to the app.
> Public traffic reaches FastAPI as `127.0.0.1` (via the local mTLS reverse
> proxy), which WOULD pass the localhost allow - so (b) is what keeps the public
> out. Do not remove either.

**Bind / firewall.** Bind the app to the internal interface so a `10.0.0.x`
box can reach it directly (e.g. `uvicorn app.main:app --host 0.0.0.0 --port 8000`)
and restrict `:8000` at the host firewall to localhost + `10.0.0.0/24`, so NAT
works while the public IP cannot reach `:8000`.

**Public banner.** `GET /api/status` returns only `{tier, gpu_online, model}` from
the ~12s cached router state (safe to poll every 10-30s). This one IS public; the
proxy forwards it. The UI renders "Running on 2x GPUs - ONLINE" when `gpu_online`,
else "2x GPUs offline (repurposed for training) - running on CPU - ONLINE".

### Self-learning (public-safe, per-session, human-in-the-loop)

OpenJarvis ships a learning loop (Capability-Evolver / ACE / GEPA / LoRA / GRPO)
that logs traces and can fine-tune models. On a PUBLIC endpoint the full loop is a
poisoning and privacy vector and would use the training GPUs, so this demo runs
only the SAFE half: it logs SANITIZED per-request traces (derived metadata only -
which skill, which backend tier, retrieved-chunk count, fallback/queue flags,
message LENGTH - never the raw visitor text) and derives structured improvement
PROPOSALS with deterministic heuristics (no LLM, no GPU). Send a `session_id` on
`/chat` to get a `learning` SSE event and `GET /api/learning/{session_id}` showing
what the agent observed and what it proposes (e.g. "frequent GPU->CPU fallback ->
pre-warm the CPU model"). Proposals are **never auto-applied**: they are
per-session, maintainer-approval-gated suggestions. Because no raw input is stored
or replayed and nothing global is mutated, untrusted public input cannot poison
persistent state or leak across sessions.

### OpenJarvis isolation (this demo cannot touch other OpenJarvis instances' data)

OpenJarvis derives its entire config/memory/traces/telemetry/learning/vault
directory from `OPENJARVIS_HOME`. This demo pins it to a DEMO-ONLY directory
(`OPENJARVIS_HOME`, default `/run/openjarvis-demo`) before any OpenJarvis import,
so it NEVER reads or writes the shared `~/.openjarvis`. Combined with using only
the stateless engine API (model host in, tokens out - no memory/traces under the
home) and separate LXC filesystems, there is zero cross-contamination. Provision
the dir with systemd `RuntimeDirectory=openjarvis-demo`. The RAG corpus is ONLY
the curated demo corpus in this repo.

### GPU VRAM hygiene on yield

The demo and training time-share the GPUs, so the only shared surface is VRAM. Two
properties guarantee no residue leaks: (1) the demo NEVER co-resides on a GPU with
a training process - the nvidia-smi gate plus the background preemptor yield the
instant a foreign process (or the lock) appears; and (2) on yield, `VllmController`
does a FULL PROCESS EXIT of vLLM (SIGTERM, then SIGKILL, of its process GROUP), so
the CUDA context is destroyed and the driver reclaims and zeroes that VRAM before
training reallocates it - it is not a pause that keeps the model resident. A fresh
GPU stint launches a new vLLM process; the demo never relies on residual VRAM
across a yield.

## Swapping in OpenAI (the drop-in seam)

The `/chat` LLM client is built entirely from three environment variables, so
moving between a local model and hosted OpenAI is a config change with **no
code edit**:

| Variable          | Local Ollama (default)        | Real OpenAI               |
| ----------------- | ----------------------------- | ------------------------- |
| `OPENAI_BASE_URL` | `http://localhost:11434/v1`   | `https://api.openai.com/v1` |
| `OPENAI_API_KEY`  | `ollama` (any non-empty)      | `sk-...` (a real key)     |
| `OPENAI_MODEL`    | `qwen2.5:0.5b`                | `gpt-4o-mini`             |

The backend uses the official `openai` Python SDK pointed at `OPENAI_BASE_URL`,
and both Ollama and OpenAI speak the identical chat-completions wire format, so
the streaming, citations and multi-turn behaviour are unchanged. This build
ships with the local Ollama defaults and never contacts a paid external API.

## Running the local LLM (Ollama)

The generative model is served by [Ollama](https://ollama.com), which runs as
its own local service alongside the API.

```bash
# Install Ollama (Linux/macOS)
curl -fsSL https://ollama.com/install.sh | sh

# Start the server (if not already running as a service)
ollama serve &

# Pull the default tiny CPU-friendly model (~397 MB)
ollama pull qwen2.5:0.5b

# Optional: pull a larger model for higher-quality answers (slower on CPU)
# ollama pull qwen2.5:7b-instruct
# Then set OPENAI_MODEL=qwen2.5:7b-instruct in .env
```

Ollama exposes an OpenAI-compatible API at `http://localhost:11434/v1`, which
is exactly what `OPENAI_BASE_URL` points to.

**Model choices:**

- `qwen2.5:0.5b` (default) - ~397 MB on disk; fits comfortably in 1 GB RAM;
  first token on a CPU server in ~2-4 seconds; suitable for demos and
  constrained environments.
- `qwen2.5:7b-instruct` - ~4.7 GB; richer, more nuanced answers; first token
  ~10-30 seconds on a CPU-only box; suitable when answer quality matters more
  than latency.

To change model: set `OPENAI_MODEL` in `.env` (or the environment) and pull
the model with `ollama pull <model>`. No code change needed.

## Endpoints

| Method | Path                | Auth | Purpose                                  |
| ------ | ------------------- | ---- | ---------------------------------------- |
| POST   | `/auth/register`    | no   | Create an account                        |
| POST   | `/auth/login`       | no   | Get a JWT bearer token                   |
| GET    | `/auth/me`          | yes  | Current user                             |
| POST   | `/documents`        | yes  | Ingest, chunk, embed and index a document|
| GET    | `/documents`        | no   | List documents (limit/offset pagination) |
| GET    | `/documents/{id}`   | no   | Fetch one document                       |
| DELETE | `/documents/{id}`   | yes  | Delete a document and its chunks         |
| GET    | `/search?q=`        | no   | Semantic search, ranked chunks + scores  |
| POST   | `/ask`              | no   | Extractive answer with citations         |
| POST   | `/chat`             | yes  | Conversational RAG answer, streamed (SSE)|
| GET    | `/models`           | no   | Curated selectable models + availability |
| GET    | `/skills`           | no   | Enabled public-safe skills               |
| GET    | `/api/status`       | no   | Public GPU/CPU banner state              |
| GET    | `/api/learning/{session_id}` | no | Per-session learning traces + proposals |
| POST   | `/api/admin/gpu/lock`   | internal | Force CPU (set the GPU-yield lock)   |
| POST   | `/api/admin/gpu/unlock` | internal | Clear the manual GPU-yield lock      |
| GET    | `/api/admin/gpu`        | internal | GPU lock/idle state and served tier  |
| GET    | `/health`           | no   | Liveness, backend and index size         |

Interactive docs: `/docs` (Swagger UI) and `/redoc`.

## Run locally

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Set a strong JWT_SECRET in .env:
#   python -c "import secrets; print(secrets.token_urlsafe(48))"

uvicorn app.main:app --reload
```

On first boot the embedding model downloads to a local cache (about 90 MB) and
the seed corpus is indexed. Then open http://127.0.0.1:8000/docs.

`/search` and `/ask` work with no extra setup. The generative `/chat` endpoint
additionally needs the local Ollama service running with the model pulled (see
"Running the local LLM" above); without it `/chat` returns an SSE `error` event
explaining the model is unreachable, while every other endpoint is unaffected.

Quick smoke test once it is running:

```bash
curl "http://127.0.0.1:8000/health"
curl "http://127.0.0.1:8000/search?q=how%20should%20configuration%20be%20managed"
curl -X POST "http://127.0.0.1:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Where should configuration be stored?"}'
```

## Run the tests

The suite is fast and fully offline: it uses a deterministic hash-based
embedder (selected via `EMBEDDING_BACKEND=hash`) and a fake LLM client, so it
never downloads model weights or contacts Ollama. You can install only the
lightweight test dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-test.txt
pytest
```

(`requirements-dev.txt` installs the test tools on top of the full runtime,
including the real model, if you want to test against both backends.)

## Configuration

All settings come from the environment (or a local `.env`); see `.env.example`
for the full list. Notable knobs:

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `JWT_SECRET` | (placeholder) | Signing key for access tokens - override in every real deployment |
| `DATABASE_URL` | sqlite+aiosqlite:///./ai_search.db | Async SQLAlchemy URL |
| `EMBEDDING_BACKEND` | `sentence-transformers` | `sentence-transformers` (real model) or `hash` (offline, for tests) |
| `EMBEDDING_MODEL_NAME` | `sentence-transformers/all-MiniLM-L6-v2` | Local sentence-transformer model |
| `OPENAI_BASE_URL` | `http://localhost:11434/v1` | LLM server base URL (OpenAI-compatible) |
| `OPENAI_API_KEY` | `ollama` | API key - any non-empty string for local Ollama |
| `OPENAI_MODEL` | `qwen2.5:0.5b` | Model name served by the LLM server |
| `LLM_BACKEND` | `openai` | `openai` (real client) or `fake` (deterministic offline, used by tests) |
| `LLM_TEMPERATURE` | `0.2` | Generation temperature (low = grounded, faithful answers) |
| `LLM_MAX_TOKENS` | `700` | Max tokens per response |
| `LLM_REQUEST_TIMEOUT` | `180.0` | Seconds before giving up on the LLM |
| `CHAT_TOP_K` | `4` | Chunks retrieved as RAG context for `/chat` |
| `CORS_ALLOW_ORIGINS` | `http://localhost:8000,http://localhost:3000` | Comma-separated browser origins. Use `*` for any origin (open demo). For a example.com demo frontend: `https://chat.example.com` |

## Run with Docker

```bash
docker build -t ai-search .
docker run -p 8000:8000 \
  -e JWT_SECRET="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')" \
  -e CORS_ALLOW_ORIGINS="http://localhost:8000" \
  ai-search
```

The image installs the CPU-only torch wheel and runs a single uvicorn worker
(one model load per process). Scale by adding replicas, not workers.

For a demo with a frontend hosted at `https://chat.example.com`:

```bash
docker run -p 8000:8000 \
  -e JWT_SECRET="..." \
  -e CORS_ALLOW_ORIGINS="https://chat.example.com" \
  -e OPENAI_MODEL="qwen2.5:0.5b" \
  ai-search
```

## Memory footprint and deployment notes

Measured on this build (Python 3.12, CPU-only torch 2.5.1, MiniLM-L6-v2,
qwen2.5:0.5b via Ollama):

- Full application (FastAPI + embedding model) peak resident memory: about
  490 MB (the embedding model and torch/transformers runtime dominate).
- qwen2.5:0.5b adds ~500 MB for the Ollama process. Total system usage for
  both processes combined is under 1 GB.
- A 512 MB free tier is borderline for the FastAPI process alone; about 1 GB
  is the comfortable, safe target for the full stack.
- Cold model load takes roughly 10 seconds on first boot; set health-check
  startup grace accordingly.
- Keep one model load per process (single worker per replica) and scale out
  horizontally rather than adding workers per replica.
- For a hard 512 MB ceiling, switch to an ONNX or quantized MiniLM build, or
  run the `hash` backend to exercise the full API surface without the model.

## Project layout

```
app/
  main.py            FastAPI app, lifespan, model load + seeding
  core/              config (pydantic-settings), security (JWT/bcrypt), deps
  db/                async engine/session + SQLAlchemy models
  schemas/           Pydantic v2 request/response models (incl. chat)
  services/          embedding, chunking, search index, LLM client, chat, auth
  routers/           auth, documents, search/ask, chat, health
  corpus/            built-in seed documents (original text)
tests/               async pytest suite (offline hash embedder + fake LLM)
```

## Notes

- No paid external API is called anywhere. Both the embedding model and the
  generative LLM run locally; OpenAI is only ever a documented config swap.
- The seed corpus is original text written for this project.
- The test suite is fully offline: `EMBEDDING_BACKEND=hash` and
  `LLM_BACKEND=fake` are forced by `tests/conftest.py` so tests are fast,
  deterministic, and never contact a model server.

Built by Talal Alyaseen.
