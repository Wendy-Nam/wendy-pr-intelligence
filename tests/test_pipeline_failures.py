"""T01 fail-closed pipeline regression tests (V01--V05)."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest


def _patch_market_paths(monkeypatch, tmp_path):
    from prmonitor.steps import market_brief
    for name in ("PROCESSED_DIR", "BRIEFING_DIR", "LOGS_DIR", "PROJECT_DIR"):
        monkeypatch.setattr(market_brief.paths, name, tmp_path / name.lower())
    for name in ("PROCESSED_DIR", "BRIEFING_DIR", "LOGS_DIR"):
        getattr(market_brief.paths, name).mkdir(parents=True, exist_ok=True)
    return market_brief


@pytest.mark.parametrize("bad_label", ["core", "cat-robots"])
def test_parallel_invalid_required_json_does_not_create_final(monkeypatch, tmp_path, bad_label):
    """V01--V03: invalid core or category artifacts are never partial success."""
    market = _patch_market_paths(monkeypatch, tmp_path)
    date = "2026-09-15"
    (market.paths.PROCESSED_DIR / f"synthesis-context-{date}.json").write_text(
        json.dumps({"categories": [{"category_id": "robots", "category_name": "로봇", "facts": []}]}),
        encoding="utf-8")
    monkeypatch.setattr(market.time, "sleep", lambda _: None)

    def fake_synthesis(job):
        # A command claims success but writes malformed JSON; the other job is valid.
        out = market.paths.BRIEFING_DIR / (
            f"briefing-core-{date}.json" if "synth-core" in str(job.log_path)
            else f"briefing-cat-robots-{date}.json")
        label = "core" if "core" in out.name else "cat-robots"
        valid = ({"tldr": "x", "insights": [], "landscape_update_points": []}
                 if label == "core" else
                 {"category_id": "robots", "category_name": "로봇",
                  "summary": "x", "headlines": []})
        out.write_text("{bad" if label == bad_label else json.dumps(valid), encoding="utf-8")
        return 0

    monkeypatch.setattr(market.llm_adapter, "run_synthesis", fake_synthesis)
    with pytest.raises(RuntimeError, match="필수 합성 job 실패"):
        market._run_parallel_synth(date, "", "low", {})
    assert not (market.paths.BRIEFING_DIR / f"newsletter-briefing-{date}.json").exists()


def test_post_resolver_failure_holds_and_skips_memory_and_email(monkeypatch, tmp_path):
    """V05: resolver failure cannot update long-lived context or send mail."""
    from prmonitor.steps import post
    for name in ("BRIEFING_DIR", "NEWSLETTER_OUTPUT_DIR", "OUTPUT_DIR", "PROCESSED_DIR", "LOGS_DIR"):
        path = tmp_path / name.lower()
        path.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(post.paths, name, path)
    date = "2026-09-15"
    (post.paths.BRIEFING_DIR / f"newsletter-briefing-{date}.json").write_text("{}", encoding="utf-8")
    (post.paths.NEWSLETTER_OUTPUT_DIR / f".quality-warnings-{date}.json").write_text("[]", encoding="utf-8")
    calls = []

    class Result:
        def __init__(self, rc): self.returncode = rc

    def fake_run(argv, **_kwargs):
        calls.append(argv)
        if "resolve-refs.py" in str(argv):
            return Result(1)
        if "format.py" in str(argv):
            (post.paths.NEWSLETTER_OUTPUT_DIR / f"newsletter-report-{date}.html").write_text("ok")
        return Result(0)

    monkeypatch.setattr(post.subprocess, "run", fake_run)
    monkeypatch.setattr(post, "send_html_email", lambda *a: pytest.fail("email must not send"))
    monkeypatch.setattr(post, "cleanup_retention", lambda: None)
    assert post.run(SimpleNamespace(date=date, hours=24, no_email=False)) == 0
    assert (post.paths.OUTPUT_DIR / "REVIEW_NEEDED.md").is_file()
    assert not any("update-landscape.py" in str(argv) for argv in calls)
