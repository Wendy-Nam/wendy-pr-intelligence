# Operations and recovery

## First checks

1. Run `python3 -m prmonitor doctor --strict` from the workspace.
2. Inspect `python3 -m prmonitor status --state-dir <workspace>/.prmonitor --run-id <id>`.
3. Use `python3 -m prmonitor jobs --state-dir <workspace>/.prmonitor --run-id <id>` to identify pending or failed work.

## Common recovery paths

| State or symptom | Action |
|---|---|
| Required job pending or failed | Submit a matching result with `ingest`, or use `repair` to issue a new request and then submit that request's result. |
| `HELD` validation | Correct the briefing or finish required work; run `validate` again. A passing revalidation changes the run to `READY`. |
| `DELIVERY_GATE_REJECTED` | Use the exact briefing, policy, validation report, and rendered HTML that were validated together. Re-render and validate after any change. |
| Duplicate send | Do not retry blindly. The delivery ledger blocks the same run/artifact/recipient combination. Inspect the existing receipt first. |
| Delivery status `unknown` | Confirm delivery with the provider or recipient before any resend; unknown means a timeout may have occurred after submission. |
| Hermes launcher unavailable | Repair Hermes' own installation/venv, then rerun `scripts/packaging/probe_hosts.py`. The core bundle does not repair host installations. |

## Verification before release

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/demo/verify_samples.py
.venv/bin/python scripts/packaging/probe_hosts.py
```

Build a host bundle with:

```bash
.venv/bin/python -m scripts.packaging.build . /tmp/prmonitor-bundle --host codex
```

Replace `codex` with `claude` or `hermes` as needed. A bundle validation confirms its manifest, included skills, and Python import; it does not prove that an unavailable external host CLI can run.

For configuration and scheduled runs, see [USAGE](../USAGE.md) and [routines/README](../routines/README.md).
