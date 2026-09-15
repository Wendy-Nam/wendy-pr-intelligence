# Multihost v1 운영 런북

## 보류/실패

`validate`가 exit 21 또는 상태 `HELD`를 반환하면 `render --allow-held`만 검토용으로 사용한다. HELD 결과는 `send`와 `memory-promote`에서 거부된다. 원인을 수정한 뒤 `jobs`/`repair`로 같은 run의 pending job만 재계획하고 `resume`으로 next action을 받는다. 진행 상황은 `status`, 목록은 `runs`로 확인하며 되살릴 수 없는 run은 `cancel` 후 `revise`로 계보를 이어 새 run을 만든다.

## 발송 unknown

전송 provider가 응답을 잃으면 ledger 상태는 `unknown`이다. 자동 재전송하지 않는다. provider 콘솔에서 Message-ID/수신 여부를 확인한 뒤 원장을 수동으로 resolve한다. `LocalTransport` fixture는 외부 발송을 하지 않는다.

## 설정/환경 복구

`doctor`의 `backend_binaries`에서 executable 존재만으로 healthy라고 판단하지 않는다. `--help` probe와 Hermes configured-template 여부를 확인한다. `services.setup.inspect_runtime()` fingerprint가 바뀌면 새 환경을 준비하고 ready marker를 교체한다. 레거시 config 이관은 `migrate_config(..., dry_run=True)`로 계획을 먼저 확인한다 — target이 이미 있으면 `preserved_existing`으로 아무것도 덮어쓰지 않는다. 이미 v1 config가 있는데 템플릿에 키가 추가된 경우에는 `upgrade_config(template, target, dry_run=True)`로 추가될 키를 확인한 뒤 실행한다(사용자 값·리스트 보존, `.bak` 1회 백업, 멱등).

## 릴리스 체크리스트

1. `.venv/bin/python -m pytest tests -q -m 'not live'`
2. `git diff --check`
3. `.venv/bin/python scripts/demo/verify_samples.py docs/demo` (구조/링크 + viewport·접근성 검사, exit 0 필요)
4. 세 host bundle의 `core_hash`가 동일한지 확인
5. 실제 LLM/email gate는 명시적 사용자 승인과 별도 비용 기록 없이는 실행하지 않는다.
