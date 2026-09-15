"""LLM backend adapter — isolates the synthesis call sites from any one CLI.

newsletter.py used to shell out to `claude -p ...` directly (3 call sites).
That's fine when Claude Code is the host, but breaks under any other agent
CLI (Codex, OpenCode/oh-my-openagent, etc.) that doesn't have a `claude`
binary or doesn't understand its flags.

Backend is selected by env var `PRM_LLM` (default: "claude"):

  claude    claude -p "<prompt>" --model X --effort Y --allowedTools ... \
              --output-format stream-json --verbose   (unchanged behavior)
  generic   $PRM_SYNTH_CMD "<prompt>"   — user supplies the exact command;
              "{prompt_file}" in PRM_SYNTH_CMD is replaced with a path to a
              temp file holding the prompt (for CLIs that don't take a
              prompt as a bare argv, e.g. `codex exec`, `opencode run`).
              If "{prompt_file}" isn't present, the prompt is appended as
              the final argv token instead.

Cost/log parsing stays Claude-specific (stream-json) and is simply skipped
for the generic backend — callers already treat cost as optional.
"""
from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
from pathlib import Path


def backend() -> str:
    return os.environ.get("PRM_LLM", "claude").strip().lower() or "claude"


def available() -> tuple[bool, str]:
    """(ok, binary_or_hint) — whether the configured backend can actually run."""
    import shutil

    be = backend()
    if be == "claude":
        b = shutil.which("claude")
        return (b is not None, b or "claude")
    if be == "generic":
        cmd = os.environ.get("PRM_SYNTH_CMD", "")
        if not cmd:
            return (False, "PRM_SYNTH_CMD not set")
        first = shlex.split(cmd)[0] if cmd else ""
        b = shutil.which(first)
        return (b is not None, first)
    return (False, f"unknown PRM_LLM backend '{be}'")


def run_synthesis(
    prompt: str,
    *,
    model: str,
    effort: str,
    allowed_tools: str,
    add_dir: str,
    log_path,
    env: dict,
) -> int:
    """Run one synthesis call, writing combined stdout/stderr to log_path.

    Returns the subprocess return code (informational — callers judge success
    by whether the expected output file appeared, same as before).
    """
    be = backend()
    if be == "claude":
        import shutil as _shutil

        claude_bin = _shutil.which("claude")
        if not claude_bin:
            raise RuntimeError("claude CLI not found on PATH")
        argv = [
            claude_bin, "-p", prompt,
            "--model", model,
            "--effort", effort,
            "--allowedTools", allowed_tools,
            "--add-dir", add_dir,
            "--output-format", "stream-json",
            "--verbose",
        ]
        with open(log_path, "w", encoding="utf-8") as lf:
            proc = subprocess.run(argv, stdout=lf, stderr=subprocess.STDOUT,
                                   env=env, check=False)
        return proc.returncode

    if be == "generic":
        cmd = os.environ.get("PRM_SYNTH_CMD", "")
        if not cmd:
            raise RuntimeError("PRM_SYNTH_CMD not set for PRM_LLM=generic")
        tmp = None
        try:
            if "{prompt_file}" in cmd:
                tmp = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".txt", delete=False, encoding="utf-8")
                tmp.write(prompt)
                tmp.close()
                argv = shlex.split(cmd.replace("{prompt_file}", tmp.name))
            else:
                argv = shlex.split(cmd) + [prompt]
            with open(log_path, "w", encoding="utf-8") as lf:
                proc = subprocess.run(argv, stdout=lf, stderr=subprocess.STDOUT,
                                       env=env, check=False)
            return proc.returncode
        finally:
            if tmp:
                Path(tmp.name).unlink(missing_ok=True)

    raise RuntimeError(f"unknown PRM_LLM backend '{be}'")
