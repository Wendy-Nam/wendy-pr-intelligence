# 설정과 품질 튜닝 가이드

이 플러그인의 **출력 품질은 코드가 아니라 설정(도메인팩)이 결정**합니다. 엔진은 회사·산업을 모르고, 워크스페이스(`${CLAUDE_PROJECT_DIR}`)의 `config/`·`data/self-context/`만 읽어 동작합니다. 즉 **어느 산업이든 이 설정을 깊게 채울수록 브리핑이 정확·날카로워집니다.** 이 문서는 그 튜닝 방법입니다.

> [!NOTE]
> 코드(`prmonitor/`·`scripts/`)는 손대지 않습니다. 전부 `config/`·`data/self-context/` 의 YAML·MD 편집입니다. 변경은 **다음 실행부터** 반영됩니다.

---

## 1. 설정이 작동하는 방식

```
뉴스 수집 → 분류(키워드) → 중요도(LLM) → 사건 클러스터링 → 합성(LLM) → 렌더 → 발송
   sources    categories      enrich        enrich(cluster)   self-context   format   delivery
   keywords   classify-tuning                                  prompt-examples
```

각 단계가 읽는 설정 파일이 다릅니다. 어디가 어긋났는지에 따라 **고칠 파일이 정해집니다**(아래 2장).

## 2. 설정 파일 지도

| 파일 | 무엇을 정하나 | 자주 만지는가 |
|---|---|---|
| `company-profile.yaml` | 회사·경쟁사·**카테고리 정의(watch_keywords·key_players)**·공급망·규제 | ★ 핵심 |
| `data/self-context/*` | 자사 서사·주요 이벤트·경쟁사 기준선 — **인사이트 "자사 함의"의 근거** | ★ 핵심 |
| `keywords.yaml` | 수집·분류 부스트/제외 키워드, 민감도(법적·부정·시황) | ★ |
| `classify-tuning.yaml` | 분류 미세조정 — 범용어, 이해관계자 가중, **`ma_route`(투자·M&A 라우팅)**, 저신호 패턴 | ★ |
| `categories.yaml` | 카테고리 라벨·색·렌더 순서 | 가끔 |
| `sources.yaml` | RSS·검색쿼리·클러스터링 임계·번역 | 초기 |
| `style.yaml` | 출력 언어·문장 길이·금지어(톤) | 초기 |
| `prompt-examples.yaml` | 인사이트 few-shot(좋은/나쁜 예) — **편집 품질** | 운영하며 |
| `pr-queries.yaml`·`tone-lexicon.yaml`·`media.yaml` | 자사명 변형·PR 톤·매체명 | 초기 |
| `delivery.yaml` | 수신자·이메일 인증·`pilot_mode` | 초기 |
| `pipelines.yaml` | 수집 시간창·발송 주기·제목 | 가끔 |

## 3. 품질을 좌우하는 4대 레버 (투자 우선순위 순)

**① self-context — 인사이트 천장.** `data/self-context/`가 "자사 함의"의 깊이를 정합니다. 비면 인사이트가 일반론이 됩니다.
- `company-narrative.md`: 포지셔닝·주요 관계(투자자·핵심 고객·전략 파트너)·전략 방향. `key_stakeholder`(대주주 등)를 명시하면 합성기가 가중합니다.
- `key-events.yaml`: 자사 주요 이벤트(투자·실적·제품·파트너십)에 **구체 수치**. 인사이트가 "경쟁사 X인데 자사는 [수치]"로 교차하는 근거.
- `competitor-landscape.yaml`: 경쟁사 기준선. 새 기사가 "기준선 대비 새 진전"인지 판단하는 잣대.

**② 카테고리 watch_keywords — 이중언어·브로드.** `company-profile.yaml`의 각 카테고리 `watch_keywords`가 분류·관련성을 좌우합니다. **니치 전문어만 넣으면 업계 표준어를 쓴 진짜 기사가 누락**됩니다. 업계 매체가 헤드라인에 실제로 쓰는 단어를 한국어+영어로 함께 넣으세요.

**③ keywords boost/exclude.** 수집망 1차 필터. 자사·경쟁사·핵심 주제어를 `boost`에, 시황·정치·연예 등 노이즈를 `exclude`/`strong_exclude`에. `sensitivity`로 법적·부정·시황 기사의 수신그룹별 처리를 정합니다.

**④ prompt-examples — 편집 판단.** 좋은 인사이트 vs 거짓 유추·날조 수치 반례. 부트스트랩이 v1 초안을 깔지만, "이 연결이 진짜냐 억지냐"의 미세 판단은 **실제 브리핑이 쌓이며 직접 큐레이션**해야 올라갑니다.

## 4. 라우팅·분류 미세조정 (`classify-tuning.yaml`)

