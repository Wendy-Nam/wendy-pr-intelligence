from __future__ import annotations
import json, secrets, sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from ..errors import ConflictError
from ..models import RunRecord, RunSpec, RunState, RUN_ID_RE, canonical_json_bytes
from .database import connect

def _now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def _new_id(): return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + secrets.token_hex(6)

class RunStore:
    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.db_path = state_dir / "state.sqlite3"
        self.db = connect(self.db_path)
    def create(self, spec: RunSpec, config_hash: str) -> RunRecord:
        run_id = _new_id(); now = _now()
        try:
            self.db.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (run_id, canonical_json_bytes(spec.as_dict()).decode(), spec.schedule_key, spec.parent_run_id, RunState.CREATED, 0, config_hash, now, now, None, None, None)); self.db.commit()
        except sqlite3.IntegrityError as exc:
            self.db.rollback()
            if spec.schedule_key:
                raise ConflictError("SCHEDULE_SLOT_EXISTS", "schedule slot already has a run", stage="create") from exc
            raise
        return RunRecord(run_id, spec, RunState.CREATED, 0, config_hash, now, now, spec.schedule_key, spec.parent_run_id)

    def get(self, run_id: str) -> RunRecord:
        row = self.db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None: raise KeyError(run_id)
        spec = RunSpec.from_dict(json.loads(row['spec_json']))
        return RunRecord(run_id, spec, RunState(row['state']), row['revision'], row['config_hash'],
                         row['created_at'], row['updated_at'], row['schedule_key'], row['parent_run_id'])
    def transition(self, run_id, expected_revision, expected_states, target_state: RunState) -> RunRecord:
        states = {str(s) for s in expected_states}; self.db.execute("BEGIN IMMEDIATE")
        row=self.db.execute("SELECT * FROM runs WHERE run_id=?",(run_id,)).fetchone()
        if row is None or row["revision"] != expected_revision or row["state"] not in states:
            self.db.rollback(); raise ConflictError("REVISION_CONFLICT", "run state/revision changed", stage="transition")
        now=_now(); cur=self.db.execute("UPDATE runs SET state=?,revision=revision+1,updated_at=? WHERE run_id=? AND revision=?",(str(target_state),now,run_id,expected_revision))
        if cur.rowcount != 1: self.db.rollback(); raise ConflictError("REVISION_CONFLICT","compare-and-swap failed",stage="transition")
        self.db.commit(); spec=RunSpec.from_dict(json.loads(row["spec_json"]))
        return RunRecord(run_id,spec,target_state,expected_revision+1,row["config_hash"],row["created_at"],now,row["schedule_key"],row["parent_run_id"])

    def write_manifest(self, run_id: str) -> Path:
        """Regenerate the human projection from DB; never trust an old manifest."""
        row = self.db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        artifacts = [dict(r) for r in self.db.execute(
            "SELECT name,revision,path,sha256,bytes FROM artifacts WHERE run_id=? AND deleted_at IS NULL",
            (run_id,))]
        payload = {"run_id": run_id, "state": row["state"], "revision": row["revision"],
                   "config_hash": row["config_hash"], "artifacts": artifacts}
        target = self.state_dir / "runs" / run_id / "manifest.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(".manifest.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
        tmp.replace(target)
        return target

    def acquire_lease(self, run_id: str, owner: str, *, ttl_seconds: int = 120,
                      now: datetime | None = None) -> bool:
        """Atomically acquire an expired lease; PID alone is never an owner."""
        if not owner or ttl_seconds <= 0:
            raise ValueError("owner and positive ttl_seconds are required")
        at = now or datetime.now(timezone.utc)
        if at.tzinfo is None:
            raise ValueError("lease time must be timezone-aware")
        current = at.astimezone(timezone.utc).isoformat(timespec="seconds")
        until = (at + timedelta(seconds=ttl_seconds)).astimezone(timezone.utc).isoformat(timespec="seconds")
        self.db.execute("BEGIN IMMEDIATE")
        cur = self.db.execute(
            "UPDATE runs SET lease_owner=?, lease_until=? WHERE run_id=? "
            "AND (lease_owner=? OR lease_until IS NULL OR lease_until < ?)",
            (owner, until, run_id, owner, current))
        if cur.rowcount != 1:
            self.db.rollback()
            return False
        self.db.commit()
        return True

    def release_lease(self, run_id: str, owner: str) -> bool:
        cur = self.db.execute("UPDATE runs SET lease_owner=NULL, lease_until=NULL WHERE run_id=? AND lease_owner=?",
                              (run_id, owner))
        self.db.commit()
        return cur.rowcount == 1

    def record_job(self, *, run_id: str, job_id: str, request_hash: str, kind: str, required: bool = True,
                   request: dict | None = None) -> None:
        self.db.execute("INSERT OR IGNORE INTO jobs(run_id,job_id,request_hash,kind,required,state,request_json) VALUES(?,?,?,?,?,?,?)",
                        (run_id,job_id,request_hash,kind,int(required),'pending',
                         json.dumps(request, ensure_ascii=False, sort_keys=True) if request is not None else None))
        self.db.commit()

    def record_attempt(self, *, run_id: str, job_id: str, request_hash: str,
                       state: str, result_hash: str | None = None,
                       result: object | None = None, error: dict | None = None) -> int:
        """Append an immutable attempt row and return its one-based attempt number."""
        row = self.db.execute("SELECT COALESCE(MAX(attempt), 0) + 1 AS n FROM job_attempts WHERE run_id=? AND job_id=?",
                              (run_id, job_id)).fetchone()
        attempt = int(row["n"])
        self.db.execute(
            "INSERT INTO job_attempts(run_id,job_id,attempt,request_hash,result_hash,state,result_json,error_json,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (run_id, job_id, attempt, request_hash, result_hash, state,
             json.dumps(result, ensure_ascii=False, sort_keys=True) if result is not None else None,
             json.dumps(error, ensure_ascii=False, sort_keys=True) if error is not None else None, _now()))
        self.db.commit()
        return attempt

    def resume_jobs(self, run_id: str, *, invalidated_request_hashes: set[str] | None = None) -> list[dict]:
        """Return only pending/failed or explicitly invalidated jobs for a safe resume."""
        invalidated = invalidated_request_hashes or set()
        rows = self.db.execute("SELECT * FROM jobs WHERE run_id=? ORDER BY job_id", (run_id,)).fetchall()
        return [dict(row) for row in rows
                if row["state"] != "succeeded" or row["request_hash"] in invalidated]

    def pending_jobs(self, run_id: str) -> list[dict]:
        rows = self.db.execute("SELECT * FROM jobs WHERE run_id=? AND state IN ('pending','failed') ORDER BY job_id", (run_id,)).fetchall()
        result=[]
        for row in rows:
            item=dict(row)
            if item.get('request_json'):
                item['request']=json.loads(item['request_json'])
            result.append(item)
        return result

    def replace_job_request(self, *, run_id: str, job_id: str, request_hash: str, request: dict) -> bool:
        """Replace a pending/failed request for bounded repair, never a succeeded job."""
        cur = self.db.execute("UPDATE jobs SET request_hash=?,request_json=?,state='pending',error_json=NULL WHERE run_id=? AND job_id=? AND state IN ('pending','failed')",
                              (request_hash, json.dumps(request, ensure_ascii=False, sort_keys=True), run_id, job_id))
        self.db.commit(); return cur.rowcount == 1

    def complete_job(self, *, run_id: str, job_id: str, result_path: str, result_hash: str) -> bool:
        self.db.execute('BEGIN IMMEDIATE')
        cur=self.db.execute("UPDATE jobs SET state='succeeded',attempts=attempts+1,result_path=?,result_hash=?,error_json=NULL WHERE run_id=? AND job_id=?",
                            (result_path,result_hash,run_id,job_id))
        if cur.rowcount == 1:
            self.db.execute("UPDATE runs SET revision=revision+1,updated_at=? WHERE run_id=?", (_now(), run_id))
            self.db.commit(); return True
        self.db.rollback(); return False

    def fail_job(self, *, run_id: str, job_id: str, error: dict) -> bool:
        cur=self.db.execute("UPDATE jobs SET state='failed',attempts=attempts+1,error_json=? WHERE run_id=? AND job_id=?",
                            (json.dumps(error,ensure_ascii=False),run_id,job_id))
        self.db.commit(); return cur.rowcount == 1
