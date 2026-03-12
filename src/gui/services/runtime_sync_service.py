from __future__ import annotations

import ipaddress
import json
import re
from dataclasses import dataclass

from flask import current_app

from gui.errors import CommandExecutionError
from gui.integrations.wireguard import adapter as wg_adapter
from gui.models import Network, Peer, db
from gui.routes import helpers

RUNTIME_PUBLIC_KEY_TAG = "runtime_public_key="


@dataclass
class RuntimeSyncSummary:
    interfaces_scanned: int = 0
    networks_upserted: int = 0
    peers_upserted: int = 0
    peers_updated: int = 0
    conflicts_skipped: int = 0
    errors: int = 0

    def to_message(self) -> str:
        return (
            "WireGuard runtime sync complete: "
            f"interfaces={self.interfaces_scanned}, "
            f"networks_upserted={self.networks_upserted}, "
            f"peers_upserted={self.peers_upserted}, "
            f"peers_updated={self.peers_updated}, "
            f"conflicts_skipped={self.conflicts_skipped}, "
            f"errors={self.errors}"
        )


def _extract_runtime_public_key(description: str | None) -> str | None:
    if not description:
        return None
    for line in description.splitlines():
        line = line.strip()
        if line.startswith(RUNTIME_PUBLIC_KEY_TAG):
            return line.split("=", 1)[1].strip()
    return None


def get_runtime_public_key(peer: Peer) -> str | None:
    return _extract_runtime_public_key(peer.description)


def _apply_runtime_public_key_tag(peer: Peer, public_key: str) -> None:
    existing = peer.description or ""
    current = _extract_runtime_public_key(existing)
    if current == public_key:
        return
    filtered_lines = []
    for line in existing.splitlines():
        if not line.strip().startswith(RUNTIME_PUBLIC_KEY_TAG):
            filtered_lines.append(line)
    filtered_lines.append(f"{RUNTIME_PUBLIC_KEY_TAG}{public_key}")
    peer.description = "\n".join([line for line in filtered_lines if line]).strip()


def list_runtime_adapters(sudo_password: str = "") -> list[str]:
    if current_app.config.get("MODE") != "server":
        return []
    try:
        output = helpers.run_sudo("wg show interfaces", sudo_password)
    except CommandExecutionError:
        return []
    return [adapter for adapter in output.strip().split() if adapter]


def adapter_is_live(adapter_name: str, sudo_password: str = "") -> bool:
    return adapter_name in set(list_runtime_adapters(sudo_password))


def get_adapter_conflict_reason(
    adapter_name: str,
    owner_network_id: int | None = None,
    sudo_password: str = "",
) -> str | None:
    if current_app.config.get("MODE") != "server":
        return None
    if not adapter_name:
        return "Adapter name is required."

    runtime_adapters = set(list_runtime_adapters(sudo_password))
    db_owner = Network.query.filter_by(adapter_name=adapter_name).first()

    if adapter_name not in runtime_adapters:
        if db_owner and owner_network_id is not None and db_owner.id != owner_network_id:
            return f"Adapter {adapter_name} is already assigned to network {db_owner.name}."
        if db_owner and owner_network_id is None:
            return f"Adapter {adapter_name} is already assigned to network {db_owner.name}."
        return None

    # Adapter is running on host.
    if db_owner is None:
        return (
            f"Adapter {adapter_name} is active on host but not linked in database. "
            "Run 'Resync from WireGuard' first."
        )
    if owner_network_id is not None and db_owner.id == owner_network_id:
        return None
    return f"Adapter {adapter_name} is already managed by network {db_owner.name}."


def _build_public_key_index() -> dict[str, Peer]:
    index: dict[str, Peer] = {}
    for peer in Peer.query.all():
        runtime_public_key = get_runtime_public_key(peer)
        if runtime_public_key:
            index[runtime_public_key] = peer
            continue
        try:
            index[wg_adapter.get_public_key(peer.private_key)] = peer
        except ValueError:
            # Ignore malformed keys during runtime indexing.
            continue
    return index


