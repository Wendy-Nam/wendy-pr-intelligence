"""Offline-safe workspace setup primitives; dependency installation remains explicit."""
from __future__ import annotations
import copy, hashlib, json, platform, sys
from pathlib import Path

def environment_fingerprint(requirements: Path | None = None) -> dict:
    raw = requirements.read_bytes() if requirements and requirements.exists() else b''
    return {'implementation': platform.python_implementation(), 'version': platform.python_version(),
            'platform': platform.platform(), 'requirements_hash': hashlib.sha256(raw).hexdigest()}

def write_ready_marker(state_dir: Path, *, requirements: Path | None = None) -> Path:
    state_dir.mkdir(parents=True, exist_ok=True)
    marker = state_dir / 'runtime-ready.json'
    tmp = marker.with_suffix('.tmp')
    tmp.write_text(json.dumps(environment_fingerprint(requirements), sort_keys=True, indent=2), encoding='utf-8')
    tmp.replace(marker)
    return marker

def inspect_runtime(state_dir: Path, *, requirements: Path | None = None) -> dict:
    marker = state_dir / 'runtime-ready.json'; expected = environment_fingerprint(requirements)
    if not marker.exists(): return {'ready': False, 'reason': 'marker_missing', 'expected': expected}
    try: actual = json.loads(marker.read_text(encoding='utf-8'))
    except (OSError, ValueError): return {'ready': False, 'reason': 'marker_invalid', 'expected': expected}
    return {'ready': actual == expected, 'reason': '' if actual == expected else 'fingerprint_mismatch', 'actual': actual, 'expected': expected}

def migrate_config(source: Path, target: Path, *, dry_run: bool = False) -> dict:
    """Copy legacy config without overwriting user edits; return a migration plan."""
    if not source.exists(): return {'status': 'missing_source', 'changed': False}
    if target.exists(): return {'status': 'preserved_existing', 'changed': False}
    plan = {'status': 'ready', 'changed': True, 'source': str(source), 'target': str(target)}
    if dry_run: return plan
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())
    return plan | {'status': 'migrated'}

def _fill_missing(defaults: dict, into: dict, prefix: str, added: list) -> None:
    for key, value in defaults.items():
        path = f'{prefix}/{key}'
        if key not in into:
            into[key] = copy.deepcopy(value); added.append(path)
        elif isinstance(value, dict) and isinstance(into[key], dict):
            _fill_missing(value, into[key], path, added)

def upgrade_config(template: Path, target: Path, *, dry_run: bool = False) -> dict:
    """Fill keys added to a bundled template into an existing user config.

    Mapping-only deep merge: existing user values (lists included) always win,
    only absent keys are added. Idempotent — a second run reports 'current'.
    """
    import yaml
    if not target.exists(): return {'status': 'missing_target', 'changed': False, 'added': []}
    if not template.exists(): return {'status': 'missing_template', 'changed': False, 'added': []}
    try:
        current = yaml.safe_load(target.read_text(encoding='utf-8')) or {}
        defaults = yaml.safe_load(template.read_text(encoding='utf-8')) or {}
    except (OSError, yaml.YAMLError):
        return {'status': 'unreadable', 'changed': False, 'added': []}
    if not isinstance(current, dict) or not isinstance(defaults, dict):
        return {'status': 'unsupported', 'changed': False, 'added': []}
    merged = copy.deepcopy(current); added: list[str] = []
    _fill_missing(defaults, merged, '', added)
    if not added: return {'status': 'current', 'changed': False, 'added': []}
    plan = {'status': 'ready', 'changed': True, 'added': added, 'target': str(target)}
    if dry_run: return plan
    backup = target.with_name(target.name + '.bak')
    if not backup.exists(): backup.write_bytes(target.read_bytes())
    tmp = target.with_name(target.name + '.tmp')
    tmp.write_text(yaml.safe_dump(merged, allow_unicode=True, sort_keys=False), encoding='utf-8')
    tmp.replace(target)
    return plan | {'status': 'upgraded', 'backup': str(backup)}
