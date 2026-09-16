from __future__ import annotations
import hashlib, json, shutil, os, subprocess, sys
from pathlib import Path

ALLOWLIST = ('prmonitor', 'scripts', 'skills', 'commands', 'config-templates', 'requirements.txt', 'hermes_plugin')
EXCLUDED = {'.git', '.venv', '.prmonitor', 'data', 'tests', 'docs', '.omx', '__pycache__'}

def _copy_filtered(src: Path, dst: Path) -> None:
    if src.is_dir():
        for child in src.iterdir():
            if child.name in EXCLUDED or child.name.startswith('.'): continue
            _copy_filtered(child, dst / child.name)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dst)

def build_bundle(repo: Path, output: Path, host: str) -> dict:
    if host not in {'claude','codex','hermes'}: raise ValueError('unknown host')
    staging = output.with_name(output.name + '.staging'); shutil.rmtree(staging, ignore_errors=True); staging.mkdir(parents=True)
    for name in ALLOWLIST:
        src=repo/name
        if src.exists(): _copy_filtered(src, staging/name)
    if host == 'claude':
        src=repo/'.claude-plugin'; _copy_filtered(src, staging/'.claude-plugin') if src.exists() else None
    elif host == 'codex':
        manifest=staging/'.codex-plugin/plugin.json'; manifest.parent.mkdir(parents=True,exist_ok=True)
        manifest.write_text(json.dumps({'name':'pr-monitor','version':'1.0.0','description':'PR Intelligence engine'},sort_keys=True,indent=2),encoding='utf-8')
    else:
        (staging/'plugin.yaml').write_text('name: pr-monitor\nversion: 1.0.0\n',encoding='utf-8')
    shutil.rmtree(output, ignore_errors=True); staging.rename(output)
    files=sorted(str(p.relative_to(output)) for p in output.rglob('*') if p.is_file())
    digest = hashlib.sha256()
    for name in files:
        if name.startswith('prmonitor/'):
            digest.update(name.encode()); digest.update(b'\0'); digest.update((output/name).read_bytes())
    core=digest.hexdigest()
    return {'host':host,'root':str(output),'files':files,'core_hash':core}

def validate_bundle(bundle: Path, host: str) -> dict:
    required = [bundle/'prmonitor']
    if host == 'claude': required.append(bundle/'.claude-plugin/plugin.json')
    elif host == 'codex': required.append(bundle/'.codex-plugin/plugin.json')
    else: required.append(bundle/'plugin.yaml')
    missing = [str(p.relative_to(bundle)) for p in required if not p.exists()]
    forbidden = [str(p.relative_to(bundle)) for p in bundle.rglob('*') if p.is_dir() and p.name in EXCLUDED]
    malformed=[]
    manifest = (bundle/'.claude-plugin/plugin.json') if host == 'claude' else (bundle/'.codex-plugin/plugin.json') if host == 'codex' else None
    if manifest and manifest.exists():
        try:
            value=json.loads(manifest.read_text(encoding='utf-8'))
            if not isinstance(value, dict) or not value.get('name'): malformed.append(str(manifest.relative_to(bundle)))
        except (OSError, ValueError): malformed.append(str(manifest.relative_to(bundle)))
    return {'valid': not missing and not forbidden and not malformed, 'missing': missing, 'forbidden': forbidden, 'malformed': malformed}

MANIFESTS = (('claude', '.claude-plugin/plugin.json'), ('codex', '.codex-plugin/plugin.json'), ('hermes', 'plugin.yaml'))

def load_installed_host(root: Path) -> dict:
    """Parse an already-installed bundle on disk: host kind, manifest identity, installed skills.

    Filesystem only — never contacts or launches a host process.
    """
    found = [(host, root / rel) for host, rel in MANIFESTS if (root / rel).is_file()]
    if not found: return {'installed': False, 'reason': 'no host manifest'}
    if len(found) > 1: return {'installed': False, 'reason': 'ambiguous host manifest: ' + ','.join(h for h, _ in found)}
    host, manifest = found[0]
    name = version = None
    try:
        text = manifest.read_text(encoding='utf-8')
        if host == 'hermes':
            fields = dict(line.split(':', 1) for line in text.splitlines() if ':' in line)
            name, version = (fields.get('name') or '').strip() or None, (fields.get('version') or '').strip() or None
        else:
            value = json.loads(text)
            if not isinstance(value, dict): raise ValueError('manifest is not an object')
            name, version = value.get('name'), value.get('version')
    except (OSError, ValueError) as exc:
        return {'installed': True, 'host': host, 'manifest': str(manifest.relative_to(root)), 'error': type(exc).__name__}
    skills = sorted(p.name for p in (root / 'skills').glob('*') if (p / 'SKILL.md').is_file()) if (root / 'skills').is_dir() else []
    return {'installed': True, 'host': host, 'manifest': str(manifest.relative_to(root)), 'name': name, 'version': version,
            'skills': skills, 'validation': validate_bundle(root, host)}

def smoke_import_bundle(bundle: Path) -> dict:
    env = dict(os.environ); env['PYTHONPATH'] = str(bundle.resolve())
    result = subprocess.run([sys.executable, '-c', 'import prmonitor; print(prmonitor.__name__)'], env=env,
                            capture_output=True, text=True, check=False, cwd=bundle.resolve())
    return {'ok': result.returncode == 0, 'stdout': result.stdout.strip(), 'stderr': result.stderr.strip()[:500]}

if __name__ == '__main__':
 import argparse
 p=argparse.ArgumentParser(); p.add_argument('repo',type=Path); p.add_argument('output',type=Path); p.add_argument('--host',required=True,choices=['claude','codex','hermes'])
 args=p.parse_args(); print(json.dumps(build_bundle(args.repo,args.output,args.host),indent=2))
