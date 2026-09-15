"""LLM backend adapter — isolates synthesis calls from any one host CLI.

newsletter.py used to shell out to `claude -p ...` directly, three times,
with near-duplicate argv-building at each call site. That breaks under any
host that isn't Claude Code, and the duplication made every future backend
mean copy-pasting subprocess plumbing again.

This module fixes both: a `SynthJob` bundles what a synthesis call needs,
and each supported host is one small `LLMBackend` subclass that knows how
to turn a job into an argv. Adding a backend means adding one class, not
touching newsletter.py.

Select the backend with `PRM_LLM` (default: "claude"):

  claude   `claude -p "<prompt>" --model X --effort Y --allowedTools ... \\
             --add-dir DIR --output-format stream-json --verbose`
  codex    `codex exec [--model X] "<prompt>"` (OpenAI Codex CLI's
             non-interactive mode). Override the command shape with
             PRM_CODEX_CMD if your Codex CLI version's flags differ —
             same {prompt}/{prompt_file}/{model} substitution as "hermes".
  hermes   Any other agent CLI (a Hermes agent, oh-my-openagent role,
             OpenCode, …), via PRM_SYNTH_CMD. Placeholders substituted:
             {prompt_file} — path to a temp file holding the prompt
                             (for CLIs that don't take a bare prompt arg)
             {model}       — the resolved model name, if the command
                             wants to pass it through explicitly
             If PRM_SYNTH_CMD has neither {prompt_file} nor {prompt},
             the prompt is appended as the final argv token.
  generic  Alias for "hermes" — same PRM_SYNTH_CMD mechanism, kept for
             backwards compatibility with earlier config.

Cost/log parsing (scripts/lib/exec-log.py) stays Claude-stream-json-shaped
and is simply unavailable for non-Claude backends; callers already treat
cost as optional.
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path

_TEMP_PROMPT_FILES: set[str] = set()
_TEMP_PROMPT_FILES_LOCK = threading.Lock()


@dataclass(frozen=True)
class SynthJob:
    """Everything one synthesis call needs — host-agnostic."""

    prompt: str
    model: str
    effort: str = "medium"
    allowed_tools: str = "Read,Write"
    add_dir: str = ""
    log_path: str | Path = ""
    env: dict | None = None
    # True for run_text() calls that read the reply straight from stdout
    # (no file output, no tool grants needed) — skips the file-writing-mode
    # flags (--allowedTools/--add-dir/--output-format stream-json) that would
    # otherwise put structured JSON events on stdout instead of a plain reply.
    text_mode: bool = False


class LLMBackend:
    """One host CLI. Subclasses implement `_argv` and, optionally, `binary`."""

    name = "base"

    def binary(self) -> str:
        """The executable this backend needs on PATH. Empty = not applicable."""
        return ""

    def available(self) -> tuple[bool, str]:
        b = self.binary()
        if not b:
            return (False, f"{self.name}: no command configured")
        return (shutil.which(b) is not None, b)

    def _argv(self, job: SynthJob) -> list[str]:
        raise NotImplementedError

    def run(self, job: SynthJob) -> int:
        """Run the job, writing combined stdout/stderr to job.log_path.

        Returns the subprocess return code (informational — callers judge
        success by whether the expected output file appeared).
        """
        argv = self._argv(job)
        try:
            with open(job.log_path, "w", encoding="utf-8") as lf:
                proc = subprocess.run(argv, stdout=lf, stderr=subprocess.STDOUT,
                                      env=job.env, check=False)
            return proc.returncode
        finally:
            _cleanup_prompt_files(argv)

    def run_text(self, job: SynthJob, timeout: float | None = None) -> tuple[int, str]:
        """Run the job and return (returncode, stdout) directly — for callers
        that read the LLM's reply from stdout instead of a written file
        (no job.log_path needed here).
        """
        argv = self._argv(job)
        try:
            proc = subprocess.run(argv, capture_output=True, text=True,
                                  env=job.env, timeout=timeout, check=False)
            return proc.returncode, proc.stdout
        finally:
            _cleanup_prompt_files(argv)


class ClaudeBackend(LLMBackend):
    """Claude Code CLI (`claude -p`) — the original, unchanged behavior."""

    name = "claude"

    def binary(self) -> str:
        return "claude"

    def _argv(self, job: SynthJob) -> list[str]:
        claude_bin = shutil.which("claude")
        if not claude_bin:
            raise RuntimeError("claude CLI not found on PATH")
        if job.text_mode:
            # Plain reply on stdout — no file-writing tools, no stream-json.
            return [claude_bin, "-p", job.prompt, "--model", job.model]
        argv = [
            claude_bin, "-p", job.prompt,
            "--model", job.model,
            "--effort", job.effort,
            "--allowedTools", job.allowed_tools,
            "--output-format", "stream-json",
            "--verbose",
        ]
        if job.add_dir:
            argv += ["--add-dir", job.add_dir]
        return argv


class CodexBackend(LLMBackend):
    """OpenAI Codex CLI, non-interactive mode (`codex exec`).

    Codex's flag surface has shifted across releases, so the shape is
    overridable with PRM_CODEX_CMD (same placeholders as HermesBackend)
    for anyone pinned to a different version.
    """

    name = "codex"

    def binary(self) -> str:
        cmd = os.environ.get("PRM_CODEX_CMD", "")
        return _first_token(cmd) if cmd else "codex"

    def _argv(self, job: SynthJob) -> list[str]:
        cmd = os.environ.get("PRM_CODEX_CMD", "")
        if cmd:
            return _build_argv(cmd, job)
        # Codex CLI 0.149.1 rejects --full-auto; keep the portable exec form.
        argv = ["codex", "exec"]
        if job.model:
            argv += ["--model", job.model]
        argv.append(job.prompt)
        return argv


class HermesBackend(LLMBackend):
    """Any other agent CLI — a Hermes agent, an oh-my-openagent role,
    OpenCode's `opencode run`, etc. Fully described by PRM_SYNTH_CMD, since
    there's no single command shape across "some other agent's CLI".
    """

    name = "hermes"

    def binary(self) -> str:
        cmd = os.environ.get("PRM_SYNTH_CMD", "")
        return _first_token(cmd)

    def _argv(self, job: SynthJob) -> list[str]:
        cmd = os.environ.get("PRM_SYNTH_CMD", "")
        if not cmd:
            raise RuntimeError(
                "PRM_SYNTH_CMD not set for PRM_LLM=hermes — e.g. "
                'PRM_SYNTH_CMD=\'my-agent-cli run --prompt-file {prompt_file}\'')
        return _build_argv(cmd, job)


_BACKENDS: dict[str, type[LLMBackend]] = {
    "claude": ClaudeBackend,
    "codex": CodexBackend,
    "hermes": HermesBackend,
    "generic": HermesBackend,  # alias, kept for back-compat
}


def _first_token(cmd: str) -> str:
    try:
        parts = shlex.split(cmd)
    except ValueError:
        return ""
    return parts[0] if parts else ""


def _build_argv(cmd: str, job: SynthJob) -> list[str]:
    """Substitute {prompt}/{prompt_file}/{model} placeholders into a command
    template, writing a temp file for {prompt_file} when it's used.
    """
    try:
        template = shlex.split(cmd)
    except ValueError as e:
        raise RuntimeError(f"invalid PRM_SYNTH_CMD template: {e}") from e
    subst = {"model": job.model}
    if "{prompt_file}" in cmd:
        import tempfile
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8")
        tmp.write(job.prompt)
        tmp.close()
        subst["prompt_file"] = tmp.name
        with _TEMP_PROMPT_FILES_LOCK:
            _TEMP_PROMPT_FILES.add(tmp.name)
    if "{prompt}" in cmd:
        subst["prompt"] = job.prompt
    try:
        argv = [token.format(**subst) for token in template]
    except KeyError as e:
        raise RuntimeError(f"unknown PRM_SYNTH_CMD placeholder: {{{e.args[0]}}}") from e
    if "{prompt_file}" not in cmd and "{prompt}" not in cmd:
        argv.append(job.prompt)
    return argv


def _cleanup_prompt_files(argv: list[str]) -> None:
    """Remove only prompt files created for this subprocess invocation."""
    with _TEMP_PROMPT_FILES_LOCK:
        owned = set(argv) & _TEMP_PROMPT_FILES
        _TEMP_PROMPT_FILES.difference_update(owned)
    for name in owned:
        try:
            Path(name).unlink(missing_ok=True)
        except OSError:
            pass


def backend_name() -> str:
    return os.environ.get("PRM_LLM", "claude").strip().lower() or "claude"


def get_backend() -> LLMBackend:
    name = backend_name()
    cls = _BACKENDS.get(name)
    if cls is None:
        raise RuntimeError(
            f"unknown PRM_LLM backend '{name}' — choose one of "
            f"{sorted(set(_BACKENDS))}")
    return cls()


def available() -> tuple[bool, str]:
    """(ok, binary_or_hint) — whether the configured backend can actually run."""
    try:
        return get_backend().available()
    except RuntimeError as e:
        return (False, str(e))


def run_synthesis(job: SynthJob) -> int:
    return get_backend().run(job)
