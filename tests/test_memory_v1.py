from prmonitor.memory import append_candidate
def test_memory_candidate_is_idempotent(tmp_path):
 a=append_candidate(tmp_path,run_id='r',source_id='a_1',observation='obs',source_date='2026-09-15')
 b=append_candidate(tmp_path,run_id='r2',source_id='a_1',observation='obs',source_date='2026-09-15')
 assert a==b and 'candidate' in a.read_text()
def test_held_candidate_cannot_promote(tmp_path):
 from prmonitor.memory import promote_candidate
 a=append_candidate(tmp_path,run_id='r',source_id='a',observation='x',source_date='d')
 import pytest
 with pytest.raises(ValueError): promote_candidate(a,run_state='HELD',refs_valid=True)

def test_memory_event_ledger_is_idempotent_and_promotes_once(tmp_path):
 from prmonitor.storage.database import connect
 from prmonitor.memory import append_event, promote_event
 db=connect(tmp_path/'s.sqlite3')
 db.execute("INSERT INTO runs(run_id,spec_json,state,revision,config_hash,created_at,updated_at) VALUES('r','{}','READY',0,'h',datetime('now'),datetime('now'))")
 db.commit()
 one=append_event(db,run_id='r',source_id='a',event_type='observation',observation='x',source_date='d')
 two=append_event(db,run_id='r2',source_id='a',event_type='observation',observation='x',source_date='d')
 assert one == two and db.execute('SELECT COUNT(*) FROM memory_events').fetchone()[0] == 1
 assert promote_event(db,one,run_state='READY',refs_valid=True)
 assert not promote_event(db,one,run_state='READY',refs_valid=True)
