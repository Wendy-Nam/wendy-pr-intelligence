"""Host-neutral run engine facade.

Adapters call this facade; it owns run/job persistence and never imports a host SDK.
"""
from __future__ import annotations
from dataclasses import dataclass
from ..models import RunSpec, RunRecord, RunState, canonical_json_hash
from ..storage.runs import RunStore
from .jobs import JobPlan, JobRequest, plan_jobs, validate_result_envelope, ingest_result
from .runs import prepare_run
from ..validation import validate_briefing, ValidationReport

def open_legacy_run(pipeline: str, *, date: str, hours: int, delivery_requested: bool = True):
    """Open a canonical run for a legacy step entry point (market/self wrappers).

    The legacy steps own their file artifacts; the engine owns run/job/attempt
    state so both entry points share one ledger instead of a parallel one.
    Returns ``(engine, prepared)`` or ``None`` when no state dir is usable — a
    ledger problem must never fail a pipeline that otherwise succeeded.
    """
    from datetime import datetime, timedelta, timezone
    from pathlib import Path
    from ..paths import resolve_paths
    try:
        ctx = resolve_paths(bundle=Path(__file__).resolve().parents[2])
        end = datetime.now(timezone.utc)
        spec = RunSpec(pipeline, 'host', ctx.workspace_id, date, 'UTC',
                       (end - timedelta(hours=hours)).isoformat(), end.isoformat(), hours,
                       delivery_requested=delivery_requested)
        engine = Engine(RunStore(ctx.state_dir))
        return engine, engine.prepare(spec)
    except Exception:  # noqa: BLE001 — ponytail: ledger is observability, not the pipeline
        return None


def close_legacy_run(opened, *, succeeded: bool, result: dict) -> None:
    """Ingest the legacy step outcome through the canonical result envelope."""
    if not opened:
        return
    engine, prepared = opened
    for request in prepared.plan.jobs:
        try:
            if succeeded:
                engine.accept_result(request, {'run_id': request.run_id, 'job_id': request.job_id,
                                               'request_hash': request.request_hash, 'result': result},
                                     result_hash=canonical_json_hash(result))
            else:
                engine.reject_result(request, result)
        except Exception:  # noqa: BLE001 — ponytail: same reason as open_legacy_run
            return


@dataclass(frozen=True)
class PreparedRun:
    record: RunRecord
    plan: JobPlan

class Engine:
    def __init__(self, store: RunStore):
        self.store = store

    def prepare(self, spec: RunSpec, *, categories: list[str] | None = None) -> PreparedRun:
        config_hash = canonical_json_hash({'workspace_id': spec.workspace_id, 'pipeline': spec.pipeline})
        record = self.store.create(spec, config_hash)
        plan = plan_jobs(record.run_id, mode=spec.mode, pipeline=spec.pipeline,
                         strategy=spec.synthesis_strategy, enrichment=spec.enrichment,
                         expected_categories=categories,
                         max_calls=spec.budget.max_calls)
        return PreparedRun(prepare_run(self.store, record, plan), plan)

    def resume(self, run_id: str) -> PreparedRun:
        """Rebuild the outstanding plan for an existing run from persisted rows.

        Survives a process restart: the request payload/hash come from the jobs
        table, so a resumed job is byte-identical to the planned one.
        """
        record = self.store.get(run_id)
        jobs = tuple(JobRequest(run_id, row['job_id'], row['kind'], bool(row['required']),
                                row.get('request') or {}, row['request_hash'])
                     for row in self.store.pending_jobs(run_id))
        actions = (f"resume:{','.join(job.job_id for job in jobs)}",) if record.spec.mode == 'host' and jobs else ()
        return PreparedRun(record, JobPlan(run_id, record.spec.mode, jobs, actions))

    def accept_result(self, request, envelope: dict, *, result_hash: str | None = None,
                      result_path: str = '') -> dict:
        attempt = ingest_result(envelope, request, result_hash=result_hash)
        if not self.store.accept_job_result(
            run_id=request.run_id, job_id=request.job_id,
            request_hash=request.request_hash, result_hash=result_hash or '',
            result=attempt['result'], result_path=result_path,
        ):
            raise ValueError('JOB_NOT_ACCEPTING_RESULTS')
        return attempt

    def reject_result(self, request, error: dict) -> None:
        """Persist a failed attempt without changing another run/job."""
        self.store.record_attempt(run_id=request.run_id, job_id=request.job_id,
                                  request_hash=request.request_hash, state='failed', error=error)
        self.store.fail_job(run_id=request.run_id, job_id=request.job_id, error=error)

    def validate(self, prepared: PreparedRun, briefing: dict, *, article_ids: set[str],
                 category_ids: set[str], policy: dict | None = None,
                 report_path: str = '') -> ValidationReport:
        report = validate_briefing(briefing, article_ids=article_ids,
                                   category_ids=category_ids, policy=policy)
        pending_required = self.store.db.execute(
            "SELECT job_id FROM jobs WHERE run_id=? AND required=1 AND state!='succeeded' ORDER BY job_id",
            (prepared.record.run_id,)).fetchall()
        if pending_required:
            from ..validation import Finding
            job_ids = tuple(row['job_id'] for row in pending_required)
            report = ValidationReport(
                'HELD', report.findings + (Finding(
                    'REQUIRED_JOBS_PENDING', 'error', '/jobs',
                    'required jobs are not complete: ' + ', '.join(job_ids), job_ids,
                ),), report.briefing_hash, report.policy_hash,
                report.required_jobs, report.coverage,
            )
        row = self.store.db.execute(
            "INSERT OR REPLACE INTO validations(run_id,revision,briefing_hash,policy_hash,status,report_path) VALUES(?,?,?,?,?,?)",
            (prepared.record.run_id, prepared.record.revision, report.briefing_hash,
             report.policy_hash, report.status, report_path))
        self.store.db.commit()
        if report_path:
            from pathlib import Path
            target = Path(report_path); target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_name(target.name + '.tmp')
            import json
            tmp.write_text(json.dumps(report.as_dict(), ensure_ascii=False, sort_keys=True, indent=2), encoding='utf-8')
            tmp.replace(target)
        expected = {RunState.PREPARED, RunState.AWAITING_LLM, RunState.GENERATING,
                    RunState.VALIDATING, RunState.HELD}
        current = self.store.get(prepared.record.run_id)
        if current.state in expected:
            target = RunState.READY if report.status == 'PASS' else RunState.HELD
            self.store.transition(current.run_id, current.revision, {current.state}, target)
        return report
