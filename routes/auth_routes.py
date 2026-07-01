from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user

from extensions import bcrypt, db, get_redis_client
from forms import LoginForm, RegisterForm
from models import User
from utils import (
    LOGIN_ATTEMPTS,
    LOGIN_WINDOW_SECONDS,
    LOCKOUT_SECONDS,
    MAX_LOGIN_ATTEMPTS,
)


auth_bp = Blueprint("auth", __name__)


def get_client_ip():
    forwarded_for = request.headers.get("X-Forwarded-For", "")

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return request.remote_addr or "unknown"


def lock_message(remaining_seconds):
    remaining_minutes = max(1, round(remaining_seconds / 60))

    return (
        f"Too many failed login attempts. You are blocked for "
        f"about {remaining_minutes} minute(s). Please try again later."
    )


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    redis_client = get_redis_client()

    submitted_username = ""
    username_key = ""

    if request.method == "POST":
        submitted_username = (request.form.get("username") or "").strip()
        username_key = submitted_username.lower()

    client_ip = get_client_ip()
    ip_key = f"ip:{client_ip}"
    now_ts = datetime.utcnow().timestamp()

    # Check lockout before validating username/password.
    if request.method == "POST":
        if redis_client:
            try:
                redis_username_lock_key = f"login:user:{username_key}:locked"
                redis_ip_lock_key = f"login:{ip_key}:locked"

                if username_key and redis_client.get(redis_username_lock_key):
                    remaining_seconds = redis_client.ttl(redis_username_lock_key)

                    if remaining_seconds is None or remaining_seconds < 0:
                        remaining_seconds = LOCKOUT_SECONDS

                    flash(lock_message(remaining_seconds))
                    return render_template("login.html", form=form)

                if redis_client.get(redis_ip_lock_key):
                    remaining_seconds = redis_client.ttl(redis_ip_lock_key)

                    if remaining_seconds is None or remaining_seconds < 0:
                        remaining_seconds = LOCKOUT_SECONDS

                    flash(lock_message(remaining_seconds))
                    return render_template("login.html", form=form)

            except Exception:
                redis_client = None

        if not redis_client:
            lockout_keys = []

            if username_key:
                lockout_keys.append(f"user:{username_key}")

            lockout_keys.append(ip_key)

            for key in lockout_keys:
                entry = LOGIN_ATTEMPTS.get(key)

                if not entry:
                    continue

                locked_until = entry.get("locked_until")

                if locked_until and now_ts < locked_until:
                    remaining_seconds = int(locked_until - now_ts)
                    flash(lock_message(remaining_seconds))
                    return render_template("login.html", form=form)

                if locked_until and now_ts >= locked_until:
                    LOGIN_ATTEMPTS.pop(key, None)

    if form.validate_on_submit():
        password = form.password.data or ""
        user = User.query.filter_by(username=submitted_username).first()

        if user and bcrypt.check_password_hash(user.password, password):
            # Successful login clears failed attempts for this username and IP.
            if redis_client:
                try:
                    redis_client.delete(f"login:user:{username_key}:count")
                    redis_client.delete(f"login:user:{username_key}:locked")
                    redis_client.delete(f"login:{ip_key}:count")
                    redis_client.delete(f"login:{ip_key}:locked")
                except Exception:
                    pass

            LOGIN_ATTEMPTS.pop(f"user:{username_key}", None)
            LOGIN_ATTEMPTS.pop(ip_key, None)

            login_user(user)
            flash("Logged in successfully.", "auth")
            return redirect(url_for("dashboard"))

        # Failed login attempt using Redis.
        if redis_client:
            try:
                failed_keys = []

                if username_key:
                    failed_keys.append(f"user:{username_key}")

                failed_keys.append(ip_key)

                locked_now = False
                highest_count = 0

                for key in failed_keys:
                    count_key = f"login:{key}:count"
                    locked_key = f"login:{key}:locked"

                    count = redis_client.incr(count_key)

                    if count == 1:
                        redis_client.expire(count_key, LOGIN_WINDOW_SECONDS)

                    highest_count = max(highest_count, int(count))

                    if count >= MAX_LOGIN_ATTEMPTS:
                        redis_client.setex(locked_key, LOCKOUT_SECONDS, "1")
                        locked_now = True

                if locked_now:
                    flash(lock_message(LOCKOUT_SECONDS))
                else:
                    attempts_left = max(0, MAX_LOGIN_ATTEMPTS - highest_count)

                    flash(
                        f"Invalid username or password. "
                        f"{attempts_left} attempt(s) remaining."
                    )

            except Exception:
                redis_client = None

        # Failed login attempt using in-memory fallback.
        if not redis_client:
            failed_keys = []

            if username_key:
                failed_keys.append(f"user:{username_key}")

            failed_keys.append(ip_key)

            locked_now = False
            highest_count = 0

            for key in failed_keys:
                entry = LOGIN_ATTEMPTS.get(
                    key,
                    {
                        "count": 0,
                        "first": now_ts,
                        "locked_until": None,
                    },
                )

                if now_ts - entry.get("first", now_ts) > LOGIN_WINDOW_SECONDS:
                    entry = {
                        "count": 0,
                        "first": now_ts,
                        "locked_until": None,
                    }

                entry["count"] = entry.get("count", 0) + 1
                highest_count = max(highest_count, entry["count"])

                if entry["count"] >= MAX_LOGIN_ATTEMPTS:
                    entry["locked_until"] = now_ts + LOCKOUT_SECONDS
                    locked_now = True

                LOGIN_ATTEMPTS[key] = entry

            if locked_now:
                flash(lock_message(LOCKOUT_SECONDS))
            else:
                attempts_left = max(0, MAX_LOGIN_ATTEMPTS - highest_count)

                flash(
                    f"Invalid username or password. "
                    f"{attempts_left} attempt(s) remaining."
                )

    elif request.method == "POST":
        flash(f"Login form did not validate: {form.errors}")

    return render_template("login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        username = (form.username.data or "").strip()
        password = form.password.data or ""

        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            flash("That username already exists. Please choose a different one.")
            return render_template("register.html", form=form)

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        new_user = User()
        new_user.username = username
        new_user.password = hashed_password
        new_user.role = "user"
        new_user.is_admin = False

        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully. Please log in.")
        return redirect(url_for("auth.login"))

    elif request.method == "POST":
        flash(f"Register form did not validate: {form.errors}")

    return render_template("register.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.")
    return redirect(url_for("auth.login"))