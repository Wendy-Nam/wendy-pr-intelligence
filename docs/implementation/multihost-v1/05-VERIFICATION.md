# 05. 검증 명세

## 1. 테스트 계층

1. Unit: 순수 함수의 규칙/경계값. mock으로 자기 구현을 그대로 재현하는 테스트는 피한다.
2. Contract: JSON schema+semantic constraint, CLI stdout envelope.
3. Integration offline: 임시 workspace+local HTTP fixture server+fake CLI+fake email transport, 실제 SQLite/파일/renderer 사용.
4. Host integration: 실제 CLI로 작은 request 실행, 설치된 host 버전·모델·날짜 기록.
5. Product QA: 생성 HTML을 desktop/mobile에서 보고 링크/톤/정보 누락 확인.

일반 CI는 1–3만 필수. 4의 결과를 fake success로 대체하지 않는다. 네트워크·유료 호출은 opt-in marker `live`로 분리한다. 테스트에서 사용자 config/실제 수신자/개인 cache를 읽지 않는다.

## 2. fixture 디렉터리

```text
tests/
  fixtures/v1/
    domainpacks/contoso/...
    articles/market-small.json       # 6 articles, 4 categories
    articles/self-small.json         # 3 direct / 2 indirect / 1 stock
    requests/market.json
    responses/valid-market.json
    responses/valid-pr.json
    responses/missing-category.json
    responses/unknown-ref.json
    responses/malformed.txt
    responses/wrong-input-hash.json
  helpers/
    fake_cli.py
    fake_http.py
    fake_delivery.py
```

fake_cli는 환경에 지정한 fixture file을 stdout으로 반환한다. modes=success,nonzero,malformed,hang,spawn-child,oversized-output,stderr-secret-marker. shell eval 없이 Python sys.executable로 실행. 실제 backend argv 구성은 fake 실행 파일로 주입하여 검증한다.

fake_delivery는 transport 호출 카운트/전송 직전 gate 상태를 기록하고 accepted/preconnect_failure/response_lost/partial 결과를 제공한다. 실제 provider endpoint를 호출하지 않는다.

시간은 FrozenClock(UTC wall time + monotonic 별도)을 주입한다. `sleep`을 patch해서 deadline 계산이 깨지는 식의 테스트 금지. 요청 재시도 budget의 횟수는 backend invocation 카운터로 확인한다.

## 3. 검증 ID 목록

### 기준선 / 긴급 수정

| ID | 조건 | 기대 |
|---|---|---|
| V00 | baseline tests + audit repro | 기존 pass 수와 재현된 defect 기록 |
| V01 | core/category 전부 CLI 실패 | final 없음, send 0, nonzero |
| V02 | core OK/category 1개 실패 | incomplete merge는 READY 불가 |
| V03 | malformed JSON 파일이 존재 | job 실패, 존재로 success 판정 금지 |
| V04 | 24h→72h 확대 | synthesis-context 새 입력으로 갱신 |
| V05 | resolver rc=1 또는 quality JSON 손상 | HELD/FAILED, send 0 |
| V06 | no-email + PR daily pipeline | 모든 단계에 전달, send 0 |
| V07 | dry-run | network/LLM/memory/email/write 0 |
| V08 | generic quote/한글/newline + glossary Codex | 정확 argv/stdin, Claude 모델명 없음 |

### 경로 / 상태 / 저장

| ID | 조건 | 기대 |
|---|---|---|
| V09 | 동일 process A→B workspace | config/path mixing 없음 |
| V10 | read-only bundle + writable workspace/cache | bundle mtime 변화 없음 |
| V11 | cwd가 repo 밖/경로에 공백·한글 | absolute launcher 정상 |
| V12 | CAS old revision으로 상태 갱신 | conflict, 원본 상태 유지 |
| V13 | DB commit 전 crash 후 orphan artifact | artifact 불신, send 금지 |
| V14 | DB commit 후 manifest write 실패 | DB로 projection 재생성 |
| V15 | traversal ID 또는 symlink output escape | allowed root 밖 쓰기 거부 |
| V16 | running lease 두 process | 한 owner만 실행, 만료 인계 기록 |

### Collection / cache

| ID | 조건 | 기대 |
|---|---|---|
| V17 | 같은 exact stage key | producer 재호출 없이 verified cache |
| V18 | hours/cutoff/config/body 변화 | 관련 downstream cache miss |
| V19 | self-context만 변화 | fetch 재사용 가능, context cache miss |
| V20 | cache hash mismatch/incomplete manifest | discard/rebuild, success 아님 |
| V21 | 모든 RSS/network 실패 | FAILED; 0건 정상처럼 표시 금지 |
| V22 | sources 정상 + eligible 0 | NO_DATA, LLM 0 |
| V23 | tracking URL 변화/fragment/ID collision | 안정 ID, 실제 충돌 명시 error |

### Backend

