from .database import db
from flask_marshmallow import Marshmallow
from marshmallow import fields

ma = Marshmallow()

# Create models
class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_key = db.Column(db.String(50), nullable=False)
    preshared_key = db.Column(db.String(50))
    endpoint_host = db.Column(db.String(50))
    endpoint_port = db.Column(db.Integer)
    persistent_keepalive = db.Column(db.Integer)
    allowed_ips = db.Column(db.String(50))
    friendly_name = db.Column(db.String(50))
    friendly_json = db.Column(db.String(50))
    last_handshake = db.Column(db.Float)
    rx_bytes = db.Column(db.Integer)
    tx_bytes = db.Column(db.Integer)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp())

# JSON Schema
class ConfigSchema(ma.Schema):
    id = fields.Int()
    public_key = fields.Str()
    preshared_key = fields.Str(allow_none=True)
    endpoint_host = fields.Str(allow_none=True)
    endpoint_port = fields.Int(allow_none=True)
    persistent_keepalive = fields.Int(allow_none=True)
    allowed_ips = fields.Str(allow_none=True)
    friendly_name = fields.Str(allow_none=True)
    friendly_json = fields.Str(allow_none=True)
    last_handshake = fields.Float(allow_none=True)
    rx_bytes = fields.Int(allow_none=True)
    tx_bytes = fields.Int(allow_none=True)
    description = fields.Str(allow_none=True)


config_schema = ConfigSchema()
configs_schema = ConfigSchema(many=True)

def config_load_test_db():
    pass