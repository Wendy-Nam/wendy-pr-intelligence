import json
from prmonitor.__main__ import main

def test_ingest_cli_rejects_mismatched_envelope(capsys, tmp_path):
 workspace=tmp_path/'w'; assert main(['run','--pipeline','market','--workspace',str(workspace)]) == 0
 payload=json.loads(capsys.readouterr().out); job=payload['jobs'][0]
 result=tmp_path/'result.json'; result.write_text(json.dumps({'run_id':'wrong','job_id':job['job_id'],'request_hash':job['request_hash'],'result':{}}))
 assert main(['ingest','--state-dir',str(workspace/'.prmonitor'),'--run-id',payload['run_id'],'--job-id',job['job_id'],'--result',str(result)]) == 2
 assert json.loads(capsys.readouterr().out)['error']['code']=='INGEST_REJECTED'

def test_ingest_cli_rejects_replacement_of_completed_result(capsys, tmp_path):
 workspace=tmp_path/'w'; assert main(['run','--pipeline','market','--workspace',str(workspace)]) == 0
 payload=json.loads(capsys.readouterr().out); job=payload['jobs'][0]
 result=tmp_path/'result.json'; result.write_text(json.dumps({'run_id':payload['run_id'],'job_id':job['job_id'],'request_hash':job['request_hash'],'result':{'v':1}}))
 args=['ingest','--state-dir',str(workspace/'.prmonitor'),'--run-id',payload['run_id'],'--job-id',job['job_id'],'--result',str(result)]
 assert main(args) == 0; capsys.readouterr()
 result.write_text(json.dumps({'run_id':payload['run_id'],'job_id':job['job_id'],'request_hash':job['request_hash'],'result':{'v':2}}))
 assert main(args) == 2
 assert json.loads(capsys.readouterr().out)['error']['message'] == 'JOB_NOT_ACCEPTING_RESULTS'

def test_ingest_cli_rejects_stale_request_after_repair(capsys, tmp_path):
 workspace=tmp_path/'w'; assert main(['run','--pipeline','market','--workspace',str(workspace)]) == 0
 payload=json.loads(capsys.readouterr().out); job=payload['jobs'][0]; errors=tmp_path/'errors.json'; errors.write_text('[]')
 assert main(['repair','--state-dir',str(workspace/'.prmonitor'),'--run-id',payload['run_id'],'--job-id',job['job_id'],'--errors',str(errors)]) == 0; capsys.readouterr()
 result=tmp_path/'result.json'; result.write_text(json.dumps({'run_id':payload['run_id'],'job_id':job['job_id'],'request_hash':job['request_hash'],'result':{}}))
 assert main(['ingest','--state-dir',str(workspace/'.prmonitor'),'--run-id',payload['run_id'],'--job-id',job['job_id'],'--result',str(result)]) == 2
 assert json.loads(capsys.readouterr().out)['error']['message'] == 'REQUEST_HASH_MISMATCH'
