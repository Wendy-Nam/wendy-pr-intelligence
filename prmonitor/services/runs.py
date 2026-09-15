"""Run-level orchestration guardrails around planned jobs."""
from __future__ import annotations
import time
from dataclasses import dataclass
from .jobs import JobPlan, JobRequest, ingest_result
from ..models import RunState

@dataclass(frozen=True)
class RunExecution:
    results: tuple[dict, ...]
    calls: int
    exhausted: bool

def prepare_run(store, record, plan: JobPlan):
    """Persist a deterministic plan and move a newly-created run to PREPARED."""
    for request in plan.jobs:
        store.record_job(run_id=request.run_id, job_id=request.job_id,
                         request_hash=request.request_hash, kind=request.kind,
                         required=request.required, request=request.payload)
    if record.state == RunState.CREATED:
        return store.transition(record.run_id, record.revision, {RunState.CREATED}, RunState.PREPARED)
    return record

def execute_headless(plan: JobPlan, invoke, *, max_calls: int, deadline_seconds: float) -> RunExecution:
    started=time.monotonic(); results=[]; calls=0
    for request in plan.jobs:
        if calls >= max_calls or time.monotonic()-started >= deadline_seconds:
            return RunExecution(tuple(results),calls,True)
        envelope=invoke(request); calls += 1
        if envelope.get('error') and not request.required:
            results.append({'run_id': request.run_id, 'job_id': request.job_id,
                            'request_hash': request.request_hash, 'warning': envelope['error']})
            continue
        results.append(ingest_result(envelope,request))
    return RunExecution(tuple(results),calls,False)
