"""Provider-neutral delivery adapters.

They deliberately require an injected sender callable; importing or constructing
these classes never opens a socket or reads credentials.
"""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from .delivery import DeliveryReceipt, LocalTransport

@dataclass
class SmtpTransport:
    sender: Callable[[bytes, str], str] | None = None
    name: str = 'smtp'
    def send(self, *, artifact: bytes, recipient: str) -> DeliveryReceipt:
        if self.sender is None: raise RuntimeError('SMTP_TRANSPORT_NOT_CONFIGURED')
        message_id = self.sender(artifact, recipient)
        import hashlib
        return DeliveryReceipt(str(message_id), 'accepted', hashlib.sha256(artifact).hexdigest(), hashlib.sha256(recipient.encode()).hexdigest())

@dataclass
class MicrosoftGraphTransport:
    sender: Callable[[bytes, str], str] | None = None
    name: str = 'microsoft_graph'
    def send(self, *, artifact: bytes, recipient: str) -> DeliveryReceipt:
        if self.sender is None: raise RuntimeError('GRAPH_TRANSPORT_NOT_CONFIGURED')
        message_id = self.sender(artifact, recipient)
        import hashlib
        return DeliveryReceipt(str(message_id), 'accepted', hashlib.sha256(artifact).hexdigest(), hashlib.sha256(recipient.encode()).hexdigest())

PROVIDERS = {'local': LocalTransport, 'smtp': SmtpTransport, 'microsoft_graph': MicrosoftGraphTransport}

def resolve_transport(name: str | None = None, *, fixture_dir: Path, sender: Callable[[bytes, str], str] | None = None):
    """Pick the transport for a send. Defaults to the offline LocalTransport.

    Live providers are selectable but inert: they carry no credentials and raise
    *_NOT_CONFIGURED unless a caller injects a sender. Actual live wiring is T14.
    """
    name = (name or os.environ.get('PRMONITOR_DELIVERY_PROVIDER') or 'local').strip().lower()
    if name not in PROVIDERS: raise ValueError('UNKNOWN_DELIVERY_PROVIDER')
    if name == 'local': return LocalTransport(fixture_dir)
    return PROVIDERS[name](sender=sender)
