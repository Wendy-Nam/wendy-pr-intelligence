import json, hashlib
from prmonitor.__main__ import main

def test_send_cli_rejects_non_ready_run(capsys, tmp_path):
 workspace=tmp_path/'w'; assert main(['run','--pipeline','market','--workspace',str(workspace)]) == 0
 payload=json.loads(capsys.readouterr().out); b=tmp_path/'b.json'; h=tmp_path/'h.html'; v=tmp_path/'v.json'
 b.write_text(json.dumps({'tldr':'ok','insights':[{'refs':['a_1']}],'category_summary':[{'category_id':'c'}]})); h.write_text('<p>x</p>')
 v.write_text(json.dumps({'status':'PASS','findings':[],'briefing_hash':'x','policy_hash':'y','required_jobs':{},'coverage':{}}))
 rc=main(['send','--state-dir',str(workspace/'.prmonitor'),'--run-id',payload['run_id'],'--briefing',str(b),'--html',str(h),'--validation',str(v),'--recipient','fixture@example.test','--fixture-dir',str(tmp_path/'fixture')])
 assert rc == 21 and json.loads(capsys.readouterr().out)['error']['code']=='DELIVERY_STATE_REJECTED'

def test_send_cli_uses_fixture_transport_after_ready(tmp_path, capsys):
 workspace=tmp_path/'w'; assert main(['run','--pipeline','market','--workspace',str(workspace)]) == 0
 payload=json.loads(capsys.readouterr().out); b=tmp_path/'b.json'; h=tmp_path/'h.html'; v=tmp_path/'v.json'
 briefing={'tldr':'ok','insights':[{'refs':['a_1']}],'category_summary':[{'category_id':'c'}]}; b.write_text(json.dumps(briefing)); h.write_text('<p>x</p>')
 result=tmp_path/'result.json'; job=payload['jobs'][0]
 result.write_text(json.dumps({'run_id':payload['run_id'],'job_id':job['job_id'],'request_hash':job['request_hash'],'result':{}}))
 assert main(['ingest','--state-dir',str(workspace/'.prmonitor'),'--run-id',payload['run_id'],'--job-id',job['job_id'],'--result',str(result)]) == 0
 capsys.readouterr()
 (tmp_path/'policy.json').write_text(json.dumps({'required_refs':['a_1']}))
 assert main(['validate','--state-dir',str(workspace/'.prmonitor'),'--run-id',payload['run_id'],'--briefing',str(b),'--article-ids','a_1','--category-ids','c','--policy',str(tmp_path/'policy.json')]) == 0
 capsys.readouterr(); v.write_text((tmp_path/'b.json.validation.json').read_text())
 rc=main(['send','--state-dir',str(workspace/'.prmonitor'),'--run-id',payload['run_id'],'--briefing',str(b),'--html',str(h),'--validation',str(v),'--policy',str(tmp_path/'policy.json'),'--recipient','fixture@example.test','--fixture-dir',str(tmp_path/'fixture')])
 assert rc == 0 and json.loads(capsys.readouterr().out)['status']=='accepted'
 assert main(['send','--state-dir',str(workspace/'.prmonitor'),'--run-id',payload['run_id'],'--briefing',str(b),'--html',str(h),'--validation',str(v),'--policy',str(tmp_path/'policy.json'),'--recipient','fixture@example.test','--fixture-dir',str(tmp_path/'fixture')]) == 21
 assert len(list((tmp_path/'fixture').glob('*.html'))) == 1

def test_validate_holds_until_required_job_is_ingested(tmp_path, capsys):
 workspace=tmp_path/'w'; assert main(['run','--pipeline','market','--workspace',str(workspace)]) == 0
 payload=json.loads(capsys.readouterr().out); b=tmp_path/'b.json'; b.write_text(json.dumps({'tldr':'ok','insights':[{'refs':[]}],'category_summary':[]}))
 assert main(['validate','--state-dir',str(workspace/'.prmonitor'),'--run-id',payload['run_id'],'--briefing',str(b)]) == 21
 report=json.loads(capsys.readouterr().out)
 assert report['status'] == 'HELD'
 assert any(f['code'] == 'REQUIRED_JOBS_PENDING' for f in report['findings'])

def test_validate_recovers_held_run_after_required_job_is_ingested(tmp_path, capsys):
 workspace=tmp_path/'w'; assert main(['run','--pipeline','market','--workspace',str(workspace)]) == 0
 payload=json.loads(capsys.readouterr().out); b=tmp_path/'b.json'; b.write_text(json.dumps({'tldr':'ok','insights':[{'refs':[]}],'category_summary':[]}))
 validate=['validate','--state-dir',str(workspace/'.prmonitor'),'--run-id',payload['run_id'],'--briefing',str(b)]
 assert main(validate) == 21; capsys.readouterr()
 job=payload['jobs'][0]; result=tmp_path/'result.json'
 result.write_text(json.dumps({'run_id':payload['run_id'],'job_id':job['job_id'],'request_hash':job['request_hash'],'result':{}}))
 assert main(['ingest','--state-dir',str(workspace/'.prmonitor'),'--run-id',payload['run_id'],'--job-id',job['job_id'],'--result',str(result)]) == 0; capsys.readouterr()
 assert main(validate) == 0
 assert json.loads(capsys.readouterr().out)['status'] == 'PASS'
