from __future__ import annotations
import hashlib
def schedule_key(scheduler_id: str, scheduled_at: str, pipeline: str) -> str:
 return hashlib.sha256('|'.join((scheduler_id,scheduled_at,pipeline)).encode()).hexdigest()[:32]
