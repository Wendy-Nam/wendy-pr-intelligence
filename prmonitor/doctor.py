"""Read-only integrity diagnostics for local state."""
from __future__ import annotations
import json
import os, sys
from pathlib import Path
from .storage.artifacts import ArtifactStore
from .storage.runs import RunStore
def inspect_workspace(state_dir: Path) -> dict:
 store=RunStore(state_dir); rows=store.db.execute('SELECT run_id,state,revision FROM runs ORDER BY created_at').fetchall(); runs=[]
 for row in rows:
  orphans=ArtifactStore(store).orphan_paths(row['run_id']); runs.append({'run_id':row['run_id'],'state':row['state'],'revision':row['revision'],'orphans':[str(x) for x in orphans]})
 from .llm.codex import CodexBackend
 from .llm.claude import ClaudeBackend
 from .llm.hermes import HermesBackend
 backend_health = {name: obj.probe(live=False) for name, obj in {
     'claude': ClaudeBackend(), 'codex': CodexBackend(), 'hermes': HermesBackend()}.items()}
 checks = {'python': {'ok': sys.version_info >= (3,11), 'version': sys.version},
           'state_writable': os.access(state_dir, os.W_OK),
           'schema': {'ok': True, 'version': store.db.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]},
           'backend_binaries': {name: {'available': health.available, 'supported': health.supported, 'reason': health.reason}
                                for name, health in backend_health.items()},
           'delivery_configured': False}
 healthy = (not any(x['orphans'] for x in runs)
            and checks['python']['ok'] and checks['state_writable'] and checks['schema']['ok'])
 return {'schema_version':1,'database':str(store.db_path),'runs':runs,'checks':checks,'healthy':healthy}
