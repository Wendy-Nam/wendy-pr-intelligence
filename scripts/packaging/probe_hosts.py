"""Record non-authenticated host binary/version/help evidence."""
from __future__ import annotations
import shutil, subprocess

def probe(name: str) -> dict:
    path = shutil.which(name)
    if not path: return {'name': name, 'available': False, 'reason': 'not found'}
    try:
        version = subprocess.run([path, '--version'], text=True, capture_output=True, timeout=5, check=False)
        help_args = ['--help'] if name != 'codex' else ['exec', '--help']
        help_result = subprocess.run([path, *help_args], text=True, capture_output=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'name': name, 'path': path, 'available': False, 'reason': type(exc).__name__}
    return {'name':name,'path':path,'available':help_result.returncode == 0,
            'version':(version.stdout or version.stderr).strip()[:300],
            'help_rc':help_result.returncode,'help_excerpt':(help_result.stdout or help_result.stderr).strip()[:500]}

def probe_all() -> dict:
    return {name: probe(name) for name in ('claude','codex','hermes')}

if __name__ == '__main__':
 import json
 print(json.dumps(probe_all(), ensure_ascii=False, indent=2))
