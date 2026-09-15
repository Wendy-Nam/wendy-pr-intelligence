from __future__ import annotations
import json, shlex
from .base import BackendHealth, Invocation
from .process import execute
class GenericBackend:
 def __init__(self, template): self.template=template
 def probe(self,live=False):
  try: argv=self._argv(''); return BackendHealth(bool(argv),'' if argv else 'empty command')
  except ValueError as e: return BackendHealth(False,str(e),False)
 def _argv(self,prompt):
  if isinstance(self.template,list): return [str(x).replace('{prompt}',prompt) for x in self.template]
  parts=shlex.split(self.template)
  return [p.replace('{prompt}',prompt) for p in parts]
 def build_invocation(self,request,options): return Invocation(self._argv(request['prompt']), '', options.get('cwd'), {})
 def execute(self, request, options=None, deadline=None):
  options = options or {}; inv = self.build_invocation(request, options)
  return execute(inv, timeout_seconds=options.get('timeout_seconds', deadline or 180),
                 max_output_bytes=options.get('max_output_bytes', 1000000), stderr_path=options.get('stderr_path'))
