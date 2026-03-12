from wireguard_tools import WireguardDevice, WireguardKey

from gui.utils.command_runner import run_sudo_command


def generate_private_key() -> str:
    return str(WireguardKey.generate())


def get_public_key(private_key: str) -> str:
    return str(WireguardKey(private_key).public_key())


def list_devices() -> list[str]:
    return [device.interface for device in WireguardDevice.list()]


def add_peer(adapter_name: str, public_key: str, allowed_ips: str, sudo_password: str) -> str:
    cmd = f"wg set {adapter_name} peer {public_key} allowed-ips {allowed_ips}"
    return run_sudo_command(cmd, sudo_password).stdout


def remove_peer(adapter_name: str, public_key: str, sudo_password: str) -> str:
    cmd = f"wg set {adapter_name} peer {public_key} remove"
    return run_sudo_command(cmd, sudo_password).stdout


def up_adapter(adapter_name: str, sudo_password: str) -> str:
    return run_sudo_command(f"wg-quick up {adapter_name}", sudo_password).stdout


def down_adapter(adapter_name: str, sudo_password: str) -> str:
    return run_sudo_command(f"wg-quick down {adapter_name}", sudo_password).stdout
