import pytest
from prmonitor.delivery_providers import SmtpTransport, MicrosoftGraphTransport

@pytest.mark.parametrize('transport', [SmtpTransport(), MicrosoftGraphTransport()])
def test_provider_adapters_require_explicit_sender(transport):
 with pytest.raises(RuntimeError, match='NOT_CONFIGURED'):
  transport.send(artifact=b'x', recipient='fixture@example.test')

def test_provider_sender_is_injected_and_receipt_is_local():
 receipt=SmtpTransport(sender=lambda artifact, recipient: 'msg-1').send(artifact=b'x', recipient='fixture@example.test')
 assert receipt.status == 'accepted' and receipt.delivery_id == 'msg-1'

def test_resolver_defaults_to_local_and_keeps_live_providers_inert(tmp_path, monkeypatch):
 from prmonitor.delivery_providers import resolve_transport
 from prmonitor.delivery import LocalTransport
 monkeypatch.delenv('PRMONITOR_DELIVERY_PROVIDER', raising=False)
 assert isinstance(resolve_transport(fixture_dir=tmp_path), LocalTransport)
 monkeypatch.setenv('PRMONITOR_DELIVERY_PROVIDER', 'smtp')
 with pytest.raises(RuntimeError, match='NOT_CONFIGURED'):
  resolve_transport(fixture_dir=tmp_path).send(artifact=b'x', recipient='fixture@example.test')
 with pytest.raises(ValueError, match='UNKNOWN_DELIVERY_PROVIDER'):
  resolve_transport('nope', fixture_dir=tmp_path)
