"""Link-local allowlist wrapper around the output stream redactor.

2026-07-03 polish: the benign IMDS link-local address 169.254.169.254 was being
mangled by the blanket IPv4 output redaction ("169.254.169.254" -> "[redacted]54")
inside an ordinary EC2-metadata answer. LinkLocalPreservingRedactor exempts the
169.254.0.0/16 range while every other IPv4 (a private host IP, any public address),
configured host tokens, secrets and /home paths stay redacted exactly as before.
"""

from __future__ import annotations

from app.core.output_redaction import LinkLocalPreservingRedactor
from app.services.guard import PromptGuard


def _stream(guard: PromptGuard, fragments: list[str]) -> str:
    r = LinkLocalPreservingRedactor(guard.make_stream_redactor())
    out = "".join(r.feed(f) for f in fragments)
    return out + r.flush()


def test_link_local_imds_ip_survives_redaction() -> None:
    g = PromptGuard()
    text = "Query the IMDS at http://169.254.169.254/latest/meta-data/public-ipv4"
    out = _stream(g, [text])
    assert "169.254.169.254" in out
    assert "[redacted]" not in out
    assert "\x00" not in out  # sentinel never escapes


def test_link_local_survives_when_split_across_fragments() -> None:
    g = PromptGuard()
    # The address is split across streamed token fragments.
    out = _stream(g, ["curl http://169.", "254.169.", "254/latest ok"])
    assert "169.254.169.254" in out and "[redacted]" not in out
    assert "\x00" not in out


def test_public_ip_still_redacted_alongside_link_local() -> None:
    g = PromptGuard(redact_terms=["203.0.113.10"])  # stand-in for a private host IP
    text = (
        "The host is at 203.0.113.10 but IMDS is always 169.254.169.254 "
        "and a random box might be 203.0.113.9."
    )
    out = _stream(g, [text])
    # Link-local preserved...
    assert "169.254.169.254" in out
    # ...while a private host IP and an arbitrary public IP are still masked.
    assert "203.0.113.10" not in out
    assert "203.0.113.9" not in out
    assert "[redacted]" in out
    assert "\x00" not in out


def test_hub_ip_masked_even_when_split_across_fragments() -> None:
    g = PromptGuard(redact_terms=["203.0.113.10"])
    out = _stream(
        g, ["we run on 203.191.", "238.237 and imds 169.254.", "169.254 done"]
    )
    assert "203.0.113.10" not in out and "[redacted]" in out
    assert "169.254.169.254" in out
    assert "\x00" not in out


def test_benign_text_passes_through_unchanged() -> None:
    g = PromptGuard()
    out = _stream(g, ["Retrieval ", "augmented ", "generation is grounded."])
    assert out == "Retrieval augmented generation is grounded."


def test_other_link_local_addresses_in_range_survive() -> None:
    g = PromptGuard()
    out = _stream(g, ["fallback address 169.254.1.1 is link-local"])
    assert "169.254.1.1" in out and "[redacted]" not in out
