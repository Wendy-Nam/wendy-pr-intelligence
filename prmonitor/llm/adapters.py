"""Thin compatibility adapter selecting the v1 backend without host side effects."""
from __future__ import annotations
import os
from .claude import ClaudeBackend
from .codex import CodexBackend
from .generic import GenericBackend
from .hermes import HermesBackend

def backend(name: str | None = None, *, generic_template=None):
    selected=(name or os.environ.get('PRM_LLM','claude')).lower()
    if selected == 'claude': return ClaudeBackend()
    if selected == 'codex': return CodexBackend()
    if selected in {'hermes','generic'}: return HermesBackend(generic_template)
    raise ValueError(f'unknown backend: {selected}')
