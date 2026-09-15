"""Canonical article identity and URL normalization shared by every stage."""
from __future__ import annotations
import hashlib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from ..errors import EngineError

def canonical_url(url: str) -> str:
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        raise EngineError("INVALID_URL", "article URL must be absolute", stage="collection")
    host = parts.hostname.lower() if parts.hostname else ""
    port = parts.port
    netloc = host if port in (None, 80 if parts.scheme.lower() == "http" else 443 if parts.scheme.lower() == "https" else -1) else f"{host}:{port}"
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not (k.lower().startswith("utm_") or k.lower() in {"gclid", "fbclid"})]
    return urlunsplit((parts.scheme.lower(), netloc, parts.path or "/", urlencode(query), ""))

def article_id(url: str | None, *, title: str = "", source: str = "", published_at: str = "") -> str:
    if url:
        return "a_" + hashlib.sha256(canonical_url(url).encode()).hexdigest()[:32]
    identity = "\0".join((title, source, published_at))
    return "u_" + hashlib.sha256(identity.encode()).hexdigest()[:32]

def registry(articles: list[dict]) -> dict[str, dict]:
    out = {}
    for article in articles:
        raw_url = article.get("canonical_url") or article.get("url")
        normalized = canonical_url(raw_url) if raw_url else ""
        aid = article_id(normalized or None, title=article.get("title", ""), source=article.get("source_name", ""), published_at=article.get("published_at", ""))
        if aid in out and out[aid].get("canonical_url") != normalized:
            raise EngineError("ARTICLE_ID_COLLISION", f"collision for {aid}", stage="collection")
        out[aid] = {**article, "id": aid, "canonical_url": normalized}
    return out
