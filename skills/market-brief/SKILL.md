---
name: market-brief
description: Prepare, validate, render, and optionally deliver a market briefing.
---

Use the shared `prmonitor` engine. In host mode, run `prmonitor run --pipeline market --mode host --json`, answer only the pending job request, then use `ingest`, `validate`, and `render`. Never send unless the run is READY and the user explicitly requests delivery.
