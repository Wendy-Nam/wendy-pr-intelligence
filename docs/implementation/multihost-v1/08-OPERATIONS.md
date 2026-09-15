# 08. 운영·복구·성능 목표와 알고리즘 참고

여기 적힌 수치는 **목표/초기 정책값**이며 현재 성능 측정값이 아니다. 릴리스 전에 T14 측정 결과를 기록하고 근거 없이 성능 달성을 주장하지 않는다.

## 1. 경량성 목표

| 항목 | 초기 목표 | 측정 |
|---|---|---|
| 설치 package | 압축 전 public bundle 10MB 이하(venv 제외) | packaging manifest bytes |
| doctor warm 실행 | 로컬 정상 환경 2초 이내, p95 | 20회 wall-clock |
| import | network/pip/mkdir 0 | monkeypatch + subprocess |
| host-mode engine LLM calls | 0 | backend invocation log |
| small market headless | synthesis 1회 기본 | JobStore counter |
| small self headless | pr_brief 1회 기본 | JobStore counter |
| 수집 동시성 | 기본 4, 설정 1..8 | 실제 동시 request count |
| 합성 동시성 | 기본 1, split opt-in 1..4 | 실제 child process count |
| 정상 cold/warm cache | 동일 exact input의 warm은 producer 재호출0 | fixture counter |
| timeout | deadline 후 5초 안에 child 정리 목표 | 실제 process tree test |
| 데이터 격리 | workspace 간 artifact collision0 | 2 workspace concurrency test |
| 재시도 | max_calls/deadline 상한 초과0 | fake clock+counter |

120KB 입력 limit은 token limit을 정확히 뜻하지 않는다. 한국어/영어/JSON 구조별 차이가 있으므로 byte limit은 메모리·전송 보호이며 모델 context budget 보장은 아니다. backend가 token estimate를 제공하면 별도 표시하되 알 수 없으면 null. 큰 input은 임의 절삭해서 기사 누락을 숨기지 않고 INPUT_TOO_LARGE와 split/기간 축소 선택지를 반환한다.

수집 속도 목표는 외부 사이트 응답에 좌우되므로 단일 총시간 SLA로 약속하지 않는다. step timings와 source error rate를 기록한다.

## 2. RunService 의사코드

```python
def run(options):
    if options.dry_run:
        return plan_only(options)  # DB/파일/네트워크 쓰기 없음
    spec = resolve_run_spec(options)
    ctx = validate_config_and_paths(spec)
    if spec.mode == 'headless' and spec.llm_enabled:
        require_backend_probe(ctx)  # 큰 수집 작업 전 확인
    run = store.create_or_get_schedule_slot(spec)
    with lease(run.id):
        collect_if_pending(ctx)
        if all_sources_failed(ctx):
            return fail('COLLECTION_FAILED')
        if genuine_no_data(ctx):
            return no_data()
        prepare_next_phase(ctx)
        if pending_jobs(ctx):
            if spec.mode == 'host':
                return awaiting_llm()
            execute_pending_with_budget(ctx)
        if enrichment_completed_but_context_not_built(ctx):
            prepare_next_phase(ctx)
            # host면 두 번째 request 반환, headless면 실행
            return continue_current_run(ctx)
        validate_current_revision(ctx)
        if validation_error(ctx):
            return fail('VALIDATION_ERROR')
        if held(ctx):
            return maybe_repair_once_or_hold(ctx)
        render_current_revision(ctx)
        mark_ready(ctx)
    # lease/transaction 경계는 각 service가 짧게 제어
    if spec.delivery_requested:
        delivery.send_verified(run.id)
    return status(run.id)
```

`continue_current_run`은 재귀를 깊게 만드는 실제 구현을 권장하지 않는다. phase loop로 구현하고 각 phase가 상태를 진전시켰는지 확인하여 무한 반복 방지. `run`, `resume`, `prepare`가 같은 service primitive를 사용한다. 각각 별도 pipeline 코드를 복사하지 않는다.

## 3. LLM 결과 수신 알고리즘

```text
read at most max_output_bytes + 1
→ 초과면 reject
→ UTF-8 strict decode
→ JSON parse (no arbitrary extraction)
→ envelope schema validation
→ pending job lookup, run/job/hash match
→ payload schema validation
→ semantic ref/category/coverage validation
→ immutable attempt artifact save
→ transaction jobs.state=succeeded + result_hash
→ downstream validation/render active revision invalidate
```

실패 응답도 진단용 크기 제한 raw artifact로 저장할 수 있다. invalid payload를 next synthesis context에 정상 결과로 넣지 않는다. 레거시 Markdown code fence 허용은 profile별 정확히 한 fence로 한정하고 diagnostics에 normalized=true를 기록한다.

retry attempts numbering은 1부터, optional skip은 attempts를 증가시키지 않는다. backend launch 실패도 비용은 0일 수 있지만 max_calls 예약 카운터는 시도한 호출로 집계한다. 프로세스 생성 전에 budget reserve하여 concurrent jobs가 상한을 넘지 않게 한다.

## 4. Delivery reservation 알고리즘

```text
BEGIN IMMEDIATE
  require active artifact & validation hashes
  inspect deliveries by dedupe_key
  accepted -> return existing receipt
  sending/unknown -> return conflict/manual-resolution
  absent or retryable failed -> reserve status=sending
COMMIT
transport.send(...)
BEGIN IMMEDIATE
  persist accepted/failed/unknown + receipt
COMMIT
```

