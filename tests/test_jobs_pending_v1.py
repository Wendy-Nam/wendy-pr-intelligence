import json
from prmonitor.__main__ import main

def test_jobs_cli_returns_persisted_request_payload(capsys, tmp_path):
 workspace=tmp_path/'w'; assert main(['run','--pipeline','market','--workspace',str(workspace)]) == 0
 payload=json.loads(capsys.readouterr().out)
 result=json.loads(__import__('subprocess').check_output(['.venv/bin/python','-m','prmonitor','jobs','--state-dir',str(workspace/'.prmonitor'),'--run-id',payload['run_id']], text=True))
 assert result['jobs'][0]['request']['kind']=='market_brief'

def test_resume_after_restart_recovers_plan_and_ingests_result(capsys, tmp_path):
 """A restarted process must recover planned jobs and finish result ingestion."""
 from prmonitor.paths import resolve_paths
 from prmonitor.storage.runs import RunStore
 from prmonitor.services.engine import Engine
 workspace=tmp_path/'w2'; assert main(['run','--pipeline','market','--workspace',str(workspace)]) == 0
 payload=json.loads(capsys.readouterr().out); run_id=payload['run_id']
 state_dir=resolve_paths(env={},cwd=workspace,bundle=tmp_path/'b').state_dir
 engine=Engine(RunStore(state_dir))  # fresh store == fresh process
 resumed=engine.resume(run_id)
 assert resumed.record.state.value=='PREPARED'
 assert [j.request_hash for j in resumed.plan.jobs]==[j['request_hash'] for j in payload['jobs']]
 req=resumed.plan.jobs[0]
 engine.accept_result(req,{'run_id':run_id,'job_id':req.job_id,'request_hash':req.request_hash,'result':{'tldr':'x'}},result_hash='h')
 assert Engine(RunStore(state_dir)).resume(run_id).plan.jobs == ()
