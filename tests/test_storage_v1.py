"""T02 offline storage/path regression coverage (V09--V15)."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest

from prmonitor.errors import ConflictError, IntegrityError
from prmonitor.models import RunSpec, RunState
from prmonitor.paths import resolve_paths
from prmonitor.storage.artifacts import ArtifactStore
from prmonitor.storage.runs import RunStore


def _spec(ctx):
    return RunSpec("market", "host", ctx.workspace_id, "2026-09-15", "Asia/Seoul",
                   "2026-09-14T00:00:00Z", "2026-09-15T00:00:00Z", 24)


def test_workspace_contexts_do_not_mix_or_write_bundle(tmp_path):
    """V09/V10: distinct process contexts retain separate workspace/cache roots."""
    bundle = tmp_path / "bundle"; bundle.mkdir()
    a = resolve_paths(env={}, cwd=tmp_path / "공간 A", bundle=bundle)
    b = resolve_paths(env={}, cwd=tmp_path / "B", bundle=bundle)
    assert a.workspace != b.workspace and a.cache != b.cache
    assert a.bundle == b.bundle == bundle
    store = RunStore(a.state_dir)
    assert store.db_path.is_file()
    assert not any(bundle.iterdir())


def test_cas_rejects_stale_revision_and_manifest_recovers(tmp_path):
    """V12/V14: DB is authoritative when a projection is lost or damaged."""
    ctx = resolve_paths(env={}, cwd=tmp_path / "workspace", bundle=tmp_path / "bundle")
    run = RunStore(ctx.state_dir); record = run.create(_spec(ctx), "a" * 64)
    changed = run.transition(record.run_id, 0, {RunState.CREATED}, RunState.COLLECTING)
    with pytest.raises(ConflictError):
        run.transition(record.run_id, 0, {RunState.CREATED}, RunState.FAILED)
    artifact = ArtifactStore(run).write_json(record.run_id, "briefing.json", changed.revision, {"ok": True})
    manifest = run.write_manifest(record.run_id)
    manifest.write_text("broken", encoding="utf-8")
    assert '"briefing.json"' in run.write_manifest(record.run_id).read_text(encoding="utf-8")
    assert ArtifactStore(run).read_verified(artifact)


def test_unregistered_or_tampered_artifact_is_not_trusted(tmp_path):
    """V13: orphan files and changed bytes cannot be read as deliverable artifacts."""
    ctx = resolve_paths(env={}, cwd=tmp_path / "workspace", bundle=tmp_path / "bundle")
    run = RunStore(ctx.state_dir); record = run.create(_spec(ctx), "a" * 64)
    artifacts = ArtifactStore(run)
    artifact = artifacts.write_json(record.run_id, "inputs/a.json", 0, {"x": 1})
    artifact.path.write_bytes(b"tampered")
    with pytest.raises(IntegrityError, match="ARTIFACT_HASH_MISMATCH"):
        artifacts.read_verified(artifact)
    with pytest.raises(IntegrityError, match="PATH_ESCAPE"):
        artifacts.write_json("../escape", "x.json", 0, {})
    with pytest.raises(IntegrityError, match="PATH_ESCAPE"):
        artifacts.write_json(record.run_id, "../escape.json", 0, {})
    outside = tmp_path / "outside"; outside.mkdir()
    (artifacts.root / record.run_id).mkdir(parents=True, exist_ok=True)
    (artifacts.root / record.run_id / "linked").symlink_to(outside, target_is_directory=True)
    with pytest.raises(IntegrityError, match="PATH_ESCAPE"):
        artifacts.write_json(record.run_id, "linked/escape.json", 0, {})
    orphan = artifacts.root / record.run_id / "briefing" / "crash.json"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text("orphan", encoding="utf-8")
    assert orphan in artifacts.orphan_paths(record.run_id)


def test_only_one_owner_gets_a_running_lease_until_expiry(tmp_path):
    """V16: a second process cannot concurrently own a run lease."""
    ctx = resolve_paths(env={}, cwd=tmp_path / "workspace", bundle=tmp_path / "bundle")
    first = RunStore(ctx.state_dir)
    record = first.create(_spec(ctx), "a" * 64)
    second = RunStore(ctx.state_dir)
    now = datetime(2026, 9, 15, tzinfo=timezone.utc)
    assert first.acquire_lease(record.run_id, "pid1-random", now=now)
    assert not second.acquire_lease(record.run_id, "pid2-random", now=now)
    assert second.acquire_lease(record.run_id, "pid2-random", now=now + timedelta(seconds=121))

def test_job_ledger_records_success_and_failure(tmp_path):
    ctx = resolve_paths(env={}, cwd=tmp_path / 'workspace', bundle=tmp_path / 'bundle')
    store = RunStore(ctx.state_dir); record = store.create(_spec(ctx), 'a' * 64)
    store.record_job(run_id=record.run_id, job_id='j1', request_hash='h', kind='market_brief', request={'prompt':'fixture'})
    assert store.db.execute("SELECT request_json FROM jobs WHERE job_id='j1'").fetchone()[0] == '{"prompt": "fixture"}'
    assert store.complete_job(run_id=record.run_id, job_id='j1', result_path='r.json', result_hash='r')
    store.record_job(run_id=record.run_id, job_id='j2', request_hash='h2', kind='category')
    assert store.fail_job(run_id=record.run_id, job_id='j2', error={'code':'FAILED'})

def test_schedule_key_is_unique_and_conflict_is_structured(tmp_path):
    ctx = resolve_paths(env={}, cwd=tmp_path / 'workspace', bundle=tmp_path / 'bundle')
    store = RunStore(ctx.state_dir)
    spec = _spec(ctx)
    spec = RunSpec(**{**spec.__dict__, 'schedule_key': 'slot'})
    store.create(spec, 'a' * 64)
    with pytest.raises(ConflictError) as exc:
        store.create(spec, 'a' * 64)
    assert exc.value.code == 'SCHEDULE_SLOT_EXISTS'


def test_domainpack_requires_operational_workspace_or_explicit_example(tmp_path):
    """Operational mode cannot silently fall back to bundled example data."""
    from prmonitor.domainpack import DomainPackError, load_domainpack
    bundle = Path(__file__).resolve().parents[1]
    ctx = resolve_paths(env={}, cwd=tmp_path / "empty", bundle=bundle)
    with pytest.raises(DomainPackError):
        load_domainpack(ctx)
    snapshot = load_domainpack(ctx, example_mode=True)
    assert snapshot.example_mode and snapshot.hash and snapshot.values["runtime"]