| ID | 조건 | 기대 |
|---|---|---|
| V24 | Codex argv on recorded profile | --full-auto 없음, supported flags only |
| V25 | model=null / role override | null이면 플래그 생략, role 정확 매핑 |
| V26 | stdout 결과+stderr logs | 응답 parse 가능, logs 섞이지 않음 |
| V27 | child timeout | parent/descendant 종료, temp cleanup |
| V28 | response size limit 초과 | 종료+OUTPUT_TOO_LARGE, 메모리 무제한 사용 없음 |
| V29 | auth/unsupported flag permanent failure | 재시도 0 |
| V30 | binary exists but interpreter missing | healthy=false, 오류 식별 |
| V31 | CLI logs에 secret marker | 공개 diagnostic/status에 marker 없음 |

### Jobs / orchestration

| ID | 조건 | 기대 |
|---|---|---|
| V32 | host mode prepare | LLM subprocess 0, pending job 반환 |
| V33 | result run_id/job_id/hash 불일치 | ingest 거부, 다른 run 수정 없음 |
| V34 | optional enrichment fail/skip | fallback warning, aggregate 계속 |
| V35 | required enrichment fail | FAILED, 합성 시작 없음 |
| V36 | single default | market job 1, implicit split/glossary 추가 없음 |
| V37 | call budget/deadline exhaustion | 다음 backend 호출 0, exit21 |
| V38 | resume after category failure | valid prior job 재사용, failed만 retry |
| V39 | split required job 수>예산 | 실행 전 오류, LLM 0 |

### Content gate / newsletter

| ID | 조건 | 기대 |
|---|---|---|
| V40 | valid fixture with all refs/categories | PASS, render READY |
| V41 | 빈 tldr/필수 insights 누락 | EMPTY_BRIEFING/SCHEMA error |
| V42 | unknown ref | error, URL fallback 추측 금지 |
| V43 | category missing/duplicate | error, 중복 집계 없음 |
| V44 | covered_refs만 있고 본문 refs 누락 | COVERAGE_GAP |
| V45 | 긴 문장 warning만 존재 | PASS 가능, warning 기록 |
| V46 | validator 내부 exception | ERROR/FAILED, send 0 |
| V47 | PASS 뒤 briefing/policy/HTML 변경 | hash mismatch, send 0 |
| V48 | HTML tag/javascript URL in LLM text | escaped text/rejected link |
| V49 | HELD preview 생성 | watermark 있고 READY/delivery 불가 |

### PR / exports

| ID | 조건 | 기대 |
|---|---|---|
| V50 | sample 6 articles | direct3/indirect2/stock1 |
| V51 | LLM tone과 확정 rule_tone 충돌 | 기존 rule 우선 |
| V52 | annotation unknown article ID | ingest 거부 |
| V53 | CSV field 내부 newline | counts는 logical records 6 |
| V54 | '=HYPERLINK(...)' 셀 | XLSX/CSV에서 formula 실행 없음 |
| V55 | HTML/CSV/XLSX 생성 | 같은 counts/tone/source IDs |
| V56 | PR --llm off | CLI 호출0, 규칙 기반 표시 |
| V57 | renderer import + render | network/backend 호출0, config global 없음 |

### Delivery / memory

| ID | 조건 | 기대 |
|---|---|---|
| V58 | HELD/FAILED/example run send | transport 호출0 |
| V59 | same dedupe concurrent requests | transport 1회 이하 |
| V60 | provider accepted 후 같은 요청 | skip, 재전송0 |
| V61 | accepted지만 response lost | unknown; resume 재전송0 |
| V62 | crash during sending | lease 만료 후 unknown |
| V63 | partial SMTP recipients | 전체 group 자동 재전송 없음 |
| V64 | no-email 또는 send_email:false | 요청 있어도 skipped |
| V65 | held landscape point | 기존 baseline/timeline 변화0 |
| V66 | accepted observation 동일 재적용 | event 1개, 월별 duplicate0 |
| V67 | memory view write 중 crash | event ledger로 idempotent 복구 |

### Setup

| ID | 조건 | 기대 |
|---|---|---|
| V68 | init deps 설치 실패 | marker ready=false, exit20 |
| V69 | init 재실행 | user config bytes 보존 |
| V70 | requirements hash 변경 | 새 runtime 선택, 옛 env 유지 |
| V71 | 회사 pack 누락 in operational | explicit error, Contoso fallback 금지 |
| V72 | init --example contoso | sample 표시, send 거부 |
| V73 | doctor 기본 호출 | pip/network/LLM 호출0 |
| V74 | migration dry-run/apply | preview no write, apply backup+검증 |

### CLI / scheduler

| ID | 조건 | 기대 |
|---|---|---|
| V75 | 모든 --json 명령 | stdout JSON 1개, logs stderr |
| V76 | no-email+send 함께 | usage error, side effect0 |
| V77 | 과거 월요일 날짜·as-of 경계 | 그 날짜 정책과 [start,end) 적용 |
| V78 | legacy alias | 문서화된 canonical mapping |
| V79 | date-only legacy post에 run 2개 | ambiguous error, 최신 임의선택 금지 |
| V80 | 동일 schedule_key 2회 | 같은 run 반환, 중복 생성0 |
| V81 | unknown subcommand/bad config | exit2와 error code, traceback 남발 없음 |

