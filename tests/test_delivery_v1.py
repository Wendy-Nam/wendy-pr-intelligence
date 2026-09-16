import pytest, hashlib
from prmonitor.delivery import LocalTransport, send_validated
from prmonitor.validation import validate_briefing
def test_local_transport_only_accepts_current_pass(tmp_path):
 b={'tldr':'ok','insights':[{'refs':['a_1']}],'category_summary':[{'category_id':'c'}]}; r=validate_briefing(b,article_ids={'a_1'},category_ids={'c'})
 digest=hashlib.sha256(b'html').hexdigest()
 receipt=send_validated(report=r,briefing=b,policy={},html=b'html',recipient='fixture@example.test',transport=LocalTransport(tmp_path),expected_html_hash=digest)
 assert receipt.status=='accepted'
 with pytest.raises(ValueError): send_validated(report=r,briefing=b,policy={},html=b'changed',recipient='x',transport=LocalTransport(tmp_path),expected_html_hash=digest)
def test_delivery_dedupe_key_is_stable():
 from prmonitor.delivery import dedupe_key
 assert dedupe_key('r','a','b') == dedupe_key('r','a','b') and dedupe_key('r','a','b') != dedupe_key('r','a','c')
def test_delivery_ledger_reserves_dedupe_once(tmp_path):
 from prmonitor.storage.database import connect
 from prmonitor.delivery import reserve_delivery
 db=connect(tmp_path/'s.sqlite3'); db.execute("INSERT INTO runs(run_id,spec_json,state,revision,config_hash,created_at,updated_at) VALUES('r','{}','READY',0,'h',datetime('now'),datetime('now'))"); db.commit(); assert reserve_delivery(db,delivery_id='d1',run_id='r',key='k',artifact_hash='a',recipient_hash='u'); assert not reserve_delivery(db,delivery_id='d2',run_id='r',key='k',artifact_hash='a',recipient_hash='u')
def test_delivery_receipt_transition_is_one_way(tmp_path):
 from prmonitor.storage.database import connect
 from prmonitor.delivery import reserve_delivery, update_delivery
 db=connect(tmp_path/'s.sqlite3'); db.execute("INSERT INTO runs(run_id,spec_json,state,revision,config_hash,created_at,updated_at) VALUES('r','{}','READY',0,'h',datetime('now'),datetime('now'))"); db.commit(); reserve_delivery(db,delivery_id='d',run_id='r',key='k',artifact_hash='a',recipient_hash='u'); assert update_delivery(db,'d','unknown'); assert not update_delivery(db,'d','accepted')

def test_transport_exception_becomes_unknown_without_retry(tmp_path):
 from prmonitor.storage.database import connect
 from prmonitor.delivery import send_reserved
 db=connect(tmp_path/'s.sqlite3'); db.execute("INSERT INTO runs(run_id,spec_json,state,revision,config_hash,created_at,updated_at) VALUES('r','{}','READY',0,'h',datetime('now'),datetime('now'))"); db.commit()
 class Lost:
  def send(self, **kwargs): raise TimeoutError('response lost')
 assert send_reserved(db,delivery_id='d',run_id='r',artifact=b'x',artifact_hash=hashlib.sha256(b'x').hexdigest(),recipient='u',transport=Lost(),key='k') is None
 assert db.execute("SELECT status FROM deliveries WHERE delivery_id='d'").fetchone()[0] == 'unknown'
