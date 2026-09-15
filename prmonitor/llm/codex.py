from __future__ import annotations
import shutil
from .base import BackendHealth, Invocation
from .process import probe_command, execute
class CodexBackend:
 name='codex'
 def probe(self,live=False):
  path=shutil.which('codex')
  if not path:
   return BackendHealth(False,'codex executable not found',False)
  ok, reason = probe_command([path, '--help'])
  return BackendHealth(ok, reason, True)
 def build_invocation(self,request,options):
  argv=['codex','exec']
  model=options.get('model')
  if model: argv += ['--model',model]
  # stdin makes prompt quoting and non-ASCII transport unambiguous.
  return Invocation(argv,request['prompt'],options.get('cwd'),{})
 def execute(self, request, options=None, deadline=None):
  options = options or {}; inv = self.build_invocation(request, options)
  return execute(inv, timeout_seconds=options.get('timeout_seconds', deadline or 180),
                 max_output_bytes=options.get('max_output_bytes', 1000000), stderr_path=options.get('stderr_path'))
