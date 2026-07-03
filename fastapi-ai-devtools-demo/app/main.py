"""FastAPI application entrypoint.

Wires together configuration, the database, the local embedding model and the
routers. On startup it loads the embedding model once, creates tables, hydrates
the in-memory vector index from SQLite and (optionally) seeds a built-in
corpus so the demo returns useful results immediately.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.isolation import configure_openjarvis_isolation
from app.core.threads import configure_model_thread_caps
from app.db.database import (
    dispose_db,
    get_session_factory,
    init_db,
)
from app.routers import (
    admin,
    auth,
    chat,
    conversations,
    documents,
    health,
    models,
    search,
    skills,
    status,
)
from app.services.conversation_store import ConversationStore
from app.services.embedding import build_embedder
from app.services.generation_gate import GenerationGate
from app.services.gpu_monitor import GpuMonitor
from app.services.gpu_preemptor import GpuPreemptor
from app.services.gpu_router import GpuRouter
from app.services.learning import SessionLearningStore
from app.services.llm_client import build_llm_client
from app.services.model_catalog import ModelCatalog
from app.services.openjarvis_engine import VllmController
from app.services.search_service import SearchService
from app.services.seed import seed_corpus_if_empty

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("app")

API_DESCRIPTION = """
An AI-First backend that does **semantic search** and **extractive question
answering** over a document corpus, powered entirely by a **local embedding
model**. No paid external API is ever contacted; the model runs in-process on
CPU.

**How it works**

1. Documents are split into overlapping chunks.
2. Each chunk is embedded into a dense vector with a local sentence-transformer.
3. Search embeds your query and ranks chunks by cosine similarity.
4. `/ask` returns the most relevant passage verbatim (extractive, fully
   grounded) together with source citations - no hallucination, no generative
   model.
5. `/chat` adds a conversational, grounded (RAG) layer: it retrieves the
   relevant passages and has a **local generative LLM** (Ollama, via its
   OpenAI-compatible API) compose a streamed, cited answer. Still no paid
   external API - the model runs locally. Pointing three env vars at OpenAI
   swaps in a hosted model with no code change.

**Try it**

