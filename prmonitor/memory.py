"""Provenance-aware self-context candidates; no automatic promotion of HELD data."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
def event_hash(*, source_id: str, event_type: str, observation: str, source_date: str) -> str:
 return hashlib.sha256('\0'.join((source_id,event_type,observation.strip(),source_date)).encode()).hexdigest()
def append_candidate(root: Path, *, run_id: str, source_id: str, observation: str, source_date: str, kind: str='interpretation') -> Path:
 digest=event_hash(source_id=source_id,event_type=kind,observation=observation,source_date=source_date)
 path=root/'candidates'/f'{digest}.json'; path.parent.mkdir(parents=True,exist_ok=True)
 if not path.exists(): path.write_text(json.dumps({'event_hash':digest,'run_id':run_id,'source_id':source_id,'observation':observation,'source_date':source_date,'kind':kind,'status':'candidate'},ensure_ascii=False,indent=2),encoding='utf-8')
 return path

def promote_candidate(path: Path, *, run_state: str, refs_valid: bool) -> Path:
 if run_state != 'READY' or not refs_valid: raise ValueError('MEMORY_PROMOTION_GATE_REJECTED')
 data=json.loads(path.read_text(encoding='utf-8')); data['status']='accepted'; target=path.parent.parent/'observations'/path.name; target.parent.mkdir(parents=True,exist_ok=True); target.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8'); return target

def append_event(db, *, run_id: str, source_id: str, event_type: str,
                 observation: str, source_date: str, payload: dict | None = None) -> str:
    """Append a provenance event once; duplicate observations are no-ops."""
    event_id = event_hash(source_id=source_id, event_type=event_type,
                          observation=observation, source_date=source_date)
    content_hash = event_id
    data = payload or {'source_id': source_id, 'observation': observation, 'source_date': source_date}
    db.execute("INSERT OR IGNORE INTO memory_events(event_id,run_id,content_hash,kind,status,payload_json) VALUES(?,?,?,?,?,?)",
               (event_id, run_id, content_hash, event_type, 'candidate', json.dumps(data, ensure_ascii=False, sort_keys=True)))
    db.commit()
    return event_id

def promote_event(db, event_id: str, *, run_state: str, refs_valid: bool) -> bool:
    if run_state != 'READY' or not refs_valid:
        raise ValueError('MEMORY_PROMOTION_GATE_REJECTED')
    cur = db.execute("UPDATE memory_events SET status='accepted', applied_at=datetime('now') WHERE event_id=? AND status='candidate'", (event_id,))
    db.commit()
    return cur.rowcount == 1
