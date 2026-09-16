"""Provider-neutral delivery adapters.

Production senders share the legacy CLI email service. Construction never opens a socket.
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
    name: str = "smtp"

    def send(self, *, artifact: bytes, recipient: str) -> DeliveryReceipt:
        if self.sender is None:
            raise RuntimeError("SMTP_TRANSPORT_NOT_CONFIGURED")
        message_id = self.sender(artifact, recipient)
        import hashlib

        return DeliveryReceipt(
            message_id,
            "accepted",
            hashlib.sha256(artifact).hexdigest(),
            hashlib.sha256(recipient.encode()).hexdigest(),
            self.name,
        )


@dataclass
class MicrosoftGraphTransport:
    sender: Callable[[bytes, str], str] | None = None
    name: str = "microsoft_graph"

    def send(self, *, artifact: bytes, recipient: str) -> DeliveryReceipt:
        if self.sender is None:
            raise RuntimeError("GRAPH_TRANSPORT_NOT_CONFIGURED")
        message_id = self.sender(artifact, recipient)
        import hashlib

        return DeliveryReceipt(
            message_id,
            "accepted",
            hashlib.sha256(artifact).hexdigest(),
            hashlib.sha256(recipient.encode()).hexdigest(),
            self.name,
        )


PROVIDERS = {
    "local": LocalTransport,
    "smtp": SmtpTransport,
    "microsoft_graph": MicrosoftGraphTransport,
}


def resolve_transport(
    name: str | None = None,
    *,
    fixture_dir: Path,
    sender: Callable[[bytes, str], str] | None = None,
    config_path: Path | None = None,
    subject: str = "[PR Monitor] Briefing",
):
    """Default to offline delivery; explicit live providers require valid configuration."""
    name = (
        (name or os.environ.get("PRMONITOR_DELIVERY_PROVIDER") or "local")
        .strip()
        .lower()
    )
    if name not in PROVIDERS:
        raise ValueError("UNKNOWN_DELIVERY_PROVIDER")
    if name == "local":
        return LocalTransport(fixture_dir)
    if sender is None:
        from . import email_service as service

        cfg = service.load_delivery_config(config_path)
        if not service._sender(cfg):
            raise ValueError("DELIVERY_SENDER_NOT_CONFIGURED")
        if name == "smtp" and not service._smtp_cfg(cfg)["host"]:
            raise ValueError("SMTP_TRANSPORT_NOT_CONFIGURED")
        if name == "microsoft_graph" and not all(service._azure_creds(cfg)):
            raise ValueError("GRAPH_TRANSPORT_NOT_CONFIGURED")
        send = service.send_mail_smtp if name == "smtp" else service.send_mail_graph

        def sender(artifact, recipient):
            result = send(cfg, subject, artifact.decode("utf-8"), [recipient])
            if not result["ok"]:
                raise RuntimeError(result.get("code", "DELIVERY_PROVIDER_ERROR"))
            return result["delivery_id"]

    return PROVIDERS[name](sender=sender)
