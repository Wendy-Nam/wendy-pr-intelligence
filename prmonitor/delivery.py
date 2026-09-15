"""Delivery ledger boundary with a local fixture transport."""
from __future__ import annotations
import hashlib, json, uuid
from dataclasses import dataclass
from pathlib import Path
from .validation import ValidationReport, deliverable_is_current
@dataclass(frozen=True)
class DeliveryReceipt:
    delivery_id: str; status: str; artifact_hash: str; recipient_hash: str
class LocalTransport:
    def __init__(self, root: Path): self.root=root
    def send(self, *, artifact: bytes, recipient: str) -> DeliveryReceipt:
        digest=hashlib.sha256(artifact).hexdigest(); rh=hashlib.sha256(recipient.encode()).hexdigest(); did=uuid.uuid4().hex
        path=self.root/f'{did}.html'; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(artifact)
        return DeliveryReceipt(did,'accepted',digest,rh)
def dedupe_key(run_id: str, artifact_hash: str, recipient_hash: str) -> str:
    return hashlib.sha256('|'.join((run_id,artifact_hash,recipient_hash)).encode()).hexdigest()
def reserve_delivery(db, *, delivery_id: str, run_id: str, key: str, artifact_hash: str, recipient_hash: str) -> bool:
 """Reserve once; duplicate dedupe keys are rejected before transport."""
 try:
  db.execute("INSERT INTO deliveries(delivery_id,run_id,dedupe_key,status,message_id,attempt,artifact_hash,recipient_hash,updated_at) VALUES(?,?,?,?,?,?,?,?,datetime('now'))",(delivery_id,run_id,key,'sending','',1,artifact_hash,recipient_hash)); db.commit(); return True
 except Exception:
  db.rollback(); return False
def update_delivery(db, delivery_id: str, status: str, *, message_id: str='', receipt: dict | None = None) -> bool:
 if status not in {'accepted','failed','unknown'}: raise ValueError('INVALID_DELIVERY_STATUS')
 cur=db.execute("UPDATE deliveries SET status=?,message_id=?,receipt_json=?,updated_at=datetime('now') WHERE delivery_id=? AND status='sending'",(status,message_id,json.dumps(receipt,ensure_ascii=False,sort_keys=True) if receipt is not None else None,delivery_id)); db.commit(); return cur.rowcount==1

def send_reserved(db, *, delivery_id: str, run_id: str, artifact: bytes, artifact_hash: str,
                  recipient: str, transport, key: str) -> DeliveryReceipt | None:
    """Reserve and call a transport exactly once; ambiguous exceptions become UNKNOWN."""
    recipient_hash = hashlib.sha256(recipient.encode()).hexdigest()
    if not reserve_delivery(db, delivery_id=delivery_id, run_id=run_id, key=key,
                            artifact_hash=artifact_hash, recipient_hash=recipient_hash):
        return None
    try:
        receipt = transport.send(artifact=artifact, recipient=recipient)
    except Exception as exc:
        update_delivery(db, delivery_id, 'unknown', receipt={'error': type(exc).__name__})
        return None
    update_delivery(db, delivery_id, receipt.status, message_id=receipt.delivery_id,
                    receipt={'status': receipt.status, 'artifact_hash': receipt.artifact_hash})
    return receipt
def send_validated(*, report: ValidationReport, briefing: dict, policy: dict, html: bytes, recipient: str, transport: LocalTransport, expected_html_hash: str, example_mode: bool=False) -> DeliveryReceipt:
    if example_mode or not deliverable_is_current(report,briefing=briefing,policy=policy,html_bytes=html,expected_html_hash=expected_html_hash): raise ValueError('DELIVERY_GATE_REJECTED')
    return transport.send(artifact=html,recipient=recipient)
