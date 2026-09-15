"""Collection outcome classification; network providers stay outside this module."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Iterable
from ..models import RunState

@dataclass(frozen=True)
class SourceResult:
    id: str
    status: str
    returned_count: int = 0
    error: dict | None = None

@dataclass(frozen=True)
class CollectionReport:
    run_id: str
    window_start: str
    window_end: str
    sources: tuple[SourceResult, ...]
    discovered_count: int
    extracted_count: int
    eligible_count: int
    excluded_count: int
    timestamp_unknown_count: int
    all_sources_failed: bool
    incomplete: bool
    diagnostics: tuple[dict, ...] = ()
    schema_version: int = 1
    @property
    def outcome(self) -> RunState:
        if self.all_sources_failed: return RunState.FAILED
        if self.eligible_count == 0: return RunState.NO_DATA
        return RunState.PREPARED
    def as_dict(self):
        d=asdict(self); d['sources']=list(d['sources']); d['diagnostics']=list(d['diagnostics']); return d

def report(run_id: str, window_start: str, window_end: str, sources: Iterable[SourceResult], *, discovered: int, extracted: int, eligible: int, excluded: int=0, timestamp_unknown: int=0, diagnostics: Iterable[dict]=()) -> CollectionReport:
    sources=tuple(sources); successful=any(x.status == 'ok' for x in sources)
    return CollectionReport(run_id,window_start,window_end,sources,discovered,extracted,eligible,excluded,timestamp_unknown,not successful,bool(sources and not all(x.status == 'ok' for x in sources)),tuple(diagnostics))

class CollectionService:
    """Stage-cache orchestration around an injected collector function."""
    def __init__(self, cache): self.cache = cache
    def collect(self, *, cache_key: str, producer, force_refresh: bool = False):
        """Producer must return a CollectionReport; no network policy lives here."""
        payload, reused = self.cache.get_or_build(cache_key, lambda: producer().as_dict(), force_refresh=force_refresh)
        sources=tuple(SourceResult(**source) for source in payload['sources'])
        report=CollectionReport(**{**payload, 'sources': sources, 'diagnostics': tuple(payload.get('diagnostics', []))})
        return report, reused
