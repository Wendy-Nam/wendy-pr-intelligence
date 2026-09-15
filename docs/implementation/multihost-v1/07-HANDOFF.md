# 07. 새 세션 시작 프롬프트와 운영법

## 1. 첫 구현 세션 — 그대로 붙여 넣기

```text
이 저장소의 PR Intelligence 멀티호스트 v1을 구현해 주세요.
계획 문서: docs/implementation/multihost-v1/README.md
진행 상태: docs/implementation/multihost-v1/STATUS.json

먼저 README, 00-DECISIONS.md, STATUS.json을 읽고 현재 git status/commit을 확인하세요.
전체 설계와 전체 코드를 한 번에 읽지 말고 04-IMPLEMENTATION.md에서 다음 미완료
티켓 하나를 선택해 그 티켓이 지정한 문서·함수만 읽으세요.
첫 세션은 T00 기준선 확인 후 여력이 있으면 T01까지만 진행하세요.

목표는 공통 Python 엔진 + Claude/Codex/Hermes 얇은 플러그인입니다.
대화형은 현재 호스트 LLM, 무인 실행은 별도 CLI adapter를 사용합니다.
감사 보고서: docs/architecture-audit/REPORT.ko.md

사용자 변경을 보존하세요. 외부 발송이나 공개 배포를 실제로 실행하지 말고
fixture/local transport로 검증하세요. 유료 live 테스트가 필요하면 범위·비용을
명확히 구분하고 현재 세션에 그 실행 권한이 있는지 확인하세요.
환경이 없어도 독립적인 코어 구현·오프라인 검증은 계속할 수 있습니다.

완료 기준은 티켓의 테스트와 05-VERIFICATION.md의 V ID입니다.
테스트 실패를 숨기려고 검증을 삭제하거나 HELD를 SUCCESS로 바꾸지 마세요.
파일 존재를 LLM 작업 성공으로 간주하지 마세요.
모델/CLI 플래그는 실제 설치 버전 help로 검증하고 이름을 추측하지 마세요.

티켓 하나를 완료하면 STATUS.json과 progress/Txx.md를 갱신하세요.
변경 파일, 실행한 테스트 명령·결과, 미검증 범위, 다음 티켓을 보고하세요.
시간이나 컨텍스트가 부족하면 미완료 상태와 정확한 다음 작업을 기록하세요.
사용자가 요청하지 않은 서브에이전트/새 Codex task는 만들지 마세요.
```

## 2. 이후 세션 — 특정 티켓 지정

```text
PR Intelligence 멀티호스트 구현을 이어가세요.
설계: docs/implementation/multihost-v1/README.md
상태: docs/implementation/multihost-v1/STATUS.json
이번 범위: TXX (04-IMPLEMENTATION.md 참고)

선행 티켓의 완료 증거와 git diff부터 확인하세요.
해당 티켓의 읽기 목록만 먼저 읽고 필요한 함수로 범위를 좁히세요.
TXX를 코드·테스트·진행 기록까지 완료하고 다른 큰 리팩터는 섞지 마세요.
명세 충돌을 발견하면 00-DECISIONS.md/02-CONTRACTS.md의 정본에 맞추어
진행하되, 사용자 의도가 달라질 수 있는 변경은 근거와 선택지를 기록하세요.
끝나면 STATUS와 progress/TXX.md에 결과를 남기세요.
```

TXX는 T02처럼 실제 ID로 바꾼다. 예: T04는 프로세스/backend, T07은 자사 PR 분해.

## 3. 리뷰 전용 세션

```text
TXX 구현을 리뷰해 주세요. 제품 코드를 추가 구현하지 말고 먼저
계획의 완료 조건 및 관련 V ID와 현재 diff를 대조하세요.
특히 성공 판정, ref/hash 일치, 외부 부작용, concurrent run, 캐시 무효화를 보세요.
문제는 재현 조건·영향·파일/함수·최소 수정 방향으로 보고하세요.
실제 검증되지 않은 CLI/메일/플러그인 설치는 미검증으로 명시하세요.
```

## 4. 실패 시 재개 기록 템플릿

```markdown
# TXX 진행 기록
- 상태: in_progress / done / blocked
- 기준 commit:
- 현재 diff:
- 읽은 문서:
- 완료한 함수/계약:
- 미완료 부분:
- 실행한 명령과 exit:
- 검증한 V IDs:
- 다음 첫 명령:
- 사용자/외부 의존성:
- 설계 변경 여부:
```

`blocked`는 티켓의 외부 의존성이 필요한 경우다. 전체 프로젝트를 멈추는 상태가 아니며 STATUS.next_ticket에서 독립적으로 진행 가능한 작업을 지정할 수 있다. 선행 core contract를 건너뛰어 통합 불가능한 코드를 만들지 않는다.

## 5. 저비용 모델이 지켜야 할 구현 규칙

1. 새로운 명세를 설계하려고 다시 시작하지 않는다. 이미 결정된 구조를 따른다.
2. 타입/필드명/state 이름을 임의 번역하지 않는다. `accepted`를 `sent`로 바꾸면 계약 위반.
3. 없는 라이브러리 API·Hermes 플래그·plugin env를 추측하지 않는다.
4. `except Exception: return 0` 같은 성공 fallback 금지. optional stage만 명시 warning으로 계속.
5. 검증기는 실패를 hard fail로 반환하고 renderer는 입력 읽기·표현만 한다.
6. 단일 워크스페이스 테스트만으로 경로 격리를 완료라고 하지 않는다.
7. schema change는 examples/test fixtures와 같이 변경하고 version 판단을 기록한다.
8. 함수 이동 중 함수명/인자와 테스트를 동시에 너무 많이 바꾸지 않는다.
9. tests/fixtures에 가상의 공개 데이터를 사용한다. 현재 사용자의 도메인팩을 복사하지 않는다.
10. 필요 없는 UI/서버/MCP layer/추가 모델 호출을 넣지 않는다.
11. 임의 retry로 auth/config 오류를 해결하려 하지 않는다.
12. 최종 보고에 실제로 실행하지 않은 테스트를 포함하지 않는다.

## 6. 완료 판정 예시

나쁜 기록: “Codex 지원 완료, 테스트 통과.”

좋은 기록:

```text
T04 done (offline contract implementation)
- Codex argv/stdin/schema output profile 구현
- fake process timeout/child cleanup/quote tests 18 passed
- Codex 실제 LLM probe: 미실행 (현재 세션 비용 승인 범위 밖)
- Hermes headless: unsupported health로 명시, local venv missing
- T14 live gates는 pending 유지
- 다음: T05
```

T04의 done은 정해진 offline 완료 조건만 의미한다. host 전체 준비 여부는 STATUS.release_gates에 따로 남겨 혼동하지 않는다.

## 7. 새 머신에서 시작할 때

1. 저장소와 이 docs 디렉터리가 포함된 최신 작업 상태를 가져온다. 현재 문서는 로컬 파일로 생성되었으며 사용자 요청 없이 원격 push하지 않았다.
2. venv는 복사하지 않는다. 지원 Python을 설치하고 requirements-dev를 준비한다.
3. `evidence/`는 기준 머신의 help이며 새 설치 버전 help와 다를 수 있다.
4. CodeGraph가 없으면 해당 분석만 생략/설치하되 제품 runtime에 의존하지 않게 한다.
5. Hermes broken launcher를 따라 사용자 전역 venv를 삭제하지 않는다. 사용자 환경 복구 범위가 별도임을 기록한다.
