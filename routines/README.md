# Routines 정의 (정본)

**이 폴더가 정본(source of truth)이다.** 루틴 프롬프트를 수정하면 여기서 고치고 커밋한다.

이 `routines/*.md` 가 곧 루틴 프롬프트의 정본이다. 플러그인은 이 파일을
scheduled-tasks MCP 로 **등록**해 실행본을 만든다 — 등록 메타데이터(cron·enabled)는
패키징으로 옮겨지지 않는 외부 상태라, 설치 때마다 한 번 등록해 줘야 한다.

| 파일 | task-id | 스케줄 |
|------|---------|--------|
| pr-monitoring-daily.md | pr-monitoring-daily | 평일 10:30 (+jitter) |
| newsletter-insight-mwf.md | newsletter-insight-mwf | 월·수·금 09:30 (+jitter) |

작업 디렉토리: `${CLAUDE_PROJECT_DIR}` (실 config·시크릿이 있는 워크스페이스).
루틴 프롬프트 안의 작업경로 자리표시자는 등록 시 이 값으로 치환된다.

## 루틴 등록 (정본 → 실행본)

루틴은 동기화 스크립트가 아니라 **플러그인 등록 플로우**로 실행본이 된다.
새 설치이거나, 루틴 프롬프트를 고쳐 다시 반영해야 할 때:

```
/setup 루틴 등록      # → ROUTINES 플로우 실행
```

`/setup ROUTINES` 는 다음을 한다:

1. `routines/{pr-monitoring-daily,newsletter-insight-mwf}.md` 의 작업경로
   자리표시자를 `${CLAUDE_PROJECT_DIR}` 로 치환한다.
2. scheduled-tasks MCP(`create_scheduled_task`)로 각 루틴을 등록한다 —
   cron 스케줄·enabled 상태는 이 MCP 가 외부 메타데이터로 관리한다.
   (또는 데스크톱 앱 Routines 화면에서 직접 추가해도 된다.)
3. 각 루틴을 "Run Now" 로 1회 실행해 권한(HTTP fetch·이메일·파일 IO)을
   사전 부여한다.

프롬프트만 고친 경우에도 같은 등록 플로우를 다시 돌리면 실행본이 갱신된다.
별도의 파일 복사 단계는 없다.

## 실행 주체: Claude Code Routines (데스크톱 앱)

**Routines 는 Claude Code 데스크톱 앱이 켜져 있어야 실행된다.** 앱이 꺼져 있으면 다음 실행 때 보충된다.
Routines 컨텍스트는 로컬 셸 전권을 가진다 — 외부 HTTP 수집, Azure 이메일 발송, 파일 I/O 모두 정상 동작.

**Cowork(클라우드)에서는 동작하지 않는다** — 샌드박스가 외부 fetch 를 차단해 수집이 0건으로 실패한다.

파이프라인 실행 흐름:
```
Claude Code Routines (데스크톱 앱)
  → bash scripts (scripts/newsletter/ or scripts/pr/)
    → Python (외부 HTTP 수집, LLM 호출, 이메일 발송)
      → 산출물 (data/output/{newsletter,pr}/*.html)
```

## 첫 등록 후

각 루틴을 **Run Now 로 1회 수동 실행**해 권한을 미리 허용해둔다.
이후 예약 실행은 저장된 권한을 자동 적용해 사용자 확인 없이 끝까지 돈다.

## Claude Code 밖에서 스케줄링하기 (Codex/OpenCode/일반 크론)

scheduled-tasks MCP·데스크톱 Routines는 Claude Code 전용이라 다른 호스트에는
없다. 엔진(`prmonitor/`)은 순수 CLI라 아무 스케줄러에서나 그대로 돌릴 수 있다:

```
# 매일 10:30, 09:30 같은 형태로 그냥 시스템 크론에 등록
30 10 * * 1-5 cd /path/to/pr-monitor && ./.venv/bin/python -m prmonitor pr-daily
30  9 * * 1,3,5 cd /path/to/pr-monitor && ./.venv/bin/python -m prmonitor newsletter
```

Claude Code가 아닌 호스트를 합성 백엔드로 쓰려면 `PRM_LLM`으로 지정한다
(`prmonitor/steps/llm_adapter.py` 참고— Claude Code Sub Agent 스펙에 안 걸리는
호출은 모두 이 어댑터 하나를 거친다):

```
export PRM_LLM=codex                             # OpenAI Codex CLI (codex exec)
# 또는
export PRM_LLM=hermes                             # 헤르메스류/그 외 에이전트 CLI 전부
export PRM_SYNTH_CMD="my-agent-cli run --prompt-file {prompt_file}"
```

트리거 자체를 별도 크론 없이 "메일 예약발송" 같은 이미 있는 스케줄링 기능에
얹는 방법도 있다 — 예를 들어 헤르메스류 에이전트가 이메일의 임시저장/예약발송
기능으로 정해진 시각에 자신을 깨우게 하고, 그 트리거가 위 크론 명령을 실행하는
식. 시스템 크론이 없는 환경에서 쓸 만한 대안이다.
