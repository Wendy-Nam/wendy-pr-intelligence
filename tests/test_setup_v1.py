from prmonitor.services.setup import environment_fingerprint, inspect_runtime, write_ready_marker

def test_runtime_marker_detects_requirements_change(tmp_path):
 req=tmp_path/'requirements.txt'; req.write_text('a==1\n')
 state=tmp_path/'.state'; write_ready_marker(state, requirements=req)
 assert inspect_runtime(state, requirements=req)['ready']
 req.write_text('a==2\n')
 assert not inspect_runtime(state, requirements=req)['ready']
