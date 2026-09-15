"""`python -m prmonitor <subcommand>` — the cross-platform CLI that replaces the
bash orchestrators (run-pre/post/pr-monitor/pr-daily/newsletter.sh + common.sh).

Each subcommand delegates to a module under :mod:`prmonitor.steps`, which exposes
``run(args) -> int``. The dispatcher owns only arg parsing and venv bootstrap;
all pipeline logic lives in the step modules (faithful ports of the .sh files).

Subcommand map:
  pre <date> [--hours N]    ← run-pre.sh         (fetch→extract→classify→aggregate→preload)
  post <date> <hours>       ← run-post.sh        (resolve-refs→format→landscape→gate→email)
  self-brief <date>         ← run-pr-monitor.sh  (render→accumulate→email; 자사 PR 모니터링)
  self-brief-daily [date]   ← run-pr-daily.sh    (pre + self-brief)
  market-brief [--hours N]  ← run-newsletter.sh  (pre → claude -p synth → post; 산업 뉴스레터)
  init                      ← SessionStart scaffolding (no venv required first)

pr-clip/pr-clip-daily/pr-monitor/pr/newsletter 는 예전 이름 — alias 로 당분간 유지.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _reexec_under_venv(venv_py) -> None:
    """Re-exec the current process under the venv interpreter (idempotent no-op
    when already running there or when the venv is missing).

    The launcher starts the dispatcher under the *system* interpreter, because at
    first run the venv does not exist yet. But the dispatcher runs config-reading
    code **in-process** (``domainpack``/PyYAML, ``pipeline_cfg``, …), so when the
    system interpreter lacks a third-party dep (commonly PyYAML) those calls die
    with ``ModuleNotFoundError`` mid-pipeline (e.g. newsletter synthesis). The
    subprocess step-scripts were already safe (they use ``paths.venv_python()``);
    this makes the parent process consistent with them.
    """
    import os
    from pathlib import Path

    venv_py = Path(venv_py)
    if not venv_py.exists():
        return  # bootstrap should have created it; be defensive

    # "Am I already running inside the venv?" Compare interpreter *prefixes*, not
    # the executable path: a venv's python is typically a symlink to the very same
    # system binary, so resolving sys.executable false-matches the venv python and
    # would skip the re-exec entirely — leaving in-process code on the dep-less
    # system interpreter. sys.prefix points at the venv root only when we are
    # actually running inside it.
    venv_dir = venv_py.parent.parent  # .venv/bin/python3 → .venv (Win: .venv/Scripts → .venv)
    try:
        if Path(sys.prefix).resolve() == venv_dir.resolve():
            return  # already under the venv interpreter
    except OSError:
        pass

    # Reconstruct the invocation: the launcher runs us as ``python LAUNCHER.py
    # <args>``; ``python -m prmonitor <args>`` is the dev path.
    if sys.argv and sys.argv[0].endswith(".py") and os.path.exists(sys.argv[0]):
        new_argv = [str(venv_py), sys.argv[0], *sys.argv[1:]]
    else:
        new_argv = [str(venv_py), "-m", "prmonitor", *sys.argv[1:]]

    if os.name == "nt":  # Windows: os.execv is flaky — spawn + propagate code.
        import subprocess
        raise SystemExit(subprocess.run(new_argv).returncode)
    os.execv(str(venv_py), new_argv)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prmonitor", description="PR Monitor pipeline CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_pre = sub.add_parser("pre", help="공통 전처리 (수집→추출→분류→집계→컨텍스트)")
    p_pre.add_argument("date", nargs="?", default=None)
    p_pre.add_argument("--hours", type=int, default=None)

    p_post = sub.add_parser("post", help="뉴스레터 후처리 (렌더→게이트→발송)")
    p_post.add_argument("date", nargs="?", default=None)
    p_post.add_argument("hours", type=int, nargs="?", default=None)
    p_post.add_argument("--no-email", action="store_true")

    # aliases=[...]: 예전 이름들도 당분간 그대로 받는다 — 이미 등록된 크론/Routines 를
    # 깨지 않기 위한 마이그레이션 유예. 새로 쓸 땐 정식 이름(self-brief*/market-brief) 사용.
    p_prmon = sub.add_parser("self-brief", aliases=["pr-clip", "pr-monitor"],
                             help="자사 PR 모니터링 (톤판정→누적→발송)")
    p_prmon.add_argument("date", nargs="?", default=None)
    p_prmon.add_argument("hours", type=int, nargs="?", default=None)
    p_prmon.add_argument("--no-email", action="store_true")

    p_pr = sub.add_parser("self-brief-daily", aliases=["pr-clip-daily", "pr"],
                          help="자사 PR 일일 (pre + self-brief)")
    p_pr.add_argument("date", nargs="?", default=None)
    p_pr.add_argument("hours", type=int, nargs="?", default=None)
    p_pr.add_argument("--no-email", action="store_true")

    p_nl = sub.add_parser("market-brief", aliases=["newsletter"],
                          help="산업 뉴스레터 (pre → 합성 → post)")
    p_nl.add_argument("date", nargs="?", default=None)
    p_nl.add_argument("--hours", type=int, default=None)
    p_nl.add_argument("--no-email", action="store_true")
    p_nl.add_argument("--dry-run", action="store_true")

    p_init = sub.add_parser("init", help="첫 실행 스캐폴딩 (config/data 골격 + venv)")
    p_init.add_argument("--force", action="store_true",
                        help="마커 없는 새 워크스페이스에서 강제 실행 (/setup 첫 설치용)")
    p_init.add_argument("--strict", action="store_true", help="runtime 준비 실패 시 exit 20")
    sub.add_parser("paths", help="해석된 경로 출력 (디버그)")
    p_doctor = sub.add_parser("doctor", help="상태 DB와 artifact 무결성 진단")
    p_doctor.add_argument("--state-dir", default=None)
    p_doctor.add_argument("--strict", action="store_true", help="unhealthy checks면 exit 1")

    p_run = sub.add_parser("run", help="canonical run 생성 및 pending 작업 반환")
    p_run.add_argument("--pipeline", choices=["market", "self"], required=True)
    p_run.add_argument("--mode", choices=["host", "headless"], default="host")
    p_run.add_argument("--workspace", default=None)
    p_run.add_argument("--date", default=None)
    p_run.add_argument("--hours", type=int, default=24)
    p_run.add_argument("--schedule-key", default=None)
    p_run.add_argument("--backend", choices=["claude","codex","hermes","generic"], default=None)
    p_run.add_argument("--llm", choices=["on","off"], default="on")
    p_run.add_argument("--strategy", choices=["single","split"], default="single")
    p_run.add_argument("--enrichment", choices=["off","optional","required"], default="off")
    p_run.add_argument("--no-email", action="store_true")
    p_run.add_argument("--dry-run", action="store_true")
    p_run.add_argument("--json", action="store_true")

    p_ingest = sub.add_parser("ingest", help="pending job result envelope 수락")
    p_ingest.add_argument("--state-dir", required=True)
    p_ingest.add_argument("--run-id", required=True)
    p_ingest.add_argument("--job-id", required=True)
    p_ingest.add_argument("--result", required=True)

    p_validate = sub.add_parser("validate", help="briefing 품질 게이트 실행")
    p_validate.add_argument("--state-dir", required=True)
    p_validate.add_argument("--run-id", required=True)
    p_validate.add_argument("--briefing", required=True)
    p_validate.add_argument("--article-ids", default="")
    p_validate.add_argument("--category-ids", default="")
    p_validate.add_argument("--policy", default=None)

    p_send = sub.add_parser("send", help="검증된 산출물을 fixture transport로 기록")
    p_send.add_argument("--state-dir", required=True)
    p_send.add_argument("--run-id", required=True)
    p_send.add_argument("--briefing", required=True)
    p_send.add_argument("--html", required=True)
    p_send.add_argument("--validation", required=True)
    p_send.add_argument("--recipient", required=True)
    p_send.add_argument("--fixture-dir", required=True)
    p_send.add_argument("--provider", default=None, help="local(기본)/smtp/microsoft_graph — live 전송 배선은 T14")

    p_render = sub.add_parser("render", help="validated briefing HTML 생성")
    p_render.add_argument("--briefing", required=True)
    p_render.add_argument("--validation", required=True)
    p_render.add_argument("--output", required=True)
    p_render.add_argument("--allow-held", action="store_true")

    p_memory = sub.add_parser("memory-promote", help="READY run의 provenance event 승격")
    p_memory.add_argument("--state-dir", required=True)
    p_memory.add_argument("--run-id", required=True)
    p_memory.add_argument("--event-id", required=True)
    p_memory.add_argument("--refs-valid", action="store_true")

    p_revise = sub.add_parser("revise", help="기존 run의 계보를 유지한 새 run 생성")
    p_revise.add_argument("--state-dir", required=True); p_revise.add_argument("--run-id", required=True)
    p_gc = sub.add_parser("gc", help="등록되지 않은 artifact 점검/삭제")
    p_gc.add_argument("--state-dir", required=True); p_gc.add_argument("--run-id", default=None); p_gc.add_argument("--remove", action="store_true")
    p_jobs = sub.add_parser("jobs", help="run의 pending job request 조회")
    p_jobs.add_argument("--state-dir", required=True); p_jobs.add_argument("--run-id", required=True)
    p_repair = sub.add_parser("repair", help="validation errors 기반 pending job request 재생성")
    p_repair.add_argument("--state-dir", required=True); p_repair.add_argument("--run-id", required=True); p_repair.add_argument("--job-id", required=True); p_repair.add_argument("--errors", required=True)
    p_status = sub.add_parser("status", help="run 상태/미완료 job 조회")
    p_status.add_argument("--state-dir", required=True); p_status.add_argument("--run-id", required=True)
    p_cancel = sub.add_parser("cancel", help="진행 중인 run을 CANCELLED로 종료")
    p_cancel.add_argument("--state-dir", required=True); p_cancel.add_argument("--run-id", required=True)
    p_resume = sub.add_parser("resume", help="미완료 job 재계획 후 next action 반환")
    p_resume.add_argument("--state-dir", required=True); p_resume.add_argument("--run-id", required=True)
    p_runs = sub.add_parser("runs", help="기록된 run 목록 (최신순)")
    p_runs.add_argument("--state-dir", required=True); p_runs.add_argument("--limit", type=int, default=20)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.cmd == "doctor":
        import json
        from pathlib import Path
        from . import paths
        from .doctor import inspect_workspace
        state = Path(args.state_dir) if args.state_dir else paths.PROJECT_DIR / ".prmonitor"
        result = inspect_workspace(state)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['healthy'] or not args.strict else 1

    if args.cmd == "ingest":
        import hashlib, json
        from pathlib import Path
        from .storage.runs import RunStore
        from .services.jobs import JobRequest, ingest_result
        store = RunStore(Path(args.state_dir))
        row = store.db.execute("SELECT * FROM jobs WHERE run_id=? AND job_id=?", (args.run_id, args.job_id)).fetchone()
        if row is None:
            print(json.dumps({'error': {'code':'JOB_NOT_FOUND','message':'unknown run/job'}}, ensure_ascii=False)); return 2
        envelope = json.loads(Path(args.result).read_text(encoding='utf-8'))
        request = JobRequest(args.run_id,args.job_id,row['kind'],bool(row['required']),{},row['request_hash'])
        try:
            attempt = ingest_result(envelope, request, result_hash=hashlib.sha256(Path(args.result).read_bytes()).hexdigest())
        except (ValueError, json.JSONDecodeError) as exc:
            print(json.dumps({'error': {'code':'INGEST_REJECTED','message':str(exc)}}, ensure_ascii=False)); return 2
        store.record_attempt(run_id=args.run_id, job_id=args.job_id, request_hash=request.request_hash,
                             state='succeeded', result_hash=attempt['result_hash'], result=attempt['result'])
        store.complete_job(run_id=args.run_id, job_id=args.job_id, result_path=args.result, result_hash=attempt['result_hash'])
        print(json.dumps({'run_id':args.run_id,'job_id':args.job_id,'status':'accepted'}, ensure_ascii=False)); return 0

    if args.cmd == "validate":
        import json
        from pathlib import Path
        from .storage.runs import RunStore
        from .services.engine import Engine, PreparedRun
        from .services.jobs import JobPlan
        store = RunStore(Path(args.state_dir)); record = store.get(args.run_id)
        briefing = json.loads(Path(args.briefing).read_text(encoding='utf-8'))
        policy = json.loads(Path(args.policy).read_text(encoding='utf-8')) if args.policy else {}
        prepared = PreparedRun(record, JobPlan(record.run_id, record.spec.mode, ()))
        report = Engine(store).validate(prepared, briefing,
                                        article_ids={x for x in args.article_ids.split(',') if x},
                                        category_ids={x for x in args.category_ids.split(',') if x},
                                        policy=policy, report_path=args.briefing + '.validation.json')
        print(json.dumps(report.as_dict(), ensure_ascii=False, sort_keys=True)); return 0 if report.status == 'PASS' else 21

    if args.cmd == "send":
        import json
        from pathlib import Path
        from .models import RunState
        from .storage.runs import RunStore
        from .validation import Finding, ValidationReport
        from .delivery import send_validated
        from .delivery_providers import resolve_transport
        store = RunStore(Path(args.state_dir)); record = store.get(args.run_id)
        if record.state != RunState.READY:
            print(json.dumps({'error': {'code':'DELIVERY_STATE_REJECTED','message':record.state.value}}, ensure_ascii=False)); return 21
        briefing = json.loads(Path(args.briefing).read_text(encoding='utf-8'))
        validation = json.loads(Path(args.validation).read_text(encoding='utf-8'))
        report = ValidationReport(validation['status'], tuple(Finding(f['code'],f['severity'],f['path'],f['message'],tuple(f.get('refs',()))) for f in validation.get('findings',[])), validation['briefing_hash'], validation['policy_hash'], validation.get('required_jobs',{}), validation.get('coverage',{}))
        html = Path(args.html).read_bytes()
        policy = {}
        try:
            transport = resolve_transport(args.provider, fixture_dir=Path(args.fixture_dir))
        except ValueError as exc:
            print(json.dumps({'error': {'code':'UNKNOWN_DELIVERY_PROVIDER','message':str(exc)}}, ensure_ascii=False)); return 21
        try:
            receipt = send_validated(report=report, briefing=briefing, policy=policy, html=html,
                                     recipient=args.recipient, transport=transport,
                                     expected_html_hash=__import__('hashlib').sha256(html).hexdigest())
        except ValueError as exc:
            print(json.dumps({'error': {'code':'DELIVERY_GATE_REJECTED','message':str(exc)}}, ensure_ascii=False)); return 21
        print(json.dumps({'delivery_id':receipt.delivery_id,'status':receipt.status,'artifact_hash':receipt.artifact_hash}, ensure_ascii=False)); return 0

    if args.cmd == "render":
        import json
        from pathlib import Path
        from .validation import Finding, ValidationReport
        from .render import render_briefing
        briefing = json.loads(Path(args.briefing).read_text(encoding='utf-8')); validation = json.loads(Path(args.validation).read_text(encoding='utf-8'))
        report = ValidationReport(validation['status'], tuple(Finding(f['code'],f['severity'],f['path'],f['message'],tuple(f.get('refs',()))) for f in validation.get('findings',[])), validation['briefing_hash'], validation['policy_hash'], validation.get('required_jobs',{}), validation.get('coverage',{}))
        try:
            output = render_briefing(briefing, report, policy={}, output=Path(args.output), allow_held=args.allow_held)
        except ValueError as exc:
            print(json.dumps({'error': {'code':'RENDER_REJECTED','message':str(exc)}}, ensure_ascii=False)); return 21
        print(json.dumps({'status':'rendered','path':str(output)}, ensure_ascii=False)); return 0

    if args.cmd == "memory-promote":
        import json
        from pathlib import Path
        from .models import RunState
        from .storage.runs import RunStore
        from .memory import promote_event
        store = RunStore(Path(args.state_dir)); record = store.get(args.run_id)
        try:
            if record.state != RunState.READY:
                raise ValueError('MEMORY_PROMOTION_GATE_REJECTED')
            changed = promote_event(store.db, args.event_id, run_state=record.state.value, refs_valid=args.refs_valid)
        except ValueError as exc:
            print(json.dumps({'error': {'code':str(exc)}}, ensure_ascii=False)); return 21
        print(json.dumps({'event_id':args.event_id,'promoted':changed}, ensure_ascii=False)); return 0

    if args.cmd == "revise":
        import json
        from pathlib import Path
        from .storage.runs import RunStore
        from .services.maintenance import revise_run
        child = revise_run(RunStore(Path(args.state_dir)), args.run_id)
        print(json.dumps({'run_id':child.run_id,'parent_run_id':child.parent_run_id,'state':child.state}, ensure_ascii=False)); return 0

    if args.cmd == "gc":
        import json
        from pathlib import Path
        from .storage.runs import RunStore
        from .services.maintenance import gc_orphans
        print(json.dumps(gc_orphans(RunStore(Path(args.state_dir)), run_id=args.run_id, remove=args.remove), ensure_ascii=False)); return 0

    if args.cmd == "jobs":
        import json
        from pathlib import Path
        from .storage.runs import RunStore
        print(json.dumps({'run_id':args.run_id,'jobs':RunStore(Path(args.state_dir)).pending_jobs(args.run_id)}, ensure_ascii=False, sort_keys=True)); return 0

    if args.cmd == "repair":
        import json
        from pathlib import Path
        from .storage.runs import RunStore
        from .services.jobs import JobRequest, build_repair_request
        store=RunStore(Path(args.state_dir)); rows=store.pending_jobs(args.run_id)
        row=next((r for r in rows if r['job_id']==args.job_id), None)
        if row is None:
            print(json.dumps({'error': {'code':'JOB_NOT_REPAIRABLE'}}, ensure_ascii=False)); return 21
        errors=json.loads(Path(args.errors).read_text(encoding='utf-8'))
        req=JobRequest(args.run_id,args.job_id,row['kind'],bool(row['required']),row.get('request') or {},row['request_hash'])
        repaired=build_repair_request(req, errors if isinstance(errors,list) else [errors])
        store.replace_job_request(run_id=args.run_id, job_id=args.job_id, request_hash=repaired.request_hash, request=repaired.payload)
        print(json.dumps({'run_id':args.run_id,'job_id':args.job_id,'request_hash':repaired.request_hash}, ensure_ascii=False)); return 0

    if args.cmd == "runs":
        import json
        from pathlib import Path
        from .storage.runs import RunStore
        rows = RunStore(Path(args.state_dir)).db.execute(
            "SELECT run_id,state,revision,schedule_key,parent_run_id,created_at,updated_at FROM runs "
            "ORDER BY created_at DESC, run_id DESC LIMIT ?", (args.limit,)).fetchall()
        print(json.dumps({'runs': [dict(r) for r in rows]}, ensure_ascii=False, sort_keys=True)); return 0

    if args.cmd in {"status", "cancel", "resume"}:
        import json
        from pathlib import Path
        from .models import RunState
        from .storage.runs import RunStore
        store = RunStore(Path(args.state_dir))
        try:
            record = store.get(args.run_id)
        except KeyError:
            print(json.dumps({'error': {'code':'RUN_NOT_FOUND','message':args.run_id}}, ensure_ascii=False)); return 2
        terminal = {RunState.READY, RunState.FAILED, RunState.CANCELLED}
        if args.cmd == "status":
            print(json.dumps({'run_id':record.run_id,'state':record.state,'revision':record.revision,
                              'schedule_key':record.schedule_key,'parent_run_id':record.parent_run_id,
                              'created_at':record.created_at,'updated_at':record.updated_at,
                              'pending_jobs':[{'job_id':r['job_id'],'kind':r['kind'],'state':r['state'],
                                               'required':bool(r['required'])} for r in store.pending_jobs(args.run_id)]},
                             ensure_ascii=False, sort_keys=True)); return 0
        if record.state in terminal:
            code = 'RUN_NOT_CANCELLABLE' if args.cmd == 'cancel' else 'RUN_NOT_RESUMABLE'
            print(json.dumps({'error': {'code':code,'message':str(record.state)}}, ensure_ascii=False)); return 21
        if args.cmd == "cancel":
            updated = store.transition(record.run_id, record.revision, {record.state}, RunState.CANCELLED)
            print(json.dumps({'run_id':updated.run_id,'state':updated.state,'revision':updated.revision},
                             ensure_ascii=False, sort_keys=True)); return 0
        from .services.engine import Engine
        plan = Engine(store).resume(args.run_id).plan
        print(json.dumps({'run_id':record.run_id,'state':record.state,'revision':record.revision,
                          'jobs':[{'job_id':j.job_id,'kind':j.kind,'required':j.required,'request_hash':j.request_hash} for j in plan.jobs],
                          'next_actions':list(plan.next_actions) or (['execute'] if plan.jobs else ['validate'])},
                         ensure_ascii=False, sort_keys=True)); return 0

    if args.cmd == "run":
        import json
        from datetime import timedelta, timezone
        from pathlib import Path
        from .paths import resolve_paths
        from .models import RunSpec
        from .storage.runs import RunStore
        from .services.engine import Engine
        workspace = Path(args.workspace).expanduser().resolve() if args.workspace else Path.cwd().resolve()
        if args.hours < 1 or args.hours > 720:
            print(json.dumps({'error': {'code':'INVALID_HOURS','message':'hours must be 1..720'}}, ensure_ascii=False)); return 2
        ctx = resolve_paths(env={}, cwd=workspace, bundle=Path(__file__).resolve().parents[1])
        end = datetime.now(timezone.utc); start = end - timedelta(hours=args.hours)
        report_date = args.date or end.astimezone().date().isoformat()
        if args.mode == 'host' and args.backend:
            print(json.dumps({'error': {'code':'HOST_BACKEND_FORBIDDEN','message':'host mode uses current host LLM'}}, ensure_ascii=False)); return 2
        spec = RunSpec(args.pipeline,args.mode,ctx.workspace_id,report_date,'UTC',start.isoformat(),end.isoformat(),args.hours,
                       llm_enabled=(args.llm == 'on'), backend=args.backend,
                       synthesis_strategy=args.strategy, enrichment=args.enrichment,
                       delivery_requested=not args.no_email, schedule_key=args.schedule_key)
        spec_errors = spec.validation_errors()
        if spec_errors:
            print(json.dumps({'error': {'code':'RUNSPEC_INVALID','details':spec_errors}}, ensure_ascii=False)); return 2
        if args.dry_run:
            payload = {'dry_run': True, 'spec': spec.as_dict(), 'workspace_id': ctx.workspace_id}
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True)); return 0
        prepared = Engine(RunStore(ctx.state_dir)).prepare(spec)
        record, plan = prepared.record, prepared.plan
        payload = {'run_id':record.run_id,'state':record.state,'revision':record.revision,'spec':spec.as_dict(),
                   'jobs':[{'job_id':j.job_id,'kind':j.kind,'required':j.required,'request_hash':j.request_hash} for j in plan.jobs],
                   'next_actions':['prepare','validate'] if args.mode == 'host' else ['execute']}
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True)); return 0

    _date_cmds = {"pre", "post", "self-brief", "pr-clip", "pr-monitor",
                 "self-brief-daily", "pr-clip-daily", "pr", "market-brief", "newsletter"}
    if args.cmd in _date_cmds:
        # legacy 모호성: date/hours 가 둘 다 positional 이라 `pre 24` 가 조용히 date="24"
        # 로 해석됐다. 정식형(YYYY-MM-DD)만 받고, 나머지는 명확한 오류로 거절한다.
        if args.date is None:
            args.date = _today()
        elif not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date):
            print(f"[prmonitor] '{args.date}' 는 날짜(YYYY-MM-DD)가 아닙니다 — "
                  f"시간 범위는 --hours 로 지정하세요.", file=sys.stderr)
            return 2

    if args.cmd == "paths":
        from . import paths
        print(paths.as_exports())
        return 0

    if args.cmd == "init":
        from .steps import init
        return init.run(args)

    # Pipeline subcommands need the venv (deps). Bootstrap is idempotent.
    from . import bootstrap, paths
    try:
        bootstrap.ensure_venv(quiet=False)
    except bootstrap.BootstrapError as e:
        print(f"[bootstrap] {e}", file=sys.stderr)
        return 1

    # Now that the venv is guaranteed, re-exec under it so in-process config reads
    # (domainpack/PyYAML, pipeline_cfg) have the deps. Only for real CLI runs;
    # programmatic/test calls pass argv explicitly and are left untouched.
    if argv is None:
        _reexec_under_venv(paths.venv_python())

    from .steps import pre, post, self_brief, self_brief_daily, market_brief
    dispatch = {
        "pre": pre.run, "post": post.run,
        "self-brief": self_brief.run, "pr-clip": self_brief.run, "pr-monitor": self_brief.run,
        "self-brief-daily": self_brief_daily.run, "pr-clip-daily": self_brief_daily.run,
        "pr": self_brief_daily.run,
        "market-brief": market_brief.run, "newsletter": market_brief.run,
    }
    _canonical = {
        "pr-clip": "self-brief", "pr-monitor": "self-brief",
        "pr-clip-daily": "self-brief-daily", "pr": "self-brief-daily",
        "newsletter": "market-brief",
    }
    if args.cmd in _canonical:
        print(f"[prmonitor] '{args.cmd}' 는 예전 이름입니다 — {_canonical[args.cmd]} 로 갱신하세요.",
              file=sys.stderr)
    return dispatch[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
