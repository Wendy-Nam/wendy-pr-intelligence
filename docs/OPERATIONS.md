# 운영 점검과 복구

실행이 멈추거나 발송이 보류됐을 때는 **상태 확인 → 원인 확인 → 필요한 작업만 복구** 순서로 처리합니다. 같은 발송을 무작정 다시 실행하지 마세요.

## 먼저 확인할 명령

1. Run `python3 -m prmonitor doctor --strict` from the workspace.
2. Inspect `python3 -m prmonitor status --state-dir <workspace>/.prmonitor --run-id <id>`.
3. Use `python3 -m prmonitor jobs --state-dir <workspace>/.prmonitor --run-id <id>` to identify pending or failed work.

## 상황별 조치

| 상태·증상 | 조치 |
|---|---|
| 필수 작업이 대기·실패 | `ingest`로 해당 요청의 결과를 반영하거나, `repair`로 새 요청을 만든 뒤 그 요청의 결과를 반영합니다. |
| 검증 상태가 `HELD` | 브리핑을 고치거나 필요한 작업을 끝낸 뒤 `validate`를 다시 실행합니다. 통과하면 `READY`가 됩니다. |
| `DELIVERY_GATE_REJECTED` | 함께 검증한 브리핑·정책·검증 보고서·렌더 HTML을 정확히 사용해야 합니다. 하나라도 바꾸면 다시 렌더·검증합니다. |
| 중복 발송 우려 | 바로 재시도하지 않습니다. 발송 기록이 같은 실행·산출물·수신자 조합을 막으므로 기존 영수증을 먼저 확인합니다. |
| 발송 상태가 `unknown` | 재발송 전에 공급자 또는 수신자에게 도착 여부를 확인합니다. 제출 후 타임아웃이 났을 수 있습니다. |
| Hermes 실행기 사용 불가 | Hermes 자체 설치·venv를 복구한 뒤 `scripts/packaging/probe_hosts.py`를 다시 실행합니다. 코어 번들은 호스트 설치를 고치지 않습니다. |

## 릴리즈 전 검증

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/demo/verify_samples.py
.venv/bin/python scripts/packaging/probe_hosts.py
```

호스트별 배포 번들은 다음처럼 만듭니다.

```bash
.venv/bin/python -m scripts.packaging.build . /tmp/prmonitor-bundle --host codex
```

필요에 따라 `codex`를 `claude` 또는 `hermes`로 바꿉니다. 번들 검증은 매니페스트·포함 스킬·Python import를 확인하지만, 설치되지 않았거나 고장 난 외부 CLI의 실제 실행까지 보장하지는 않습니다.

조직별 설정은 [USAGE](../USAGE.md), 정기 실행은 [routines/README](../routines/README.md)를 참고하세요.
