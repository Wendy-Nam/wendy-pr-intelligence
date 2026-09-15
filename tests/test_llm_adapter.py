"""T01 argv and temporary prompt-file regressions (V08)."""
from pathlib import Path


def test_generic_prompt_file_is_removed_after_run_text(monkeypatch):
    from prmonitor.steps import llm_adapter
    captured = {}

    class Result:
        returncode = 0
        stdout = "ok"

    def fake_run(argv, **_kwargs):
        captured["path"] = argv[1]
        assert Path(argv[1]).read_text(encoding="utf-8") == "한글 'quoted'\nline"
        return Result()

    monkeypatch.setenv("PRM_SYNTH_CMD", "fake {prompt_file}")
    monkeypatch.setattr(llm_adapter.subprocess, "run", fake_run)
    rc, text = llm_adapter.HermesBackend().run_text(
        llm_adapter.SynthJob(prompt="한글 'quoted'\nline", model=""))
    assert (rc, text) == (0, "ok")
    assert not Path(captured["path"]).exists()


def test_generic_template_keeps_prompt_as_one_argv_token():
    from prmonitor.steps.llm_adapter import SynthJob, _build_argv
    argv = _build_argv("tool --prompt {prompt} --model {model}",
                       SynthJob(prompt="한글 'quoted'\nline", model="model-x"))
    assert argv == ["tool", "--prompt", "한글 'quoted'\nline", "--model", "model-x"]
