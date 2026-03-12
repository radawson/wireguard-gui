from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required
from gui.errors import CommandExecutionError, EntityNotFoundError, ValidationError
from gui.models import Network, db, subnets
from gui.routes import helpers
from gui.services import network_service

networks = Blueprint("networks", __name__, url_prefix="/networks")

## ROUTES ##
@networks.route("/", methods=["GET"])
@login_required
def networks_all():
    network_list = network_service.list_networks()
    for network in network_list:
        network.peer_count = helpers.get_peer_count(network.id)
    return render_template("networks.html", networks=network_list)


@networks.route("/<int:network_id>", methods=["GET", "POST"])
@login_required
def network_detail(network_id):
    network = Network.query.filter_by(id=network_id).first()
    if not network:
        flash(f"Network {network_id} not found", "danger")
        return redirect(url_for("networks.networks_all"))

    adapters = helpers.get_adapter_names()
    if request.method == "POST":
        try:
            network_service.save_network_from_form(network, request.form)
            flash("Network updated successfully", "success")
            return redirect(url_for("networks.networks_all"))
        except (ValidationError, EntityNotFoundError) as exc:
            flash(str(exc), "danger")
        except Exception:
            db.session.rollback()
            flash("Error updating network", "danger")

    return render_template(
        "network_detail.html",
        subnets=subnets,
        network=network,
        lighthouses=helpers.get_lighthouses(),
        adapters=adapters,
        s_button="Update",
    )


@networks.route("/add", methods=["GET", "POST"])
@login_required
def networks_add():
    lighthouses = helpers.get_lighthouses()
    adapters = helpers.get_adapter_names()
    if request.method == "POST":
        try:
            network_service.create_network_from_form(request.form)
            flash("Network added successfully", "success")
            return redirect(url_for("networks.networks_all"))
        except (ValidationError, EntityNotFoundError) as exc:
            flash(str(exc), "danger")
        except Exception:
            db.session.rollback()
            flash("Error adding network", "danger")

    new_network = {"id": 0, "public_key": "", "name": ""}
    return render_template(
        "network_detail.html",
        network=new_network,
        subnets=subnets,
        lighthouses=lighthouses,
        adapters=adapters,
        s_button="Add",
    )


@networks.route("/update/<int:network_id>", methods=["POST"])
@login_required
def network_update(network_id):
    network = Network.query.get(network_id)
    if not network:
        flash(f"Network {network_id} not found", "danger")
        return redirect(url_for("networks.networks_all"))
    try:
        network_service.save_network_from_form(network, request.form)
        flash("Network updated in database", "success")
    except Exception as exc:
        db.session.rollback()
        flash(str(exc), "danger")
    return redirect(url_for("networks.networks_all"))


@networks.route("/delete/<int:network_id>", methods=["POST"])
@login_required
def network_delete(network_id):
    network = Network.query.filter_by(id=network_id).first()
    if not network:
        return jsonify({"category": "danger", "message": "Network not found"}), 404
    message = helpers.remove_peers_all(network.id)
    db.session.delete(network)
    db.session.commit()
    message += f"\nNetwork deleted successfully"
    category = "success"
    return jsonify({"category": category, "message": message})


@networks.route("/activate/<int:network_id>", methods=["POST"])
@login_required
def network_activate(network_id):
    try:
        message = network_service.activate_network(
            network_id,
            request.form.get("sudoPassword") or current_app.config["SUDO_PASSWORD"],
        )
        return jsonify({"category": "success", "message": message})
    except (ValidationError, EntityNotFoundError) as exc:
        return jsonify({"category": "warning", "message": str(exc)})
    except CommandExecutionError as exc:
        return jsonify({"category": "danger", "message": f"Error activating network: {exc}"})


@networks.route("/deactivate/<int:network_id>", methods=["POST"])
@login_required
def network_deactivate(network_id):
    try:
        message = network_service.deactivate_network(
            network_id,
            request.form.get("sudoPassword") or current_app.config["SUDO_PASSWORD"],
        )
        return jsonify({"category": "success", "message": message})
    except (ValidationError, EntityNotFoundError) as exc:
        return jsonify({"category": "warning", "message": str(exc)})
    except CommandExecutionError as exc:
        return jsonify({"category": "danger", "message": f"Error deactivating network: {exc}"})


@networks.route("/api/<int:network_id>", methods=["POST", "GET", "PATCH", "DELETE"])
@login_required
def network_api(network_id):
    if request.method == "GET":
        if network_id == 0:
            return jsonify([network.to_dict() for network in Network.query.all()])
        network = Network.query.get(network_id)
        if not network:
            return jsonify({"error": "Network not found"}), 404
        return jsonify(network.to_dict())
    elif request.method == "PATCH":
        network = Network.query.get(network_id)
        if not network:
            return jsonify({"error": "Network not found"}), 404
        for key, value in (request.json or {}).items():
            setattr(network, key, value)
        db.session.commit()
        return jsonify(network.to_dict())
    elif request.method == "DELETE":
        network = Network.query.get(network_id)
        if not network:
            return jsonify({"error": "Network not found"}), 404
        db.session.delete(network)
        db.session.commit()
        return jsonify({"message": "Network removed from database"})
    return jsonify({"error": "Invalid request method"}), 405

@networks.route("/api/ip/<int:network_id>", methods=["GET"])
@login_required
def network_ip(network_id):
    ip_dict = helpers.get_available_ip(network_id)
    return jsonify(ip_dict)