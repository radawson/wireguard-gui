from flask import Blueprint, current_app, flash, redirect, render_template, session, url_for
from flask_login import current_user, login_required
from gui.oidc import oidc
from gui.models import User

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