"""Small, ordered SQLite migrations for the v1 local state ledger."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

MIGRATIONS = {
    1: """
    CREATE TABLE IF NOT EXISTS runs(
      run_id TEXT PRIMARY KEY, spec_json TEXT NOT NULL, schedule_key TEXT UNIQUE,
      parent_run_id TEXT, state TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0,
      config_hash TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      lease_owner TEXT, lease_until TEXT, last_error_json TEXT
    );
    CREATE TABLE IF NOT EXISTS jobs(
      run_id TEXT NOT NULL, job_id TEXT NOT NULL, request_hash TEXT NOT NULL,
      kind TEXT NOT NULL, required INTEGER NOT NULL, state TEXT NOT NULL,
      attempts INTEGER NOT NULL DEFAULT 0, result_path TEXT, result_hash TEXT, error_json TEXT,
      PRIMARY KEY(run_id, job_id), FOREIGN KEY(run_id) REFERENCES runs(run_id)
    );
    CREATE TABLE IF NOT EXISTS artifacts(
      run_id TEXT NOT NULL, name TEXT NOT NULL, revision INTEGER NOT NULL,
      path TEXT NOT NULL, sha256 TEXT NOT NULL, bytes INTEGER NOT NULL, deleted_at TEXT,
      PRIMARY KEY(run_id,name,revision), FOREIGN KEY(run_id) REFERENCES runs(run_id)
    );
    CREATE TABLE IF NOT EXISTS validations(
      run_id TEXT NOT NULL, revision INTEGER NOT NULL, briefing_hash TEXT NOT NULL,
      policy_hash TEXT NOT NULL, status TEXT NOT NULL, report_path TEXT NOT NULL,
      PRIMARY KEY(run_id,revision), FOREIGN KEY(run_id) REFERENCES runs(run_id)
    );
    CREATE TABLE IF NOT EXISTS deliveries(
      delivery_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, dedupe_key TEXT NOT NULL UNIQUE,
      status TEXT NOT NULL, message_id TEXT NOT NULL, attempt INTEGER NOT NULL,
      artifact_hash TEXT NOT NULL, recipient_hash TEXT NOT NULL, receipt_json TEXT,
      updated_at TEXT NOT NULL, FOREIGN KEY(run_id) REFERENCES runs(run_id)
    );
    CREATE TABLE IF NOT EXISTS memory_events(
      event_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, content_hash TEXT NOT NULL,
      kind TEXT NOT NULL, status TEXT NOT NULL, payload_json TEXT NOT NULL, applied_at TEXT,
      FOREIGN KEY(run_id) REFERENCES runs(run_id)
    );
    """,
    2: """
    CREATE TABLE IF NOT EXISTS job_attempts(
      run_id TEXT NOT NULL, job_id TEXT NOT NULL, attempt INTEGER NOT NULL,
      request_hash TEXT NOT NULL, result_hash TEXT, state TEXT NOT NULL,
      result_json TEXT, error_json TEXT, created_at TEXT NOT NULL,
      PRIMARY KEY(run_id, job_id, attempt),
      FOREIGN KEY(run_id, job_id) REFERENCES jobs(run_id, job_id)
    );
    """,
    3: """
    ALTER TABLE jobs ADD COLUMN request_json TEXT;
    """,
}


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=5000")
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
    current = db.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()[0]
    if current > max(MIGRATIONS):
        raise RuntimeError(f"state DB schema {current} is newer than this engine")
    for version, sql in MIGRATIONS.items():
        if version <= current:
            continue
        with db:
            db.executescript(sql)
            db.execute("INSERT INTO schema_migrations(version, applied_at) VALUES(?, ?)",
                       (version, datetime.now(timezone.utc).isoformat(timespec="seconds")))
    return db
