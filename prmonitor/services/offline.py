"""Deterministic fixture pipeline for CI and release verification."""
from __future__ import annotations
import hashlib
from dataclasses import dataclass
from pathlib import Path
from ..delivery import LocalTransport, send_validated
from ..models import RunSpec
from ..render import render_briefing
from ..storage.runs import RunStore
from .engine import Engine

@dataclass(frozen=True)
class OfflineResult:
    run_id: str
    status: str
    html: Path
    delivery_id: str | None

def run_fixture(store: RunStore, spec: RunSpec, *, root: Path, recipient: str = 'fixture@example.test') -> OfflineResult:
    engine = Engine(store); prepared = engine.prepare(spec)
    for request in prepared.plan.jobs:
        engine.accept_result(request, {'run_id': request.run_id, 'job_id': request.job_id,
                                       'request_hash': request.request_hash, 'result': {'fixture': True}}, result_hash='fixture')
    briefing = {'tldr': 'Fixture briefing', 'insights': [{'observation': 'Fixture observation', 'refs': ['a_1']}],
                'category_summary': [{'category_id': 'fixture'}]}
    report = engine.validate(prepared, briefing, article_ids={'a_1'}, category_ids={'fixture'}, policy={})
    html = root / 'fixture.html'; render_briefing(briefing, report, policy={}, output=html)
    receipt = send_validated(report=report, briefing=briefing, policy={}, html=html.read_bytes(),
                             recipient=recipient, transport=LocalTransport(root / 'delivery'),
                             expected_html_hash=hashlib.sha256(html.read_bytes()).hexdigest())
    return OfflineResult(prepared.record.run_id, report.status, html, receipt.delivery_id)
