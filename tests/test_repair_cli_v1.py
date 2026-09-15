import json
from prmonitor.__main__ import main

def test_repair_cli_replaces_pending_request_hash(capsys, tmp_path):
 workspace=tmp_path/'w'; assert main(['run','--pipeline','market','--workspace',str(workspace)]) == 0
 payload=json.loads(capsys.readouterr().out); job=payload['jobs'][0]; errors=tmp_path/'errors.json'; errors.write_text(json.dumps([{'code':'UNKNOWN_REF'}]))
 assert main(['repair','--state-dir',str(workspace/'.prmonitor'),'--run-id',payload['run_id'],'--job-id',job['job_id'],'--errors',str(errors)]) == 0
 repaired=json.loads(capsys.readouterr().out); assert repaired['request_hash'] != job['request_hash']
