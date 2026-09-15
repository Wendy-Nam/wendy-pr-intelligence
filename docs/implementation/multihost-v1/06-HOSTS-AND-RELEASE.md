# 06. 호스트 연결·패키징·출시

## 1. 조사 근거와 불확실성

확인일 2026-09-15. 로컬 Codex 0.149.1, Claude Code 2.1.270. 도움말 원문은 evidence/에 있다. Hermes launcher는 존재하지만 참조 venv Python이 없어 실행 불가했다. 따라서 Hermes headless argv는 이 설계에서 확정하지 않는다.

공식 자료:

- [OpenAI 플러그인 예제 저장소](https://github.com/openai/plugins): `.codex-plugin/plugin.json`과 skills 구조 확인.
- [OpenAI 플러그인 안내](https://learn.chatgpt.com/docs/plugins).
- [Claude Code plugins reference](https://code.claude.com/docs/en/plugins-reference).
- [Hermes native plugins](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins).
- [Hermes creating skills](https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills).
- [GitHub Pages publishing source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

호스트 문서는 바뀔 수 있다. T11/T14는 설치 대상 버전의 parser/명령으로 검증하고 이 표를 갱신한다. 문서의 예제 manifest를 그대로 붙여 놓고 실제 loader 검증을 생략하지 않는다.

## 2. Host mode 공통 스킬

각 스킬의 사용자 노출 description은 짧게, 상세 절차/계약은 references로 나눈다. 파일 경로/런타임 문제를 사용자의 업무 흐름에 장황하게 노출하지 않는다.

### market-brief skill 본문 필수 절차

1. 사용자 workspace와 기간 결정. 명확한 기존 설정은 재질문하지 않음.
2. 공통 launcher의 doctor/config validate.
3. `run --pipeline market --mode host --json`.
4. pending request만 읽고 requested schema에 맞는 LLMResult 작성.
5. `ingest` 후 필요하면 `prepare`로 다음 phase 요청.
6. 모든 required jobs 완료 후 validate.
7. 수정 가능한 finding은 max_repairs 안에서 수정. error가 남으면 HELD 안내.
8. render, READY HTML 링크 제시. 발송은 사용자 요청/등록 정책이 있는 경우에만 `send`.

PR skill도 같은 절차이며 pipeline=self. “Task/Agent를 추가로 띄워라”는 지시를 기본에 넣지 않는다. host session 결과는 현재 context에서 생성한다.

### 입력과 출력 위치

모든 launcher args는 shell escaping 가능한 argv 또는 호스트 terminal tool의 명시 인자로 전달. 스킬의 임의 날짜 텍스트를 shell interpolation하지 않는다. result JSON은 workspace의 일반 임시 경로에 작성 후 ingest가 run store로 복사할 수 있다. hidden/sensitive directory 쓰기 권한을 강제로 우회하지 않는다.

## 3. Headless CLI adapter

### Codex — 검증할 기본 실행 형태

현재 로컬 help에서 지원하는 옵션에 기반한 **후보 invocation**:

```text
codex exec
  --skip-git-repo-check
  --ephemeral
  --sandbox read-only
  --cd <workspace>
  --output-schema <self-contained-schema-path>
  --output-last-message <engine-owned-attempt-output-path>
  [--model <explicit-model>]
  -
```

stdin에 request.instructions+JSON input+response envelope 설명을 넣는다. `--output-last-message`가 read-only sandbox와 함께 실제로 지정 파일을 쓰는지는 T04 live probe에서 검증해야 한다. CLI 자신의 출력 저장 기능과 모델 Write 도구 권한은 다른 층이다. 실패하면 stdout JSON을 파싱하는 profile로 구현한다. `--full-auto`는 사용하지 않는다.

- 기존 사용자 config의 모델 선택을 보존. `--ignore-user-config`는 기본 사용 금지(인증/모델 설정을 깨뜨릴 수 있음).
- 모델 도구 호출이 필요 없는 단일 structured response를 요청. reply에 CLI 이벤트 JSON이 섞이지 않게 `--json`과 마지막 메시지 출력을 혼동하지 않는다.
- effort는 지원 profile에서만 config override로 설정하고 실제 TOML 키를 probe/공식 docs로 확인. 미지원이면 “not applied” 기록; 임의 플래그 생성 금지.
- writable workspace가 필요한 fallback은 별도 capability이며 제한된 attempt dir만 add-dir, core는 stdout 결과 모드를 우선.

### Claude — 검증할 기본 형태

```text
claude --print [--model <explicit-model>]
  --output-format json
  --json-schema <schema-json>
  --tools ""
```

이는 schema/tools 옵션을 대상 CLI `--help`에서 확인한 뒤 활성화하는 profile이다. `-p`의 plain-text response를 받는 fallback도 지원하되 accepted output shape를 명시한다. CLI JSON의 `result`/structured_output/error envelope는 profile별 adapter가 해석한다. stream-json 로그 전체를 payload로 취급하지 않는다.

- `--bare`는 현재 help에 API-key-only 인증 제약이 있으므로 구독 기반 OAuth 사용자에게 기본 적용하지 않는다.
- permission bypass 플래그를 compatibility 해결책으로 넣지 않는다.
- 부모 Claude 세션의 nested-session env guard는 임의 제거하지 말고 공식 지원 여부를 확인. host mode로 해결 가능한 경우 headless nested는 unsupported로 표시.
- 현재 `MAX_THINKING_TOKENS=0`을 모든 backend에 전파하는 방식 폐기. provider별 지원 설정만 사용.

### Hermes

두 경로를 구분한다.

1. **Native skill/plugin host mode**: register_skill로 공통 skill 노출. Hermes 내부 LLM이 request 수행. 외부 hermes CLI가 필요 없음.
2. **Headless CLI**: 설치가 복구된 뒤 도움말·작은 실제 request로 stdout/schema/prompt 입력을 검증하고 `hermes.py` profile 구현.

우회로로 generic template을 사용할 수 있지만 이를 검증된 Hermes backend라고 이름만 바꿔 표시하지 않는다. `doctor`는 hermes_native_skill_supported와 hermes_headless_supported를 다른 check로 출력한다.

### Generic

config 예시(실제 CLI 이름은 사용자가 지정):

```yaml
generic:
  argv: ["agent-cli", "run", "--prompt-file", "{prompt_file}"]
  output: stdout_json
  env_allowlist: []
```

placeholders는 prompt_file/model만 권장. `{prompt}` legacy 지원은 tokenized argv 안의 문자열 치환으로 한 인자를 보존. stdout_json은 envelope JSON 전체 하나; response 파일 경로 template을 지원할 경우 `attempt-dir` 아래로 제한.

## 4. 호스트 패키지

### 공통 artifact allowlist

```text
prmonitor/**
scripts/(필수 CLI shim 및 launcher support만)
prmonitor_launch.py
requirements.txt
prompts/**
skills/**
config-templates/defaults/**
config-templates/examples/**
LICENSE
호스트별 manifest/entrypoint
```

exclude: .git, .venv, .prmonitor, actual config, data/output, data/raw, self-context 실데이터, logs, .env, architecture audit machine paths, tests, CodeGraph binary/cache, local screenshots. 명시 allowlist 기준으로 staging build; `copytree(repo)` 후 blacklist 몇 개 지우는 패키징 금지.

### Claude artifact

```text
bundle/
 .claude-plugin/plugin.json
 commands/setup.md
 commands/newsletter.md
 commands/self-brief.md
 hooks/hooks.json
 skills/...
 prmonitor/...
```

기존 marketplace repo root 설치 경로를 유지하려면 source root에 generated manifest/commands를 유지하고 packaging check가 template와 drift를 검사한다. hook은 opted-in workspace의 빠른 확인만 수행. `userConfig`/비밀 주입 등 현재 manifest field는 현재 Claude parser와 대조하여 지원하지 않으면 문서와 구현 모두 수정한다. Codex 형식을 Claude schema로 복사하지 않는다.

### Codex artifact

```text
bundle/
 .codex-plugin/plugin.json
 skills/pr-setup/SKILL.md
 skills/pr-monitor/SKILL.md
 skills/market-brief/SKILL.md
 prmonitor/...
```

최소 manifest 필드는 실제 official example 기반으로 검증. 호스트 지정 CLI 변수가 자동 주입된다고 가정하지 않는다. 스킬의 own location에서 bundle root를 계산하는 wrapper/상대 reference를 제공하고 workspace는 사용자 cwd 또는 명시 --workspace로 설정. `.claude-plugin`만 있는 현재 repo가 곧 Codex installable plugin이라는 설명은 금지.

### Hermes artifact — native plugin 우선

```text
bundle/
 plugin.yaml
 __init__.py
 skills/...
 prmonitor/...
```

공식 문서가 제공하는 registration 패턴을 target 버전에 맞춰 적용:

```python
from pathlib import Path

def register(ctx):
    skills_dir = Path(__file__).parent / "skills"
    for child in sorted(skills_dir.iterdir()):
        skill_md = child / "SKILL.md"
        if skill_md.is_file():
            ctx.register_skill(child.name, skill_md)
```

register는 skill 등록만 하고 pip install/news fetch/model 호출을 하지 않는다. Hermes plugin 자체 import와 prmonitor의 Python deps import를 분리하여 Hermes 환경에 엔진의 의존성을 억지로 설치하지 않는다.

Hermes는 portable Agent Plugins 패키지도 지원하는 문서가 있지만 v1은 native register_skill 경로 하나를 먼저 검증한다. 두 배포 방식 동시 지원을 필수로 만들지 않는다.

## 5. Legacy compatibility 표

| 기존 진입점 | v1 처리 | 주의 |
|---|---|---|
| `market-brief` / `newsletter` | headless market service wrapper | PRM_LLM/default claude legacy 해석, 경고 |
| `pre` | collect + prepare | 기존 date 인자 유지; 새 run_id 출력 |
| `post date hours` | 해당 legacy-linked run validate/render + 설정 정책 발송 | run이 여러 개면 명시 ID 요청 |
| `self-brief-daily` / `pr` | self 전체 실행 | hours/no-email 전달 |
| `self-brief` / `pr-clip` / `pr-monitor` | 이미 준비된 self run 후처리 | 기존 precondition을 조용히 전체 수집으로 바꾸지 않음 |
| `init --force` | opt-in init | overwrite 의미 아님 |
| legacy 날짜 파일 | 선택적 export copy | resume/send source 아님 |
| CLAUDE_* vars | PRM vars보다 낮은 우선순위 | globals에서만 해석하지 않음 |
| PRM_SYNTH_CMD | generic legacy template parser | shell execution 없음 |

legacy 발송 정책: migration 시 기존 pipeline.send_email 값을 `legacy_auto_send`로 명시 저장하고 사용자에게 변경점을 안내한다. 신규 canonical run은 기본 발송 요청 false. 기존 설정에 send_email 누락이면 auto-send를 새로 켜지 않는다. legacy self 예전 동작이 “항상 시도”였더라도 새 기본은 보수적으로 false이며 breaking change로 기록한다.

## 6. 버전 매트릭스 기록 형식

| Host | version | install/load | host mode | headless | notes |
|---|---|---|---|---|---|
| Codex | 0.149.1(기준) | 아직 미검증 | 미검증 | --full-auto 불가 확인 | 실제 profile probe 필요 |
| Claude | 2.1.270(기준) | repo artifact 존재 | 미검증 | CLI 존재 | nested/auth 확인 |
| Hermes | unknown | launcher 존재 | 미검증 | 실행 불가 | venv 경로 누락 |

버전을 고정해 영원히 지원한다고 말하지 않는다. release-tested range는 실제 검증한 version만 우선 기록. 나머지는 capability probe 기반 지원/미지원 판정.

## 7. CI / Pages / 릴리스

- offline tests는 Python3.11/3.12. headless fixture process termination은 OS별 테스트.
- packaging job은 각 artifact 내부 schema/path/allowlist/core hash 검증.
- Pages는 docs/demo만 upload. 지금 공개 URL 유지:
  - https://wendy-nam.github.io/wendy-pr-intelligence/
  - https://wendy-nam.github.io/wendy-pr-intelligence/self-brief.html
  - https://wendy-nam.github.io/wendy-pr-intelligence/market-brief.html
- workflow actions는 구현 시점 지원 버전으로 확인하고 가능하면 검증된 commit SHA pin. 기존 Pages 정상 동작을 호환성 리팩터 중 끊지 않음.
- release note는 생성 방식 변경(single/host), dry-run 정의, 경로 migration, auto-send 정책, 최소 Python, 지원 host matrix를 포함.
- 배포 전 사용자의 실제 domainpack을 public sample로 복사하지 않음. build allowlist만으로 민감 데이터가 코드 파일 안에 들어간 경우까지 막을 수 없으므로 fixture 내용도 검토.

## 8. CodeGraph 활용

개발 전후 구조 비교용으로만 사용. `codegraph-server --graph-only --run-tool codegraph_generate_architecture_doc` 결과를 baseline와 비교한다. 함수 complex score가 내려가도 동작 검증을 대체하지 않는다. dynamic dispatch/subprocess/ref contracts는 테스트가 정본이다. 설치 경로가 다른 새 머신에서는 codegraph command discovery 후 사용하며 hardcoded 사용자 경로를 새 제품 코드에 넣지 않는다.
