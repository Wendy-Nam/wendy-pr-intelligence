"""Production provider wiring with fake network boundaries; never sends email."""

import hashlib
from dataclasses import replace
from types import SimpleNamespace

import pytest

from prmonitor import email_service as service
from prmonitor.delivery import DeliveryReceipt, send_reserved
from prmonitor.delivery_providers import resolve_transport
from prmonitor.storage.database import connect


@pytest.fixture
def config(tmp_path, monkeypatch):
    cfg = {
        "email": {
            "from": "sender@example.test",
            "smtp": {"host": "smtp.example.test", "user": "u", "password": "p"},
            "azure": {"tenant_id": "t", "client_id": "c", "client_secret": "s"},
        }
    }
    monkeypatch.setattr(service, "load_delivery_config", lambda path=None: cfg)
    return cfg


@pytest.mark.parametrize("port", [587, 465])
def test_smtp_factory_tls_auth_and_receipt(config, tmp_path, monkeypatch, port):
    config["email"]["smtp"]["port"] = port
    events = []

    class SMTP:
        def __init__(self, host, port, **kwargs):
            events.append(("connect", port, kwargs["timeout"]))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def starttls(self, **kwargs):
            events.append("tls")

        def login(self, user, password):
            events.append(("login", user, password))

        def send_message(self, msg):
            assert msg["Subject"] == "Daily"
            assert msg["To"] == "reader@example.test"
            assert "<p>hello</p>" in msg.get_body(("html",)).get_content()
            events.append("send")
            return {}

    monkeypatch.setattr(service.smtplib, "SMTP", SMTP)
    monkeypatch.setattr(service.smtplib, "SMTP_SSL", SMTP)
    transport = resolve_transport("smtp", fixture_dir=tmp_path, subject="Daily")
    receipt = transport.send(artifact=b"<p>hello</p>", recipient="reader@example.test")
    assert receipt.provider == "smtp" and receipt.status == "accepted"
    assert ("tls" in events) == (port == 587)
    assert events.index(("login", "u", "p")) < events.index("send")


@pytest.mark.parametrize("status", [202, 400, 503])
def test_graph_response_contract(config, tmp_path, monkeypatch, status):
    calls = []

    def post(url, **kwargs):
        calls.append((url, kwargs))
        if len(calls) == 1:
            return SimpleNamespace(ok=True, json=lambda: {"access_token": "token"})
        return SimpleNamespace(
            status_code=status, headers={"request-id": "request-123"}
        )

    monkeypatch.setattr(service.requests, "post", post)
    transport = resolve_transport("microsoft_graph", fixture_dir=tmp_path)
    if status == 202:
        receipt = transport.send(
            artifact=b"<p>hello</p>", recipient="reader@example.test"
        )
        assert receipt.delivery_id == "request-123" and receipt.status == "accepted"
    else:
        with pytest.raises(RuntimeError, match="graph_error"):
            transport.send(artifact=b"x", recipient="reader@example.test")
    assert calls[1][1]["timeout"] == 15
    assert (
        calls[1][1]["json"]["message"]["toRecipients"][0]["emailAddress"]["address"]
        == "reader@example.test"
    )


@pytest.mark.parametrize("payload", [{}, [], {"access_token": ""}])
def test_graph_malformed_token(config, monkeypatch, payload):
    monkeypatch.setattr(
        service.requests,
        "post",
        lambda *a, **k: SimpleNamespace(ok=True, json=lambda: payload),
    )
    token, error = service.get_graph_token(config)
    assert token is None and error


@pytest.mark.parametrize(
    "bad_field",
    ["artifact_hash", "recipient_hash", "status", "delivery_id", "provider", "timeout"],
)
def test_bad_receipt_or_timeout_is_unknown_and_never_retried(tmp_path, bad_field):
    db = connect(tmp_path / "state.sqlite3")
    db.execute(
        "INSERT INTO runs(run_id,spec_json,state,revision,config_hash,created_at,updated_at) VALUES('r','{}','READY',0,'h',datetime('now'),datetime('now'))"
    )
    db.commit()
    digest = hashlib.sha256(b"x").hexdigest()
    receipt = DeliveryReceipt(
        "id", "accepted", digest, hashlib.sha256(b"u").hexdigest(), "smtp"
    )

    class Transport:
        name = "smtp"
        calls = 0

        def send(self, **kwargs):
            self.calls += 1
            if bad_field == "timeout":
                raise TimeoutError("secret must not be logged")
            return replace(receipt, **{bad_field: ""})

    transport = Transport()
    args = dict(
        db=db,
        delivery_id="d",
        run_id="r",
        artifact=b"x",
        artifact_hash=digest,
        recipient="u",
        transport=transport,
        key="key",
    )
    assert send_reserved(**args) is None
    assert send_reserved(**args) is None
    assert transport.calls == 1
    row = db.execute("SELECT status, receipt_json FROM deliveries").fetchone()
    assert row[0] == "unknown" and "secret" not in row[1]


def test_wrong_artifact_hash_rejected_before_network(tmp_path):
    with pytest.raises(ValueError, match="ARTIFACT_HASH_MISMATCH"):
        send_reserved(
            None,
            delivery_id="d",
            run_id="r",
            artifact=b"x",
            artifact_hash="wrong",
            recipient="u",
            transport=None,
            key="k",
        )