### Packaging

| ID | 조건 | 기대 |
|---|---|---|
| V82 | Claude artifact | manifest/load hook/skills validate |
| V83 | Codex artifact | .codex-plugin/skills paths validate |
| V84 | Hermes artifact | plugin.yaml+register_skill validate |
| V85 | artifacts compare | 동일 core 파일 hash |
| V86 | package secret allowlist scan | config/venv/logs/private data 없음 |
| V87 | 외부 read-only 설치 경로 | workspace outputs만 생성 |
| V88 | update 후 재실행 | 기존 domainpack/output/receipts 보존 |

### Demo / Pages

| ID | 조건 | 기대 |
|---|---|---|
| V89 | builder 실행 | network/LLM/email 0 |
| V90 | 두 번 생성 | HTML/JSON hash 동일 |
| V91 | 모든 상대 링크+anchor | 존재하고 접근 가능한 이름 |
| V92 | viewport390/desktop | horizontal overflow 없음 |
| V93 | 두 브리핑 | 가상 데이터 배너와 홈 링크 |
| V94 | Pages artifact inspection | docs/demo allowlist 외 파일0 |

## 4. 테스트 명령 표준

```bash
python -m pytest tests -q -m 'not live'
python -m pytest tests/test_pipeline_failures.py -q
python -m pytest tests/test_llm_adapter.py -q
python scripts/demo/build_samples.py
```

아직 파일이 없으면 해당 티켓에서 생성. 기존 test names는 유지하고 새 테스트는 기능 단위로 나눈다. 위 V ID는 테스트 함수 docstring/param id에 붙여 traceability 확보. 95개의 함수를 기계적으로 만들 필요는 없으며 parametrized test가 여러 V 조건을 다룰 수 있다.

추가 권장 테스트: SQLite actual two-process contention, short-lived subprocess with child, deterministic fixture server 500→200. 이런 경계는 mock만으로 대체하지 않는다.

## 5. 품질 평가 — 구조 테스트와 별도

대표 fixture 3종: 일반일(6–10건), 주요 이슈일(20–30건), 기사 부족일(0–2건). 한국어/영문 혼합, 같은 회사 다른 사건, 같은 사건 복수 매체, 자사 간접언급 포함.

각 실제 LLM 출력에 다음 0/1/2 평가:

| 항목 | 0 | 1 | 2 |
|---|---|---|---|
| 사실 보존 | 수치/주체 오류 | 일부 모호 | 핵심 사실 정확 |
| 근거 연결 | 관계없는 ref | 부분 연결 | 문장별 타당 |
| 커버리지 | 중요 기사 누락 | 일부 부차 누락 | 필수 기사 전부 |
| 자사 함의 | 근거 없는 확언 | 일반적 제안 | 맥락+불확실성 적절 |
| 한국어 가독성 | 이해 어려움 | 편집 필요 | 바로 검토 가능 |

합계 수치만으로 출시하지 않는다. **사실 보존 0 또는 근거 연결 0이면 해당 fixture 실패**. 모델을 바꾸면 같은 fixture로 비교. 예상 토큰/소요시간/호출 수/가능한 경우 비용을 함께 기록. 비용 unavailable은 null.

## 6. Release gates

### G1 오프라인 엔진

V00–V81 통과, README의 8개 주요 결함 각각 regression 보유. 일부 기존 테스트가 새 정책 때문에 바뀌면 그 이유와 새 test를 기록. 무조건 기존 기대값 삭제로 pass 만들지 않음.

### G2 호스트

Claude/Codex/Hermes 각각 (a) 실제 설치 발견, (b) host mode, (c) headless mode 결과를 별개 열로 기록. unavailable 조합이 있으면 release note 지원 표에 그대로 표시. 패키지 build 성공이 headless 정상의 증거가 아님.

### G3 콘텐츠/운영

3종 대표 사례 quality review, 실패 시 발송 0, unknown 전송 자동 재시도 0, 설정 보존/rollback rehearsal.

### G4 배포

V82–V94, 공개 샘플 URL 유지, package allowlist 검증. live email은 별도 지정 수신자가 있을 때만 수락 증거 확인. 미실행이면 delivery provider의 live 검증 상태를 미검증으로 기록.

## 7. 완료 보고 증거 형식

```text
ticket: T06
commit: <hash 또는 uncommitted>
commands:
 - python -m pytest ... → exit0, N passed
verified: [V40,V41,...]
not_run: [live CLI; 이유]
behavior_change: ...
artifact: progress/T06.md
next_ticket: T07
```

“테스트 완료”만 적지 않는다. 검증한 범위와 외부 의존성 미검증을 분리한다.
