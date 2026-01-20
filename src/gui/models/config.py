from .database import db

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

def config_load_test_db():
    pass