import ipaddress
import os
import re
import socket
from os.path import exists

import psutil
from flask import current_app, g, has_request_context

from gui.errors import CommandExecutionError
from gui.models import Network, Peer, db
from gui.utils.command_runner import run_command, run_sudo_command


def check_wireguard(sudo_password=""):
    if not sudo_password:
        sudo_password = current_app.config["SUDO_PASSWORD"]
    if not exists("/etc/wireguard"):
        if run_command("uname -s").stdout.strip() == "Linux":
            run_sudo("apt update", sudo_password)
            run_sudo("apt -y full-upgrade", sudo_password)
            run_sudo("apt -y install wireguard", sudo_password)
            return True
        return False
    return True


def config_add_peer(config_string: str, peer: Peer) -> str:
    new_config_string = config_string
    new_config_string += (
        f"\n[Peer]\nPublicKey = {peer.public_key}\nAllowedIPs = {peer.allowed_ips}\n"
        f"Endpoint = {peer.endpoint_host}:{peer.endpoint_port}\n"
    )
    if peer.preshared_key:
        new_config_string += f"PresharedKey = {peer.preshared_key}\n"
    return new_config_string


def config_build(peer: Peer, network: Network) -> str:
    if peer.lighthouse:
        subnet = str(network.subnet)
        network_config_string = ""
    else:
        subnet = str(peer.subnet)
        network_config_string = network.get_config()
    config_file_string = (
        f"[Interface]\nPrivateKey = {peer.private_key}\n"
        f"Address = {peer.network_ip}/{subnet}\nListenPort = {peer.listen_port}\nSaveConfig = true\n"
    )
    if peer.post_down:
        config_file_string += f"PostDown = {peer.post_down}\n"
    if peer.post_up:
        config_file_string += f"PostUp = {peer.post_up}\n"
    if peer.dns:
        config_file_string += f"DNS = {peer.dns}\n\n"
    elif network.dns_server:
        config_file_string += f"DNS = {network.dns_server}\n\n"
    else:
        config_file_string += "\n"
    config_file_string += network_config_string

    return config_file_string


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
    run_cmd(
        "openssl req -nodes -x509 -newkey rsa:4096"
        + f" -keyout {cert_path}/{key_name} -out {cert_path}/{cert_name}"
        + " -subj /O=ClockWorx/CN=wireguard-gui"
    )


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
        network_cidr = ipaddress.IPv4Network(f"{base_ip}/{subnet}")
    except ValueError:
        current_app.logger.warning("Invalid network range for available IP lookup: %s/%s", base_ip, subnet)
        return {}

    for ip in network_cidr:
        if str(ip).split(".")[3] not in {"0", "255"}:
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
        allowed_ips_match = re.match(r"\s*allowed ips: (\S+)", line)
        transfer_match = re.match(r"\s*transfer: (\S+)", line)
        handshake_match = re.match(r"\s*latest handshake: (.+ ago)", line)

        if peer_match:
            current_peer = peer_match.group(1)
            peers_data[current_peer] = {}
        elif endpoint_match and current_peer:
            peers_data[current_peer]["endpoint"] = endpoint_match.group(1)
            peers_data[current_peer]["endpoint_port"] = endpoint_match.group(2)
        elif allowed_ips_match and current_peer:
            peers_data[current_peer]["allowed_ips"] = allowed_ips_match.group(1)
        elif transfer_match and current_peer:
            transfer_data = transfer_match.group(1).split("/")
            if len(transfer_data) >= 2:
                peers_data[current_peer]["transfer_rx"] = transfer_data[0]
                peers_data[current_peer]["transfer_tx"] = transfer_data[1]
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
