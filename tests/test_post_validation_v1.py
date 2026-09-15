"""T06: legacy post wrapper routes its gate through the canonical services."""
import json
from types import SimpleNamespace

DATE = "2026-09-15"

BRIEFING = {
    "tldr": "요약",
    "insights": [{"observation": "관찰", "facts": [{"ref": "a1"}]}],
    "category_summary": [{"category_id": "battery"}],
}
FACTS = {"categories": [{"category_id": "battery", "facts": [{"id": "a1", "title": "t"}]}]}


def _setup(monkeypatch, tmp_path, briefing=None, on_format=None):
    from prmonitor.steps import post

    for name in ("BRIEFING_DIR", "NEWSLETTER_OUTPUT_DIR", "OUTPUT_DIR", "PROCESSED_DIR", "LOGS_DIR"):
        path = tmp_path / name.lower()
        path.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(post.paths, name, path)
    briefing_path = post.paths.BRIEFING_DIR / f"newsletter-briefing-{DATE}.json"
    briefing_path.write_text(json.dumps(briefing or BRIEFING), encoding="utf-8")
    (post.paths.PROCESSED_DIR / f"newsletter-facts-{DATE}.json").write_text(
        json.dumps(FACTS), encoding="utf-8")
    (post.paths.NEWSLETTER_OUTPUT_DIR / f".quality-warnings-{DATE}.json").write_text(
        "[]", encoding="utf-8")
    html = post.paths.NEWSLETTER_OUTPUT_DIR / f"newsletter-report-{DATE}.html"

    class Result:
        def __init__(self, rc): self.returncode = rc

    def fake_run(argv, **_kwargs):
        if "format.py" in str(argv):
            html.write_text("<p>ok</p>", encoding="utf-8")
            if on_format:
                on_format(briefing_path)
        return Result(0)

    monkeypatch.setattr(post.subprocess, "run", fake_run)
    monkeypatch.setattr(post, "cleanup_retention", lambda: None)
    sent = []
    monkeypatch.setattr(post, "send_html_email", lambda *a: sent.append(a))
    return post, html, sent


def test_validated_briefing_sends(monkeypatch, tmp_path):
    post, html, sent = _setup(monkeypatch, tmp_path)
    assert post.run(SimpleNamespace(date=DATE, hours=24, no_email=False)) == 0
    assert sent and "REVIEW NEEDED" not in html.read_text(encoding="utf-8")


def test_unknown_ref_holds_with_watermark(monkeypatch, tmp_path):
    bad = json.loads(json.dumps(BRIEFING))
    bad["insights"][0]["facts"] = [{"ref": "missing"}]
    post, html, sent = _setup(monkeypatch, tmp_path, briefing=bad)
    assert post.run(SimpleNamespace(date=DATE, hours=24, no_email=False)) == 0
    assert not sent
    assert "REVIEW NEEDED" in html.read_text(encoding="utf-8")
    assert (post.paths.OUTPUT_DIR / "REVIEW_NEEDED.md").is_file()


def test_briefing_changed_after_validation_blocks_send(monkeypatch, tmp_path):
    def tamper(briefing_path):
        changed = json.loads(json.dumps(BRIEFING))
        changed["tldr"] = "검증 이후 바뀐 원고"
        briefing_path.write_text(json.dumps(changed), encoding="utf-8")

    post, _html, sent = _setup(monkeypatch, tmp_path, on_format=tamper)
    assert post.run(SimpleNamespace(date=DATE, hours=24, no_email=False)) == 0
    assert not sent