- **`ma_route`**: 투자·M&A 사건을 제품 카테고리가 아니라 자금 카테고리로 보냅니다. 지분 인수/투자/매각·펀드·ETF·투자자 등은 "휴머노이드/배터리" 같은 제품군이 아니라 **투자 사건**이므로 따로 모읍니다.
  ```yaml
  ma_route:
    target: funding          # 도메인팩의 자금 카테고리 id
    keywords: ["지분 인수","지분 투자","펀드","ETF","투자 유치","시리즈 A","투자자", "M&A", ...]
  ```
  ⚠️ "투자" 단독 같은 과매칭어는 빼고 **구체어**만. (없으면 무동작 = 중립.)
- `generic_category_terms`: 카테고리를 단독으로 결정하지 못하는 범용어(분류·중복판정에서 제외).
- `stakeholder_boosts`: 자사 직접 이해관계자(대주주 등) 언급 가중.
- `low_signal_*`: 전시회 부스참가·시장보고서 등 tier1 부적합 패턴.

## 5. 부트스트랩이 도달해야 할 깊이 (기준)

`/setup`의 단계형 부트스트랩(Phase 0~5)은 아래 깊이를 목표로 합니다 — 새 조직도 이 수준까지 채워야 품질이 납니다. **번들 예시 도메인팩(Contoso Motors·EV)이 이 깊이의 본보기**입니다:
- 경쟁사 8~12곳 + 각 별칭·카테고리
- 카테고리 5~7개 + 각 이중언어 watch_keywords·key_players
- self-context 3종(narrative·key-events·competitor-landscape) 시드
- ma_route·sensitivity·sources(생존 확인된 RSS+쿼리)

번들 `config-templates/`를 열어 "이 정도 밀도"를 기준으로 자기 산업에 맞게 채우세요.

## 6. 수집·발송

- **수집 범위**: `pipelines.yaml`의 `hours`(평일)·`monday_hours`(주말 몫). 실행 시 한 번만 넓게 지정할 수도 있습니다 — `/market-brief 2026-06-15 168`(주간).
- **발송**: `delivery.yaml`의 `recipients` 그룹 + `email.provider`(microsoft_graph|smtp). **`pilot_mode: true`면 alerts 그룹으로만** 발송(실발송 전 검증용). 실발송은 `false`.

---

자세한 명령·설치는 [README](README.md), 설정 스키마 본보기는 `config-templates/<name>.yaml` 참고.

## 발송 경로와 검증 범위

| 용도 | 진입점 | 네트워크 |
|---|---|---|
| 오프라인 발송 확인 | `python -m prmonitor send --provider local …` (기본값) | 없음 |
| 검증된 실행 결과의 실발송 | `python -m prmonitor send --provider smtp …` 또는 `--provider microsoft_graph` | 있음 |
| 기존 자동화·테스트 메일·첨부파일 | `python scripts/send-email.py …` (호환 wrapper) | 있음 |

두 진입점의 SMTP/Graph 구현과 설정 로딩은 `prmonitor/email_service.py`를 공유합니다.
`prmonitor send`는 READY 상태·검증 보고서·중복 발송 ledger를 확인합니다.
기존 스크립트는 직접 발송 도구이므로 이 실행 상태/ledger 게이트를 제공하지 않습니다.

`send`의 provider는 `--provider` → `PRMONITOR_DELIVERY_PROVIDER` → `local` 순으로 선택합니다.
실발송 설정은 `--delivery-config`로 지정하거나 워크스페이스 `config/delivery.yaml`에서 읽습니다.
인증값과 발신자는 기존 환경변수(`SMTP_*`, `AZURE_*`, `EMAIL_FROM`, `CLAUDE_PLUGIN_OPTION_*`)가 YAML보다 우선합니다.
제목은 `--subject`, 수신자는 `--recipient`로 지정합니다. 이 명시적 수신자는 legacy `--to`처럼 그룹/파일럿 라우팅을 적용하지 않습니다.
기존 스크립트의 provider 선택(`PRM_EMAIL_PROVIDER` → `email.provider` → Graph)은 하위호환을 위해 유지합니다.

`accepted`는 SMTP/Graph 서버가 요청을 접수했다는 뜻이며 받은편지함 도착을 보장하지 않습니다.
SMTP ID는 클라이언트 Message-ID, Graph ID는 request-id(없으면 로컬 시도 ID)입니다.
수신 확인 연동은 아직 없어 내장 provider는 `delivered`를 반환하지 않습니다.
잘못된 receipt 또는 응답 유실은 `unknown`으로 남기고 자동 재발송하지 않습니다.
재시도 전에 공급자 로그에서 실제 접수 여부를 확인해야 합니다.

오프라인 테스트는 재현 가능한 엔진 동작, 가짜 SMTP/HTTP 경계, 패키징을 검증합니다.
실제 메일 수신, RSS/본문 추출 성공률, 호스트 CLI 버전별 출력 호환성은 별도의 live 검증이 필요합니다.
실제 자격증명과 외부 서비스로 검증했다고 의미하지 않습니다.
