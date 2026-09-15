"""Central model-role and backend resolution for host/headless runs."""
from __future__ import annotations
import os

def resolve_model(role: str, *, backend: str | None = None, explicit: str | None = None,
                  config: dict | None = None) -> str | None:
    if explicit:
        return explicit
    env = os.environ.get(f"PRM_{role.upper()}_MODEL")
    if env:
        return env
    models = ((config or {}).get("llm") or {}).get("models") or {}
    return models.get(role)

def resolve_backend(*, mode: str, requested: str | None = None, config: dict | None = None) -> str | None:
    if mode == "host":
        return None
    return requested or ((config or {}).get("llm") or {}).get("backend")
