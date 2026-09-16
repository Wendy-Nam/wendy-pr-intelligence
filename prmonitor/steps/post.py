"""시장 인텔리전스 브리핑 후처리.

합성 JSON의 출처를 연결하고 HTML을 렌더한 뒤, 품질 게이트를 통과한 결과만
발송한다. 출처 해소·렌더·자사 컨텍스트 업데이트의 세부 도구는 명시적 argv로
호출하고, 스키마·참조·카테고리·커버리지는 공통 검증 모듈이 책임진다.
"""
from __future__ import annotations

import hashlib
import subprocess
import time
from datetime import datetime

from .. import paths
from ..render import HELD_WATERMARK
from ..validation import deliverable_is_current, validate_briefing
from ..common import (
    err,
    load_json,
    log,
    ok,
    pipeline_cfg,
    require_file,
    send_html_email,
    warn,
    cleanup_retention,
)

QW_THRESHOLD = 5  # — 품질 경고 임계


def _canonical_briefing(briefing: dict) -> dict:
    """뉴스레터 briefing → canonical validator 형태.

    레거시 briefing 은 출처를 ``insight["facts"][i]["ref"]`` 로 담는다
    (resolve-refs 가 id 로 조인하는 그 필드). validation.validate_briefing 은
    ``insight["refs"]`` 를 본다 — 여기서만 얕게 변환하고 게이트 로직은
    canonical 서비스가 전담한다.
    """
    insights = briefing.get("insights") if isinstance(briefing, dict) else None
    return {
        "tldr": briefing.get("tldr") if isinstance(briefing, dict) else None,
        "insights": [
            {"observation": i.get("observation"),
             "refs": [f.get("ref") for f in (i.get("facts") or [])
                      if isinstance(f, dict) and f.get("ref")]}
            for i in (insights or []) if isinstance(i, dict)
        ],
        "category_summary": (briefing.get("category_summary") or []) if isinstance(briefing, dict) else [],
    }


def _validation_inputs(facts: dict) -> tuple[set[str], set[str]]:
    """facts → (article_ids, category_ids). 기사가 있는 카테고리만 briefing 필수.

    ``uncategorized`` 는 분류 실패 버킷이라 뉴스레터 섹션이 아니다 — 기대 집합에서 제외.
    """
    article_ids, category_ids = set(), set()
    for cat in facts.get("categories", []) or []:
        if not isinstance(cat, dict):
            continue
        cat_facts = [f for f in (cat.get("facts") or []) if isinstance(f, dict)]
        article_ids |= {f["id"] for f in cat_facts if f.get("id")}
        cid = cat.get("category_id")
        if cid and cid != "uncategorized" and cat_facts:
            category_ids.add(cid)
    return article_ids, category_ids


def _compute_counts(date_str: str) -> tuple[int, int, str]:
    """국내/해외 기사 수 + 수집 시작일 — ports the inline ``"$PY" -c``.

    Reads newsletter-facts (briefing의 all_sources 폐지 — facts가 전체 기사 원천).
    .kr TLD URL 또는 title 한글 포함 → 국내. 모든 실패는 (0, 0, date_str) 폴백
    ( ``|| echo "0 0 ${DATE}"``).
    """
    facts_path = paths.PROCESSED_DIR / f"newsletter-facts-{date_str}.json"
    try:
        d = load_json(facts_path)
        sources = [
            a
            for cat in d.get("categories", [])
            for a in cat.get("facts", [])
        ]

        def is_domestic(s: dict) -> bool:
            url = s.get("source_url", "") or ""
            title = s.get("title", "") or ""
            if ".kr/" in url or url.endswith(".kr"):
                return True
            if any("가" <= c <= "힣" for c in title):
                return True
            return False

        domestic = sum(1 for s in sources if is_domestic(s))
        foreign = len(sources) - domestic
        dates = [s.get("source_date", "") for s in sources if s.get("source_date")]
        start = min(dates) if dates else date_str
        return foreign, domestic, start
    except Exception:
        return 0, 0, date_str  # 폴백


