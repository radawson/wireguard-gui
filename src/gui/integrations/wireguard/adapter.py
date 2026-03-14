import os
import re

from wireguard_tools import WireguardKey
from wireguard_tools.daemon_client import WgDaemonClient

_IFACE_RE = re.compile(r"^[a-zA-Z0-9_=+.\-]{1,15}$")
_BASE64_RE = re.compile(r"^[A-Za-z0-9+/]{42}[AEIMQUYcgkosw048]=$")
_CIDR_RE = re.compile(
    r"^[0-9a-fA-F.:]+/\d{1,3}(,[0-9a-fA-F.:]+/\d{1,3})*$"
)

_client: WgDaemonClient | None = None


def _get_client() -> WgDaemonClient:
    global _client  # noqa: PLW0603
    if _client is None:
        _client = WgDaemonClient(
            socket_path=os.environ.get("WG_DAEMON_SOCKET"),
        )
    return _client


def _validate_interface(name: str) -> str:
    if not _IFACE_RE.match(name):
        raise ValueError(f"Invalid interface name: {name!r}")
    return name


def _validate_key(key: str) -> str:
    if not _BASE64_RE.match(key):
        raise ValueError(f"Invalid WireGuard key format: {key!r}")
    return key


def _validate_allowed_ips(ips: str) -> str:
    cleaned = ips.replace(" ", "")
    if not _CIDR_RE.match(cleaned):
        raise ValueError(f"Invalid allowed-ips format: {ips!r}")
    return cleaned


def generate_private_key() -> str:
    return str(WireguardKey.generate())


def get_public_key(private_key: str) -> str:
    return str(WireguardKey(private_key).public_key())


def list_devices() -> list[str]:
    return _get_client().list_devices()


def add_peer(
    adapter_name: str,
    public_key: str,
    allowed_ips: str,
    sudo_password: str | None = None,
    *,
    endpoint: str | None = None,
    preshared_key: str | None = None,
    persistent_keepalive: int | None = None,
) -> str:
    iface = _validate_interface(adapter_name)
    key = _validate_key(public_key)
    ips = _validate_allowed_ips(allowed_ips)

    kwargs: dict = {
        "allowed_ips": ips.split(","),
    }
    if endpoint is not None:
        if ":" in endpoint:
            host, _, port = endpoint.rpartition(":")
            kwargs["endpoint_host"] = host.strip("[]")
            kwargs["endpoint_port"] = int(port)
    if preshared_key is not None:
        _validate_key(preshared_key)
        kwargs["preshared_key"] = preshared_key
    if persistent_keepalive is not None:
        kwargs["persistent_keepalive"] = int(persistent_keepalive)

    _get_client().set_peer(iface, key, **kwargs)
    return ""


def remove_peer(
    adapter_name: str,
    public_key: str,
    sudo_password: str | None = None,
) -> str:
    iface = _validate_interface(adapter_name)
    key = _validate_key(public_key)
    _get_client().remove_peer(iface, key)
    return ""


def up_adapter(
    adapter_name: str,
    sudo_password: str | None = None,
) -> str:
    iface = _validate_interface(adapter_name)
    _get_client().up(iface)
    return ""


def down_adapter(
    adapter_name: str,
    sudo_password: str | None = None,
) -> str:
    iface = _validate_interface(adapter_name)
    _get_client().down(iface)
    return ""
