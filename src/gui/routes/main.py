from flask import Blueprint, current_app, flash, redirect, render_template, session, url_for
from flask_login import login_required, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from gui.models import db, User
from gui.oidc import oidc
from gui.models import User
from logger import Logger

logger = Logger().get_logger()

main = Blueprint('main', __name__)

## ROUTES ##

# Route for the home page
@main.route("/")
def index():
    # Check to see if the admin user has been created yet
    user_count = User.query.count()
    if user_count == 0:
        message = "No users found. Please create an admin user."
        flash(message, "warning")
        return redirect(url_for("users.register", admin=True))
    if oidc.user_loggedin:
        logger.info(f"OIDC user logged in: {oidc.user_loggedin}")
        user_info = session['oidc_auth_profile']
        logger.info("User is already logged in.")
        # Check if the user exists in the local DB
        user = User.query.filter_by(auth_id=user_info["sub"]).first()
        logger.debug(f"User found: {user}")
        if not user:
            # Optionally create a new user if not found in the local DB
            new_user = User(
                email=user_info["email"],
                username=user_info["name"].lower(),
                auth_id=user_info["sub"],
                password=generate_password_hash(""),  # Dummy password
            )
            db.session.add(new_user)
            db.session.commit()
            user = new_user
            flash(f"Welcome {user.username}, your account has been created.", "success")
        
        login_user(user)

        
    return render_template("index.html")

# Route for the about page
@main.route("/about")
def about():
    version = current_app.__version__
    return render_template("about.html", version=version)


# Route for the user profile page
@main.route('/profile')
@oidc.require_login
def profile():
    if oidc.user_loggedin:
        user_info = session.get("oidc_auth_profile")
        return render_template('profile.html', current_user=user_info)
    else:
        flash("You need to log in to access this page", "warning")
        return redirect(url_for("main.index"))

# Route for testing purposes - Delete when dev work completed
@main.route("/test")
def test():
    if oidc.user_loggedin:
        user_info = session.get("oidc_auth_profile")
        message = f"Claims:{user_info}"
    else:
        message = "Test Message"
    flash(message, "success")
    return render_template("test.html")