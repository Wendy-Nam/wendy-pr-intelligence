from __future__ import annotations
import hashlib, json, os, uuid
from pathlib import Path, PurePosixPath
from ..errors import IntegrityError
from ..models import ArtifactRecord
from .runs import RunStore

class ArtifactStore:
    def __init__(self, runs: RunStore): self.runs=runs; self.root=runs.state_dir / "runs"
    def _path(self, run_id, name):
        if not run_id or "/" in run_id or "\\" in run_id or not name:
            raise IntegrityError("PATH_ESCAPE","invalid artifact path")
        logical = PurePosixPath(name)
        if logical.is_absolute() or ".." in logical.parts or "." in logical.parts:
            raise IntegrityError("PATH_ESCAPE", "invalid artifact path")
        root=(self.root/run_id).resolve()
        target=(root.joinpath(*logical.parts)).resolve()
        if root != target and root not in target.parents:
            raise IntegrityError("PATH_ESCAPE","artifact escapes run root")
        return target
    def write_json(self, run_id, logical_name, revision, obj):
        raw=json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode(); path=self._path(run_id,logical_name); path.parent.mkdir(parents=True,exist_ok=True)
        tmp=path.with_name(f".tmp-{uuid.uuid4().hex}");
        with open(tmp,"wb") as f: f.write(raw); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,path); sha=hashlib.sha256(raw).hexdigest(); self.runs.db.execute("INSERT INTO artifacts VALUES(?,?,?,?,?,?,NULL)",(run_id,logical_name,revision,str(path),sha,len(raw))); self.runs.db.commit()
        return ArtifactRecord(run_id,logical_name,revision,path,sha,len(raw))
    def read_verified(self, record):
        path=self._path(record.run_id,record.name); raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=record.sha256: raise IntegrityError("ARTIFACT_HASH_MISMATCH","artifact changed")
        row=self.runs.db.execute("SELECT 1 FROM artifacts WHERE run_id=? AND name=? AND revision=? AND sha256=?",(record.run_id,record.name,record.revision,record.sha256)).fetchone()
        if not row: raise IntegrityError("UNREGISTERED_ARTIFACT","artifact is not registered")
        return raw

    def orphan_paths(self, run_id: str) -> list[Path]:
        """Doctor-facing list of files without an artifact DB record.

        These are intentionally only reported, never promoted automatically.
        """
        root = (self.root / run_id).resolve()
        if not root.is_dir():
            return []
        known = {Path(row[0]).resolve() for row in self.runs.db.execute(
            "SELECT path FROM artifacts WHERE run_id=? AND deleted_at IS NULL", (run_id,))}
        return [path for path in root.rglob("*") if path.is_file()
                and path.name != "manifest.json" and not path.name.startswith(".tmp-")
                and path.resolve() not in known]