def _quality_warning_count(date_str: str) -> int:
    """품질 경고 JSON 길이 — ports the inline ``"$PY" -c``.

    파일 없음·파싱 실패·비배열은 검증 실패다. 품질 게이트를 건너뛰고
    발송하는 것보다 보류하는 편이 안전하다.
    """
    qw_file = paths.NEWSLETTER_OUTPUT_DIR / f".quality-warnings-{date_str}.json"
    warnings = load_json(qw_file)
    if not isinstance(warnings, list):
        raise ValueError("quality warnings JSON root must be an array")
    # 문장 길이(글자수 초과) 경고는 발송을 막지 않는다 — 가독성 참고일 뿐 사실 오류가
    # 아니다. 발송 게이트는 날조·비약·금지어 등 '내용 오류'만 센다. (길이 경고는 로그엔 남음)
    blocking = [w for w in warnings
                if not (isinstance(w, str) and "자 문장 (>" in w)]
    return len(blocking)


def _deliverable_is_current(report, briefing_path, policy: dict, html_path, html_hash: str) -> bool:
    """발송 직전 신선도 게이트 — briefing 은 디스크에서 다시 읽어 비교한다.

    검증 이후 누군가 briefing 을 고쳤다면 그 원고는 검증된 적이 없다.
    """
    try:
        return deliverable_is_current(
            report, briefing=_canonical_briefing(load_json(briefing_path)), policy=policy,
            html_bytes=html_path.read_bytes(), expected_html_hash=html_hash)
    except Exception as e:  # noqa: BLE001 — 읽을 수 없으면 발송하지 않는다
        warn(f"발송 전 신선도 확인 실패 — {e}")
        return False


def _write_exec_log(
    date_str: str,
    hours: int,
    run_id: str,
    started_at: str,
    status: int,
    briefing,
    html_out,
) -> None:
    """exec-log.py 호출 — ports write_exec_log().

    PR_MONITOR_EXEC_LOGGED=1 이면 헤드리스 경로 trap이 전담 → skip.
    """
    import os

    if os.environ.get("PR_MONITOR_EXEC_LOGGED") == "1":  #
        return
    argv = [
        str(paths.venv_python()),
        str(paths.SCRIPTS_DIR / "lib" / "exec-log.py"),
        "--pipeline", "newsletter",
        "--date", date_str,
        "--run-id", run_id,
        "--started", started_at,
        "--status", str(status),
        "--hours", str(hours),
        "--output", str(briefing),
        "--output", str(html_out),
    ]
    try:
        r = subprocess.run(argv, check=False)
    except OSError:
        warn("실행 로그 기록 실패")  #
        return
    if r.returncode != 0:
        warn("실행 로그 기록 실패")  #


