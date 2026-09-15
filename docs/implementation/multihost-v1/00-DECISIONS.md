# 00. 범위와 설계 결정

## A. 확인된 현황

기준 커밋은 README에 기록했다. Python 엔진·Claude 플러그인·Codex/generic CLI adapter·도메인팩·Pages 샘플이 존재한다. 감사 당시 기존 테스트 134개 통과. Pages 작업 후 formatter 테스트 41개 통과. 실제 유료 LLM 전체 실행과 실메일 전송은 미검증이다.

| ID | 현황/결함 | 근거 | 해결 티켓 |
|---|---|---|---|
| F01 | 병렬 LLM 전부 실패해도 빈 JSON 확정, 발송 경로 진입 | market_brief._run_parallel_synth, audit reproduction | T01,T05,T06 |
| F02 | Codex 0.149.1이 --full-auto 거부 | evidence/codex-exec-help.txt, 감사 | T01,T04 |
| F03 | hours 확대 시 synthesis-context 캐시 잔존 | pre.run | T01,T03 |
| F04 | resolver 오류/검증 파일 손상을 PASS처럼 취급 | post.run/_quality_warning_count | T01,T06 |
| F05 | glossary에 Claude 모델 기본값 유출 | market_brief: glossary_model | T01,T04 |
| F06 | generic prompt 치환 후 shlex.split으로 본문 손상 | llm_adapter._build_argv | T01,T04 |
| F07 | 공개 no-email/dry-run 미등록, PR 경로 이메일 항상 시도 | __main__, self_brief, self_brief_daily | T01,T07 |
| F08 | 보류된 내용도 self-context 갱신 가능 | post.run | T01,T08 |
| F09 | 함수와 설정이 import-time global에 결합 | paths/domainpack/script constants | T02,T03,T07 |
| F10 | 출력 파일 존재가 최신·성공의 증거로 사용됨 | pre/market/post | T02,T05,T06 |
| F11 | init이 bootstrap 실패를 삼키고 marker 생성 | steps/init.py | T02,T09 |
| F12 | domainpack이 회사 설정 누락을 예시 팩으로 폴백 | domainpack.pack_path | T02,T09 |
| F13 | source ID는 URL MD5 앞 6자리, enrichment ID도 별도 | aggregate.article_id, enrich._aid | T03 |
| F14 | 월별 CSV 건수를 물리적 줄 수로 계산 | self_brief._count_csv_rows | T07 |
| F15 | PR renderer 안에 수집·LLM·CSV·XLSX·HTML 모두 결합 | render_pr_clipping.main | T07 |
| F16 | venv healthy가 일부 import만 검사, 의존성 변경 반영 없음 | bootstrap.venv_healthy | T09 |

F01–F07 중 일부는 실패 주입으로 재현했다. F08 이후는 코드 경로/구조 확인이며 운영 사고가 실제 발생했다는 뜻이 아니다. 전체 발생 빈도를 알 수 없다.

## B. 확정 결정(ADR)

### ADR-01: 로컬 CLI + Python 라이브러리

서버·Docker·Redis·분산 큐·웹 DB·MCP server를 필수 런타임으로 추가하지 않는다. 코드의 배포 단위는 repo bundle이며 인터페이스는 `python /bundle/prmonitor_launch.py ...`가 정본. `prm`은 설명용 약칭, 실제 console script 생성은 v1 필수 범위가 아니다.

### ADR-02: Python 3.11 이상

3.9+/3.10+ 안내 혼재를 3.11+로 통일한다. 목표 CI는 3.11·3.12, 주 플랫폼 macOS/Linux, Windows는 명시적 지원 gate 통과 후 지원 표시한다. 런타임에서 조기 버전 오류를 제공한다. 이미 있는 라이브러리는 유지. 신규 검증용 `jsonschema` 하나만 허용하되 T02에서 실제 설치 가능한 버전을 확인해 정확 버전 고정. DB·UUID·시간·hash는 stdlib 사용.

### ADR-03: 공통 LLM 계약, 다른 실행 수단

`mode=host`는 새 LLM 프로세스를 호출하지 않는다. 현재 에이전트가 작업 요청 JSON을 읽고 결과를 제출한다. `mode=headless`는 engine이 CLI를 호출한다. 선택은 사용자/스킬이 명시한다. Claude에서 실행 중이라는 이유로 무조건 `claude -p`를 실행하지 않는다.

### ADR-04: 기본 합성은 single

