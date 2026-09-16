"""PR Monitor multi-host news intelligence engine package.

Domain-agnostic news-automation pipeline. Org-specific knowledge lives in the
domain pack under the workspace ``config/`` directory. See
``docs/ARCHITECTURE.md`` for the runtime boundaries.
"""
__version__ = "0.5.6"


class PrMonitorError(RuntimeError):
    """Base for all engine errors — lets callers ``except PrMonitorError`` catch
    any plugin-originated failure (venv bootstrap, domain-pack load, …) while
    still subclassing RuntimeError for legacy ``except RuntimeError`` paths."""
