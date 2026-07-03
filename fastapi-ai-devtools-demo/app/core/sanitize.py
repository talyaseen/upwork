"""Output sanitization helpers.

The public read endpoints (``/search``, ``/ask``, ``/chat``) echo corpus text
back to the caller. Even though the corpus is a curated, server-controlled seed
set, we HTML-escape every corpus-derived string on OUTPUT so that a browser
client can never be coerced into executing markup that round-tripped through the
API (stored-XSS defence in depth). Escaping is applied at the response boundary
only - never to the text used to ground the model - so retrieval quality is
unchanged. Seed text contains no HTML metacharacters, so this is a visual no-op
for the shipped corpus while still neutralising any ``<script>`` / ``<img
onerror=...>`` payload that might ever reach an output field.
"""

from __future__ import annotations

import html


def escape_html(value: str) -> str:
    """HTML-escape a string for safe embedding in an HTML context.

    Escapes ``& < > " '`` (``quote=True``) so the value is inert in both element
    and attribute contexts. Non-strings are returned unchanged.
    """
    if not isinstance(value, str):
        return value
    return html.escape(value, quote=True)
