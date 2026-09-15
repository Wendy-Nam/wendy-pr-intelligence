import json
from prmonitor.__main__ import main

def test_render_cli_requires_allow_held(capsys, tmp_path):
 b=tmp_path/'b.json'; v=tmp_path/'v.json'; out=tmp_path/'out.html'
 b.write_text(json.dumps({'tldr':'x','insights':[],'category_summary':[]})); v.write_text(json.dumps({'status':'HELD','findings':[{'code':'EMPTY','severity':'error','path':'/','message':'bad','refs':[]}],'briefing_hash':'x','policy_hash':'y','required_jobs':{},'coverage':{}}))
 assert main(['render','--briefing',str(b),'--validation',str(v),'--output',str(out)]) == 21
 assert main(['render','--briefing',str(b),'--validation',str(v),'--output',str(out),'--allow-held']) == 0
 assert 'REVIEW NEEDED' in out.read_text()
