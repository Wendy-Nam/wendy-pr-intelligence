def test_init_strict_returns_exit20_on_runtime_failure(monkeypatch, tmp_path):
 from prmonitor.steps import init
 from prmonitor import paths
 class Args: force=True; strict=True
 monkeypatch.setattr(paths, 'PROJECT_DIR', tmp_path)
 monkeypatch.setattr(paths, 'CONFIG_TEMPLATES', tmp_path/'missing-templates')
 monkeypatch.setattr(paths, 'INIT_MARKER', tmp_path/'.marker')
 monkeypatch.setattr(paths, 'ensure_dirs', lambda: None)
 import prmonitor.bootstrap as bootstrap
 monkeypatch.setattr(bootstrap, 'venv_healthy', lambda: False)
 monkeypatch.setattr(bootstrap, 'ensure_venv', lambda quiet=True: (_ for _ in ()).throw(RuntimeError('broken')))
 assert init.run(Args()) == 20