def run(args) -> int:
    """후처리를 실행한다. 0은 성공, 그 외 값은 실패다."""
    # ── 인자 — date/hours from dispatcher; --no-email via attr ──
    date_str = args.date
    hours = args.hours if getattr(args, "hours", None) is not None else 24  #
    no_email = bool(getattr(args, "no_email", False))  #

    # ensure_venv는 dispatcher(__main__)가 이미 수행. 출력 디렉터리 보장.
    paths.NEWSLETTER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    paths.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # ── 실행 메트릭 로깅 준비 ──
    run_id = time.strftime("%H%M%S")          #  date +%H%M%S
    started_at = datetime.now().astimezone().isoformat(timespec="seconds")  #

    # 발송 보류 사유 누적 (품질 게이트) — 비면 정상 발송
    hold_reasons: list[str] = []

    # 산출물 경로. 3-root: processed→PLUGIN_DATA, output→PROJECT_DIR.
    briefing = paths.BRIEFING_DIR / f"newsletter-briefing-{date_str}.json"
    html_out = paths.NEWSLETTER_OUTPUT_DIR / f"newsletter-report-{date_str}.html"

    status = 1  # trap EXIT는 $? 를 기록 — 성공 경로에서 0으로 설정
    try:
        log(f"=== PR Monitor 후처리 시작 ({date_str}) ===")  #

        # ── Step 8 precondition: briefing 존재 ──
        if not briefing.is_file():
            err(f"Step 8: {briefing} 없음.")  #
            err("  → Step 7 (인사이트 합성)이 완료되지 않았습니다.")  #
            err("  → @insight-synthesizer 에이전트가 briefing JSON을 먼저 생성해야 합니다.")  #
            return 1  # exit 1

        # ── Step 8-pre: resolve-refs ──
        log("Step 8-pre: 출처 ref 해석 (resolve-refs)...")  #
        resolve_rc = 0
        try:
            rr = subprocess.run(
                [str(paths.venv_python()),
                 str(paths.SCRIPTS_DIR / "newsletter" / "resolve-refs.py"),
                 date_str],
                check=False,
            )  #
            resolve_rc = rr.returncode
        except OSError as e:
            resolve_rc = 1
            warn(f"resolve-refs 실행 실패 — {e}")
        if resolve_rc == 2:  #
            warn("resolve-refs: 미해결 출처 비율 > 30% — 발송 보류 대상")  #
            hold_reasons.append(
                "출처 ref 미해결 비율 > 30% — 인라인 출처 [n] 매칭 손상 가능")  #
        elif resolve_rc != 0:  #
            warn(f"resolve-refs 실패 (rc={resolve_rc}) — 발송 보류 대상")  #
            hold_reasons.append(f"출처 ref 해석 실패 (rc={resolve_rc})")

        # ── Step 8-pre: canonical 검증 (schema/ref/category/coverage) ──
        # 게이트 규칙은 prmonitor.validation 이 단독 소유 — 여기선 입력만 맞춘다.
        policy = {"qw_threshold": QW_THRESHOLD}
        canonical, report = {}, None
        try:
            facts = load_json(paths.PROCESSED_DIR / f"newsletter-facts-{date_str}.json")
            article_ids, category_ids = _validation_inputs(facts)
            canonical = _canonical_briefing(load_json(briefing))
            report = validate_briefing(canonical, article_ids=article_ids,
                                       category_ids=category_ids, policy=policy)
        except Exception as e:  # noqa: BLE001 — 검증 불가는 통과가 아니라 보류다
            warn(f"briefing 검증 실행 실패 — {e}")
            hold_reasons.append(f"briefing 검증 실행 실패 — {e}")
        if report is not None and report.status != "PASS":
            for f in report.findings:
                warn(f"검증 실패 [{f.code}] {f.path} — {f.message}")
            hold_reasons.append(
                f"briefing 검증 HELD — {', '.join(sorted({f.code for f in report.findings}))}")

        # ── Step 8: 국내/해외 기사 수 자동 계산 ──
        log("Step 8: 국내/해외 기사 수 자동 계산...")  #
        foreign, domestic, collection_start = _compute_counts(date_str)

        # 직전 발행 마커 — PREV_RUN 은 .sh 에서도 미사용이라 읽기만.
        last_run_file = paths.NEWSLETTER_OUTPUT_DIR / ".last-newsletter-run"

        # ── Step 8: HTML 생성 ──
        log(f"Step 8: HTML 생성 (해외 {foreign}건, 국내 {domestic}건)...")  #
        facts_path = paths.PROCESSED_DIR / f"newsletter-facts-{date_str}.json"
        fmt_argv = [
            str(paths.venv_python()),
            str(paths.SKILLS_DIR / "briefing-formatter" / "format.py"),
            "--input", str(briefing),
            "--date", date_str,
            "--output", str(html_out),
            "--collection-start", collection_start,
            "--foreign", str(foreign),
            "--domestic", str(domestic),
            "--hours", str(hours),
            "--facts", str(facts_path),
        ]  #
        try:
            fmt = subprocess.run(fmt_argv, check=False)
        except OSError as e:
            err(f"Step 8: format.py 실행 실패 — {e}")
            return 1
        if fmt.returncode != 0:  # (if ! ...)
            err("Step 8: format.py 실패")  #
            return 1  # exit 1

        # 발행 시각 기록 — date "+%Y-%m-%d %H:%M"
        last_run_file.write_text(
            datetime.now().strftime("%Y-%m-%d %H:%M") + "\n", encoding="utf-8")

        require_file(html_out, f"Step 8: {html_out} 미생성")  #

        html_size = html_out.stat().st_size  #  wc -c
        ok(f"Step 8: HTML 생성 완료 ({html_size} bytes)")  #

        # ── Step 8-post: 품질 경고 게이트 ──
        qw_file = paths.NEWSLETTER_OUTPUT_DIR / f".quality-warnings-{date_str}.json"
        try:
            qw_count = _quality_warning_count(date_str)
        except Exception as e:
            warn(f"품질 경고 검증 실패 — {e}")
            hold_reasons.append(f"품질 경고 검증 파일 오류 — {qw_file}")
            qw_count = 0
        if qw_count > QW_THRESHOLD:  #
            warn(f"품질 경고 {qw_count}건 > {QW_THRESHOLD}건 — 발송 보류 대상")  #
            hold_reasons.append(
                f"품질 경고 {qw_count}건 (임계 {QW_THRESHOLD}건 초과) — {qw_file} 확인")  #

        # 보류 확정 → 산출물에 HELD 워터마크 (canonical 렌더러와 동일 표식).
        if hold_reasons:
            html_out.write_text(HELD_WATERMARK + html_out.read_text(encoding="utf-8"),
                                encoding="utf-8")
        # 발송 직전 재확인용 렌더 해시 — 이 시점 이후 바뀐 HTML 은 발송하지 않는다.
        html_hash = hashlib.sha256(html_out.read_bytes()).hexdigest()

        # ── Step 9: competitor-landscape 자동 갱신 ──
        if hold_reasons:
            log("Step 9: 검증 보류 상태 — competitor-landscape 갱신 skip")
        else:
            log("Step 9: competitor-landscape.yaml 갱신 확인...")
            try:
                subprocess.run(
                    [str(paths.venv_python()),
                     str(paths.SCRIPTS_DIR / "pipeline" / "update-landscape.py"),
                     date_str],
                    check=False,
                )
            except OSError as e:
                warn(f"update-landscape 실행 실패 (후처리는 계속) — {e}")

        # ── Step 10: 이메일 발송 ──
        source_count = foreign + domestic  #
        email_group = pipeline_cfg("newsletter", "email_group", "newsletter_briefing")  #
        subject_tpl = pipeline_cfg(
            "newsletter", "subject",
            "[뉴스레터] 로봇 산업군 동향 및 인사이트 ({date}) - 출처 {count}건")  #
        subject = subject_tpl.replace("{date}", date_str)  #
        subject = subject.replace("{count}", str(source_count))  #

        # 게이트 통과(보류 사유 없음) → 이전 실행의 stale REVIEW_NEEDED.md 제거.
        # (안 지우면 깨끗한 재실행도 옛 보류서 때문에 헛경고가 뜬다.)
        if not hold_reasons:
            (paths.OUTPUT_DIR / "REVIEW_NEEDED.md").unlink(missing_ok=True)

        send_disabled = not pipeline_cfg("newsletter", "send_email", True)  # 상시 발송 차단 토글
        if no_email or send_disabled:  #
            why = "--no-email" if no_email else "pipelines.yaml send_email: false"
            log(f"Step 10: {why} — 발송 skip")  #
        elif hold_reasons:  #  ${#HOLD_REASONS[@]} > 0
            # 품질 게이트 발동 → 발송 보류 + REVIEW_NEEDED.md
            review_file = paths.OUTPUT_DIR / "REVIEW_NEEDED.md"  #
            review_file.parent.mkdir(parents=True, exist_ok=True)
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")  #
            lines = [
                "# 발송 보류 — 사용자 확인 필요",  #
                "",
                f"- 일시: {now_str}",  #
                f"- 대상: {html_out}",  #
                "",
                "## 사유",  #
            ]
            lines += [f"- {r}" for r in hold_reasons]  #
            lines += [
                "",
                "## 확인 후 수동 발송",  #
                "```bash",  #
                f'python3 "${{CLAUDE_PLUGIN_ROOT}}/prmonitor_launch.py" post {date_str} {hours}',
                "```",  #
                "(브리핑 JSON 수정 후 재실행하면 HTML 재생성 + 게이트 재평가)",  #
            ]
            review_file.write_text("\n".join(lines) + "\n", encoding="utf-8")  #
            warn(f"Step 10: 품질 게이트 발동 — 발송 보류. {review_file} 확인.")  #
        elif report is None or not _deliverable_is_current(
                report, briefing, policy, html_out, html_hash):
            # 검증 이후 briefing/policy/HTML 이 바뀌었다 — 검증되지 않은 원고다.
            warn("Step 10: 검증 이후 산출물이 변경됨 — 발송 skip")
        else:  #
            send_html_email(email_group, subject, html_out)  #

        # ── 완료 ──
        cleanup_retention()  #
        ok("후처리 완료")  #
        log(f"  📄 {html_out}")  #

        status = 0  # 성공 — trap EXIT 가 기록할 종료 상태
        return 0
    finally:
        # trap 'write_exec_log $?' EXIT — 성공/실패 모두 기록.
        _write_exec_log(date_str, hours, run_id, started_at, status, briefing, html_out)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("date")
    ap.add_argument("hours", type=int, nargs="?", default=24)
    ap.add_argument("--no-email", dest="no_email", action="store_true")
    raise SystemExit(run(ap.parse_args()))
