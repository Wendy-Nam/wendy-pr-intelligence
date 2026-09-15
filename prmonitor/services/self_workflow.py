"""Canonical self-PR workflow over explicit collected articles."""
from __future__ import annotations
from dataclasses import dataclass
from ..pipelines.pr import to_pr_records

@dataclass(frozen=True)
class SelfReport:
    records: tuple[dict, ...]
    counts: dict

def prepare_self_report(articles: list[dict], *, company_aliases: list[str], llm_enabled: bool = False) -> SelfReport:
    """Rules-first PR report preparation; no network/backend call is made here."""
    records = to_pr_records(articles, company_aliases=company_aliases)
    tones = {tone: sum(1 for record in records if record['tone'] == tone)
             for tone in ('positive','neutral','negative')}
    return SelfReport(tuple(records), {'total': len(records), 'tones': tones, 'llm_enabled': llm_enabled})
