from __future__ import annotations
import json
import ipaddress

from typing import List
from wireguard_tools import WireguardKey
from .database import db
from .peer import Peer
from flask_marshmallow import Marshmallow
from marshmallow import fields
from sqlalchemy.orm import Mapped, mapped_column, relationship

ma = Marshmallow()

# Association table for lighthouses
lighthouse_table = db.Table(
    "lighthouses",
    db.Column("network_id", db.Integer, db.ForeignKey("network.id")),
    db.Column("peer_id", db.Integer, db.ForeignKey("peer.id")),
)


# Network Model
class Network(db.Model):
    __tablename__ = "network"
    id: Mapped[int] = mapped_column(primary_key=True)  # type: ignore
    active = db.Column(db.Boolean, default=False)
    adapter_name = db.Column(db.String(50))
    allowed_ips = db.Column(db.String(50))
    base_ip = db.Column(db.String(50))
    description = db.Column(db.Text)
    dns_server = db.Column(db.String(50))
    lighthouse: Mapped[List[Peer]] = relationship(secondary=lighthouse_table)
    name = db.Column(db.String(50))
    peers_list: Mapped[List["Peer"]] = relationship()
    persistent_keepalive = db.Column(db.Integer)
    private_key = db.Column(db.String(50))
    proxy = db.Column(db.Boolean, default=False)
    subnet = db.Column(db.Integer)

    @classmethod
    def append_ip(self, ip, host):
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            return "Please enter a valid IP address"
        base_ip = ip.split(".")[:3]
        base_ip.append(str(host))
        result = ".".join(base_ip)
        return result

    def get_config(self):
        if len(self.lighthouse) > 0:
            lh = self.lighthouse[0]
        else:
            lh = None
        wg_config = f"[Peer]\nPublicKey = {self.get_public_key()}\n"
        if len(self.allowed_ips) > 0:
            wg_config += f"AllowedIPs = {self.allowed_ips}\n"
        if lh:
            wg_config += f"Endpoint = {lh.endpoint_host}:{lh.listen_port}\n"
        if self.persistent_keepalive:
            wg_config += f"PersistentKeepalive = {self.persistent_keepalive}\n"
        return wg_config

    def get_endpoint(self):
        lh = Peer.query.get(self.lighthouse)
        return {
            "endpoint_host": lh.endpoint_host,
            "listen_port": lh.listen_port,
            "private_key": lh.private_key,
            "public_key": self.get_public_key(lh.public_key),
        }
    
    def get_peer_count(self):
        count = len(self.peers_list)
        count += len(self.lighthouse)
        return count
    
    def get_public_key(self) -> WireguardKey:
        print(f"Lighthouse for {self.name} is {self.lighthouse}")
        if self.lighthouse:
            public_key = self.lighthouse[0].get_public_key()
        else:
            try:
                public_key = str(WireguardKey(self.private_key).public_key())
            except ValueError as e:
                public_key = None
        return public_key

    def to_dict(self):
        dict_ = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        if len(self.lighthouse) > 0:
            dict_["endpoint_host"] = self.lighthouse[0].endpoint_host
            dict_["listen_port"] = self.lighthouse[0].listen_port
        else:
            dict_["endpoint_host"] = None
            dict_["listen_port"] = None
        dict_["peer_count"] = self.get_peer_count()
        return dict_

class Network_Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_key = db.Column(db.String(50), nullable=False)
    preshared_key = db.Column(db.String(50))
    endpoint_host = db.Column(db.String(50))
    endpoint_port = db.Column(db.Integer)
    persistent_keepalive = db.Column(db.Integer)
    allowed_ips = db.Column(db.String(50))


# JSON Schema
class NetworkSchema(ma.Schema):
    id = fields.Int()
    active = fields.Bool()
    adapter_name = fields.Str(allow_none=True)
    allowed_ips = fields.Str(allow_none=True)
    base_ip = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    dns_server = fields.Str(allow_none=True)
    lighthouse = fields.List(fields.Raw(), allow_none=True)
    name = fields.Str(allow_none=True)
    peers_list = fields.List(fields.Raw(), allow_none=True)
    persistent_keepalive = fields.Int(allow_none=True)
    private_key = fields.Str(allow_none=True)
    proxy = fields.Bool()
    subnet = fields.Int(allow_none=True)


class NetworkConfigSchema(ma.Schema):
    id = fields.Int()
    public_key = fields.Str()
    preshared_key = fields.Str(allow_none=True)
    endpoint_host = fields.Str(allow_none=True)
    endpoint_port = fields.Int(allow_none=True)
    persistent_keepalive = fields.Int(allow_none=True)
    allowed_ips = fields.Str(allow_none=True)


network_schema = NetworkSchema()
networks_schema = NetworkSchema(many=True)

network_config_schema = NetworkConfigSchema()
network_configs_schema = NetworkConfigSchema(many=True)


def network_load_test_db():
    # Dummy list for testing
    network1 = Network(
        name="network 1",
        proxy=False,
        lh_ip="10.10.11.1",
        public_key="m1cSyM6Veev3vQIMYQ23gr22Qn/Vu3vg5d8xBTu43gE=",
        peers_list=json.dumps(
            [
                "kHuDnIycdQYOVpSSMLqZwfe8D9eQSElSoIdWBFz8+jo=",
            ]
        ),
        base_ip="10.10.11.0",
        subnet="24",
        adapter_name="wg0",
        dns_server="10.10.11.1",
        description="A basic /24 network",
        active=True,
    )
    network2 = Network(
        name="network 2",
        proxy=True,
        lh_ip="172.122.88.1",
        public_key="Wek3/glj4oirvt6gPw3BPL1wLrb47KxXKUwShvBNy0Y=",
        peers_list=json.dumps(["Wek3/glj4oirvt6gPw3BPL1wLrb47KxXKUwShvBNy0Y="]),
        base_ip="172.122.88.0",
        subnet="16",
        adapter_name="wg0",
        dns_server="1.1.1.1,1.1.2.2",
        description="Another network that could be slightly larger and uses the server as a proxy",
        active=False,
    )
    network3 = Network(
        name="network 3",
        proxy=False,
        lh_ip="192.168.43.1",
        public_key="OIa8lH814Mzuo1oIT+AQpe8Wm/9JEIf3Tg6g7t5e1k8=",
        peers_list=json.dumps(["OIa8lH814Mzuo1oIT+AQpe8Wm/9JEIf3Tg6g7t5e1k8="]),
        base_ip="192.168.43.0",
        subnet="24",
        adapter_name="wg0",
        description="A small, closed network",
        active=True,
    )

    network_list = [network1.__dict__, network2.__dict__, network3.__dict__]
    db.session.bulk_insert_mappings(Network, network_list)
    db.session.commit()
