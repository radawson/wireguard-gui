from flask import current_app

from gui.errors import EntityNotFoundError, ValidationError
from gui.integrations.wireguard import adapter as wg_adapter
from gui.models import db, Network, Peer
from gui.repositories.peer_repository import PeerRepository


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
    network_id = int(form_data.get("network") or 0)
    if network_id <= 0:
        raise ValidationError("A valid network is required")
    network = Network.query.get(network_id)
    if not network:
        raise EntityNotFoundError(f"Network {network_id} not found")

    peer = Peer(
        name=form_data.get("name"),
        private_key=form_data.get("private_key"),
        network_ip=form_data.get("network_ip"),
        subnet=int(form_data.get("subnet") or 32),
        listen_port=int(form_data.get("listen_port")) if form_data.get("listen_port") else None,
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
    peer.private_key = form_data.get("private_key", peer.private_key)
    peer.network_ip = form_data.get("network_ip", peer.network_ip)
    peer.endpoint_host = form_data.get("endpoint_ip", peer.endpoint_host)
    peer.listen_port = int(form_data.get("listen_port")) if form_data.get("listen_port") else peer.listen_port
    peer.subnet = int(form_data.get("subnet")) if form_data.get("subnet") else peer.subnet
    peer.dns = form_data.get("dns", peer.dns)
    peer.network_id = int(form_data.get("network")) if form_data.get("network") else peer.network_id
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
    wg_adapter.add_peer(
        network.adapter_name,
        peer.get_public_key(),
        f"{peer.network_ip}/{peer.subnet}",
        secret,
    )
    peer.active = True
    db.session.commit()
    return "Peer added to running server"
