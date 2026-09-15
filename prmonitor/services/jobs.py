"""Deterministic job planning and result envelopes for host/headless runs."""
from __future__ import annotations
import hashlib, json, uuid
from dataclasses import dataclass
from ..models import canonical_json_hash

@dataclass(frozen=True)
class JobRequest:
    run_id: str
    job_id: str
    kind: str
    required: bool
    payload: dict
    request_hash: str

@dataclass(frozen=True)
class JobPlan:
    run_id: str
    mode: str
    jobs: tuple[JobRequest, ...]
    next_actions: tuple[str, ...] = ()

    @property
    def required_job_ids(self) -> tuple[str, ...]:
        return tuple(job.job_id for job in self.jobs if job.required)

def plan_jobs(run_id: str, *, mode: str, pipeline: str = "market", strategy: str = "single",
              enrichment: str = "off", expected_categories: list[str] | None = None,
              max_calls: int = 3) -> JobPlan:
    categories = expected_categories or []
    jobs = [("market_brief", True)] if pipeline == "market" else [("pr_brief", True)]
    if strategy == "split":
        jobs = [("core", True), *[(f"category:{x}", True) for x in categories]]
    if enrichment == "required":
        jobs.insert(0, ("enrichment", True))
    elif enrichment == "optional":
        jobs.insert(0, ("enrichment", False))
    if len(jobs) > max_calls:
        raise ValueError(f"planned required jobs ({len(jobs)}) exceed max_calls ({max_calls})")
    requests=[]
    for kind, required in jobs:
        payload={"pipeline":pipeline,"kind":kind,"categories":categories}
        jid=uuid.uuid5(uuid.NAMESPACE_URL, f"{run_id}:{kind}").hex[:16]
        requests.append(JobRequest(run_id,jid,kind,required,payload,canonical_json_hash(payload)))
    actions=("submit:" + ",".join(x.job_id for x in requests),) if mode == "host" else ()
    return JobPlan(run_id,mode,tuple(requests),actions)

def validate_result_envelope(envelope: dict, request: JobRequest) -> dict:
    if envelope.get("run_id") != request.run_id or envelope.get("job_id") != request.job_id:
        raise ValueError("RESULT_ID_MISMATCH")
    if envelope.get("request_hash") != request.request_hash:
        raise ValueError("REQUEST_HASH_MISMATCH")
    if not isinstance(envelope.get("result"), (dict,list)):
        raise ValueError("RESULT_SCHEMA_INVALID")
    return envelope

def ingest_result(envelope: dict, request: JobRequest, *, result_hash: str | None = None) -> dict:
    """Validate then return an immutable attempt record for RunStore persistence."""
    validate_result_envelope(envelope, request)
    return {"run_id": request.run_id, "job_id": request.job_id,
            "request_hash": request.request_hash, "result_hash": result_hash,
            "result": envelope["result"], "attempted_at": envelope.get("attempted_at")}

def resume_plan(plan: JobPlan, prior: dict[str, dict], *, invalidated: set[str] | None = None) -> JobPlan:
    """Reuse only succeeded jobs with the same request hash; retry failed/pending jobs."""
    invalidated = invalidated or set()
    jobs = tuple(job for job in plan.jobs
                 if not (job.job_id in prior and prior[job.job_id].get('state') == 'succeeded'
                         and prior[job.job_id].get('request_hash') == job.request_hash
                         and job.job_id not in invalidated))
    return JobPlan(plan.run_id, plan.mode, jobs,
                   (f"resume:{','.join(job.job_id for job in jobs)}",) if plan.mode == 'host' and jobs else ())

def build_repair_request(request: JobRequest, validation_errors: list[dict] | tuple[dict, ...]) -> JobRequest:
    """Create a bounded repair request tied to the original job and its exact errors."""
    payload = dict(request.payload)
    payload['repair_for'] = request.request_hash
    payload['validation_errors'] = list(validation_errors)
    return JobRequest(request.run_id, request.job_id, request.kind, request.required,
                      payload, canonical_json_hash(payload))
