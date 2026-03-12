import re
import shlex

from wireguard_tools import WireguardDevice, WireguardKey

from gui.utils.command_runner import run_sudo_command

_IFACE_RE = re.compile(r"^[a-zA-Z0-9_=+.\-]{1,15}$")
_BASE64_RE = re.compile(r"^[A-Za-z0-9+/]{42}[AEIMQUYcgkosw048]=$")
_CIDR_RE = re.compile(
    r"^[0-9a-fA-F.:]+/\d{1,3}(,[0-9a-fA-F.:]+/\d{1,3})*$"
)


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
    return [device.interface for device in WireguardDevice.list()]


def add_peer(
    adapter_name: str,
    public_key: str,
    allowed_ips: str,
    sudo_password: str,
    *,
    endpoint: str | None = None,
    preshared_key: str | None = None,
    persistent_keepalive: int | None = None,
) -> str:
    iface = _validate_interface(adapter_name)
    key = _validate_key(public_key)
    ips = _validate_allowed_ips(allowed_ips)
    cmd = f"wg set {shlex.quote(iface)} peer {shlex.quote(key)} allowed-ips {shlex.quote(ips)}"
    if endpoint is not None:
        cmd += f" endpoint {shlex.quote(endpoint)}"
    if preshared_key is not None:
        _validate_key(preshared_key)
        cmd += f" preshared-key <(echo {shlex.quote(preshared_key)})"
    if persistent_keepalive is not None:
        cmd += f" persistent-keepalive {int(persistent_keepalive)}"
    return run_sudo_command(cmd, sudo_password).stdout


def remove_peer(adapter_name: str, public_key: str, sudo_password: str) -> str:
    iface = _validate_interface(adapter_name)
    key = _validate_key(public_key)
    cmd = f"wg set {shlex.quote(iface)} peer {shlex.quote(key)} remove"
    return run_sudo_command(cmd, sudo_password).stdout


def up_adapter(adapter_name: str, sudo_password: str) -> str:
    iface = _validate_interface(adapter_name)
    return run_sudo_command(f"wg-quick up {shlex.quote(iface)}", sudo_password).stdout


def down_adapter(adapter_name: str, sudo_password: str) -> str:
    iface = _validate_interface(adapter_name)
    return run_sudo_command(f"wg-quick down {shlex.quote(iface)}", sudo_password).stdout
