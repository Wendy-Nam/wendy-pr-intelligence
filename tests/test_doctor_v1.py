from prmonitor.doctor import inspect_workspace
from prmonitor.models import RunSpec
from prmonitor.paths import resolve_paths
from prmonitor.storage.runs import RunStore
def test_doctor_reports_orphan_without_promoting_it(tmp_path):
 ctx=resolve_paths(env={},cwd=tmp_path/'w',bundle=tmp_path/'b'); run=RunStore(ctx.state_dir); record=run.create(RunSpec('market','host',ctx.workspace_id,'2026-09-15','Asia/Seoul','s','e',24),'a'*64)
 orphan=ctx.state_dir/'runs'/record.run_id/'x.json'; orphan.parent.mkdir(parents=True,exist_ok=True); orphan.write_text('{}')
 result=inspect_workspace(ctx.state_dir); assert not result['healthy'] and result['runs'][0]['orphans']
