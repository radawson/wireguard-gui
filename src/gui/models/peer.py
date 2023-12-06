from .database import db
from flask_marshmallow import Marshmallow
import json

from wireguard_tools import WireguardKey

ma = Marshmallow()


# Create models
class Peer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    private_key = db.Column(db.String(50))
    address = db.Column(db.String(50))  # This is the IP address of the peer without subnet
    subnet = db.Column(db.Integer, default=32)      # This is the subnet for the Peer address
    listen_port = db.Column(db.Integer)
    lighthouse = db.Column(db.Boolean, default=False) # Is this a lighthouse peer?
    dns = db.Column(db.String(50))      # A peer could have a specific DNS requirement but generally leave it to the network config
    peers_list = db.Column(db.Text)
    network = db.Column(db.Integer)
    post_up = db.Column(db.Text)
    post_down = db.Column(db.Text)
    description = db.Column(db.Text)
    active = db.Column(db.Boolean, default=False)

    def get_peers(self):
        j_config = json.loads(self.peers_list)
        peers = []
        for peer in j_config:
            wg_config = f"[Peer]\nPublicKey = {peer['public_key']}\n"
            allowed_ips = peer["allowed_ips"]
            if len(allowed_ips) > 0:
                wg_config += f"AllowedIPs = {peer['allowed_ips']}\n"
            if peer["endpoint_host"]:
                wg_config += f"Endpoint = {peer['endpoint_host']}:{peer['endpoint_port']}\n"
            if peer["persistent_keepalive"]:
                wg_config += f"PersistentKeepalive = {peer['persistent_keepalive']}\n"
            if peer["preshared_key"]:
                wg_config += f"PresharedKey = {peer['preshared_key']}\n"
            
            peers.append(wg_config)
        return peers
    
    def get_public_key(self):
        public_key = WireguardKey(self.private_key).public_key()
        return public_key
    
    def is_lighthouse(self):
        return self.lighthouse
    
# JSON Schema
class PeerSchema(ma.Schema):
    class Meta:
        fields = ("id", "name", "private_key", "peers_list", "network", "description", "active")


peer_schema = PeerSchema()
peers_schema = PeerSchema(many=True)


def peer_load_test_db():
    # Dummy list for testing
    peer_list = [
        {
            "name": "peer 1",
            "address": "10.10.11.11/32",
            "private_key": "iISiPbGn4wSPhloFOtDN2BgqfJ1MqKKkmm0WtWc9sFE=",
            "dns": "10.10.11.53",
            "peers_list": [{
                "Endpoint": "myserver.dyndns.org:51820",
                "AllowedIPs": ["10.10.11.0/24"],
                "PublicKey": "iISiPbGn4wSPhloFOtDN2BgqfJ1MqKKkmm0WtWc9sFE=",
                "PersistentKeepalive": 25,
                "Endpoint": "myserver.dyndns.org:51820",
            }],
            "network": 1,
            "description": "description 1",
            "active": True,
        },
        {
            "name": "peer 2",
            "address": "10.10.11.18/32",
            "private_key": "iISiPl0n4wSPhloFOtDN2BgqfJ1MqKKkmm0WtWc9sFE=",
            "dns": "10.10.11.53",
            "peers_list": [{
                    "AllowedIPs": ["0.0.0.0/0", "::/0"],
                    "PublicKey": "iISiPbGn4wSPhloFOtDN2BgqfJ1MqKKkmm0WtWc9sFE=",
                    "PersistentKeepalive": 25,
                    "Endpoint": "myserver.dyndns.org:51820",
                }],
            "network": 1,
            "description": "description 2",
        },
        {
            "name": "peer 3",
            "address": "10.10.11.19/32",
            "private_key": "YHmRePvK5Eay19KJe7QYcgNUgKEL4ky5X1xql+UhEGo=",
            "dns": "10.10.11.53",
            "peers_list": {
                    "AllowedIPs": ["0.0.0.0/0", "::/0"],
                    "PublicKey": "iISiPbGn4wSPhloFOtDN2BgqfJ1MqKKkmm0WtWc9sFE=",
                    "PersistentKeepalive": 25,
                    "Endpoint": "myserver.dyndns.org:51820",
                },
            "network": 1,
            "description": "RasPi honeypot",
        },
        {
            "name": "server 1",
            "address": "10.10.11.1/32",
            "private_key": "wBIQfi2Z+DFhAW7Z57tqVTyG/z1MQpzNwGlWrAcF2F4=",
            "listen_port": 51820,
            "dns": "10.10.11.53",
            "lighthouse": True,
            "peers_list": {
                    "AllowedIPs": ["0.0.0.0/0", "::/0"],
                    "PublicKey": "iISiPbGn4wSPhloFOtDN2BgqfJ1MqKKkmm0WtWc9sFE=",
                    "PersistentKeepalive": 25,
                    "Endpoint": "myserver.dyndns.org:51820",
                },
            "network": 1,
            "description": "Auto-generated peer for the lighthouse",
        },
        {
            "name": "server 2",
            "address": "172.122.88.1/32",
            "private_key": "KIy+vrfZDJ5KqHm0qrLK58Mqy5iV2OKx+l/vKXfTaXI=",
            "listen_port": 51820,
            "dns": "172.122.88.53",
            "lighthouse": True,
            "peers_list": {
                    "AllowedIPs": ["0.0.0.0/0", "::/0"],
                    "PublicKey": "iISiPbGn4wSPhloFOtDN2BgqfJ1MqKKkmm0WtWc9sFE=",
                    "PersistentKeepalive": 25,
                    "Endpoint": "myserver.dyndns.org:51820",
                },
            "network": 2,
            "description": "Auto-generated peer for the lighthouse",
        },
        {
            "name": "server 3",
            "address": "192.168.43.1/32",
            "private_key": "aHt3pJBwvbcvlA8sXDCsWuN3tRs20kg8nR8Z4kyayGA=",
            "listen_port": 51820,
            "lightouse": True,
            "peers_list": {
                    "AllowedIPs": ["192.168.43.0/24"],
                    "PublicKey": "OIa8lH814Mzuo1oIT+AQpe8Wm/9JEIf3Tg6g7t5e1k8=",
                    "PersistentKeepalive": 25,
                    "Endpoint": "myserver.dyndns.org:51820",
                },
            "network": 3,
            "description": "Auto-generated peer for the lighthouse",
        },
    ]
    for peer in peer_list:
        peer["peers_list"] = json.dumps(peer["peers_list"])   
    db.session.bulk_insert_mappings(Peer, peer_list)
    db.session.commit()
