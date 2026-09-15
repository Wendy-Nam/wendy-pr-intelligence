import json
from prmonitor.__main__ import main

def test_validate_cli_holds_empty_briefing(capsys, tmp_path):
 workspace=tmp_path/'w'; assert main(['run','--pipeline','market','--workspace',str(workspace)]) == 0
 payload=json.loads(capsys.readouterr().out)
 briefing=tmp_path/'briefing.json'; briefing.write_text(json.dumps({'tldr':'','insights':[],'category_summary':[]}))
 rc=main(['validate','--state-dir',str(workspace/'.prmonitor'),'--run-id',payload['run_id'],'--briefing',str(briefing)])
 assert rc == 21 and json.loads(capsys.readouterr().out)['status']=='HELD'
 assert (tmp_path/'briefing.json.validation.json').exists()
