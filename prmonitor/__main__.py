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

    # aliases=[...]: 예전 이름들도 당분간 그대로 받는다 — 이미 등록된 크론/Routines 를
    # 깨지 않기 위한 마이그레이션 유예. 새로 쓸 땐 정식 이름(self-brief*/market-brief) 사용.
    p_prmon = sub.add_parser("self-brief", aliases=["pr-clip", "pr-monitor"],
                             help="자사 PR 모니터링 (톤판정→누적→발송)")
    p_prmon.add_argument("date", nargs="?", default=None)
    p_prmon.add_argument("hours", type=int, nargs="?", default=None)

    p_pr = sub.add_parser("self-brief-daily", aliases=["pr-clip-daily", "pr"],
                          help="자사 PR 일일 (pre + self-brief)")
    p_pr.add_argument("date", nargs="?", default=None)
    p_pr.add_argument("hours", type=int, nargs="?", default=None)

    p_nl = sub.add_parser("market-brief", aliases=["newsletter"],
                          help="산업 뉴스레터 (pre → 합성 → post)")
    p_nl.add_argument("date", nargs="?", default=None)
    p_nl.add_argument("--hours", type=int, default=None)

    p_init = sub.add_parser("init", help="첫 실행 스캐폴딩 (config/data 골격 + venv)")
    p_init.add_argument("--force", action="store_true",
                        help="마커 없는 새 워크스페이스에서 강제 실행 (/setup 첫 설치용)")
    sub.add_parser("paths", help="해석된 경로 출력 (디버그)")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    _date_cmds = {"pre", "post", "self-brief", "pr-clip", "pr-monitor",
                 "self-brief-daily", "pr-clip-daily", "pr", "market-brief", "newsletter"}
    if getattr(args, "date", None) is None and args.cmd in _date_cmds:
        args.date = _today()

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
