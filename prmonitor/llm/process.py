from __future__ import annotations
import os, signal, subprocess, time, re
import json
from .base import Invocation, BackendResult

_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|password|secret)(\s*[=:]\s*)([^\s,;]+)"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+"),
)

def redact(text: str) -> str:
    """Redact common credential forms before putting process output in diagnostics."""
    for pattern in _SECRET_PATTERNS:
        if pattern.groups:
            text = pattern.sub(lambda m: m.group(1) + m.group(2) + "[REDACTED]", text)
        else:
            text = pattern.sub("Bearer [REDACTED]", text)
    return text

def _process_failure(returncode: int, stderr: bytes) -> dict:
    detail = redact(stderr.decode(errors='replace')).strip()
    lowered = detail.lower()
    if any(marker in lowered for marker in ('unauthorized', 'authentication', 'invalid api key', 'not logged in')):
        code, retryable = 'AUTH_FAILED', False
    elif any(marker in lowered for marker in ('unknown option', 'unrecognized option', 'unsupported flag', 'invalid flag')):
        code, retryable = 'UNSUPPORTED_FLAG', False
    else:
        code, retryable = 'PROCESS_FAILED', True
    result = {'code': code, 'retryable': retryable, 'returncode': returncode}
    if detail:
        result['message'] = detail[-2000:]
    return result

def parse_json_response(result: BackendResult) -> tuple[dict | list | None, dict | None]:
 """Parse the complete stdout only; never trim from first/last braces."""
 if result.error: return None, result.error
 try: return json.loads(result.stdout_json_or_text), None
 except json.JSONDecodeError: return None, {'code':'INVALID_JSON_RESPONSE','retryable':False}

def execute(invocation: Invocation, *, timeout_seconds: float, max_output_bytes: int, stderr_path=None) -> BackendResult:
 start=time.monotonic(); kwargs={'stdin':subprocess.PIPE,'stdout':subprocess.PIPE,'stderr':subprocess.PIPE,'text':False,'cwd':invocation.cwd,'env':{**os.environ,**invocation.env_delta}}
 if os.name != 'nt': kwargs['start_new_session']=True
 try:
  proc=subprocess.Popen(invocation.argv,**kwargs)
 except OSError as exc:
  return BackendResult(None,error={'code':'PROCESS_START_FAILED','retryable':False,'message':redact(str(exc))},duration_ms=int((time.monotonic()-start)*1000))
 try:
  out,err=proc.communicate(invocation.stdin.encode(),timeout=timeout_seconds)
 except subprocess.TimeoutExpired:
  if os.name != 'nt': os.killpg(proc.pid,signal.SIGTERM)
  else: proc.terminate()
  try: out,err=proc.communicate(timeout=3)
  except subprocess.TimeoutExpired:
   if os.name != 'nt': os.killpg(proc.pid,signal.SIGKILL)
   else: proc.kill()
   out,err=proc.communicate()
  if stderr_path:
   stderr_path.write_bytes(err)
  return BackendResult(None,error={'code':'TIMEOUT','retryable':True},stderr_path=stderr_path,duration_ms=int((time.monotonic()-start)*1000))
 if len(out)>max_output_bytes:
  if stderr_path:
   stderr_path.write_bytes(err)
  return BackendResult(proc.returncode,error={'code':'OUTPUT_TOO_LARGE','retryable':False},stderr_path=stderr_path,duration_ms=int((time.monotonic()-start)*1000))
 if stderr_path: stderr_path.write_bytes(err)
 error = _process_failure(proc.returncode, err) if proc.returncode else None
 return BackendResult(proc.returncode,out.decode(errors='replace'),stderr_path,duration_ms=int((time.monotonic()-start)*1000),error=error)

def probe_command(argv: list[str], *, timeout_seconds: float = 3.0) -> tuple[bool, str]:
 """Run a non-authenticated help probe and return a redacted diagnostic."""
 try:
  completed = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             timeout=timeout_seconds, check=False)
 except (OSError, subprocess.TimeoutExpired) as exc:
  return False, redact(str(exc))
 if completed.returncode != 0:
  detail = (completed.stderr or completed.stdout).decode(errors='replace').strip()
  return False, redact(detail) or f"help exited {completed.returncode}"
 return True, ""
