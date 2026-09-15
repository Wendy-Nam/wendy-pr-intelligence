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
 (tmp_path/'policy.json').write_text('{}')
 assert main(['validate','--state-dir',str(workspace/'.prmonitor'),'--run-id',payload['run_id'],'--briefing',str(b),'--article-ids','a_1','--category-ids','c','--policy',str(tmp_path/'policy.json')]) == 0
 capsys.readouterr(); v.write_text((tmp_path/'b.json.validation.json').read_text())
 rc=main(['send','--state-dir',str(workspace/'.prmonitor'),'--run-id',payload['run_id'],'--briefing',str(b),'--html',str(h),'--validation',str(v),'--recipient','fixture@example.test','--fixture-dir',str(tmp_path/'fixture')])
 assert rc == 0 and json.loads(capsys.readouterr().out)['status']=='accepted'
