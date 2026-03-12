import ipaddress
import json

from flask_login import login_required
from gui.routes import helpers
from gui.errors import ValidationError
from flask import (
    Blueprint,
    current_app,
    flash,
    render_template,
    request,
)
from ..models import db, Network, Peer, subnets
from gui.services import runtime_sync_service
from wireguard_tools import WireguardKey


wizard = Blueprint("wizard", __name__, url_prefix="/wizard")


## ROUTES ##
@wizard.route("/setup", methods=["GET"])
@login_required
def setup():
    defaults = {
        "base_ip": current_app.config["BASE_IP"],
        "base_port": current_app.config["BASE_PORT"],
        "dns": current_app.config["BASE_DNS"],
    }
    return render_template("wizard_setup.html", defaults=defaults, subnets=subnets)


@wizard.route("/basic", methods=["POST"])
@login_required
def wizard_basic():
    # print(request.form)
    # Get the form data
    message = "Build Log:"
    name = request.form.get("name")
    description = request.form.get("description")
    base_ip = request.form.get("base_ip")
    subnet = request.form.get("subnet")
    sudo_password = request.form.get("sudoPassword")
    if sudo_password == "":
        sudo_password = current_app.config["SUDO_PASSWORD"]
    dns = current_app.config["BASE_DNS"]

    defaults = {
        "base_ip": current_app.config["BASE_IP"],
        "base_port": current_app.config["BASE_PORT"],
        "dns": current_app.config["BASE_DNS"],
    }

    # Test inputs
    if not name:
        message = "Please enter a name for the network"
        flash(message, "warning")
        return render_template("wizard_setup.html", defaults=defaults, subnets=subnets)
    defaults["name"] = name
    # test base_ip string to make sure it is a valid IP address
    try:
        ipaddress.ip_address(base_ip)
    except ValueError:
        message = "Please enter a valid IP address"
        flash(message, "warning")
        return render_template("wizard_setup.html", defaults=defaults, subnets=subnets)
    defaults["base_ip"] = base_ip
    # test subnet to make sure it is a valid subnet
    try:
        subnet_int = int(subnet)
    except (TypeError, ValueError):
        message = "Please enter a valid subnet"
        flash(message, "warning")
        return render_template("wizard_setup.html", defaults=defaults, subnets=subnets)
    if subnet_int not in range(0, 33):
        message = "Please enter a valid subnet"
        flash(message, "warning")
        return render_template("wizard_setup.html", defaults=defaults, subnets=subnets)
    listen_port = defaults["base_port"]

    # Append CIDR subnet to base_ip
    allowed_ips = base_ip + "/" + str(subnet_int)

    # Get the IP address of the current machine
    endpoint_host = helpers.get_public_ip()

    # Create a private key for the lighthouse
    new_key = WireguardKey.generate()
    private_key = str(new_key)

    # Get adapter name from rotation
    adapter_name = "wg0"
    if current_app.config.get("MODE") == "server":
        conflict = runtime_sync_service.get_adapter_conflict_reason(
            adapter_name,
            owner_network_id=None,
            sudo_password=sudo_password,
        )
        if conflict:
            flash(conflict, "danger")
            return render_template("wizard_setup.html", defaults=defaults, subnets=subnets)

    # Create a lighthouse first
    # Create a new peer object
    # The lighthouse is always the first peer in the network
    lh_address = Network.append_ip(base_ip, 1)

    # Get adapter names for the machine
    adapters = helpers.get_adapter_names()
    print(f"Adapters found:{adapters}")

    uplink_adapter = helpers.get_uplink_adapter()
    post_up_string = (
        f"iptables -A FORWARD -i {adapter_name} -j ACCEPT; "
        f"iptables -t nat -A POSTROUTING -o {uplink_adapter} -j MASQUERADE"
    )
    post_down_string = (
        f"iptables -D FORWARD -i {adapter_name} -j ACCEPT; "
        f"iptables -t nat -D POSTROUTING -o {uplink_adapter} -j MASQUERADE"
    )
    new_peer = Peer(
        active = False,
        description="Auto-generated peer for the lighthouse",
        endpoint_host=endpoint_host,
        listen_port=listen_port,
        lighthouse=True,
        name=f"Lighthouse server for {name}",
        network_id=0,
        network_ip=lh_address,
        peers_list = "",
        preshared_key="",
        post_up=post_up_string,
        post_down=post_down_string,
        private_key=private_key,
        subnet=subnet_int,
    )

    if dns:
        new_peer.dns = dns

    # Add the new peer to the database
    db.session.add(new_peer)
    db.session.commit()
    message += "\nPeer added to database"

    # Create a new network object
    # TODO: fix config name rotation
    lighthouse_list = [new_peer]
    new_network = Network(
        active = False,
        adapter_name=adapter_name,
        allowed_ips = allowed_ips,
        base_ip=base_ip,
        dns_server=dns,
        description=description,
        lighthouse= lighthouse_list,
        name=name,
        peers_list=[],
        persistent_keepalive=25,
        private_key=new_peer.private_key,
        proxy=False,
        subnet=subnet_int,
    )

    # Add the new network to the database
    db.session.add(new_network)
    db.session.commit()
    message += "\nNetwork added to database"

    new_peer.network_id = new_network.id

    db.session.commit()
    message += "\nPeer network updated"

    if current_app.config["MODE"] == "server":
        # Create the adapter configuration file
        adapter_string = helpers.config_build(new_peer, new_network)

        if helpers.config_save(adapter_string, "server", f"{adapter_name}.conf"):
            message += "\nNetwork config saved successfully"
        else:
            message += "\nError creating network config file"
        networks = Network.query.all()

        # check if wireguard is installed
        if helpers.check_wireguard(sudo_password):
            try:
                helpers.run_sudo(
                    f"cp {current_app.basedir}/output/server/{adapter_name}.conf /etc/wireguard/{adapter_name}.conf",
                    sudo_password,
                )
            except Exception as e:
                print(e)
                message += (
                    f"\nError copying configuration file to /etc/wireguard/{adapter_name}.conf"
                )
            else:
                message += f"\nConfiguration file copied to /etc/wireguard/{adapter_name}.conf"
        else:
            message += "\nWireguard is not installed on this machine"

        # Enable IP forwarding
        message += helpers.enable_ip_forwarding_v4(sudo_password)

    print(message)
    flash(message, "info")
    networks = Network.query.all()
    return render_template("networks.html", networks=networks)


@wizard.route("/advanced", methods=["POST"])
@login_required
def wizard_advanced():
    message = "Advanced wizard not implemented yet"
    defaults = {
        "base_ip": current_app.config["BASE_IP"],
        "base_port": current_app.config["BASE_PORT"],
        "dns": current_app.config["BASE_DNS"],
    }
    flash(message, "warning")
    return render_template("wizard_setup.html", defaults=defaults, subnets=subnets)
