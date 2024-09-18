from flask import Flask
from flask_oidc import OpenIDConnect

oidc = OpenIDConnect()

def create_app():
    app = Flask(__name__)
    oidc.init_app(app)
    return app
