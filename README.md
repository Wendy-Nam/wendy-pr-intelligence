<p align="center">
  <img src="docs/demo/assets/pr-monitor-banner.svg" alt="PR 인텔리전스 — 뉴스, 맥락, 판단" width="720">
</p>

**PR·마케팅 대행사의 리서치, 뉴스 클리핑, 정기 브리핑 제작 업무를 자동화하는 멀티호스트 인텔리전스 도구입니다.**

국내외 보도와 글로벌 경쟁사·산업 키워드를 원하는 주기로 수집해, 출처가 연결된 브리핑으로 만듭니다. 사람이 반복해서 하던 검색·분류·요약·리포트 편집은 줄이고, 담당자는 메시지 판단과 고객 커뮤니케이션에 집중할 수 있습니다.

| 만드는 결과 | 쓰임 |
|---|---|
| **자사 PR 브리핑** | 회사 언급을 직접·간접·주가 보도로 나누고, 톤·맥락·월별 누적을 확인 |
| **시장 인텔리전스 브리핑** | 해외 외신과 해외 경쟁사를 포함한 시장 동향을 묶고 자사·고객사 시사점 제시 |

수집 → 본문 추출 → 분류 → 중요도 판정 → LLM 합성 → 품질 검증 → HTML/이메일 순서로 실행합니다. 검증에 걸린 결과는 보내지 않고 `HELD`로 보류합니다.

## 미리보기

- [홈](https://wendy-nam.github.io/wendy-pr-intelligence/)
- [자사 PR 브리핑 예시](https://wendy-nam.github.io/wendy-pr-intelligence/self-brief.html)
- [업계 브리핑 예시](https://wendy-nam.github.io/wendy-pr-intelligence/market-brief.html)

예시의 기업·기사·수치는 모두 가상입니다.

## 시작하기

### Claude Code

```text
/plugin marketplace add Wendy-Nam/wendy-pr-intelligence
/plugin install wendy-pr-intelligence@news-monitor
```

첫 세션에서 설정과 Python 환경을 준비합니다. 이후 `/setup`에서 회사, 경쟁사, 뉴스 소스, 수신자를 설정하세요.

### Codex · Hermes 등

공통 엔진은 Python CLI로도 실행할 수 있습니다. Claude Code가 아닌 환경에서는 먼저 초기화합니다.

```bash
python3 prmonitor_launch.py init --force
export PRM_LLM=codex
python3 prmonitor_launch.py market-brief
```

| 백엔드 | 설정 |
|---|---|
| Claude | 기본값 `PRM_LLM=claude` |
| Codex | `PRM_LLM=codex` |
| Hermes·기타 CLI | `PRM_LLM=hermes`와 `PRM_SYNTH_CMD='… {prompt_file}'` |

호스트별 배포 번들은 다음과 같이 만듭니다.

```bash
.venv/bin/python -m scripts.packaging.build . /tmp/prmonitor-bundle --host codex
```

`claude`, `codex`, `hermes` 중 대상 호스트를 지정합니다. Hermes는 정상 설치된 CLI 또는 `PRM_SYNTH_CMD`가 있어야 실제 합성을 실행할 수 있습니다.

## 사용

| 명령 | 용도 |
|---|---|
| `/setup` | 회사·소스·수신자·스케줄 설정 |
| `/market-brief [date] [hours]` | 업계 브리핑 생성·발송 |
| `/self-brief [date] [hours]` | 자사 PR 브리핑 생성·발송 |

CLI에서는 `market-brief`, `self-brief`, `init`, `doctor`를 사용합니다. `python3 -m prmonitor --help`로 전체 옵션을 확인하세요.
`newsletter`는 기존 자동화가 깨지지 않도록 남긴 CLI alias이며, 새 작업에서는 사용하지 않습니다.

## 설정과 운영

조직별 정보는 워크스페이스의 `config/`와 `data/self-context/`에만 둡니다. 코드 수정 없이 회사·경쟁사·키워드·뉴스 소스·스타일·수신자를 바꿀 수 있습니다.

새 조직 설정은 `/setup` 또는 `pr-setup` 스킬에 회사명·산업을 주면 시작할 수 있습니다. 깊은 초안이 필요하면 `domain-pack-research` 스킬이 공개 리서치로 경쟁사·카테고리·소스·키워드·self-context를 만들고, 승인 뒤에만 YAML에 반영합니다.

- 설정 및 품질 튜닝: [USAGE.md](USAGE.md)
- 구조와 안전 경계: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- 장애 대응·복구: [docs/OPERATIONS.md](docs/OPERATIONS.md)
- 정기 실행: [routines/README.md](routines/README.md)

## 검증과 개발

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/demo/verify_samples.py
.venv/bin/python scripts/packaging/probe_hosts.py
```

뉴스 수집에는 네트워크가 필요합니다. Cowork 같은 클라우드 샌드박스에서는 수집이 제한될 수 있으므로 로컬 환경에서 실행하세요.

## License

[MIT](LICENSE) © Wendy Nam
