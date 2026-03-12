from flask import (
    Blueprint,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required
from gui.errors import CommandExecutionError, EntityNotFoundError, ValidationError
from gui.integrations.wireguard import adapter as wg_adapter
from gui.models import Network, Peer, db
from gui.routes import helpers
from gui.services import peer_service

peers = Blueprint("peers", __name__, url_prefix="/peers")


sample_config = {
    "interface": {
        "address": "10.10.10.11/32",
        "listern_port": "51820",
        "private_key": "iISiPbGn4wSPhloFOtDN2BgqfJ1MqKKkmm0WtWc9sFE=",
    },
    "peer": {
        "AllowedIPs": ["0.0.0.0/0", "::/0"],
        "PublicKey": "iISiPbGn4wSPhloFOtDN2BgqfJ1MqKKkmm0WtWc9sFE=",
        "PersistentKeepalive": 25,
        "Endpoint": "myserver.dyndns.org:51820",
    },
}

def query_all_peers(network_id=None):
    if network_id is not None:
        peer_query = peer_service.list_peers(int(network_id))
    else:
        peer_query = peer_service.list_peers()
    if current_app.config.get("MODE") != "server":
        return peer_query
    status_by_adapter = {}
    for peer in peer_query:
        peer.public_key = helpers.get_peer_public_key(peer)
        network = helpers.get_network(peer.network_id)
        if network.name == "Invalid Network placeholder":
            continue
        if network.adapter_name not in status_by_adapter:
            status_by_adapter[network.adapter_name] = helpers.get_peers_status(
                network.adapter_name
            )
        current_peers = status_by_adapter[network.adapter_name]
        if not peer.public_key:
            continue
        for key in current_peers:
            if str(peer.public_key) == str(key):
                if "latest_handshake" in current_peers[str(peer.public_key)]:
                    if int(
                        current_peers[str(peer.public_key)]["latest_handshake"]
                    ) <= int(current_app.config["PEER_ACTIVITY_TIMEOUT"]):
                        print(f"Peer {peer.public_key} is active")
                        peer.active = True
                    else:
                        peer.active = False
                else:
                    peer.active = False
    return peer_query


def query_all_networks():
    return Network.query.all()


## ROUTES ##


@peers.route("/", methods=["GET", "POST"])
@login_required
def peers_all():
    network_id_raw = request.args.get("network_id")
    network_id = None
    if network_id_raw:
        try:
            network_id = int(network_id_raw)
        except ValueError:
            flash("Ignoring invalid network filter value.", "warning")
    peer_list = query_all_peers(network_id)
    if getattr(g, "wg_status_unavailable", False):
        flash(
            "Live WireGuard status is unavailable (sudo/WireGuard command check failed). "
            "Showing database values only.",
            "warning",
        )
    return render_template("peers.html", peer_list=peer_list)


@peers.route("/add", methods=["GET", "POST"])
@login_required
def peers_add():
    network_list = query_all_networks()
    new_peer = {"id": 0, "config": sample_config, "public_key": "", "network_id": 1}
    if request.method == "POST":
        try:
            peer = peer_service.create_peer_from_form(request.form)
            if current_app.config["MODE"] == "server":
                network = Network.query.get(peer.network_id)
                if network:
                    wg_adapter.add_peer(
                        network.adapter_name,
                        peer.get_public_key(),
                        f"{peer.network_ip}/{peer.subnet}",
                        request.form.get("sudoPassword") or current_app.config["SUDO_PASSWORD"],
                    )
            flash("Peer added successfully", "success")
            return redirect(url_for("peers.peer_detail", peer_id=peer.id))
        except (ValidationError, EntityNotFoundError) as exc:
            flash(str(exc), "danger")
        except ValueError as exc:
            flash(str(exc), "danger")
        except CommandExecutionError as exc:
            flash(f"Peer added to database, but failed on server: {exc}", "warning")

    avail_ip = helpers.get_available_ip()
    return render_template(
        "peer_detail.html",
        networks=network_list,
        peer=new_peer,
        avail_ip=avail_ip,
        s_button="Add",
    )


@peers.route("/update/<int:peer_id>", methods=["POST"])
@login_required
def peer_update(peer_id):
    peer = Peer.query.get(peer_id)
    if not peer:
        flash("Peer not found", "danger")
        return redirect(url_for("peers.peers_all"))
    try:
        peer_service.update_peer_from_form(peer, request.form)
        flash(f"Peer {peer_id} updated in database", "success")
    except (ValidationError, EntityNotFoundError, ValueError) as exc:
        db.session.rollback()
        flash(str(exc), "danger")
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Unexpected peer update error for peer_id=%s", peer_id)
        flash("Error updating peer", "danger")
    return redirect(url_for("peers.peers_all"))


@peers.route("/delete/<int:peer_id>", methods=["POST"])
@login_required
def peer_delete(peer_id):
    peer = Peer.query.filter_by(id=peer_id).first()
    if not peer:
        flash("Peer not found", "danger")
        return redirect(url_for("peers.peers_all"))
    try:
        if current_app.config["MODE"] == "server":
            network = helpers.get_network(peer.network_id)
            peer_public_key = helpers.get_peer_public_key(peer)
            if not peer_public_key:
                raise ValidationError("Peer does not contain a valid WireGuard public key")
            wg_adapter.remove_peer(
                network.adapter_name,
                peer_public_key,
                current_app.config["SUDO_PASSWORD"],
            )
        peer_service.remove_peer(peer_id)
        flash(f"Peer {peer_id} deleted successfully", "success")
    except CommandExecutionError as exc:
        flash(f"Error removing peer from running server: {exc}", "danger")
    return redirect(url_for("peers.peers_all"))


@peers.route("/<int:peer_id>", methods=["GET"])
@login_required
def peer_detail(peer_id):
    peer = Peer.query.filter_by(id=peer_id).first()
    if not peer:
        flash("Peer not found", "danger")
        return redirect(url_for("peers.peers_all"))

    return render_template(
        "peer_detail.html",
        networks=query_all_networks(),
        peer=peer,
        s_button="Update",
    )

@peers.route("/api/<int:peer_id>", methods=["POST","GET", "PATCH", "DELETE"])
@login_required
def peer_api(peer_id):
    if request.method == "GET":
        if peer_id == 0:
            return jsonify([peer.to_dict() for peer in Peer.query.all()])
        peer = Peer.query.get(peer_id)
        if not peer:
            return jsonify({"error": "Peer not found"}), 404
        return jsonify(peer.to_dict())
    elif request.method == "PATCH":
        peer = Peer.query.get(peer_id)
        if not peer:
            return jsonify({"error": "Peer not found"}), 404
        data = request.json or {}
        allowed_fields = {
            "name",
            "description",
            "dns",
            "endpoint_host",
            "listen_port",
            "network_ip",
            "subnet",
            "network_id",
            "preshared_key",
            "lighthouse",
            "private_key",
            "active",
        }
        unknown_fields = sorted(set(data.keys()) - allowed_fields)
        if unknown_fields:
            return jsonify({"error": f"Unknown fields: {', '.join(unknown_fields)}"}), 400
        try:
            for key, value in data.items():
                setattr(peer, key, value)
            db.session.commit()
        except (ValueError, TypeError) as exc:
            db.session.rollback()
            return jsonify({"error": str(exc)}), 400
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Unexpected peer API patch error for peer_id=%s", peer_id)
            return jsonify({"error": "Unable to update peer"}), 500
        return jsonify(peer.to_dict())
    elif request.method == "DELETE":
        peer = Peer.query.get(peer_id)
        if not peer:
            return jsonify({"error": "Peer not found"}), 404
        db.session.delete(peer)
        db.session.commit()
        return jsonify({"message": "Peer removed from database"})
    return jsonify({"error": "Invalid request method"}), 405

@peers.route("/activate/<int:peer_id>", methods=["POST"])
@login_required
def peer_activate(peer_id):
    try:
        message = peer_service.activate_peer(peer_id, current_app.config["SUDO_PASSWORD"])
        return jsonify({"category": "success", "message": message})
    except (ValidationError, EntityNotFoundError) as exc:
        return jsonify({"category": "warning", "message": str(exc)})
    except CommandExecutionError as exc:
        return jsonify({"category": "danger", "message": str(exc)})