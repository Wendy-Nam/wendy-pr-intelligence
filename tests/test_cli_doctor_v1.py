from prmonitor.__main__ import main

def test_doctor_strict_returns_nonzero_for_orphan(capsys, tmp_path):
 state=tmp_path/'.state'
 from prmonitor.storage.runs import RunStore
 from prmonitor.models import RunSpec
 store=RunStore(state); rec=store.create(RunSpec('market','host','w','2026-09-15','UTC','s','e',24),'h')
 (state/'runs'/rec.run_id).mkdir(parents=True); (state/'runs'/rec.run_id/'orphan.json').write_text('{}')
 assert main(['doctor','--state-dir',str(state),'--strict']) == 1
 assert 'healthy' in capsys.readouterr().out
