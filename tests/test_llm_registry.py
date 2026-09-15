def test_model_resolution_precedence(monkeypatch):
 from prmonitor.llm.registry import resolve_model
 monkeypatch.setenv('PRM_SYNTHESIS_MODEL','env-model')
 assert resolve_model('synthesis',explicit='cli-model',config={'llm':{'models':{'synthesis':'cfg'}}}) == 'cli-model'
 assert resolve_model('synthesis',config={'llm':{'models':{'synthesis':'cfg'}}}) == 'env-model'
def test_host_mode_never_selects_headless_backend():
 from prmonitor.llm.registry import resolve_backend
 assert resolve_backend(mode='host',requested='codex',config={'llm':{'backend':'hermes'}}) is None
