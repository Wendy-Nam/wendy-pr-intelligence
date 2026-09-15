from prmonitor.llm.base import Invocation
from prmonitor.llm.process import execute

def test_process_keeps_stdout_and_stderr_separate(tmp_path):
 r=execute(Invocation(['sh','-c','cat; echo err >&2'],'한글'),timeout_seconds=2,max_output_bytes=100,stderr_path=tmp_path/'err')
 assert r.process_rc == 0 and r.stdout_json_or_text == '한글' and (tmp_path/'err').read_text().strip() == 'err'
def test_process_rejects_oversize_output():
 r=execute(Invocation(['sh','-c','printf 12345']),timeout_seconds=2,max_output_bytes=4)
 assert r.error['code'] == 'OUTPUT_TOO_LARGE'
def test_codex_invocation_uses_stdin_without_full_auto():
 from prmonitor.llm.codex import CodexBackend
 inv=CodexBackend().build_invocation({'prompt':"한글 'quote'\nline"},{'model':None})
 assert inv.argv == ['codex','exec'] and inv.stdin.startswith('한글') and '--full-auto' not in inv.argv
def test_generic_array_template_preserves_prompt_token():
 from prmonitor.llm.generic import GenericBackend
 inv=GenericBackend(['tool','--prompt','{prompt}']).build_invocation({'prompt':"a b '한글'"},{})
 assert inv.argv[-1] == "a b '한글'"
def test_claude_null_model_omits_model_flag():
 from prmonitor.llm.claude import ClaudeBackend
 assert '--model' not in ClaudeBackend().build_invocation({'prompt':'x'},{'model':None}).argv
def test_process_timeout_returns_sanitized_error():
 from prmonitor.llm.process import execute
 from prmonitor.llm.base import Invocation
 r=execute(Invocation(['sh','-c','sleep 2']),timeout_seconds=.01,max_output_bytes=10)
 assert r.error == {'code':'TIMEOUT','retryable':True}

def test_missing_binary_is_structured_failure():
 from prmonitor.llm.process import execute
 from prmonitor.llm.base import Invocation
 r=execute(Invocation(['/definitely/missing/cli'],'x'),timeout_seconds=1,max_output_bytes=10)
 assert r.error['code'] == 'PROCESS_START_FAILED'

def test_response_parser_does_not_salvage_json_from_log_text():
 from prmonitor.llm.process import parse_json_response
 from prmonitor.llm.base import BackendResult
 value,error=parse_json_response(BackendResult(0,'log {"ok":true} trailing'))
 assert value is None and error['code'] == 'INVALID_JSON_RESPONSE'

def test_process_writes_stderr_for_timeout_and_redacts_diagnostic(tmp_path):
 from prmonitor.llm.process import execute
 r=execute(Invocation(['sh','-c','echo "API_KEY=topsecret" >&2; sleep 2']),timeout_seconds=.01,max_output_bytes=100,stderr_path=tmp_path/'err')
 assert r.error['code'] == 'TIMEOUT'
 assert 'topsecret' in (tmp_path/'err').read_text()  # raw artifact is retained for debugging

def test_probe_rejects_binary_with_broken_interpreter(monkeypatch):
 from prmonitor.llm import codex
 monkeypatch.setattr(codex.shutil, 'which', lambda _: '/tmp/not-a-real-interpreter')
 monkeypatch.setattr(codex, 'probe_command', lambda argv: (False, 'bad interpreter'))
 health=codex.CodexBackend().probe()
 assert not health.available and 'interpreter' in health.reason

def test_auth_and_unsupported_failures_are_permanent_and_redacted():
 from prmonitor.llm.process import execute
 auth=execute(Invocation(['sh','-c','echo "unauthorized API_KEY=topsecret" >&2; exit 2']),timeout_seconds=1,max_output_bytes=100)
 assert auth.error['code'] == 'AUTH_FAILED' and auth.error['retryable'] is False
 assert 'topsecret' not in auth.error['message']
 bad=execute(Invocation(['sh','-c','echo "unknown option --full-auto" >&2; exit 2']),timeout_seconds=1,max_output_bytes=100)
 assert bad.error['code'] == 'UNSUPPORTED_FLAG' and bad.error['retryable'] is False
