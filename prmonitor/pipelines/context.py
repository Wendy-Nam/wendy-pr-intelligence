"""Immutable synthesis-context construction from explicit snapshots."""
from __future__ import annotations
from copy import deepcopy
from ..models import canonical_json_hash

def build_context(*, date: str, categories: list[dict], competitor_articles: dict, self_context: dict, window_start: str, window_end: str) -> dict:
    """Return a detached JSON-compatible context; callers may safely cache it."""
    result={"date":date,"window_start":window_start,"window_end":window_end,
            "categories":deepcopy(categories),"competitor_articles":deepcopy(competitor_articles),
            "self_context_bundle":deepcopy(self_context)}
    result["input_hash"]=canonical_json_hash({k:v for k,v in result.items() if k != "input_hash"})
    return result
