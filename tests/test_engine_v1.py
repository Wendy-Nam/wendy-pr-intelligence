from prmonitor.models import RunSpec
from prmonitor.paths import resolve_paths
from prmonitor.storage.runs import RunStore
from prmonitor.services.engine import Engine

def test_engine_prepare_and_accept_result_are_scoped(tmp_path):
 ctx=resolve_paths(env={},cwd=tmp_path/'w',bundle=tmp_path/'b')
 store=RunStore(ctx.state_dir); engine=Engine(store)
 spec=RunSpec('market','host',ctx.workspace_id,'2026-09-15','UTC','s','e',24)
 prepared=engine.prepare(spec)
 req=prepared.plan.jobs[0]
 attempt=engine.accept_result(req, {'run_id':req.run_id,
                                    'job_id':req.job_id,'request_hash':req.request_hash,'result':{'tldr':'x'}}, result_hash='h')
 assert prepared.record.state.value == 'PREPARED' and attempt['result_hash']=='h'

def test_engine_validation_holds_bad_briefing_and_never_ready(tmp_path):
 ctx=resolve_paths(env={},cwd=tmp_path/'w',bundle=tmp_path/'b'); store=RunStore(ctx.state_dir); engine=Engine(store)
 prepared=engine.prepare(RunSpec('market','host',ctx.workspace_id,'2026-09-15','UTC','s','e',24))
 report=engine.validate(prepared, {'tldr':'','insights':[],'category_summary':[]}, article_ids=set(), category_ids=set())
 assert report.status == 'HELD' and store.get(prepared.record.run_id).state.value == 'HELD'

def test_legacy_wrapper_routes_through_engine_ledger(tmp_path, monkeypatch):
 """Legacy market/self entry points record jobs+attempts through the canonical engine."""
 from prmonitor.services.engine import open_legacy_run, close_legacy_run
 from prmonitor.storage.runs import RunStore
 from prmonitor.paths import resolve_paths
 monkeypatch.setenv('PRM_PROJECT_DIR', str(tmp_path/'w'))
 opened=open_legacy_run('market', date='2026-09-15', hours=24)
 engine, prepared = opened
 close_legacy_run(opened, succeeded=True, result={'date':'2026-09-15'})
 store=RunStore(resolve_paths(cwd=tmp_path/'w').state_dir)
 assert store.pending_jobs(prepared.record.run_id) == []
 assert store.db.execute("SELECT state FROM job_attempts WHERE run_id=?", (prepared.record.run_id,)).fetchone()['state']=='succeeded'
