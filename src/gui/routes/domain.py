from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import login_required, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from gui.models import db, Domain
from gui.oidc import oidc
from logger import Logger

logger = Logger().get_logger()

domains = Blueprint('domains', __name__, url_prefix="/domains")

## ROUTES ##

# Route for the home page
@domains.route("/")
def domains_all():
    return render_template("domains.html")

@domains.route("/api/<int:domain_id>", methods=["POST", "GET", "PATCH", "DELETE"])
@login_required
def domain_api(domain_id):
    if request.method == "GET":
        if domain_id == 0:
            return jsonify([domain.to_dict() for domain in Domain.query.all()])
        return jsonify(Domain.query.get(domain_id).to_dict())
    elif request.method == "POST":
        try:
            db.session.add(Domain(**request.json))
            db.session.commit()
            logger.debug(f"Domain {request.json['name']} added to database")
            flash(f"Domain {request.json['name']} added to database", "success")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding domain: {str(e)}")
            flash(f"Error adding domain: {str(e)}", "danger")
    elif request.method == "PATCH":
        message = f"Updating network {domain_id}\n"
        domain = Domain.query.get(domain_id)
        # If database
        for key, value in request.json.items():
            setattr(domain, key, value)
        db.session.commit()
        message += "Domain updated in database"
        flash(message, "success")
        return jsonify(domain)
    elif request.method == "DELETE":
        message = f"Deleting domain {domain_id}\n"
        network = Domain.query.get(domain_id)
        # If server
        db.session.delete(network)
        db.session.commit()
        message += "Network removed from database"
        flash(message, "success")
        return jsonify(message)
    else:
        return jsonify("Invalid request method")