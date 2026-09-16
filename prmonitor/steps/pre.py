"""시장·PR 브리핑이 함께 쓰는 결정론적 전처리 단계.

URL 수집·본문 추출·분류·카테고리 집계·합성용 컨텍스트 생성을 순서대로 실행한다.
LLM은 호출하지 않는다. 각 세부 처리는 ``scripts/pipeline/``의 독립 Python 도구를
venv 인터프리터와 명시적 인자로 호출하며, 실패하면 다음 단계로 진행하지 않는다.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime

from .. import paths
from ..common import count_urls, err, log, ok, require_file, resolve_hours


# Default collection window when --hours is unset ( → HOURS=48).
# Sourced from the newsletter pipeline policy to honour the architecture contract;
# falls back to 48 to match the bash literal default exactly.
_DEFAULT_HOURS = 48


def _py() -> str:
    """세부 Python 도구를 실행할 venv 인터프리터 경로를 반환한다."""
    return str(paths.venv_python())


def _scripts_dir():
    return paths.SCRIPTS_DIR / "pipeline"


def _run_step(argv: list[str], fail_msg: str) -> bool:
    """Run a pipeline step-script subprocess. True on success, False on failure.

    출력은 캡처하지 않고 현재 콘솔로 전달한다. 종료 코드가 0이 아니면 파이프라인을
    중단한다. 셸을 거치지 않고 명시적 argv 목록만 사용한다.
    """
    try:
        r = subprocess.run(argv, check=False)
    except OSError as e:
        err(f"{fail_msg} ({e})")
        return False
    if r.returncode != 0:
        err(fail_msg)
        return False
    return True


def run(args) -> int:
    # ── 인자 파싱 ──────────────────────────────────────────
    # Dispatcher (__main__.py) already split out `date` (defaulted to today when
    # omitted) and `--hours` (None when unset). `date_given` distinguishes an
    # explicit date from the today-default, needed for the Monday bump below.
    date = args.date
    date_given = getattr(args, "_date_given", None)
    if date_given is None:
        # __main__ defaults args.date to today when omitted; we can't see the
        # original here, so treat "date == today" as the no-date case to match
        # (`if [ -z "$DATE" ]`). This reproduces the bash branch:
        # an explicit today date and an omitted date behave identically anyway,
        # since both resolve DATE to today and both are eligible for the bump.
        date_given = date != datetime.now().strftime("%Y-%m-%d")

    # HOURS default = 48. When --hours unset, take the newsletter
    # policy default (architecture contract) but keep the bash literal as fallback.
    if getattr(args, "hours", None) is not None:
        hours = int(args.hours)
    else:
        try:
            hours = int(resolve_hours("newsletter"))
        except Exception:
            hours = _DEFAULT_HOURS
        if hours <= 0:
            hours = _DEFAULT_HOURS

    # 월요일이면 기본 96h... 실제 72h.
    # Only when no date was given AND hours is still the default 48.
    if not date_given:
        if datetime.now().weekday() == 0 and hours == 48:  # weekday()==0 → Monday (== `date +%u`==1)
            hours = 72
            log("월요일 감지 — 수집 범위 72시간으로 자동 설정 (pipelines.yaml 정책)")

    # mkdir -p data/raw data/processed data/output logs/executions.
    # Three-root aware: ensure the writable dir skeleton exists.
    paths.ensure_dirs()

    log(f"=== PR Monitor 전처리 시작 ({date}, {hours}h) ===")

    # ── Step 0: venv 세팅 ──────────────────────────────────
    # Already handled by the dispatcher (bootstrap.ensure_venv) before run().

    py = _py()
    sdir = _scripts_dir()

    # ── Step 1: URL 수집 ──────────────────────────────────
    urls_file = paths.RAW_DIR / f"urls-{date}.json"
    hours_marker = paths.RAW_DIR / f"urls-{date}.hours"

    # 같은 날 다른 수집창 처리:
    #   기존 창 >= 요청 창 → superset 재사용
    #   기존 창 <  요청 창 → 재수집 + 하위 산출물 무효화
    prev_hours = 0
    if urls_file.is_file():
        # PREV_HOURS=$(cat "$HOURS_MARKER" 2>/dev/null || echo 0)
        try:
            prev_hours = int(hours_marker.read_text(encoding="utf-8").strip() or 0)
        except (OSError, ValueError):
            prev_hours = 0
        if prev_hours < hours:  #
            log(f"Step 1: 기존 수집창 {prev_hours}h < 요청 {hours}h — 재수집 (하위 산출물 무효화)")
            # rm -f urls + marker + extracted + classified + facts
            for stale in (
                urls_file,
                hours_marker,
                paths.PROCESSED_DIR / f"extracted-{date}.json",
                paths.PROCESSED_DIR / f"classified-{date}.json",
                paths.PROCESSED_DIR / f"newsletter-facts-{date}.json",
                paths.PROCESSED_DIR / f"synthesis-context-{date}.json",
                paths.PROCESSED_DIR / f"enriched-{date}.json",
            ):
                stale.unlink(missing_ok=True)

    if urls_file.is_file():  #
        url_count = count_urls(urls_file)  #
        log(f"Step 1: URL 수집 skip (기존 파일 재사용, {url_count}건, 수집창 {prev_hours}h ≥ {hours}h)")
        if url_count == 0:  #
            err("기존 URL 파일에 수집된 기사가 0건입니다. 파이프라인을 중단합니다.")
            return 1
    else:
        log(f"Step 1: URL 수집 시작 ({hours}h)...")  #
        # 주간 실행(HOURS > 24) → --hours-override
        override_args: list[str] = []
        if hours > 24:
            override_args = ["--hours-override"]
            log("Step 1: 주간 모드 감지 — --hours-override 적용 (쿼리별 time_window 무시)")
        # "$PY" scripts/pipeline/fetch-urls.py --date "$DATE" --hours "$HOURS" $OVERRIDE_FLAG
        argv = [py, str(sdir / "fetch-urls.py"),
                "--date", date, "--hours", str(hours), *override_args]
        if not _run_step(argv, "Step 1: fetch-urls.py 실패"):  #
            return 1

        # require_file urls-{date}.json — exits(1) on miss.
        require_file(urls_file, f"Step 1: urls-{date}.json 미생성. fetch-urls.py 로그 확인.")

        url_count = count_urls(urls_file)  #
        if url_count == 0:  #
            err("Step 1: 수집된 기사 0건. 네트워크 연결 또는 RSS 피드 설정 확인.")
            err("  → config/sources.yaml 에서 RSS 주소 확인")
            err("  → 인터넷 연결 확인")
            return 1
        # echo "$HOURS" > "$HOURS_MARKER"
        hours_marker.write_text(f"{hours}\n", encoding="utf-8")
        ok(f"Step 1: URL 수집 완료 ({url_count}건, 수집창 {hours}h)")

    # ── Step 2: 원문 추출 ─────────────────────────────────
    extracted = paths.PROCESSED_DIR / f"extracted-{date}.json"

    if extracted.is_file():  #
        # ART_COUNT = json['success'] of extracted file
        art_count: object = "?"
        try:
            from ..common import load_json
            art_count = load_json(extracted).get("success", 0)
        except Exception:
            art_count = "?"
        log(f"Step 2: 원문 추출 skip (기존 파일, {art_count}건 성공)")
    else:
        log("Step 2: 원문 추출 시작...")  #
        # "$PY" scripts/pipeline/batch-extract.py "$DATE"
        if not _run_step([py, str(sdir / "batch-extract.py"), date],
                         "Step 2: batch-extract.py 실패"):  #
            return 1
        require_file(extracted, f"Step 2: extracted-{date}.json 미생성")  #
        ok("Step 2: 원문 추출 완료")

    # ── Step 3: 분류 ────────────────────────────────────
    classified = paths.PROCESSED_DIR / f"classified-{date}.json"

    if classified.is_file():  #
        log("Step 3: 분류 skip (기존 파일)")
    else:
        log("Step 3: 기사 분류 시작...")  #
        # "$PY" scripts/pipeline/classify.py "$DATE"
        if not _run_step([py, str(sdir / "classify.py"), date],
                         "Step 3: classify.py 실패"):  #
            return 1
        require_file(classified, f"Step 3: classified-{date}.json 미생성")  #
        ok("Step 3: 분류 완료")

    # ── Step 6: 집계 ────────────────────────────────────
    # (Step 4·5 결번 — LLM 팩트추출·인용검증 → 결정론적 집계로 통합)
    all_facts = paths.PROCESSED_DIR / f"newsletter-facts-{date}.json"

    # ── Step 5b: 기사 보강 (Haiku importance + 한국어 1줄요약) ────────────────
    # aggregate 직전, facts 가 아직 없을 때만. 비치명적 — 실패해도 aggregate 가
    # 키워드 점수로 폴백한다. 키워드론 묘기 vs 실속 구분이 안 돼 tier 가 뒤집히는
    # 문제를 Haiku 편집 중요도로 잡는다.
    if not all_facts.is_file():
        log("Step 5b: 기사 보강 시작 (Haiku importance + 한국어 요약)...")
        _run_step([py, str(sdir / "enrich-articles.py"), date],
                  "Step 5b: enrich-articles.py 경고")  # 실패해도 계속

    if all_facts.is_file():  #
        log("Step 6: 집계 skip (기존 파일)")
    else:
        log("Step 6: 카테고리별 집계 시작...")  #
        # "$PY" scripts/pipeline/aggregate.py "$DATE" --hours "$HOURS"
        if not _run_step([py, str(sdir / "aggregate.py"), date, "--hours", str(hours)],
                         "Step 6: aggregate.py 실패"):  #
            return 1
        require_file(all_facts, f"Step 6: newsletter-facts-{date}.json 미생성")  #
        ok("Step 6: 집계 완료")

    # ── Step 7: 압축 컨텍스트 생성 ───────────────────────
    synthesis_ctx = paths.PROCESSED_DIR / f"synthesis-context-{date}.json"

    if synthesis_ctx.is_file():  #
        log("Step 7: 압축 컨텍스트 skip (기존 파일)")
    else:
        log("Step 7: insight-synthesizer용 압축 컨텍스트 생성...")  #
        # "$PY" scripts/pipeline/preload-synthesis-context.py "$DATE"
        if not _run_step([py, str(sdir / "preload-synthesis-context.py"), date],
                         "Step 7: preload-synthesis-context.py 실패"):  #
            return 1
        require_file(synthesis_ctx, f"Step 7: synthesis-context-{date}.json 미생성")  #
        ok("Step 7: 압축 컨텍스트 완료")

    # ── 완료 ─────────────────────────────────────────────
    # FACT_COUNT = json['total_facts'] of newsletter-facts
    fact_count: object = "?"
    try:
        from ..common import load_json
        fact_count = load_json(all_facts).get("total_facts", "?")
    except Exception:
        fact_count = "?"

    print("", file=sys.stderr)
    ok(f"전처리 완료: {all_facts} (팩트 약 {fact_count}건)")
    print("", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(run(None))
