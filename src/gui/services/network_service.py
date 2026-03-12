from flask import current_app

from gui.errors import EntityNotFoundError, ValidationError
from gui.integrations.wireguard import adapter as wg_adapter
from gui.models import db, Network, Peer
from gui.repositories.network_repository import NetworkRepository
from . import runtime_sync_service


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
    if current_app.config.get("MODE") == "server":
        conflict = runtime_sync_service.get_adapter_conflict_reason(
            network.adapter_name,
            owner_network_id=network.id,
            sudo_password=current_app.config.get("SUDO_PASSWORD", ""),
        )
        if conflict:
            raise ValidationError(conflict)
    network.proxy = bool(form_data.get("proxy"))
    network.subnet = _parse_int_field(
        form_data.get("subnet", network.subnet or 24),
        "Subnet",
        minimum=0,
        maximum=32,
    )
    network.dns_server = form_data.get("dns_server", network.dns_server)
    network.allowed_ips = form_data.get("allowed_ips", network.allowed_ips)
    keepalive = form_data.get("persistent_keepalive")
    network.persistent_keepalive = (
        _parse_int_field(keepalive, "Persistent keepalive", minimum=0) if keepalive else 0
    )

    lighthouse_id = form_data.get("lighthouse")
    if lighthouse_id:
        lighthouse_pk = _parse_int_field(lighthouse_id, "Lighthouse")
        lighthouse = Peer.query.get(lighthouse_pk)
        network.lighthouse = [lighthouse] if lighthouse else []
    db.session.add(network)
    db.session.commit()


def create_network_from_form(form_data) -> Network:
    lighthouse_id = form_data.get("lighthouse")
    lighthouse_list = []
    private_key = form_data.get("private_key", "")
    if lighthouse_id:
        lighthouse_pk = _parse_int_field(lighthouse_id, "Lighthouse")
        lighthouse = Peer.query.get(lighthouse_pk)
        if lighthouse:
            lighthouse_list = [lighthouse]
            private_key = lighthouse.private_key

    adapter_name = form_data.get("adapter_name") or "wg0"
    subnet = _parse_int_field(form_data.get("subnet", 24), "Subnet", minimum=0, maximum=32)
    persistent_keepalive = _parse_int_field(
        form_data.get("persistent_keepalive") or 0,
        "Persistent keepalive",
        minimum=0,
    )

    if not form_data.get("name"):
        raise ValidationError("Network name is required")
    if current_app.config.get("MODE") == "server":
        conflict = runtime_sync_service.get_adapter_conflict_reason(
            adapter_name,
            owner_network_id=None,
            sudo_password=current_app.config.get("SUDO_PASSWORD", ""),
        )
        if conflict:
            raise ValidationError(conflict)

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
    conflict = runtime_sync_service.get_adapter_conflict_reason(
        network.adapter_name,
        owner_network_id=network.id,
        sudo_password=secret,
    )
    if conflict:
        raise ValidationError(conflict)
    if runtime_sync_service.adapter_is_live(network.adapter_name, secret):
        network.active = True
        db.session.commit()
        return f"Adapter {network.adapter_name} is already active; no changes were applied."
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
