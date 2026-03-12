import ipaddress
import os
import re
import shutil
import socket
from os.path import exists

import psutil
from flask import current_app, g, has_request_context

from gui.errors import CommandExecutionError
from gui.models import Network, Peer, db
from gui.utils.command_runner import run_command, run_sudo_command

from wireguard_tools import WireguardConfig, WireguardPeer, WireguardKey


def _detect_install_command() -> list[str] | None:
    """Return install commands for the detected package manager, or None."""
    if shutil.which("apt-get"):
        return [
            "apt-get update",
            "apt-get -y install wireguard",
        ]
    if shutil.which("dnf"):
        return ["dnf -y install wireguard-tools"]
    if shutil.which("yum"):
        return ["yum -y install wireguard-tools"]
    if shutil.which("pacman"):
        return ["pacman -S --noconfirm wireguard-tools"]
    if shutil.which("zypper"):
        return ["zypper -n install wireguard-tools"]
    if shutil.which("apk"):
        return ["apk add wireguard-tools"]
    return None


def check_wireguard(sudo_password=""):
    if not sudo_password:
        sudo_password = current_app.config["SUDO_PASSWORD"]
    if shutil.which("wg"):
        return True
    if not exists("/etc/wireguard"):
        if run_command("uname -s").stdout.strip() == "Linux":
            commands = _detect_install_command()
            if commands is None:
                current_app.logger.error("No supported package manager found")
                return False
            for cmd in commands:
                run_sudo(cmd, sudo_password)
            return True
        return False
    return True


def config_add_peer(config_string: str, peer: Peer) -> str:
    wg_peer = WireguardPeer(
        public_key=peer.public_key,
        allowed_ips=[peer.allowed_ips] if peer.allowed_ips else [],
        endpoint_host=peer.endpoint_host or None,
        endpoint_port=peer.endpoint_port or None,
        preshared_key=peer.preshared_key or None,
    )
    lines = wg_peer.as_wgconfig_snippet()
    return config_string + "\n".join(lines) + "\n"


def config_build(peer: Peer, network: Network) -> str:
    subnet = str(network.subnet) if peer.lighthouse else str(peer.subnet)

    dns_str = peer.dns or network.dns_server or ""
    dns_entries: list[str] = [d.strip() for d in dns_str.split(",") if d.strip()] if dns_str else []

    config = WireguardConfig(
        private_key=peer.private_key,
        listen_port=peer.listen_port,
        addresses=[f"{peer.network_ip}/{subnet}"],
        save_config=True,
    )

    for entry in dns_entries:
        config._add_dns_entry(entry)

    if peer.post_down:
        config.postdown.append(peer.post_down)
    if peer.post_up:
        config.postup.append(peer.post_up)

    config_string = config.to_wgconfig(wgquick_format=True)

    if not peer.lighthouse:
        config_string += "\n" + network.get_config()

    return config_string


def config_save(config_file_string, directory, filename) -> "bool":
    os.makedirs(f"{current_app.config['OUTPUT_DIR']}/{directory}", exist_ok=True)
    try:
        with open(f"{current_app.config['OUTPUT_DIR']}/{directory}/{filename}", "w", encoding="utf-8") as config_file:
            config_file.write(config_file_string)
    except OSError:
        return False
    return True


def enable_ip_forwarding_v4(sudo_password):
    message = ""
    try:
        run_sudo("sysctl -w net.ipv4.ip_forward=1", sudo_password)
        message += "\nIPv4 forwarding enabled (runtime)"
        # Persist forwarding in a distro-agnostic location and reload all sysctl settings.
        run_sudo("mkdir -p /etc/sysctl.d", sudo_password)
        run_sudo(
            'sh -c "echo net.ipv4.ip_forward=1 > /etc/sysctl.d/99-wireguard-gui.conf"',
            sudo_password,
        )
        run_sudo("sysctl --system", sudo_password)
        message += "\nIPv4 forwarding persistence updated"
    except CommandExecutionError as e:
        message += f"\nError enabling ipv4 forwarding: {e}"
    return message


def generate_cert(cert_path, cert_name, key_name):
    if not exists(cert_path):
        os.makedirs(cert_path)
    try:
        run_cmd(
            "openssl req -nodes -x509 -newkey rsa:4096"
            + f" -keyout {cert_path}/{key_name} -out {cert_path}/{cert_name}"
            + " -subj /O=ClockWorx/CN=wireguard-gui"
        )
    except CommandExecutionError as exc:
        current_app.logger.error("Failed to generate TLS certificate: %s", exc)


def get_adapter_names():
    adapters = psutil.net_if_addrs()
    adapter_names = []
    for adapter in adapters:
        if adapter != "lo":
            adapter_names.append(adapter)
    return adapter_names


def get_uplink_adapter():
    # Prefer the default route interface when available.
    try:
        default_route = run_cmd("ip route show default").splitlines()
        for line in default_route:
            match = re.search(r"\bdev\s+(\S+)", line)
            if match:
                return match.group(1)
    except CommandExecutionError:
        pass

    # Fallback to first non-virtual adapter.
    virtual_prefixes = ("wg", "docker", "br-", "veth", "virbr", "tun")
    for adapter in get_adapter_names():
        if adapter.startswith(virtual_prefixes):
            continue
        return adapter
    return "eth0"

