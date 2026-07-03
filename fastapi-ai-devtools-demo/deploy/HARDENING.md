# Hardening and containment

Defense-in-depth for the PUBLIC OpenJarvis demo. Layers, what each enforces, and
how it was validated (2026-06-30, on the 2x T4 host).

## 1. App layer (strongest): no dangerous capabilities reach the agent

The agent surface is EXACTLY three prompt-only skills and nothing else:

| skill        | what it does                                    | execution |
|--------------|-------------------------------------------------|-----------|
| `qa`         | grounded RAG over the sanitized corpus + cites  | none      |
| `code-review`| reviews PASTED TEXT (static analysis)           | none      |
| `mermaid`    | emits Mermaid SOURCE from a description         | none*     |

No OpenJarvis agent, tool registry, interpreter, shell, file tool, web/HTTP tool,
MCP, or messaging channel is wired in. The only OpenJarvis imports are the two
local inference engines (`engine.ollama`, `engine.openai_compat_engines`) and the
`core.types` message dataclasses. Enforced by tests:

- `tests/test_containment.py::test_skill_surface_is_exactly_the_allowlist`
- `tests/test_containment.py::test_app_only_imports_safe_openjarvis_modules`

### Zero code execution (code-review never runs the reviewed code)
`code-review` is pure LLM text analysis. It never shells out, never `eval`/`exec`,
never writes-then-runs. Proven by spawning-blocked test: even when the pasted code
is `os.system('touch /tmp/pwned')`, no process is spawned and `/tmp/pwned` is never
created - `tests/test_containment.py::test_code_review_never_executes_reviewed_code`.

(*) `mermaid` server-side SVG rendering shells out to `mmdc`. It is OFF by default
(`MERMAID_RENDER_ENABLED=false`); the frontend renders Mermaid client-side. With the
flag off the server runs NO subprocess for any chat/skill request -
`tests/test_containment.py::test_mermaid_render_off_by_default_spawns_no_subprocess`.

### Filesystem: input is text, never a path
`code-review` treats its input as TEXT; a path-looking message (`/etc/passwd`) is
never opened - `tests/test_containment.py::test_code_review_input_is_text_not_a_filepath`.

## 2. Prompt layer: in-house injection / jailbreak guard

`app/services/guard.py` adds an INPUT filter (refuses attacks before any model call)
and an OUTPUT filter (redacts configured host/identity/secret tokens; refuses on a
secret or system-prompt leak), plus a hardening clause appended to every system
prompt. Chosen IN-HOUSE (not an external ClawHub skill): Snyk's ToxicSkills found
~36% of community skills themselves carry injection, and OpenJarvis's first-party
`InjectionScanner` delegates to a Rust extension this lean install does not build.
In-house = auditable, pure-Python, network-free, zero supply-chain risk. Patterns
informed by the OpenJarvis Rust injection ruleset.