뉴스레터는 기본 1개 `market_brief` job 안에 tldr/insights/category summaries/headlines/glossary를 함께 생성한다. 기사 보강은 기본 off, 선택 on. 큰 입력의 split 모드는 후속 티켓에서 활성화하며 예상 호출 수를 실행 전에 표시한다. 기존 병렬 6개가 기본인 동작은 변경한다.

### ADR-05: 구조적 완전성과 문장 스타일은 다른 판정

필수 데이터 누락·unknown ref·검증 장애는 오류다. 문장 길이·선호 어휘 등은 warning이다. 경고 개수 5개 이하이면 무조건 발송하는 기존 기준을 폐기한다. 정책은 finding code별 severity로 관리한다.

### ADR-06: JSON schema와 의미 검증을 모두 사용

Schema는 타입·필수 필드·enum·형식을 검증한다. ref가 실제 기사에 존재하는지, 동일 카테고리가 중복됐는지, 반환 run_id/hash가 맞는지는 코드로 추가 검증한다. JSON Schema 통과가 사실성 검증 완료라는 뜻은 아니다.

### ADR-07: 실행 ID가 출력 소유권

날짜는 표시 정보다. 실행 키는 `YYYYMMDDTHHMMSSZ-<uuid4 앞 12자리>`이며 생성 시 충돌 확인. 한 실행 내 attempt도 분리한다. 날짜 기반 legacy 파일은 compatibility export일 뿐 resume/send의 입력으로 사용하지 않는다.

### ADR-08: SQLite는 상태·전송 원장에만 사용

stdlib sqlite3로 워크스페이스별 메타데이터 저장. 장시간 트랜잭션을 열고 네트워크 작업하지 않는다. 뉴스 본문·LLM JSON·HTML은 파일 저장. DB가 상태의 정본이며 manifest.json은 사람이 읽는 projection이다. DB 손실 시 manifest를 보고 자동 발송 이력을 복원하지 않는다.

### ADR-09: 전송은 별도 명령, exactly-once 보장은 하지 않음

새 canonical run은 기본 생성만 한다. 자동 발송은 명시적으로 등록한 정책에 한해 수행. 기존 명령의 설정 기반 발송은 한 번의 마이그레이션에서 보존 가능하지만 묵시적으로 확대하지 않는다. SMTP/Graph의 응답 유실 때문에 외부 exactly-once 전송은 보장할 수 없다. 불명확하면 `unknown`으로 남기고 자동 재전송하지 않는다.

### ADR-10: 검증된 결과만 영속 맥락으로 승격

기계적으로 확인 가능한 출처 기반 관찰만 자동 timeline 후보가 된다. 전략 시사점/해석은 review candidate로 저장한다. 메일 발송 성공 여부와 내용의 적격성은 분리한다. 검증 PASS + 내용 유형 정책으로 적용 여부를 결정한다.

### ADR-11: 버전 호환은 증거로 관리

CLI의 플래그·응답 포맷은 실제 `--help`/probe 결과로 확정한다. 현재 Codex CLI는 `--full-auto`를 쓰지 않는다. Hermes는 broken local install을 별도 환경 결함으로 기록한다. 문서에서 임의 Hermes headless 플래그를 만들지 않는다.

### ADR-12: 배포는 하나의 엔진, 호스트별 artifact

source에서 공통 엔진·스킬을 유지하고 staging artifact를 생성한다. Claude manifest·Codex manifest·Hermes native registration은 adapter 디렉터리에서 조합한다. 사용자에게 세 환경별 중복 코드 편집을 요구하지 않는다.

## C. 범위

### v1 필수

감사 결함, typed 계약/상태/캐시, host/headless 경로, 세 호스트 패키징, 설정·설치 진단, PR 모듈 분리, 출처 검증, 발송 원장, self-context 후보/승격, 회귀/통합 테스트, 공개 샘플 유지.

### 명시적 비목표

뉴스 SaaS 서버화, 사용자 계정/결제, 임베딩 검색을 제품 의존성으로 추가, 자동 도메인 리서치의 무제한 실행, GUI 설정 편집기, 기존 구독 인증을 API 키로 전환, 모든 문장 진위를 규칙으로 완전 증명, 사용자 스케줄 자동 대량 수정.

### 디폴트의 근거

경량성은 설치 크기만이 아니라 LLM 호출 수·컨텍스트·운영 복잡도다. 현재 코드의 유효한 도메인 로직은 이동·감싸기부터 한다. 기사 분류 알고리즘과 HTML 디자인을 같은 티켓에서 재작성하지 않는다.
