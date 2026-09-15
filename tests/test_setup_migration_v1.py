from prmonitor.services.setup import migrate_config

def test_config_migration_is_dry_run_and_preserves_existing(tmp_path):
 source=tmp_path/'old.yaml'; target=tmp_path/'new.yaml'; source.write_text('x: 1\n')
 assert migrate_config(source,target,dry_run=True)['changed'] and not target.exists()
 assert migrate_config(source,target)['status']=='migrated'
 target.write_text('x: 2\n')
 assert migrate_config(source,target)['status']=='preserved_existing' and target.read_text()=='x: 2\n'

def _write(path, text):
 path.write_text(text, encoding='utf-8'); return path

def test_upgrade_fills_new_keys_and_preserves_user_values(tmp_path):
 from prmonitor.services.setup import upgrade_config
 import yaml
 tmpl=_write(tmp_path/'runtime.tmpl.yaml','schema_version: 1\nllm: {backend: null, max_calls: 3}\nretention: {cache_days: 7}\n')
 target=_write(tmp_path/'runtime.yaml','llm: {backend: codex}\nkeywords: [a, b]\n')
 plan=upgrade_config(tmpl,target,dry_run=True)
 assert plan['changed'] and sorted(plan['added'])==['/llm/max_calls','/retention','/schema_version']
 assert yaml.safe_load(target.read_text())=={'llm':{'backend':'codex'},'keywords':['a','b']}
 out=upgrade_config(tmpl,target)
 assert out['status']=='upgraded'
 data=yaml.safe_load(target.read_text(encoding='utf-8'))
 assert data=={'llm':{'backend':'codex','max_calls':3},'keywords':['a','b'],'schema_version':1,'retention':{'cache_days':7}}
 assert (tmp_path/'runtime.yaml.bak').read_text(encoding='utf-8')=='llm: {backend: codex}\nkeywords: [a, b]\n'
 assert upgrade_config(tmpl,target)=={'status':'current','changed':False,'added':[]}

def test_upgrade_noops_without_target_or_template(tmp_path):
 from prmonitor.services.setup import upgrade_config
 tmpl=_write(tmp_path/'t.yaml','a: 1\n')
 assert upgrade_config(tmpl,tmp_path/'nope.yaml')['status']=='missing_target'
 assert upgrade_config(tmp_path/'nope.yaml',tmpl)['status']=='missing_template'

def test_init_upgrades_existing_runtime_config(monkeypatch, tmp_path):
 from prmonitor.steps import init
 from prmonitor import paths
 import yaml
 templates=tmp_path/'config-templates'; templates.mkdir()
 _write(templates/'runtime.yaml','schema_version: 1\nllm: {backend: null}\n')
 config=tmp_path/'config'; config.mkdir()
 _write(config/'runtime.yaml','llm: {backend: codex}\n')
 monkeypatch.setattr(paths,'CONFIG_TEMPLATES',templates)
 monkeypatch.setattr(paths,'CONFIG_DIR',config)
 monkeypatch.setattr(paths,'INIT_MARKER',tmp_path/'.marker')
 monkeypatch.setattr(paths,'ensure_dirs',lambda: None)
 import prmonitor.bootstrap as bootstrap
 monkeypatch.setattr(bootstrap,'venv_healthy',lambda: True)
 class Args: force=True; strict=False
 assert init.run(Args())==0
 assert yaml.safe_load((config/'runtime.yaml').read_text(encoding='utf-8'))=={'llm':{'backend':'codex'},'schema_version':1}
