from prmonitor.models import RunSpec
from prmonitor.paths import resolve_paths
from prmonitor.storage.runs import RunStore
from prmonitor.services.engine import Engine

def test_engine_reject_result_records_only_target_job(tmp_path):
 ctx=resolve_paths(env={},cwd=tmp_path/'w',bundle=tmp_path/'b'); store=RunStore(ctx.state_dir); prepared=Engine(store).prepare(RunSpec('market','host',ctx.workspace_id,'2026-09-15','UTC','s','e',24))
 req=prepared.plan.jobs[0]; Engine(store).reject_result(req, {'code':'INVALID_JSON'})
 assert store.db.execute("SELECT state FROM jobs WHERE job_id=?",(req.job_id,)).fetchone()[0]=='failed'
 assert store.db.execute("SELECT COUNT(*) FROM job_attempts WHERE job_id=?",(req.job_id,)).fetchone()[0]==1
