from __future__ import annotations
import json
import ipaddress

from typing import List
from wireguard_tools import WireguardKey
from .database import db
from .peer import Peer
from flask_marshmallow import Marshmallow
from sqlalchemy.orm import Mapped, mapped_column, relationship

ma = Marshmallow()

# Association table
# lighthouse_table = db.Table(
#     "lighthouses",
#     db.Column("domain_id", db.Integer, db.ForeignKey("domain.id")),
#     db.Column("provider_id", db.Integer, db.ForeignKey("provider.id")),
# )


# Domain Model
class Domain(db.Model):
    __tablename__ = "domain"
    id: Mapped[int] = mapped_column(primary_key=True)  # type: ignore
    name = db.Column(db.String(50))
    subdomain = db.Column(db.Integer)
    tld = db.Column(db.String(10))

    @classmethod
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

class Provider(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_key = db.Column(db.String(50), nullable=False)
    preshared_key = db.Column(db.String(50))
    endpoint_host = db.Column(db.String(50))
    endpoint_port = db.Column(db.Integer)
    persistent_keepalive = db.Column(db.Integer)
    allowed_ips = db.Column(db.String(50))


# JSON Schema
class NetworkSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "active",
            "adapter_name",
            "allowed_ips",
            "base_ip",
            "description",
            "dns_server",
            "lighthouse",
            "name",
            "peers_list",
            "persistent_keepalive",
            "private_key",
            "proxy",
            "subnet",
        )


class NetworkConfigSchema(ma.Schema):
    class Meta:
        fields = (
            "id",
            "public_key",
            "preshared_key",
            "endpoint_host",
            "endpoint_port",
            "persistent_keepalive",
            "allowed_ips",
        )


network_schema = NetworkSchema()
networks_schema = NetworkSchema(many=True)

network_config_schema = NetworkConfigSchema()
network_configs_schema = NetworkConfigSchema(many=True)


def domain_load_test_db():
    # Dummy list for testing


    domain_list = []
    db.session.bulk_insert_mappings(Domain, domain_list)
    db.session.commit()
