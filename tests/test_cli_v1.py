import json
from prmonitor.__main__ import main

def test_canonical_run_cli_emits_single_json(capsys, tmp_path):
 assert main(['run','--pipeline','market','--mode','host','--workspace',str(tmp_path),'--hours','2','--json']) == 0
 payload=json.loads(capsys.readouterr().out)
 assert payload['spec']['pipeline']=='market' and payload['state']=='PREPARED' and payload['jobs']

def test_run_dry_run_does_not_create_state(capsys, tmp_path):
 assert main(['run','--pipeline','self','--workspace',str(tmp_path),'--dry-run','--no-email','--llm','off']) == 0
 payload=json.loads(capsys.readouterr().out)
 assert payload['dry_run'] and payload['spec']['delivery_requested'] is False
 assert not (tmp_path/'.prmonitor').exists()

def _prepared(tmp_path, capsys):
 assert main(['run','--pipeline','market','--workspace',str(tmp_path),'--hours','2']) == 0
 return json.loads(capsys.readouterr().out)['run_id'], str(tmp_path/'.prmonitor')

def test_status_resume_cancel_lifecycle(capsys, tmp_path):
 run_id, state_dir = _prepared(tmp_path, capsys)
 assert main(['status','--state-dir',state_dir,'--run-id',run_id]) == 0
 status=json.loads(capsys.readouterr().out)
 assert status['state']=='PREPARED' and status['pending_jobs']
 assert main(['resume','--state-dir',state_dir,'--run-id',run_id]) == 0
 resumed=json.loads(capsys.readouterr().out)
 assert resumed['jobs'] and resumed['next_actions']
 assert main(['cancel','--state-dir',state_dir,'--run-id',run_id]) == 0
 assert json.loads(capsys.readouterr().out)['state']=='CANCELLED'
 assert main(['cancel','--state-dir',state_dir,'--run-id',run_id]) == 21
 assert json.loads(capsys.readouterr().out)['error']['code']=='RUN_NOT_CANCELLABLE'
 assert main(['resume','--state-dir',state_dir,'--run-id',run_id]) == 21
 assert json.loads(capsys.readouterr().out)['error']['code']=='RUN_NOT_RESUMABLE'

def test_runs_lists_created_run(capsys, tmp_path):
 run_id, state_dir = _prepared(tmp_path, capsys)
 assert main(['runs','--state-dir',state_dir]) == 0
 assert [r['run_id'] for r in json.loads(capsys.readouterr().out)['runs']] == [run_id]

def test_unknown_run_id_is_structured_error(capsys, tmp_path):
 _rid, state_dir = _prepared(tmp_path, capsys)
 assert main(['status','--state-dir',state_dir,'--run-id','nope']) == 2
 assert json.loads(capsys.readouterr().out)['error']['code']=='RUN_NOT_FOUND'

def test_legacy_positional_hours_rejected_as_date(capsys):
 assert main(['pre','24']) == 2
 assert 'YYYY-MM-DD' in capsys.readouterr().err
