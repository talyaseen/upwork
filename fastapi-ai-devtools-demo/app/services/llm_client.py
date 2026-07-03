"""Generative LLM client behind a tiny Protocol.

The /chat endpoint talks to a local generative model through an
OpenAI-COMPATIBLE API. By default that is a local Ollama instance exposed at
http://localhost:11434/v1, so no paid external API is ever contacted and
nothing leaves the box. The exact same wire format is what real OpenAI speaks,
which is the whole point of the seam: pointing OPENAI_BASE_URL / OPENAI_API_KEY
/ OPENAI_MODEL at api.openai.com swaps in a hosted model with no code change.

Two interchangeable implementations:

- ``OpenAICompatibleLLMClient`` wraps the official ``openai`` async SDK and
  streams chat-completion token deltas. It works against any OpenAI-compatible
  server (Ollama, vLLM, LocalAI, OpenAI itself).

- ``EchoLLMClient`` is a deterministic, network-free client used by the test
  suite (and as a safe offline fallback). It echoes a short, grounded-looking
  reply derived from the messages it is handed, so tests can assert that
  retrieval context and prior turns were threaded through without ever loading
  a model or opening a socket.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from app.core.config import Settings


@runtime_checkable
class LLMClient(Protocol):
    """Common interface for all generative backends."""

    model: str

    def stream_chat(
        self, messages: list[dict[str, str]]
    ) -> AsyncIterator[str]:
        """Stream assistant token deltas for a chat-completion request.

        ``messages`` is the standard OpenAI chat array (role/content dicts).
        Yields incremental text fragments as they are generated.
        """
        ...


class OpenAICompatibleLLMClient:
    """Streams from any OpenAI-compatible server (local Ollama by default)."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: float,
        repetition_penalty: float | None = None,
    ) -> None:
        # Imported lazily so the test suite never needs to construct a real
        # client when it runs with the "fake" backend.
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=0,
        )
        self.model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        # 2026-07-01 incident fix: vLLM (and other vLLM-compatible servers)
        # accept ``repetition_penalty`` as a provider extension via
        # ``extra_body`` on the OpenAI SDK; it is NOT a standard OpenAI field
        # so it cannot be passed as a direct keyword to ``.create()``. None
        # (e.g. when pointed at real OpenAI, which has no such field) sends
        # no extra body at all.
        self._repetition_penalty = repetition_penalty

    async def stream_chat(
        self, messages: list[dict[str, str]]
    ) -> AsyncIterator[str]:
        extra_body = (
            {"repetition_penalty": self._repetition_penalty}
            if self._repetition_penalty is not None
            else None
        )
        stream = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            stream=True,
            extra_body=extra_body,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None)
            if content:
                yield content

    async def aclose(self) -> None:
        """Release the wrapped ``AsyncOpenAI`` HTTP client (awaited).

        Per-request clients must be closed or their connection pool / file
        descriptors leak (FD churn once per request). ``AsyncOpenAI`` exposes an
        ASYNC ``.close()``; a caller that fell back to a generic sync ``close()``
        would invoke that coroutine WITHOUT awaiting it (leaving the pool open and
        emitting a "coroutine was never awaited" warning). This wrapper therefore
        exposes only an async ``aclose()`` - which ``_aclose_client`` prefers and
        awaits - and no sync ``close()``.
        """
        await self._client.close()


