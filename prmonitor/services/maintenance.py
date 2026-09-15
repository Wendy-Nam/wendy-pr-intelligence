from __future__ import annotations
from pathlib import Path
from ..models import RunSpec
from ..storage.artifacts import ArtifactStore
from ..storage.runs import RunStore

def revise_run(store: RunStore, run_id: str) -> object:
    parent = store.get(run_id)
    data = parent.spec.as_dict(); data['parent_run_id'] = parent.run_id; data['schedule_key'] = None
    return store.create(RunSpec.from_dict(data), parent.config_hash)

def gc_orphans(store: RunStore, *, run_id: str | None = None, remove: bool = False) -> dict:
    runs = [run_id] if run_id else [r['run_id'] for r in store.db.execute('SELECT run_id FROM runs')]
    found=[]
    for rid in runs:
        paths=ArtifactStore(store).orphan_paths(rid); found.extend(paths)
        if remove:
            for path in paths: path.unlink(missing_ok=True)
    return {'orphans': [str(p) for p in found], 'removed': remove}
