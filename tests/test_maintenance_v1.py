import json
from prmonitor.models import RunSpec
from prmonitor.paths import resolve_paths
from prmonitor.storage.runs import RunStore
from prmonitor.services.maintenance import revise_run, gc_orphans

def test_revise_preserves_parent_lineage_and_gc_is_explicit(tmp_path):
 ctx=resolve_paths(env={},cwd=tmp_path/'w',bundle=tmp_path/'b'); store=RunStore(ctx.state_dir)
 parent=store.create(RunSpec('market','host',ctx.workspace_id,'2026-09-15','UTC','s','e',24),'h')
 child=revise_run(store,parent.run_id); assert child.parent_run_id==parent.run_id
 orphan=ctx.state_dir/'runs'/parent.run_id/'orphan.json'; orphan.parent.mkdir(parents=True,exist_ok=True); orphan.write_text('{}')
 assert gc_orphans(store,run_id=parent.run_id)['orphans'] and orphan.exists()
 assert gc_orphans(store,run_id=parent.run_id,remove=True)['removed'] and not orphan.exists()
