import os
from pathlib import Path

from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
import yaml

from .routes import dashboard, main, networks, peers, settings, users, wizard

version = "0.3.3b0"

def _load_config(config_path: str, basedir: str) -> dict:
    with open(config_path, encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file) or {}
    for key, value in config.items():
        if isinstance(value, str):
            config[key] = value.format(basedir=basedir)
    return config


def create_app(config_path: str | None = None, initialize_side_effects: bool = True):
    basedir = os.getcwd()
    app = Flask(__name__)
    CORS(app)
    app.basedir = basedir
    app.__version__ = version

    config_file = config_path or "config.yaml"
    app.config.update(_load_config(config_file, basedir))
    app.config.setdefault("AUTO_CREATE_DB", True)

    app.config["LINUX"] = str(os.name) == "posix"

    if initialize_side_effects:
        from .routes import helpers

        cert_path = Path(app.config["PKI_CERT_PATH"])
        cert_path.mkdir(parents=True, exist_ok=True)
        cert_file = cert_path / app.config["PKI_CERT"]
        key_file = cert_path / app.config["PKI_KEY"]
        if not cert_file.exists() or not key_file.exists():
            helpers.generate_cert(app.config["PKI_CERT_PATH"], app.config["PKI_CERT"], app.config["PKI_KEY"])

    @app.context_processor
    def inject_mode():
        return dict(mode=app.config["MODE"])

    from .models import db

    db.init_app(app)
    Migrate(app, db)

    if app.config.get("AUTO_CREATE_DB", True):
        with app.app_context():
            db.create_all()

    from flask_login import LoginManager

    login_manager = LoginManager()
    login_manager.login_view = "user.login"
    login_manager.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    app.register_blueprint(dashboard)
    app.register_blueprint(main)
    app.register_blueprint(networks)
    app.register_blueprint(peers)
    app.register_blueprint(settings)
    app.register_blueprint(users)
    app.register_blueprint(wizard)

    return app
