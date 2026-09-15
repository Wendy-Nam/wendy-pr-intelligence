def test_probe_reports_missing_binary(monkeypatch):
 from scripts.packaging import probe_hosts
 monkeypatch.setattr(probe_hosts.shutil, 'which', lambda name: None)
 assert probe_hosts.probe('hermes')['available'] is False
