from __future__ import annotations
import shutil
from .base import BackendHealth, Invocation
from .process import probe_command, execute
class ClaudeBackend:
 def probe(self,live=False):
  path=shutil.which('claude')
  if not path:
   return BackendHealth(False,'claude executable not found',False)
  ok, reason = probe_command([path, '--help'])
  return BackendHealth(ok, reason, True)
 def build_invocation(self,request,options):
  argv=['claude','-p','-']
  if options.get('model'): argv += ['--model',options['model']]
  return Invocation(argv,request['prompt'],options.get('cwd'),{})
 def execute(self, request, options=None, deadline=None):
  options = options or {}; inv = self.build_invocation(request, options)
  return execute(inv, timeout_seconds=options.get('timeout_seconds', deadline or 180),
                 max_output_bytes=options.get('max_output_bytes', 1000000), stderr_path=options.get('stderr_path'))
