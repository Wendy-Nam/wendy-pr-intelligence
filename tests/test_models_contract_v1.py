from prmonitor.models import RunSpec

def test_runspec_validation_catches_contract_errors_without_breaking_decode():
 spec=RunSpec('market','host','w','2026-09-15','Not/AZone','s','e',0,backend='codex')
 assert {'HOURS','TIMEZONE','WINDOW_FORMAT','HOST_BACKEND'} <= set(spec.validation_errors())