class EchoLLMClient:
    """Deterministic offline client (tests and network-free fallback).

    It never loads a model or opens a socket. The reply is synthesised from
    the messages it receives so that callers (and tests) can observe that the
    retrieved context block and the conversation history were passed through.
    """

    def __init__(self, model: str = "echo-offline") -> None:
        self.model = model

    @staticmethod
    def _split_messages(
        messages: list[dict[str, str]],
    ) -> tuple[str, str, int]:
        system = ""
        last_user = ""
        non_system = 0
        for m in messages:
            role = m.get("role", "")
            content = m.get("content", "")
            if role == "system":
                system = content
            else:
                non_system += 1
                if role == "user":
                    last_user = content
        # The trailing user turn is the current question, not prior history.
        prior_turns = max(non_system - 1, 0)
        return system, last_user, prior_turns

    @staticmethod
    def _synthesize(system: str, last_user: str, prior_turns: int) -> str:
        """Produce a deterministic reply whose SHAPE matches the active skill.

        The offline suite must exercise CONTENT-GATED artifact emission (a real
        diagram vs a real review vs plain prose), so the fake branches on the
        system prompt the skill installed - mirroring the output shape the real
        7B produces - instead of always returning generic grounded prose.
        """
        sys_low = system.lower()
        if "mermaid diagram" in sys_low:
            # Valid, fence-less Mermaid source (the diagram skill's contract).
            return (
                "flowchart TD\n"
                "  User[User] --> App[Application]\n"
                "  App --> Auth[Auth Service]\n"
                "  Auth --> App\n"
                "  App --> User"
            )
        if "## findings" in sys_low:
            # A structured review matching the code-review skill's Markdown
            # contract (Findings table + Suggested fixes).
            return (
                "## Findings\n\n"
                "| Severity | Location | Issue | Why it matters |\n"
                "| --- | --- | --- | --- |\n"
                "| WARNING | add() | Subtracts instead of adding | Wrong result |"
                "\n\n"
                "## Suggested fixes\n\n"
                "```python\n"
                "def add(a, b):\n"
                "    return a + b\n"
                "```\n"
                "Return the sum, not the difference."
            )
        context_present = "Context:" in system or "[1]" in system
        return (
            f"Based on the retrieved context, here is the grounded answer to "
            f"your question about '{last_user}'. "
            f"context_used={context_present} prior_turns={prior_turns}. "
            f"The supporting passages are cited as sources below."
        )

    async def stream_chat(
        self, messages: list[dict[str, str]]
    ) -> AsyncIterator[str]:
        system, last_user, prior_turns = self._split_messages(messages)
        # A canned reply, streamed space-delimited so the SSE token framing is
        # exercised exactly as in production. Splitting on spaces preserves the
        # newlines inside a Mermaid/Markdown reply.
        reply = self._synthesize(system, last_user, prior_turns)
        for word in reply.split(" "):
            yield word + " "


def build_chat_client(
    settings: Settings, *, tier: str, model: str
) -> LLMClient:
    """Build a generative client for a given tier ("gpu"/"cpu") and model.

    This is the single factory the GPU router uses to materialise the right
    client per request. The backend selector decides the transport:

    - ``fake``       -> ``EchoLLMClient`` (offline; tests never touch a socket).
    - ``openjarvis`` -> the in-process OpenJarvis engine API (vLLM on GPU,
                        Ollama on CPU). Imported LAZILY so the offline test
                        suite never imports OpenJarvis (and never pays its
                        ~2s torch import).
    - ``openai``     -> the plain OpenAI-compatible client against the tier's
                        endpoint (a lighter alternative transport).
    """
    if settings.llm_backend == "fake":
        return EchoLLMClient(model=model)

    if settings.llm_backend == "openjarvis":
        # Lazy import: keeps OpenJarvis (and torch) out of the offline test path.
        from app.services.openjarvis_engine import build_openjarvis_client

        return build_openjarvis_client(settings, tier=tier, model=model)

    # llm_backend == "openai": OpenAI-compatible transport to the GPU endpoint.
    return OpenAICompatibleLLMClient(
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key,
        model=model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        timeout=settings.llm_request_timeout,
        repetition_penalty=settings.llm_repetition_penalty,
    )


def build_llm_client(settings: Settings) -> LLMClient:
    """Construct the PRIMARY (GPU, 7B) generative client.

    GPU-only demo: there is no CPU fallback client. When the GPU is unavailable the
    router reports OFFLINE rather than serving a weaker model.
    """
    return build_chat_client(settings, tier="gpu", model=settings.openai_model)
