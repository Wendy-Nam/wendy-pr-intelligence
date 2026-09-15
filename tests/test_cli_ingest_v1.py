import json
from prmonitor.__main__ import main

def test_ingest_cli_rejects_mismatched_envelope(capsys, tmp_path):
 workspace=tmp_path/'w'; assert main(['run','--pipeline','market','--workspace',str(workspace)]) == 0
 payload=json.loads(capsys.readouterr().out); job=payload['jobs'][0]
 result=tmp_path/'result.json'; result.write_text(json.dumps({'run_id':'wrong','job_id':job['job_id'],'request_hash':job['request_hash'],'result':{}}))
 assert main(['ingest','--state-dir',str(workspace/'.prmonitor'),'--run-id',payload['run_id'],'--job-id',job['job_id'],'--result',str(result)]) == 2
 assert json.loads(capsys.readouterr().out)['error']['code']=='INGEST_REJECTED'
