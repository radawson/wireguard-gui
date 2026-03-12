from flask import current_app

from gui.errors import EntityNotFoundError, ValidationError
from gui.integrations.wireguard import adapter as wg_adapter
from gui.models import db, Network, Peer
from gui.repositories.peer_repository import PeerRepository
from wireguard_tools import WireguardKey


def _parse_int_field(value, field_name: str, *, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field_name} must be a number") from exc
    if minimum is not None and parsed < minimum:
        raise ValidationError(f"{field_name} must be >= {minimum}")
    if maximum is not None and parsed > maximum:
        raise ValidationError(f"{field_name} must be <= {maximum}")
    return parsed


def list_peers(network_id: int | None = None) -> list[Peer]:
    if network_id:
        return PeerRepository.by_network(network_id)
    return PeerRepository.all()


def get_peer_or_404(peer_id: int) -> Peer:
    peer = PeerRepository.get(peer_id)
    if not peer:
        raise EntityNotFoundError(f"Peer {peer_id} not found")
    return peer


def create_peer_from_form(form_data) -> Peer:
    network_id = _parse_int_field(form_data.get("network") or 0, "Network")
    if network_id <= 0:
        raise ValidationError("A valid network is required")
    network = Network.query.get(network_id)
    if not network:
        raise EntityNotFoundError(f"Network {network_id} not found")
    private_key = form_data.get("private_key")
    if not private_key:
        raise ValidationError("Private key is required")
    try:
        WireguardKey(private_key)
    except (ValueError, TypeError) as exc:
        raise ValidationError("Invalid WireGuard private key") from exc
    listen_port = None
    if form_data.get("listen_port"):
        listen_port = _parse_int_field(
            form_data.get("listen_port"),
            "Listen port",
            minimum=1,
            maximum=65535,
        )
    subnet = _parse_int_field(form_data.get("subnet") or 32, "Subnet", minimum=0, maximum=32)

    peer = Peer(
        name=form_data.get("name"),
        private_key=private_key,
        network_ip=form_data.get("network_ip"),
        subnet=subnet,
        listen_port=listen_port,
        lighthouse=form_data.get("lighthouse") == "on",
        dns=form_data.get("dns"),
        description=form_data.get("description"),
        network_id=network_id,
        preshared_key=form_data.get("preshared_key"),
        endpoint_host=form_data.get("endpoint_ip") or form_data.get("endpoint_host"),
    )
    db.session.add(peer)
    db.session.commit()
    return peer


def update_peer_from_form(peer: Peer, form_data) -> None:
    peer.name = form_data.get("name", peer.name)
    peer.description = form_data.get("description", peer.description)
    private_key = form_data.get("private_key", peer.private_key)
    if private_key:
        try:
            WireguardKey(private_key)
        except (ValueError, TypeError) as exc:
            raise ValidationError("Invalid WireGuard private key") from exc
    peer.private_key = private_key
    peer.network_ip = form_data.get("network_ip", peer.network_ip)
    peer.endpoint_host = form_data.get("endpoint_ip", peer.endpoint_host)
    if form_data.get("listen_port"):
        peer.listen_port = _parse_int_field(
            form_data.get("listen_port"),
            "Listen port",
            minimum=1,
            maximum=65535,
        )
    if form_data.get("subnet"):
        peer.subnet = _parse_int_field(form_data.get("subnet"), "Subnet", minimum=0, maximum=32)
    peer.dns = form_data.get("dns", peer.dns)
    if form_data.get("network"):
        network_id = _parse_int_field(form_data.get("network"), "Network")
        network = Network.query.get(network_id)
        if not network:
            raise EntityNotFoundError(f"Network {network_id} not found")
        peer.network_id = network_id
    peer.preshared_key = form_data.get("preshared_key", peer.preshared_key)
    peer.lighthouse = form_data.get("lighthouse") == "on"
    db.session.add(peer)
    db.session.commit()


def remove_peer(peer_id: int) -> None:
    peer = get_peer_or_404(peer_id)
    db.session.delete(peer)
    db.session.commit()


def activate_peer(peer_id: int, sudo_password: str | None = None) -> str:
    peer = get_peer_or_404(peer_id)
    network = Network.query.get(peer.network_id)
    if not network:
        raise EntityNotFoundError(f"Network {peer.network_id} not found")
    if current_app.config["MODE"] != "server":
        peer.active = True
        db.session.commit()
        return "Peer activated in database"

    secret = sudo_password or current_app.config["SUDO_PASSWORD"]
    try:
        peer_public_key = peer.get_public_key()
    except (ValueError, TypeError) as exc:
        raise ValidationError("Invalid WireGuard private key") from exc
    wg_adapter.add_peer(
        network.adapter_name,
        peer_public_key,
        f"{peer.network_ip}/{peer.subnet}",
        secret,
    )
    peer.active = True
    db.session.commit()
    return "Peer added to running server"
