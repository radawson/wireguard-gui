from flask import Blueprint, render_template, request
from gui.models import db, Peer, Network
import json

# Testing wg input
import wireguard_tools as wgt

devices = wgt.WireguardDevice.list()

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

## FUNCTIONS ##

# print(peer_list)
def query_all_peers():
    peer_query = Peer.query.all()
    for peer in peer_query:
        peer.public_key = wgt.WireguardKey(
            peer.private_key
        ).public_key()
    return peer_query

def query_all_networks():
    network_query = Network.query.all()
    return network_query


## ROUTES ##


@peers.route("/", methods=["GET", "POST", "DELETE", "PATCH"])
def peers_all():
    if request.method == "POST":
        message = "Bulk peers added successfully"
        peer_list = query_all_peers()
        return render_template("peers.html", message=message, peer_list=peer_list)

    elif request.method == "GET":
        network_id = request.args.get('network_id')
        if network_id:
            peer_list = Peer.query.filter_by(network=network_id).all()
        else:
            peer_list = query_all_peers()
        return render_template("peers.html", peer_list=peer_list)
    else:
        message = "Invalid request method"
        return render_template("peers.html", message=message, peer_list=peer_list)


@peers.route("/add", methods=["GET", "POST"])
def peers_add():
    network_list = query_all_networks()
    new_peer = {}
    new_peer["config"] = sample_config
    new_peer["public_key"] = ""
    new_peer["network"] = 1
    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        private_key = request.form["private_key"]
        address = request.form["address"]
        dns = request.form["dns"]
        #peer_config = request.form["peer_config"]
        network = request.form["network"]

        new_peer = Peer(
            name=name,
            private_key=private_key,
            address=address,
            dns=dns,
            #peer_config=peer_config,
            network=network,
            description=description,
        )
        db.session.add(new_peer)
        db.session.commit()
        message = "Peer added successfully"
        peer_list = query_all_peers()
        return render_template("peers.html", message=message, peer_list=peer_list)
    else:
        return render_template(
            "peer_detail.html",
            networks=network_list,
            peer=new_peer,
            s_button="Add",
        )


@peers.route("/<int:peer_id>", methods=["GET", "POST"])
def peer_detail(peer_id):
    #peer = next((item for item in peer_list if item["id"] == int(peer_id)), None)
    peer = Peer.query.filter_by(id=peer_id).first()
    print(f"Found: {peer}")

    if request.method == "POST":
        peer.name = request.form["name"]
        peer.description = request.form["description"]
        peer.private_key = request.form["private_key"]
        peer.address = request.form["address"]
        peer.dns = request.form["dns"]
        #peer_config = request.form["peer_config"]
        peer.network = request.form["network"]
        print(f"Peer network ID {peer.network}")
      
        db.session.commit()
        message = "Peer updated successfully"
        peer_list = query_all_peers()
        return render_template("peers.html", message=message, peer_list=peer_list)

    elif request.method == "GET":
            return render_template(
            "peer_detail.html",
            networks=query_all_networks(),
            peer=peer,
            s_button="Update",
        )
    else:
        message = "Invalid request method"
        return render_template("peer_detail.html", peer=peer, message=message)
