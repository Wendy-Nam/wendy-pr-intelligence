import json
from prmonitor.__main__ import main

def test_memory_promote_cli_rejects_created_run(capsys, tmp_path):
 workspace=tmp_path/'w'; assert main(['run','--pipeline','market','--workspace',str(workspace)]) == 0
 payload=json.loads(capsys.readouterr().out)
 rc=main(['memory-promote','--state-dir',str(workspace/'.prmonitor'),'--run-id',payload['run_id'],'--event-id','x','--refs-valid'])
 assert rc == 21 and json.loads(capsys.readouterr().out)['error']['code']=='MEMORY_PROMOTION_GATE_REJECTED'
