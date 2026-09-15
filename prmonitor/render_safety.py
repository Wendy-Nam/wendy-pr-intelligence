"""Output safety primitives used by renderers for LLM-supplied text/links."""
from __future__ import annotations
import html
from urllib.parse import urlsplit

def text(value: object) -> str:
    return html.escape(str(value or ""), quote=False)

def safe_url(value: object) -> str | None:
    raw=str(value or '').strip(); parts=urlsplit(raw)
    if parts.scheme.lower() not in {'http','https'} or not parts.netloc: return None
    return html.escape(raw,quote=True)