Blocks (each its own test, `tests/test_guard.py`): classic injection ("ignore
previous instructions", DAN, developer mode, "pretend no restrictions"), system-
prompt extraction, code-exec / file-read coercion, exfiltration. Legitimate pasted
code (with `os.system`, `eval`, `subprocess`) is NOT blocked under the code-review
skill. Benign questions pass.

### Location non-revealability (maintainer #1 priority)
The model must never reveal where it runs - directly or indirectly. Enforced by:
1. The system prompt orders it to treat its own location as unknown and decline.
2. The input guard REFUSES host/IP/region/country/city/provider/datacenter/ISP/
   timezone probes AND self-discovery commands (`ping yourself`, `hostname`, ...) -
   `tests/test_guard.py::test_location_probes_blocked_as_own_line_item`.
3. The model has NO tool/network/shell to self-discover its address.
4. The corpus is sanitized (no IP/host/region/provider; hosting = "a top secret
   location"); re-verified - no host IP, region/country, hosting-provider, or
   datacenter strings anywhere.
5. Output guard backstop redacts configured host tokens + bare IPs + `/home` paths.

No real IP/location string is hard-coded in the source. Maintainer-specific redaction
terms are injected via `GUARD_REDACT_TERMS` in the gitignored `.env` at deploy.

## 3. OS layer: systemd sandbox (`openjarvis-backend.service`)

Confines the FastAPI backend (vLLM and Ollama run as separate services it reaches
over localhost). Delivered, NOT auto-installed. Validated live via `systemd-run`
with the same directives:

| guarantee                                   | directive                         | result |
|---------------------------------------------|-----------------------------------|--------|
| cannot read `/home`                         | `ProtectHome=true`                | DENIED |
| cannot read the `.env` / secrets            | `InaccessiblePaths=...`           | DENIED |
| cannot write outside the data dir           | `ProtectSystem=strict`            | DENIED (read-only fs) |
| CAN write only the data dir                 | `ReadWritePaths=/var/lib/...`     | allowed |
| no privilege escalation                     | `NoNewPrivileges` + caps dropped  | enforced |
| non-root                                    | `User=openjarvis`                 | enforced |
| minimal devices (only nvidia ro)            | `DevicePolicy=closed`+`DeviceAllow`| enforced |
| no new namespaces / SUID / realtime         | `RestrictNamespaces` etc.         | enforced |

Run `sudo bash deploy/verify_sandbox.sh` on the deploy host to reproduce.

### Caveat 1 - egress filtering needs cgroup-BPF or a host firewall
`IPAddressDeny=any` / `IPAddressAllow=localhost` is the intended egress lockdown,
but it requires cgroup-v2 BPF support. On the validation LXC it was NOT enforced
(external `curl` still succeeded). ON THE DEPLOY HOST verify it is enforced, AND
enforce an egress default-deny at the HOST FIREWALL (nftables/ufw: allow loopback +
:11434 + :8000, deny the rest) as the guaranteed layer. The reverse-proxy edge in
front of this deploy already runs a default-deny egress allowlist.

### Caveat 2 - MemoryDenyWriteExecute (W^X)
Validated on this build: `import torch` (CPU) and the full app factory load fine
under `MemoryDenyWriteExecute=true`. Left commented OFF pending a load-test of the
real `sentence-transformers` embedding path under traffic (some torch/BLAS runtime
paths map W+X). Enable once that passes; if it ever breaks startup, drop ONLY that
one line and keep the rest.

## 4. Thread cap (`ollama-thread-cap.conf`)

`CPUAffinity=0-31` confines inference to 32 of 56 CPUs (validated:
`Cpus_allowed_list == 0-31`); the serving layer keeps the other 24 cores. (The CPU
1B fallback was REMOVED - GPU-only demo - so the Ollama-off-GPU pin is now moot for
serving, but the affinity cap still applies to any local inference process.)

## 5. GPU-ONLY (no CPU fallback)

Maintainer decision (2026-06-30): the demo serves ONLY the GPU 7B. When the GPU is
unavailable (serving training, or yielded via the lock) the demo reports OFFLINE
(`backend_tier: "offline"`, `done.finish_reason: "offline"`, banner shows offline)
instead of answering with a weaker, more-jailbreakable small model. This both
improves answer quality and removes the easiest jailbreak surface.

## 6. Red-team results + fixes (external red-team, 38 attempts)

VERDICT: location/IP NEVER leaked via any vector (the model has no infra knowledge
- it declines or hallucinates a WRONG provider); no code execution via code-review;
no web/file/shell tool reachable. Fixes applied to the confirmed findings:

| finding | severity | fix |
|---|---|---|
| `/api/admin` IP-gate defeatable via XFF + uvicorn proxy-headers | HIGH | THREE layers now: reject any admin request carrying a forwarding header; peer-IP allowlist; `X-Admin-Token` shared secret (set for go-live). Never run uvicorn with `--proxy-headers`. |
| output-guard redaction defeated by streamed token-splitting | MED | streaming redactor with a carryover buffer redacts sensitive tokens ACROSS fragments (`PromptGuard.make_stream_redactor`) |
| input guard ignored history | MED | `inspect_input` now scans prior turns too |
| system-prompt clause extractable (translation/completion) | MED | prompt-layer is best-effort; the durable fix is the **safety LoRA** (`training/`) - refusals baked into the weights |
| `GUARD_REDACT_TERMS` unset by default | config | documented; set in the gitignored `.env` at go-live |
| over-blocks legit security code-review | LOW | guard targets instructions-to-the-assistant, not code keywords; safety-LoRA dataset includes legit security-review positives |
| `Server: uvicorn` header | LOW | response-header middleware sets `Server: demo` + `X-Content-Type-Options`/`Referrer-Policy` |
| no rate-limit on public endpoints | LOW | enforced at the CF/proxy edge (architecture) + the in-app generation queue |

### Weight-level safety (the maintainer's "bake it into the weights") - TRAINED + VALIDATED
`training/` is a LoRA pipeline (`build_safety_dataset.py` + `train_safety_lora.py`
+ `merge_safety_lora.py` + README) that teaches the 7B to refuse host/location,
system-prompt-extraction, jailbreak, and code-exec coercion - including the
multilingual/indirect paraphrases that slip a regex - while preserving normal Q&A
and code review. TRAINED + VALIDATED 2026-06-30 on the 2x T4: on guard-bypassing
prompts with a NEUTRAL system prompt (so refusals come from the WEIGHTS), the base
model leaked 5/10 (all HALLUCINATED wrong locations) and the safety model leaked
0/10 - clean refusals even for Spanish/German/French. For production the adapter is
MERGED into the weights (vLLM runtime LoRA is too slow on Turing/T4) and served as
a normal model at full speed.

## GO-LIVE GATES (must hold before public exposure)
1. Public edge (CF + proxy nginx) STRIPS `/api/admin` (layer c).
2. `ADMIN_TOKEN` set; uvicorn NOT run with `--proxy-headers`.
3. `GUARD_REDACT_TERMS` set to the real host/provider tokens (gitignored `.env`).
4. Host-firewall egress default-deny (the `IPAddressDeny` cgroup-BPF caveat).
5. (Recommended) train + serve the safety LoRA so refusals are in the weights.
