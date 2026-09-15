"""Host-neutral v1 data contracts.  No paths, environment, or I/O here."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo
from enum import StrEnum
from pathlib import Path
from typing import Any

RUN_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[a-f0-9]{12}$")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def canonical_json_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


class RunState(StrEnum):
    CREATED = "CREATED"
    COLLECTING = "COLLECTING"
    NO_DATA = "NO_DATA"
    PREPARED = "PREPARED"
    AWAITING_LLM = "AWAITING_LLM"
    GENERATING = "GENERATING"
    VALIDATING = "VALIDATING"
    HELD = "HELD"
    READY = "READY"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class PathContext:
    bundle: Path
    workspace: Path
    cache: Path

    @property
    def workspace_id(self) -> str:
        return hashlib.sha256(str(self.workspace.resolve()).encode()).hexdigest()[:16]

    @property
    def state_dir(self) -> Path:
        return self.workspace / ".prmonitor"


@dataclass(frozen=True)
class SynthesisBudget:
    max_calls: int = 3
    max_parallel: int = 1
    job_timeout_seconds: int = 180
    run_timeout_seconds: int = 600
    max_input_bytes: int = 120000
    max_output_bytes: int = 1000000
    max_repairs: int = 1


@dataclass(frozen=True)
class RunSpec:
    pipeline: str
    mode: str
    workspace_id: str
    report_date: str
    timezone: str
    window_start: str
    window_end: str
    hours: int
    llm_enabled: bool = True
    backend: str | None = None
    force_refresh: bool = False
    example_mode: bool = False
    synthesis_strategy: str = "single"
    enrichment: str = "off"
    budget: SynthesisBudget = field(default_factory=SynthesisBudget)
    delivery_requested: bool = False
    parent_run_id: str | None = None
    schedule_key: str | None = None
    schema_version: int = 1

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["synthesis"] = {"strategy": data.pop("synthesis_strategy"),
                             "enrichment": data.pop("enrichment"),
                             "budget": data.pop("budget")}
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunSpec":
        """Decode the public nested JSON form without relying on globals."""
        data = dict(data)
        syn = data.pop("synthesis", {}) or {}
        budget = syn.pop("budget", {}) or {}
        data["synthesis_strategy"] = syn.get("strategy", "single")
        data["enrichment"] = syn.get("enrichment", "off")
        data["budget"] = SynthesisBudget(**budget)
        return cls(**data)

    def validation_errors(self) -> list[str]:
        """Return contract violations without mutating legacy-compatible records."""
        errors=[]
        if self.schema_version != 1: errors.append('SCHEMA_VERSION')
        if self.pipeline not in {'market','self'}: errors.append('PIPELINE')
        if self.mode not in {'host','headless'}: errors.append('MODE')
        if not 1 <= self.hours <= 720: errors.append('HOURS')
        try: ZoneInfo(self.timezone)
        except Exception: errors.append('TIMEZONE')
        try:
            start=datetime.fromisoformat(self.window_start.replace('Z','+00:00'))
            end=datetime.fromisoformat(self.window_end.replace('Z','+00:00'))
            if start.tzinfo is None or end.tzinfo is None or start >= end: errors.append('WINDOW')
        except ValueError: errors.append('WINDOW_FORMAT')
        if self.mode == 'host' and self.backend is not None: errors.append('HOST_BACKEND')
        if self.enrichment not in {'off','optional','required'}: errors.append('ENRICHMENT')
        if self.synthesis_strategy not in {'single','split'}: errors.append('STRATEGY')
        return errors


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    spec: RunSpec
    state: RunState
    revision: int
    config_hash: str
    created_at: str
    updated_at: str
    schedule_key: str | None = None
    parent_run_id: str | None = None


@dataclass(frozen=True)
class ArtifactRecord:
    run_id: str
    name: str
    revision: int
    path: Path
    sha256: str
    bytes: int
