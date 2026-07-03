"""Link-local allowlist wrapper around the output stream redactor.

The output guard (``PromptGuard.make_stream_redactor``) defensively masks every
bare IPv4 token so the hub's public IP / any host address can never leak. That
same blanket rule also masked the *benign* IMDS link-local address
``169.254.169.254`` (the AWS EC2 Instance Metadata Service endpoint) inside a
perfectly normal ops answer, e.g. "curl http://169.254.169.254/latest/..." came
out as "curl http://[redacted]54/...". Link-local addresses (169.254.0.0/16) are
RFC 3927 non-routable and can never be a public or the hub's address, so they are
safe to surface verbatim.

This wraps the guard's stream redactor WITHOUT modifying it (guard.py is a frozen
security boundary): before a fragment reaches the inner redactor, complete
link-local addresses are swapped for an opaque sentinel the inner redactor leaves
untouched; after the inner redactor emits, the sentinel is swapped back to the
original address. Everything else (the hub IP, any other public IPv4, configured
host tokens, secrets, /home paths) is redacted exactly as before.

Both swaps are streaming-safe: each side buffers a bounded holdback so an address
or a sentinel split across token/emit boundaries is handled whole. The sentinel
uses NUL delimiters that never survive a full turn - by the time ``feed``/``flush``
returns, every complete sentinel has been restored, so a NUL can never reach the
client.
"""

from __future__ import annotations

import re

# Link-local range 169.254.0.0/16 (RFC 3927). Only these are preserved; every
# other IPv4 stays subject to the guard's blanket redaction.
_LINKLOCAL_RE = re.compile(r"\b169\.254\.\d{1,3}\.\d{1,3}\b")
# Longest link-local literal "169.254.255.255" == 15 chars: hold back that much
# so an address spanning fragments is matched only once fully assembled.
_LINKLOCAL_HOLD = 15

# Opaque, NUL-delimited sentinel carrying the address (dots -> dashes so it can
# never re-match the IPv4 rule and the guard leaves it intact). Longest form
# "\x00LL169-254-255-255\x00" == 19 chars.
_SENTINEL_RE = re.compile(r"\x00LL([0-9-]+)\x00")
_SENTINEL_HOLD = 19


def _to_sentinel(m: re.Match[str]) -> str:
    return "\x00LL" + m.group(0).replace(".", "-") + "\x00"


def _from_sentinel(m: re.Match[str]) -> str:
    return m.group(1).replace("-", ".")


class _StreamSub:
    """Stateful streaming regex substitution with a bounded holdback tail.

    Mirrors the guard redactor's own carry-over trick: substitute over the whole
    buffer each feed, emit everything except the last ``hold`` chars (where a
    match could still be completing), and carry the tail forward.
    """

    def __init__(self, pattern: re.Pattern[str], repl, hold: int) -> None:
        self._re = pattern
        self._repl = repl
        self._hold = hold
        self._buf = ""

    def feed(self, text: str) -> str:
        self._buf += text
        done = self._re.sub(self._repl, self._buf)
        if len(done) > self._hold:
            emit, self._buf = done[: -self._hold], done[-self._hold :]
            return emit
        self._buf = done
        return ""

    def flush(self) -> str:
        out = self._re.sub(self._repl, self._buf)
        self._buf = ""
        return out


class LinkLocalPreservingRedactor:
    """Wraps a stream redactor, exempting link-local (169.254.0.0/16) addresses.

    Exposes the same ``feed``/``flush`` contract as the inner redactor so it is a
    drop-in replacement at the call site.
    """

    def __init__(self, inner) -> None:
        self._inner = inner
        self._protect = _StreamSub(_LINKLOCAL_RE, _to_sentinel, _LINKLOCAL_HOLD)
        self._restore = _StreamSub(_SENTINEL_RE, _from_sentinel, _SENTINEL_HOLD)

    def feed(self, fragment: str) -> str:
        if not fragment:
            return ""
        return self._restore.feed(self._inner.feed(self._protect.feed(fragment)))

    def flush(self) -> str:
        drained = self._inner.feed(self._protect.flush())
        tail = self._inner.flush()
        out = self._restore.feed(drained + tail) + self._restore.flush()
        # Defense in depth: a NUL sentinel must never escape. If generation was
        # truncated mid-sentinel, strip the marker rather than leak a control char.
        if "\x00" in out:
            out = _SENTINEL_RE.sub(_from_sentinel, out).replace("\x00", "")
        return out