def _infer_ip_and_subnet(allowed_ips: str | None) -> tuple[str, int]:
    if not allowed_ips:
        return "", 32
    first = allowed_ips.split(",")[0].strip()
    try:
        network = ipaddress.ip_network(first, strict=False)
        if isinstance(network, ipaddress.IPv4Network):
            host = str(network.network_address)
            return host, int(network.prefixlen)
    except ValueError:
        return "", 32
    return "", 32


def _parse_wg_peer_keys(wg_output: str) -> list[dict[str, str]]:
    peers: list[dict[str, str]] = []
    current_peer: dict[str, str] | None = None
    for line in wg_output.splitlines():
        peer_match = re.match(r"\s*peer:\s+(\S+)", line)
        allowed_ips_match = re.match(r"\s*allowed ips:\s+(.+)", line)
        if peer_match:
            if current_peer:
                peers.append(current_peer)
            current_peer = {"public_key": peer_match.group(1), "allowed_ips": ""}
            continue
        if allowed_ips_match and current_peer is not None:
            current_peer["allowed_ips"] = allowed_ips_match.group(1).strip()
    if current_peer:
        peers.append(current_peer)
    return peers


def _upsert_network_for_adapter(adapter_name: str) -> tuple[Network, bool]:
    network = Network.query.filter_by(adapter_name=adapter_name).first()
    if network:
        if not network.active:
            network.active = True
        return network, False
    subnet_default = int(current_app.config.get("BASE_NETMASK", 24))
    network = Network(
        active=True,
        adapter_name=adapter_name,
        allowed_ips="",
        base_ip=current_app.config.get("BASE_IP", "10.0.0.0"),
        dns_server=current_app.config.get("BASE_DNS", ""),
        description=f"Imported from runtime adapter {adapter_name}",
        lighthouse=[],
        name=f"Imported {adapter_name}",
        peers_list=[],
        persistent_keepalive=int(current_app.config.get("BASE_KEEPALIVE", 25)),
        private_key="",
        proxy=False,
        subnet=subnet_default,
    )
    db.session.add(network)
    db.session.flush()
    return network, True


def _create_runtime_peer(network: Network, public_key: str, allowed_ips: str) -> Peer:
    network_ip, subnet = _infer_ip_and_subnet(allowed_ips)
    peer = Peer(
        active=True,
        description="Imported from runtime",
        dns=network.dns_server or "",
        endpoint_host="",
        listen_port=0,
        name=f"Imported {network.adapter_name} {public_key[:8]}",
        network_ip=network_ip,
        lighthouse=False,
        network_id=network.id,
        peers_list=json.dumps([]),
        post_up="",
        post_down="",
        preshared_key="",
        preshared_keys=[],
        private_key=wg_adapter.generate_private_key(),
        subnet=subnet or 32,
    )
    _apply_runtime_public_key_tag(peer, public_key)
    return peer


def sync_runtime_state(sudo_password: str = "") -> RuntimeSyncSummary:
    summary = RuntimeSyncSummary()
    if current_app.config.get("MODE") != "server":
        return summary

    adapters = list_runtime_adapters(sudo_password)
    summary.interfaces_scanned = len(adapters)
    public_key_index = _build_public_key_index()

    for adapter_name in adapters:
        network, created = _upsert_network_for_adapter(adapter_name)
        if created:
            summary.networks_upserted += 1
        try:
            output = helpers.run_sudo(f"wg show {adapter_name}", sudo_password)
        except CommandExecutionError:
            summary.errors += 1
            continue
        for runtime_peer in _parse_wg_peer_keys(output):
            public_key = runtime_peer["public_key"]
            allowed_ips = runtime_peer.get("allowed_ips", "")
            existing_peer = public_key_index.get(public_key)
            if existing_peer:
                if existing_peer.network_id != network.id:
                    existing_peer.network_id = network.id
                existing_peer.active = True
                if allowed_ips and not existing_peer.network_ip:
                    inferred_ip, inferred_subnet = _infer_ip_and_subnet(allowed_ips)
                    existing_peer.network_ip = inferred_ip
                    existing_peer.subnet = inferred_subnet
                summary.peers_updated += 1
                continue
            new_peer = _create_runtime_peer(network, public_key, allowed_ips)
            db.session.add(new_peer)
            db.session.flush()
            public_key_index[public_key] = new_peer
            summary.peers_upserted += 1
    db.session.commit()
    return summary
