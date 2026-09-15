#!/usr/bin/env python3
"""Shared, hardened RSS/Google-News fetch — one implementation for both the
newsletter collector (scripts/pipeline/fetch-urls.py) and the PR clipping
collector (scripts/pr/render_pr_clipping.py).

Both used to fetch feeds independently: fetch-urls.py had raw-bytes fetch +
retry + 3-stage XML-recovery fallback (real news feeds routinely emit control
characters, unescaped `&`, or truncated XML), while render_pr_clipping.py's
Google News collector called `feedparser.parse(url)` directly with none of
that — so the exact same broken-feed class of failure silently dropped PR
mentions that the newsletter path would have recovered. This module is that
recovery logic, extracted once so both collectors get it.

Pure `requests`/`feedparser`/(optional) `lxml` — no OS-specific paths or
shell calls, so it behaves the same on Windows/Linux/macOS.
"""
from __future__ import annotations

import re
import sys
import time

import feedparser
import requests

USER_AGENT = "PRMonitor/0.2 (+news-monitor plugin)"
DEFAULT_TIMEOUT = 15
DEFAULT_RETRIES = 3


def fix_common_xml_errors(raw: bytes) -> bytes:
    """Strip/repair the invalid bytes real-world RSS feeds routinely emit.

    - BOM removal
    - control characters outside XML 1.0's allowed set (tab/LF/CR)
    - bare `&` not part of a known entity → `&amp;` (the most common cause
      of feedparser choking on an otherwise-fine feed)
    """
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]

    allowed_control = {0x09, 0x0A, 0x0D}
    cleaned = bytearray(b for b in raw if b >= 0x20 or b in allowed_control)
    raw = bytes(cleaned)

    try:
        text = raw.decode("utf-8", errors="replace")
        text = re.sub(
            r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", "&amp;", text)
        raw = text.encode("utf-8")
    except Exception:
        pass
    return raw


def fetch_raw_bytes(url: str, timeout: int = DEFAULT_TIMEOUT,
                    max_retries: int = DEFAULT_RETRIES) -> bytes | None:
    """GET raw bytes with retry. Connection reset/timeout → exponential
    backoff retry; DNS failure/4xx → give up immediately (retrying won't help).
    """
    backoff = 1.0
    for attempt in range(max_retries):
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT},
                             timeout=timeout, allow_redirects=True)
            if 400 <= r.status_code < 500:
                return None
            r.raise_for_status()
            return r.content
        except requests.exceptions.ConnectionError:
            if attempt == max_retries - 1:
                return None
            time.sleep(backoff)
            backoff *= 2
        except requests.exceptions.Timeout:
            if attempt == max_retries - 1:
                return None
            time.sleep(backoff)
            backoff *= 2
        except Exception:
            if attempt > 0:
                return None
            time.sleep(backoff)
    return None


def parse_with_fallback(raw: bytes, url: str, source_name: str = "") -> "feedparser.FeedParserDict":
    """3-stage parse: feedparser as-is → after fix_common_xml_errors →
    lxml recover mode (if installed) re-encoded through feedparser.
    """
    parsed = feedparser.parse(raw)
    if parsed.entries:
        return parsed

    fixed = fix_common_xml_errors(raw)
    parsed = feedparser.parse(fixed)
    if parsed.entries:
        print(f"  INFO [{source_name or url}] XML 1차 보정 후 {len(parsed.entries)}건 복구",
              file=sys.stderr)
        return parsed

    try:
        from lxml import etree
        parser = etree.XMLParser(recover=True, encoding="utf-8")
        root = etree.fromstring(fixed, parser=parser)
        if root is not None:
            reconstructed = etree.tostring(root, encoding="utf-8")
            parsed = feedparser.parse(reconstructed)
            if parsed.entries:
                print(f"  INFO [{source_name or url}] lxml recover 로 {len(parsed.entries)}건 복구",
                      file=sys.stderr)
                return parsed
    except ImportError:
        pass  # lxml 없으면 skip — 앞 두 단계 결과로 계속
    except Exception as e:
        print(f"  WARN [{source_name or url}] lxml recover 에러: {e}", file=sys.stderr)

    return parsed  # 빈 상태로 반환 (entries=0) — 호출부가 판단


def fetch_parsed_feed(url: str, source_name: str = "",
                      timeout: int = DEFAULT_TIMEOUT,
                      max_retries: int = DEFAULT_RETRIES) -> "feedparser.FeedParserDict":
    """The full robust path: raw bytes → 3-stage fallback parse, with a last-
    resort direct `feedparser.parse(url)` if the raw-bytes fetch itself failed
    (matches feedparser's own network handling as a final safety net).
    """
    raw = fetch_raw_bytes(url, timeout=timeout, max_retries=max_retries)
    if raw is None:
        try:
            return feedparser.parse(url, agent=USER_AGENT,
                                    request_headers={"User-Agent": USER_AGENT})
        except Exception as e:
            print(f"  WARN fetch 실패 [{source_name or url}]: {e}", file=sys.stderr)
            return feedparser.parse(b"")  # empty parsed result, entries=[]
    return parse_with_fallback(raw, url, source_name)