def get_available_ip(network_id: int = 0) -> dict:
    if network_id == 0:
        network = get_network(network_id)
        network.base_ip = current_app.config["BASE_IP"]
        network.subnet = current_app.config["BASE_NETMASK"]
    else:
        network = get_network(network_id)
    ip_dict = {}
    if network.base_ip == "":
        base_ip = current_app.config["BASE_IP"]
    else:
        base_ip = network.base_ip
    if network.subnet == 0:
        subnet = current_app.config["BASE_NETMASK"]
    else:
        subnet = network.subnet

    try:
        network_cidr = ipaddress.ip_network(f"{base_ip}/{subnet}", strict=False)
    except ValueError:
        current_app.logger.warning("Invalid network range for available IP lookup: %s/%s", base_ip, subnet)
        return {}

    if isinstance(network_cidr, ipaddress.IPv4Network):
        for ip in network_cidr:
            octets = str(ip).split(".")
            if octets[3] not in {"0", "255"}:
                ip_dict[str(ip)] = None
    else:
        for ip in network_cidr.hosts():
            ip_dict[str(ip)] = None

    if network.peers_list:
        for peer in network.peers_list:
            ip_dict[peer.network_ip] = peer.name

    return ip_dict

def get_lighthouses():
    return Peer.query.filter_by(lighthouse=True).all()


def get_peer_public_key(peer: Peer) -> str | None:
    description = peer.description or ""
    for line in description.splitlines():
        line = line.strip()
        if line.startswith("runtime_public_key="):
            return line.split("=", 1)[1].strip()
    try:
        return peer.get_public_key()
    except (ValueError, TypeError):
        return None


def get_network(network_id: int) -> Network:
    network = Network.query.get(network_id)
    if network:
        return network
    return Network(
        name="Invalid Network placeholder",
        lighthouse=[],
        private_key="",
        peers_list=[],
        base_ip="0.0.0.0",
        subnet=0,
        dns_server="",
        description="Invalid Network placeholder",
        allowed_ips="",
        adapter_name="",
    )

def get_peer_count(network_id: int) -> int:
    count = 0
    with db.session.no_autoflush:
        network = Network.query.get(network_id)
        if not network:
            return 0
        count = len(network.peers_list or [])
        count += len(network.lighthouse or [])
    return count

def get_peers_status(network_adapter="all", sudo_password=""):
    if not current_app.config["LINUX"]:
        return {}
    try:
        output = run_sudo(f"wg show {network_adapter}", sudo_password)
    except CommandExecutionError as exc:
        # Do not break page rendering when sudo credentials are unavailable.
        current_app.logger.warning("Unable to read WireGuard status: %s", exc)
        if has_request_context():
            g.wg_status_unavailable = True
        return {}
    return parse_wg_output(output)



def get_public_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except OSError:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def parse_wg_output(output):
    output_lines = output.split("\n")
    peers_data = {}
    current_peer = None

    for line in output_lines:
        peer_match = re.match(r"\s*peer: (\S+)", line)
        endpoint_match = re.match(r"\s*endpoint: (\S+):(\d+)", line)
        allowed_ips_match = re.match(r"\s*allowed ips: (.+)", line)
        transfer_match = re.match(
            r"\s*transfer:\s+(.+?)\s+received,\s+(.+?)\s+sent", line
        )
        handshake_match = re.match(r"\s*latest handshake: (.+ ago)", line)

        if peer_match:
            current_peer = peer_match.group(1)
            peers_data[current_peer] = {}
        elif endpoint_match and current_peer:
            peers_data[current_peer]["endpoint"] = endpoint_match.group(1)
            peers_data[current_peer]["endpoint_port"] = endpoint_match.group(2)
        elif allowed_ips_match and current_peer:
            peers_data[current_peer]["allowed_ips"] = allowed_ips_match.group(1).strip()
        elif transfer_match and current_peer:
            peers_data[current_peer]["transfer_rx"] = transfer_match.group(1)
            peers_data[current_peer]["transfer_tx"] = transfer_match.group(2)
        elif handshake_match and current_peer:
            time_str = handshake_match.group(1)
            time_lst = time_str[:-4].split(", ")
            days, hours, minutes, seconds = 0, 0, 0, 0
            for element in time_lst:
                if "day" in element:
                    days = int(element.split()[0])
                elif "hour" in element:
                    hours = int(element.split()[0])
                elif "minute" in element:
                    minutes = int(element.split()[0])
                elif "second" in element:
                    seconds = int(element.split()[0])
            total_seconds = days * 86400 + hours * 3600 + minutes * 60 + seconds
            peers_data[current_peer]["latest_handshake"] = total_seconds

    return peers_data


def port_open(port: int):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        return sock.connect_ex(("127.0.0.1", port)) == 0
    finally:
        sock.close()


def remove_peers_all(network_id: int, sudo_password=""):
    message = f"Removing peers from network {network_id}"
    if not sudo_password:
        sudo_password = current_app.config["SUDO_PASSWORD"]
    network = get_network(network_id)
    message += f"\n\tNetwork {network.name} found"
    peers = Peer.query.filter_by(network_id=network.id).all()
    for peer in peers:
        peer_public_key = get_peer_public_key(peer)
        if not peer_public_key:
            message += f"\n\t\tSkipped peer {peer.name} because no valid public key was found"
            continue
        run_sudo(
            f"wg set {network.adapter_name} peer {peer_public_key} remove",
            sudo_password,
        )
        message += f"\n\t\tRemoved peer {peer.name} from adapter {network.adapter_name}"
        peer.active = False
        peer.network_id = 0
        message += f"\n\t\tUnregistered peer {peer.name} from network"
    db.session.commit()
    return message


def run_cmd(command) -> str:
    return run_command(command).stdout


def run_sudo(command: str, password: str = "") -> str:
    if not current_app.config["LINUX"]:
        return "Command line options not implemented for Windows"
    if not password:
        password = current_app.config.get("SUDO_PASSWORD", "")
    return run_sudo_command(command, password).stdout
