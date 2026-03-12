import sys
from pathlib import Path

import pytest
import yaml
from werkzeug.security import generate_password_hash

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gui import create_app  # noqa: E402
from gui.models import User, db  # noqa: E402


def _write_test_config(tmp_path: Path) -> Path:
    config = {
        "TEMPLATES_AUTO_RELOAD": True,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path}/wg-test.db",
        "HOST_IP": "127.0.0.1",
        "HOST_PORT": "5000",
        "BASE_DIR": str(tmp_path),
        "MODE": "database",
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
def app(tmp_path: Path):
    config_path = _write_test_config(tmp_path)
    app = create_app(config_path=str(config_path), initialize_side_effects=False)
    app.config.update(TESTING=True)

    with app.app_context():
        db.create_all()
        admin = User(
            username="admin",
            email="admin@example.com",
            password=generate_password_hash("adminpass"),
        )
        db.session.add(admin)
        db.session.commit()

    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client):
    return client.post(
        "/login",
        data={"name": "admin", "password": "adminpass", "remember": "on"},
        follow_redirects=True,
    )


def test_login_page_loads(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Login" in response.data


def test_authenticated_routes_work(client):
    login_response = _login(client)
    assert login_response.status_code == 200
    assert b"WGG" in login_response.data or b"Dashboard" in login_response.data

    dashboard_response = client.get("/dashboard/")
    assert dashboard_response.status_code == 200

    networks_response = client.get("/networks/")
    assert networks_response.status_code == 200

    peers_response = client.get("/peers/")
    assert peers_response.status_code == 200


def test_network_api_returns_json_list(client):
    _login(client)
    response = client.get("/networks/api/0")
    assert response.status_code == 200
    assert response.is_json
    assert isinstance(response.get_json(), list)
