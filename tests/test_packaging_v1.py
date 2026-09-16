from pathlib import Path
from scripts.packaging.build import build_bundle, validate_bundle, smoke_import_bundle, load_installed_host

def test_host_bundle_allowlist_and_manifest(tmp_path):
 repo=Path(__file__).parents[1]; out=tmp_path/'codex'
 result=build_bundle(repo,out,'codex')
 assert (out/'.codex-plugin/plugin.json').exists()
 assert not (out/'docs').exists() and not (out/'tests').exists()
 assert result['core_hash']
 claude=build_bundle(repo,tmp_path/'claude','claude')
 hermes=build_bundle(repo,tmp_path/'hermes','hermes')
 assert claude['core_hash'] == result['core_hash'] == hermes['core_hash']
 assert validate_bundle(out,'codex')['valid']
 for host in ('claude', 'codex', 'hermes'):
  assert validate_bundle(tmp_path/host, host)['valid']
  assert smoke_import_bundle(tmp_path/host)['ok']

def test_installed_host_parses_manifest_and_skills(tmp_path):
 repo=Path(__file__).parents[1]; out=tmp_path/'hermes'
 build_bundle(repo,out,'hermes')
 info=load_installed_host(out)
 assert info['installed'] and info['host'] == 'hermes'
 assert info['name'] == 'pr-monitor' and info['version'] == '1.0.0'
 assert 'market-brief' in info['skills'] and info['validation']['valid']
 claude=tmp_path/'claude'; build_bundle(repo,claude,'claude')
 assert load_installed_host(claude)['host'] == 'claude'

def test_installed_host_reports_missing_and_malformed(tmp_path):
 assert load_installed_host(tmp_path) == {'installed': False, 'reason': 'no host manifest'}
 bad=tmp_path/'bad'; (bad/'.codex-plugin').mkdir(parents=True)
 (bad/'.codex-plugin/plugin.json').write_text('{not json',encoding='utf-8')
 info=load_installed_host(bad)
 assert info['installed'] and info['host'] == 'codex' and info['error']
 (bad/'plugin.yaml').write_text('name: pr-monitor\n',encoding='utf-8')
 assert load_installed_host(bad)['reason'].startswith('ambiguous')