`retryable failed`의 재시도는 자동 run resume에서 하지 않는다. 명시 send 재시도 또는 승인된 scheduler retry policy가 필요하다. transport가 요청 body 일부를 보낸 이후 발생한 통신 오류는 보수적으로 unknown. provider의 정확한 no-delivery 증거가 있으면 failed로 분류 가능하다.

operator resolve --outcome not-sent는 기존 row에 resolution 기록을 남기고 failed/retryable로 바꾸지만 즉시 네트워크를 호출하지 않는다. 다음 명시 send가 attempt 증가 후 수행한다. accepted resolution은 receipt에 operator-resolved=true.

## 5. 장애별 운영 절차

| 증상 | 먼저 볼 것 | 조치 | 금지 |
|---|---|---|---|
| CLI 옵션 거부 | doctor backend.version/help | 검증된 profile 선택/업데이트 | sandbox bypass 추가 |
| Hermes launcher broken | executable+interpreter path | 환경 복구 후 probe; core 작업 계속 | 전역 venv 무조건 삭제 |
| 기사가 0건 | collection source statuses | 정상 0건인지 전부 실패인지 구분 | 빈 결과 자동 정상 발송 |
| 오래된 원고 | spec.window/input_hash | 새 cutoff run 생성 | 날짜 파일 수동 덮어쓰기 |
| LLM 일부 실패 | jobs required/attempts | failed job만 retry | 실패 job을 optional로 변경 |
| JSON malformed | attempt raw/error path | bounded repair | 첫/마지막 brace로 임의 절취 |
| quality HELD | findings code/path/refs | 원고 수정 후 검증 | warning file 지우고 전송 |
| sender timeout | delivery state/receipt | unknown 확인, 수락 여부 수동 조사 | 자동 전체 group 재전송 |
| memory 내용 잘못됨 | event_id/source refs | revoke 후보 + view rebuild | curated baseline 덮어쓰기 |
| workspace 이동 | workspace metadata/DB | migrate 경로+cache namespace 재생성 | 다른 workspace cache 합치기 |
| deps update 실패 | runtime manifest/error | 이전 정상 env 유지+원인 해결 | failed env를 healthy로 표시 |
| projection 누락 | state.sqlite3 | repair-projections | manifest만 보고 DB 이력 추정 |

## 6. 보존 정책과 삭제

- gc 기본은 preview. `--apply`만 삭제한다.
- active lease가 있는 run/attempt는 삭제 금지.
- READY artifact의 provenance 입력은 audit_days까지 유지. output 삭제 시 DB artifact.deleted_at(추가 column)을 기록하여 링크 상태를 구분.
- delivery ledger는 기본 보존. HTML/recipient 원문을 영구 보존해야 한다는 뜻은 아니다. hash/status/시각을 남긴다.
- monthly view를 만들었다는 이유로 원본 PR records를 바로 삭제하지 않는다. retention 정책과 backup 여부에 따른다.
- cache는 삭제 가능하나 runstore/receipts/self-context는 “캐시 정리” 대상이 아니다.
- symlink를 따라 allowed root 밖을 지우지 않는다. preview와 apply 사이 파일 변경 시 recheck한다.

## 7. 설정 이전 상세

마이그레이션 보고 필드:

```text
migration_version, workspace, detected_layout, files_to_create,
files_to_update, files_preserved, backup_dir,
warnings, requires_decision, before_hashes, after_hashes
```

기존 config/company-profile.yaml 등의 값은 원형 보존. runtime.yaml 신규 defaults만 추가. default example company가 섞인 경우 자동으로 실제 회사명으로 추론하지 않는다. example_mode를 표시하고 사용자 입력/현재 config로 확정한다.

legacy run files는 history import로만 등록: `origin=legacy`, validation=unverified, delivery=unknown/not_recorded. 과거 HTML이 있다는 이유로 accepted receipt를 생성하지 않는다. legacy 원본은 import가 성공해도 이동·삭제하지 않는다.

새 engine 버전의 DB migration은 append-only schema migrations. 실제 SQLite ALTER 지원 범위 안에서 구현하고 DB backup fixture로 rollback 시험한다. 메이저 schema downgrade는 자동 처리하지 않는다.

## 8. 추적 이벤트

events.jsonl / structured log 이벤트 목록:

- run.created, stage.started, stage.succeeded, stage.failed.
- cache.hit, cache.miss, cache.corrupt.
- job.planned, job.attempt_started, job.attempt_finished, job.repair_requested.
- validation.completed, artifact.committed.
- delivery.reserved, delivery.accepted, delivery.failed, delivery.unknown, delivery.resolved.
- memory.candidate_created, memory.observation_applied.

공통 필드: timestamp, run_id, stage/job_id(optional), event, duration_ms(optional), error_code(optional), attempt(optional). 모델 로그를 엔진 log schema에 그대로 흘리지 않는다.

## 9. 설계 변경 프로토콜

구현 중 실제 CLI가 schema mode를 지원하지 않는 등 명세와 다른 사실을 발견하면:

1. 관련 티켓/계약을 표시한다.
2. 정확한 명령/버전/실패 결과를 evidence에 저장한다.
3. 기존 invariants(검증, no side effects, explicit budget)를 유지하는 최소 대안을 선택한다.
4. 00-DECISIONS의 새 ADR 또는 기존 ADR amendment에 이유를 기록한다.
5. STATUS.design_changes에 링크를 남긴다.
6. 해당 example/schema/test를 함께 갱신한다.

모듈명이 취향에 맞지 않는다는 이유만으로 설계를 재편하지 않는다. 사용자의 업무 흐름·권한·배포 범위를 바꾸는 결정이면 새 사용자 지시를 반영해야 한다.
