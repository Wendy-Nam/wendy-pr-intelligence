# PR Intelligence — 멀티호스트 v1 구현 설계 패키지

작성: 2026-09-15 · 기준: `99b1d80d27fa63140043068e4a933a5b462c6a2c`

**이 문서는 구현 명세다. 아래의 신규 API·CLI·파일은 별도 표시가 없으면 아직 구현되지 않았다.** 사용자는 권장 개선 전체를 구현할 계획이며, 이 패키지는 새 세션의 상대적으로 저렴한 모델이 작은 단위로 구현할 수 있도록 작성했다. 여기서 특정 모델의 실제 가격이나 품질을 가정하지 않는다.

## 목적

하나의 로컬 Python 엔진을 Claude Code·Codex·Hermes에서 재사용한다. 대화형 실행은 현재 호스트의 LLM을 사용하고, 무인 실행만 별도 CLI backend를 사용한다. 뉴스 수집·검증·렌더·전송은 엔진이 책임진다. 실패를 성공처럼 표시하거나 오래된 입력으로 발송하지 않는다.

## 읽는 순서

| 문서 | 내용 | 누가 읽는가 |
|---|---|---|
| [00-DECISIONS.md](00-DECISIONS.md) | 확정 설계 선택, 현황·목표 구분, 범위 | 모든 구현 세션 |
| [01-ARCHITECTURE.md](01-ARCHITECTURE.md) | 모듈·경로·저장·동시성·보안 경계 | 코어 구현 |
| [02-CONTRACTS.md](02-CONTRACTS.md) | JSON 계약, 상태 전이, CLI, 설정, 오류 | 모든 구현 세션 |
| [03-WORKFLOWS.md](03-WORKFLOWS.md) | 설치·대화형·무인·재개·발송·업데이트 | 파이프라인·호스트 구현 |
| [04-IMPLEMENTATION.md](04-IMPLEMENTATION.md) | 작업 티켓, 파일별 수정, 의존 순서 | 실제 구현 담당 |
| [05-VERIFICATION.md](05-VERIFICATION.md) | 테스트 ID·fixture·장애 주입·출시 기준 | 구현·리뷰 |
| [06-HOSTS-AND-RELEASE.md](06-HOSTS-AND-RELEASE.md) | 호스트 어댑터·패키징·Pages·릴리스 | 호환성·배포 |
| [07-HANDOFF.md](07-HANDOFF.md) | 새 세션에 붙일 프롬프트·보고 형식 | 사용자·새 모델 |
| [08-OPERATIONS.md](08-OPERATIONS.md) | 복구·성능 목표·핵심 알고리즘 | 구현·운영 |
| [STATUS.json](STATUS.json) | 진행 상태의 초기 정본 | 매 작업 종료 시 갱신 |
| [examples/](examples/) | 서로 연결되는 유효 JSON 예시 | 계약·fixture 작성 |
| [evidence/](evidence/) | 기준 커밋 및 설치된 CLI 도움말 | 버전별 옵션 검증 |

원래 감사: [REPORT.ko.md](../../architecture-audit/REPORT.ko.md). 기존 2026-06 설계는 역사적 맥락이며 충돌 시 이 패키지의 v1 목표를 따른다. 사용자 후속 지시는 모든 계획보다 우선한다.

## 세션 비용을 줄이는 사용법

1. 새 세션은 `07-HANDOFF.md`의 시작 프롬프트를 사용한다.
2. 전체 저장소·전체 설계서를 매번 읽지 않는다. README → STATUS → 해당 티켓의 명시 문서만 읽는다.
3. 기본 한 세션 한 티켓. 선행 티켓이 끝나지 않았다면 순서를 건너뛰지 않는다.
4. 완료는 코드+테스트+기록으로 판정한다. 코드가 없어도 되는 조사 티켓은 재현 가능한 조사 결과가 산출물이다.
5. 미완료 상태를 `done`으로 바꾸지 않는다. 유료 CLI/메일 통합시험 미실행을 단위 테스트 통과로 대체하지 않는다.

## 핵심 결과물

- 동일한 `RunSpec`과 `LLMResult`를 사용하는 세 호스트.
- 실행 ID별 입력·중간 산출물·검증·렌더·발송 기록.
- 필수 합성 누락/잘못된 ref/검증 실패 시 HELD 또는 FAILED.
- 외부 발송과 장기 맥락 갱신은 검증된 결과만 사용.
- 재생성·재실행·중복 스케줄에도 이전 실행이나 다른 회사 데이터가 섞이지 않음.
- 설치 패키지에는 코드·공개 템플릿·스킬만 포함. CodeGraph·venv·사용자 데이터 제외.
- 기존 GitHub Pages 샘플 유지와 재생성 검증.

## 완료 정의

`05-VERIFICATION.md`의 release gate를 모두 만족하고 `STATUS.json`이 근거 파일을 가리켜야 한다. Hermes 로컬 환경 복구가 안 되면 다른 경로는 구현하되 Hermes headless를 완료라고 표시하지 않는다. 모델의 글 품질은 별도 대표 사례 평가가 필요하며 규칙 검증만으로 사실성 전체를 보증하지 않는다.

## 설계 자체의 검증

JSON Schema, 요청/응답 hash, 기사 ID, 필수 ref/category coverage, artifact hash, 문서 내부 링크, 티켓/검증 ID 누락을 검사했다. 결과는 [plan-validation.txt](evidence/plan-validation.txt)에 있다. 이는 설계 예시의 정합성 검증이며 제품 구현 테스트 통과를 의미하지 않는다.

```bash
uv run --no-project --with jsonschema python docs/implementation/multihost-v1/evidence/verify_plan.py
```

STATUS의 티켓 상태는 pending/in_progress/done/blocked를 허용한다. 제품 runtime dependency는 이 문서 검증용 uv 임시 환경과 별개다.
