"""자사 PR 일일 브리핑의 정식 실행 경로 (CLI: ``self-brief-daily``).

수집 시간창은 ``pipelines.yaml`` 정책 또는 명시한 ``--hours``에서 정하고,
같은 시간창으로 전처리와 자사 PR 브리핑을 연속 실행한다. 앞 단계가 실패하면
다음 단계는 실행하지 않는다.
"""
from __future__ import annotations

from argparse import Namespace

from ..common import log, resolve_hours


def run(args) -> int:
    # Lazy sibling import (mirrors __main__.main which imports steps inside the
    # function) so importing this module never hard-depends on pre/self_brief.
    from . import pre, self_brief

    date = args.date
    # 시간창: 인자로 명시되면 그것을, 없으면 정책(평일 hours·월요일 monday_hours).
    # 매일 안 돌리는 사용자가 수집창을 직접 넓힐 수 있게 override 를 받는다.
    hours = getattr(args, "hours", None)
    if hours is None:
        hours = resolve_hours("pr_monitoring")
    hours = int(hours)

    log(f"=== PR 모니터링 일괄 실행 ({date}, {hours}h) ===")

    # 전처리와 자사 PR 브리핑이 같은 날짜·수집창을 사용한다.
    no_email = bool(getattr(args, "no_email", False))
    rc = pre.run(Namespace(date=date, hours=hours, no_email=no_email))
    if rc != 0:  # set -euo pipefail → 첫 실패에서 중단
        return rc

    # 같은 hours 를 self_brief 에도 넘긴다(override 일관성). 인자 없으면 self_brief 이
    # 동일 정책으로 재해석하므로 결과는 같다.
    return self_brief.run(Namespace(date=date, hours=hours, no_email=no_email))


if __name__ == "__main__":
    raise SystemExit(run(Namespace(date=None)))
