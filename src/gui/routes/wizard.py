import ipaddress
import json

from flask_login import login_required
from gui.routes import helpers
from flask import (
    Blueprint,
    current_app,
    flash,
    render_template,
    request,
)
from ..models import db, Network, Peer, subnets
from wireguard_tools import WireguardKey
from logger import Logger

logger = Logger().get_logger()


wizard = Blueprint("wizard", __name__, url_prefix="/wizard")


### Element Functions ###
def create_network(
    active: bool = False,
    adapter_name: str = "",
    allowed_ips: str = "",
    base_ip: str = "",
    dns_server: str = "",
    description: str = "",
    lighthouse: list = [],
    name: str = "",
    peers_list: list = [],
    persistent_keepalive: int = 25,
    private_key: str = "",
    proxy: bool = False,
    subnet: int = 32,
) -> Network:
    try:
        new_network = Network(
            active=active,
            adapter_name=adapter_name,
            allowed_ips=allowed_ips,
            base_ip=base_ip,
            dns_server=dns_server,
            description=description,
            lighthouse=lighthouse,
            name=name,
            peers_list=peers_list,
            persistent_keepalive=persistent_keepalive,
            private_key=private_key,
            proxy=proxy,
            subnet=subnet,
        )

    except Exception as e:
        logger.error(f"Error creating network: {str(e)}")
        raise e
    else:
        logger.info(f"Network {name} created successfully")

    # Add the new network to the database
    try:
        db.session.add(new_network)
        db.session.commit()
    except Exception as e:
        logger.error(f"Error adding network to database: {str(e)}")
        raise e
    else:
        logger.info(f"Network {name} added to database")
        return new_network


def create_peer(
    active: bool = False,
    description: str = "",
    dns: str = "",
    endpoint_host: str = "",
    listen_port: int = None,
    name: str = "",
    network_ip: str = "",  # This is the IP address of the peer without subnet
    lighthouse: bool = False,  # Is this a lighthouse peer?
    network_id: int = 0,  # network: Mapped["Network"] = relationship(back_populates="peers_list")
    peers_list: str = "",
    post_up: str = "",
    post_down: str = "",
    preshared_key: str = "",
    private_key: str = "",
    subnet: int = 32,
) -> Peer:

    new_peer = Peer(
        active=active,
        description=description,
        endpoint_host=endpoint_host,
        listen_port=listen_port,
        name=name,
        network_ip=network_ip,
        lighthouse=lighthouse,
        network_id=network_id,
        peers_list=peers_list,
        post_up=post_up,
        post_down=post_down,
        preshared_key=preshared_key,
        private_key=private_key,
        subnet=subnet,
    )

    if dns:
        new_peer.dns = dns

    # Add the new peer to the database
    try:
        db.session.add(new_peer)
        db.session.commit()
    except Exception as e:
        logger.error(f"Error adding peer: {str(e)}")
        raise e
    else:
        logger.info(f"Peer {name} added to database")
        return new_peer


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
    if int(subnet) not in range(0, 33):
        message = "Please enter a valid subnet"
        flash(message, "warning")
        return render_template("wizard_setup.html", defaults=defaults, subnets=subnets)
    listen_port = defaults["base_port"]

    # Append CIDR subnet to base_ip
    allowed_ips = base_ip + "/" + str(subnet)

    # Get the IP address of the current machine
    endpoint_host = helpers.get_public_ip()

    # Create a private key for the lighthouse
    new_key = WireguardKey.generate()
    private_key = str(new_key)

    # Get adapter name from rotation
    adapter_name = "wg0"

    # Create a lighthouse first
    # Create a new peer object
    # The lighthouse is always the first peer in the network
    lh_address = Network.append_ip(base_ip, 1)

    # Get adapter names for the machine
    adapters = helpers.get_adapter_names()
    print(f"Adapters found:{adapters}")

    post_up_string = f"iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o {adapters[0]} -j MASQUERADE"
    post_down_string = f"iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o {adapters[0]} -j MASQUERADE"

    if dns:
        new_dns = dns
    else:
        new_dns = None

    # Create a new network 
    # TODO: fix config name rotation
    lighthouse_list = []
    try:
        new_network = create_network(
            active=False,
            adapter_name=adapter_name,
            allowed_ips=allowed_ips,
            base_ip=base_ip,
            dns_server=dns,
            description=description,
            lighthouse=lighthouse_list,
            name=name,
            peers_list=[],
            persistent_keepalive=25,
            private_key=private_key,
            proxy=False,
            subnet=subnet,
        )
    except Exception as e:
        message += f"\nError creating network: {str(e)}"
        flash(message, "danger")
        logger.error(message)
        return render_template("wizard_setup.html", defaults=defaults, subnets=subnets)

    # Create the lighthouse peer
    try:
        new_peer = create_peer(
            active=False,
            description="Auto-generated peer for the lighthouse",
            dns=new_dns,
            endpoint_host=endpoint_host,
            listen_port=listen_port,
            name=f"Lighthouse server for {name}",
            network_ip=lh_address,
            lighthouse=True,
            network_id=new_network.id,
            peers_list="",
            post_up=post_up_string,
            post_down=post_down_string,
            preshared_key="",
            private_key=private_key,
            subnet=subnet,
        )
    except Exception as e:
        message += f"\nError creating lighthouse: {str(e)}"
        flash(message, "danger")
        logger.error(message)
        return render_template("wizard_setup.html", defaults=defaults, subnets=subnets)
    else:
        message += "Lighthouse added to database\n"
        logger.info(message)

    new_peer.network = new_network  # Assign the network object, not just the ID
    new_network.lighthouse.append(new_peer)  # Add the peer to the network's lighthouse list

    # Update the database
    try:
        db.session.commit()
    except Exception as e:
        message += f"\nError updating database: {str(e)}"
        flash(message, "danger")
        logger.error(message)
        return render_template("wizard_setup.html", defaults=defaults, subnets=subnets)
    message += "\nPeer network updated"

    if current_app.config["MODE"] == "server":
        # Create the adapter configuration file
        adapter_string = helpers.config_build(new_peer, new_network)

        if helpers.config_save(adapter_string, "server", "wg0.conf"):
            message += "\nNetwork config saved successfully"
        else:
            message += "\nError creating network config file"
        networks = Network.query.all()

        # check if wireguard is installed
        if helpers.check_wireguard(sudo_password):
            try:
                helpers.run_sudo(
                    f"cp {current_app.basedir}/output/server/wg0.conf /etc/wireguard/wg0.conf",
                    sudo_password,
                )
            except Exception as e:
                print(e)
                message += (
                    "\nError copying configuration file to /etc/wireguard/wg0.conf"
                )
            else:
                message += "\nConfiguration file copied to /etc/wireguard/wg0.conf"
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
