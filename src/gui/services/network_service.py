from flask import current_app

from gui.errors import EntityNotFoundError, ValidationError
from gui.integrations.wireguard import adapter as wg_adapter
from gui.models import db, Network, Peer
from gui.repositories.network_repository import NetworkRepository


def list_networks() -> list[Network]:
    return NetworkRepository.all()


def get_network_or_404(network_id: int) -> Network:
    network = NetworkRepository.get(network_id)
    if not network:
        raise EntityNotFoundError(f"Network {network_id} not found")
    return network


def save_network_from_form(network: Network, form_data) -> None:
    network.name = form_data.get("name", network.name)
    network.base_ip = form_data.get("base_ip", network.base_ip)
    network.description = form_data.get("description", network.description)
    network.private_key = form_data.get("private_key", network.private_key)
    network.adapter_name = form_data.get("adapter_name") or "wg0"
    network.proxy = bool(form_data.get("proxy"))
    network.subnet = int(form_data.get("subnet", network.subnet or 24))
    network.dns_server = form_data.get("dns_server", network.dns_server)
    network.allowed_ips = form_data.get("allowed_ips", network.allowed_ips)
    keepalive = form_data.get("persistent_keepalive")
    network.persistent_keepalive = int(keepalive) if keepalive else 0

    lighthouse_id = form_data.get("lighthouse")
    if lighthouse_id:
        lighthouse = Peer.query.get(int(lighthouse_id))
        network.lighthouse = [lighthouse] if lighthouse else []
    db.session.add(network)
    db.session.commit()


def create_network_from_form(form_data) -> Network:
    lighthouse_id = form_data.get("lighthouse")
    lighthouse_list = []
    private_key = form_data.get("private_key", "")
    if lighthouse_id:
        lighthouse = Peer.query.get(int(lighthouse_id))
        if lighthouse:
            lighthouse_list = [lighthouse]
            private_key = lighthouse.private_key

    adapter_name = form_data.get("adapter_name") or "wg0"
    subnet = int(form_data.get("subnet", 24))
    persistent_keepalive = int(form_data.get("persistent_keepalive") or 0)

    if not form_data.get("name"):
        raise ValidationError("Network name is required")

    network = Network(
        active=False,
        adapter_name=adapter_name,
        allowed_ips=form_data.get("allowed_ips"),
        base_ip=form_data.get("base_ip"),
        dns_server=form_data.get("dns_server"),
        description=form_data.get("description"),
        lighthouse=lighthouse_list,
        name=form_data.get("name"),
        peers_list=[],
        persistent_keepalive=persistent_keepalive,
        private_key=private_key,
        proxy=bool(form_data.get("proxy")),
        subnet=subnet,
    )
    db.session.add(network)
    db.session.commit()
    return network


def activate_network(network_id: int, sudo_password: str | None = None) -> str:
    if current_app.config["MODE"] != "server":
        raise ValidationError("Cannot activate network in database mode")
    network = get_network_or_404(network_id)
    secret = sudo_password or current_app.config["SUDO_PASSWORD"]
    wg_adapter.up_adapter(network.adapter_name, secret)
    network.active = True
    db.session.commit()
    return "Network activated successfully"


def deactivate_network(network_id: int, sudo_password: str | None = None) -> str:
    if current_app.config["MODE"] != "server":
        raise ValidationError("Cannot deactivate network in database mode")
    network = get_network_or_404(network_id)
    secret = sudo_password or current_app.config["SUDO_PASSWORD"]
    wg_adapter.down_adapter(network.adapter_name, secret)
    network.active = False
    db.session.commit()
    return "Network deactivated successfully"
