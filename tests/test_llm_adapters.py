import pytest
from prmonitor.llm.adapters import backend
def test_backend_selection_is_explicit():
 assert backend('codex').name == 'codex'
 assert backend('claude').__class__.__name__ == 'ClaudeBackend'
 with pytest.raises(ValueError): backend('unknown')

def test_generic_backend_execute_uses_bounded_process(tmp_path):
 from prmonitor.llm.generic import GenericBackend
 result=GenericBackend(['sh','-c','printf "{\\"ok\\":true}"']).execute({'prompt':'ignored'}, {'timeout_seconds':1,'max_output_bytes':100})
 assert result.process_rc == 0 and result.stdout_json_or_text.startswith('{')
