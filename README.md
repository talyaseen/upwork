# AI dev-tools chatbot demo

A self-hosted, retrieval-grounded AI assistant for developer workflows, in two
components:

- **`fastapi-ai-devtools-demo/`** - Python / FastAPI backend. Grounded RAG over a
  sanitized corpus, streaming chat (SSE), an in-house prompt-injection / jailbreak
  guard, output redaction, and a hardened deployment story. Serves a local 7B via
  an OpenAI-compatible engine; no paid external API is contacted by default.
- **`flutter-ai-chat/`** - Flutter (web) chat frontend. Streaming answers,
  citations, Mermaid diagram rendering, code-review and Q&A skills.

Each component has its own `README.md` with setup, configuration, and test
instructions.

## External dependency: OpenJarvis

The generative engine layer builds on [OpenJarvis](https://github.com/open-jarvis/OpenJarvis),
which is an **external dependency** and is **not** bundled in this repository.
The backend uses only its in-process engine API (local Ollama / vLLM) plus the
message dataclasses - no OpenJarvis agent, tool registry, shell, file, or network
tool is wired in. Clone and install it alongside the backend as described in
`fastapi-ai-devtools-demo/README.md`.

## Configuration and secrets

No secrets are committed. Copy `fastapi-ai-devtools-demo/.env.example` to `.env`
and fill in the values for your deployment; `.env` is gitignored. Host- and
provider-specific redaction tokens are supplied out-of-band via `GUARD_REDACT_TERMS`.