- `POST /auth/register` then `POST /auth/login` to get a bearer token.
- `GET /search?q=...` works without auth against the built-in seed corpus.
- `POST /ask` for an extractive answer with citations.
- `POST /chat` (auth) for a streamed, conversational, grounded answer.
"""

TAGS_METADATA = [
    {"name": "auth", "description": "Register and obtain JWT access tokens."},
    {
        "name": "documents",
        "description": "Ingest, list, read and delete documents. Writes "
        "require authentication.",
    },
    {
        "name": "search",
        "description": "Semantic search and extractive Q&A over the corpus.",
    },
    {
        "name": "chat",
        "description": "Conversational, grounded (RAG) chat streamed over "
        "Server-Sent Events, powered by a local generative LLM with GPU-yield "
        "routing, dynamic preemption, a generation queue and model selection.",
    },
    {
        "name": "models",
        "description": "The curated set of selectable LLM models and their "
        "current availability.",
    },
    {
        "name": "skills",
        "description": "The enabled, public-safe (prompt-only) skills.",
    },
    {
        "name": "status",
        "description": "Public GPU/CPU banner state (safe fields only).",
    },
    {
        "name": "admin",
        "description": "Internal-only GPU-yield lock control (IP-gated, no token; "
        "the public nginx layers must never forward /api/admin).",
    },
    {"name": "health", "description": "Liveness and readiness probe."},
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logger.info(
        "Starting %s v%s (embedding backend: %s)",
        settings.app_name,
        settings.app_version,
        settings.embedding_backend,
    )

    # Load the embedding model once, off the event loop (it can be slow).
    embedder = await run_in_threadpool(build_embedder, settings)
    search_service = SearchService(embedder=embedder, settings=settings)
    app.state.search_service = search_service
    logger.info(
        "Embedding model ready (dimension=%d).", search_service.dimension
    )

    # HARD-ISOLATE this public demo's OpenJarvis (demo-only OPENJARVIS_HOME) so
    # nothing from any other OpenJarvis instance can leak in or be polluted.
    oj_home = configure_openjarvis_isolation(settings)
    logger.info("OpenJarvis demo home: %s", oj_home)

    # Cap ONLY the LLM inference threads (serving layer stays uncapped).
    applied = configure_model_thread_caps(settings)
    logger.info("Model thread cap applied: %s", applied)

    # Build the GPU-aware router + generation gate + model catalog. Constructing
    # the clients is cheap (no network call); models are contacted lazily on the
    # first request. The "fake" backend is fully offline (test suite).
    catalog = ModelCatalog.from_settings(settings)
    monitor = GpuMonitor(settings)
    vllm_controller = VllmController()
    router = GpuRouter(
        primary=build_llm_client(settings),
        settings=settings,
        monitor=monitor,
        catalog=catalog,
    )
    app.state.model_catalog = catalog
    app.state.gpu_monitor = monitor
    app.state.vllm_controller = vllm_controller
    app.state.llm_router = router
    app.state.generation_gate = GenerationGate(
        max_concurrent=settings.gen_max_concurrent,
        max_queue=settings.gen_max_queue,
    )
    # Public-safe, per-session self-learning surface (None when disabled).
    app.state.learning_store = (
        SessionLearningStore(settings) if settings.learning_enabled else None
    )
    # Durable conversation log: every completed /chat exchange is persisted to
    # the app's DB (the existing async SQLAlchemy store). Read access is
    # internal-only (see app/routers/conversations.py).
    app.state.conversation_store = ConversationStore()
    logger.info(
        "LLM router ready (backend=%s gpu_model=%s, GPU-only, queue=%d/%d).",
        settings.llm_backend,
        settings.openai_model,
        settings.gen_max_concurrent,
        settings.gen_max_queue,
    )

    # Always-on dynamic GPU preemptor (yields the GPU to training instantly).
    # Skip it for the offline "fake" backend so the test suite never polls
    # nvidia-smi in the background.
    preemptor: GpuPreemptor | None = None
    if settings.gpu_monitor_enabled and settings.llm_backend != "fake":
        preemptor = GpuPreemptor(
            router=router, settings=settings, controller=vllm_controller
        )
        preemptor.start()
        logger.info("GPU preemptor started (interval=%.1fs).",
                    settings.gpu_monitor_interval_seconds)
    app.state.gpu_preemptor = preemptor

    await init_db()

    factory = get_session_factory()
    async with factory() as session:
        await search_service.load_index(session)
        if settings.seed_on_startup:
            await seed_corpus_if_empty(session, search_service)
        else:
            await session.commit()
    logger.info(
        "Index ready (%d chunks indexed).", search_service.size
    )

    try:
        yield
    finally:
        if preemptor is not None:
            await preemptor.stop()
        await dispose_db()
        logger.info("Shutdown complete.")


def create_app() -> FastAPI:
    settings = get_settings()
    # Public demo: the interactive API docs (/docs, /redoc) and the raw
    # OpenAPI schema (/openapi.json) are DISABLED to shrink the attack surface
    # and to avoid FastAPI's auto-generated metadata exposing any identity. The
    # title/description carry no personal name, contact, or terms of service.
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=API_DESCRIPTION,
        openapi_tags=TAGS_METADATA,
        lifespan=lifespan,
        license_info={"name": "MIT"},
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    # Allow browser clients (such as the Flutter web app) to call the API
    # cross-origin. Origins are configurable via CORS_ALLOW_ORIGINS.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def _harden_response_headers(request, call_next):
        # Do not advertise the server stack ("Server: uvicorn") and add a couple of
        # cheap hardening headers. The public edge (CF/nginx) can override these.
        response = await call_next(request)
        response.headers["Server"] = "demo"
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(documents.router)
    app.include_router(search.router)
    app.include_router(chat.router)
    app.include_router(conversations.router)
    app.include_router(models.router)
    app.include_router(skills.router)
    app.include_router(status.router)
    app.include_router(admin.router)
    return app


app = create_app()
