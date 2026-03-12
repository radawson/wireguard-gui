import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gui import create_app  # noqa: E402
from gui.errors import ValidationError  # noqa: E402
from gui.models import Network, Peer, db  # noqa: E402
from gui.services import network_service, runtime_sync_service  # noqa: E402


def _write_config(tmp_path: Path, mode: str) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    config = {
        "TEMPLATES_AUTO_RELOAD": True,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path}/wg-test.db",
        "HOST_IP": "127.0.0.1",
        "HOST_PORT": "5000",
        "BASE_DIR": str(tmp_path),
        "MODE": mode,
        "SECRET_KEY": "test-secret",
        "SUDO_PASSWORD": "test",
        "PKI_CERT_PATH": str(tmp_path / "pki"),
        "PKI_CERT": "cert.pem",
        "PKI_KEY": "key.pem",
        "BASE_IP": "10.100.200.0",
        "BASE_IP6": "fd00:100:200::",
        "BASE_NETMASK": "24",
        "BASE_NETMASK6": "64",
        "BASE_PORT": "51820",
        "BASE_PORT6": "51820",
        "BASE_DNS": "",
        "BASE_DNS6": "",
        "BASE_KEEPALIVE": "25",
        "ADAPTER_PREFIX": "wg",
        "PEER_ACTIVITY_TIMEOUT": 300,
        "OUTPUT_DIR": str(tmp_path / "output"),
        "LOG_DIR": str(tmp_path / "logs"),
        "AUTO_CREATE_DB": True,
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config_path


@pytest.fixture()
def server_app(tmp_path: Path):
    config_path = _write_config(tmp_path, mode="server")
    app = create_app(config_path=str(config_path), initialize_side_effects=False)
    app.config.update(TESTING=True)
    with app.app_context():
        db.create_all()
    return app


def test_runtime_sync_is_idempotent(server_app, monkeypatch):
    def fake_run_sudo(command: str, password: str = "") -> str:
        if command == "wg show interfaces":
            return "wg99"
        if command == "wg show wg99":
            return (
                "interface: wg99\n"
                "  public key: AAAA\n"
                "peer: rVhWk3NfAQJQnYEdwY8H5G5bD8e4j+zY3E8M1q9dYhM=\n"
                "  allowed ips: 10.100.200.11/32\n"
            )
        return ""

    monkeypatch.setattr(runtime_sync_service.helpers, "run_sudo", fake_run_sudo)

    with server_app.app_context():
        first = runtime_sync_service.sync_runtime_state("test")
        second = runtime_sync_service.sync_runtime_state("test")
        assert first.interfaces_scanned == 1
        assert second.interfaces_scanned == 1
        assert Network.query.filter_by(adapter_name="wg99").count() == 1
        imported_peers = Peer.query.filter(Peer.description.contains("runtime_public_key=")).all()
        assert len(imported_peers) == 1


def test_create_network_blocks_conflicting_live_adapter(server_app, monkeypatch):
    monkeypatch.setattr(runtime_sync_service, "list_runtime_adapters", lambda password="": ["wg0"])

    with server_app.app_context():
        existing = Network(
            name="existing",
            adapter_name="wg0",
            base_ip="10.10.10.0",
            subnet=24,
            private_key="",
            allowed_ips="10.10.10.0/24",
            dns_server="",
            description="",
            persistent_keepalive=25,
            proxy=False,
            active=True,
        )
        db.session.add(existing)
        db.session.commit()

        with pytest.raises(ValidationError):
            network_service.create_network_from_form(
                {
                    "name": "new",
                    "adapter_name": "wg0",
                    "base_ip": "10.20.0.0",
                    "subnet": "24",
                    "allowed_ips": "10.20.0.0/24",
                    "persistent_keepalive": "25",
                }
            )


def test_activate_network_noops_when_adapter_already_live(server_app, monkeypatch):
    monkeypatch.setattr(runtime_sync_service, "list_runtime_adapters", lambda password="": ["wg7"])

    with server_app.app_context():
        network = Network(
            name="net7",
            adapter_name="wg7",
            base_ip="10.70.0.0",
            subnet=24,
            private_key="",
            allowed_ips="10.70.0.0/24",
            dns_server="",
            description="",
            persistent_keepalive=25,
            proxy=False,
            active=False,
        )
        db.session.add(network)
        db.session.commit()

        called = {"up": False}

        def _should_not_run(*args, **kwargs):
            called["up"] = True

        monkeypatch.setattr(network_service.wg_adapter, "up_adapter", _should_not_run)
        message = network_service.activate_network(network.id, "test")
        assert "already active" in message
        assert called["up"] is False
        assert db.session.get(Network, network.id).active is True


def test_startup_sync_runs_only_in_server_mode(tmp_path: Path, monkeypatch):
    call_counter = {"count": 0}

    def _fake_sync(password: str = ""):
        call_counter["count"] += 1
        return runtime_sync_service.RuntimeSyncSummary(interfaces_scanned=0)

    monkeypatch.setattr(runtime_sync_service, "sync_runtime_state", _fake_sync)

    server_config = _write_config(tmp_path / "server", mode="server")
    server_pki = (tmp_path / "server" / "pki")
    server_pki.mkdir(parents=True, exist_ok=True)
    (server_pki / "cert.pem").write_text("cert", encoding="utf-8")
    (server_pki / "key.pem").write_text("key", encoding="utf-8")
    create_app(config_path=str(server_config), initialize_side_effects=True)
    assert call_counter["count"] == 1

    db_config = _write_config(tmp_path / "database", mode="database")
    db_pki = (tmp_path / "database" / "pki")
    db_pki.mkdir(parents=True, exist_ok=True)
    (db_pki / "cert.pem").write_text("cert", encoding="utf-8")
    (db_pki / "key.pem").write_text("key", encoding="utf-8")
    create_app(config_path=str(db_config), initialize_side_effects=True)
    assert call_counter["count"] == 1
