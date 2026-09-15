from prmonitor.models import RunSpec
from prmonitor.paths import resolve_paths
from prmonitor.storage.runs import RunStore
from prmonitor.services.offline import run_fixture

def test_offline_fixture_runs_prepare_validate_render_send(tmp_path):
 ctx=resolve_paths(env={},cwd=tmp_path/'w',bundle=tmp_path/'b'); store=RunStore(ctx.state_dir)
 result=run_fixture(store,RunSpec('market','headless',ctx.workspace_id,'2026-09-15','UTC','s','e',24),root=tmp_path)
 assert result.status == 'PASS' and result.delivery_id and result.html.exists()
