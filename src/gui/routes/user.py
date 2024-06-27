from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from gui.models import db, User

users = Blueprint("user", __name__)


## ROUTES ##
@users.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("name").lower()
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.')
            return redirect(url_for('user.login'))
        login_user(user, remember=remember)
        return redirect(url_for("main.index"))
    else:
        return render_template("login.html")


@users.route("/logout")
@login_required
def logout():
    logout_user()
    # Redirect to home page
    return redirect(url_for("main.index"))


@users.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        username = request.form.get("name").lower()
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash('Passwords do not match')
            return redirect(url_for("user.register"))

        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists')
            return redirect(url_for("user.login"))

        new_user = User(
            email=email,
            username=username,
            password=generate_password_hash(password),          
        )

        db.session.add(new_user)
        db.session.commit()
        message = f"User {new_user.username} added successfully"
        flash(message, "success")
        return redirect(url_for("user.login"))
    else:
        if request.args.get("admin") == "True":
            return render_template("register.html", admin=True)
        else:
            return render_template("register.html")

@users.route("/api/<int:user_id>", methods=["GET", "POST", "PATCH", "DELETE"])
@login_required
def user_api(user_id):
    if request.method == "GET":
        if user_id == 0:
            return jsonify([user.to_dict() for user in User.query.all()])
        return jsonify(User.query.get(user_id))
    elif request.method == "POST":
        return jsonify("POST method not allowed yet"), 405
    elif request.method == "PATCH":
        return jsonify("PATCH method not allowed yet"), 405
    elif request.method == "DELETE":
        user = User.query.get(user_id)
        if user:
            db.session.delete(user)
            db.session.commit()
            return jsonify("User deleted successfully")
        else:
            return jsonify("User not found"), 404
    else:
        return jsonify("Invalid request method"), 405