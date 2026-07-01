from flask import Blueprint, render_template, redirect, url_for, flash, abort, current_app
from flask_login import login_required, current_user
from functools import wraps

from forms import DeleteForm
from models import User, WorkoutSession, ExerciseEntry, Meal, PersonalRecord, PredictionLog
from utils import get_orphan_exercises, delete_orphan_exercises

from extensions import db

admin_bp = Blueprint("admin", __name__)


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not (
            getattr(current_user, "is_admin", False)
            or getattr(current_user, "role", None) == "admin"
            or (hasattr(current_user, "has_role") and current_user.has_role("admin"))
        ):
            abort(403)

        return func(*args, **kwargs)

    return wrapper


@admin_bp.route("/admin/debug")
@login_required
@admin_required
def admin_debug():
    limit = current_app.config.get("DEBUG_ROW_LIMIT", 50)

    users = User.query.order_by(User.id.asc()).limit(limit).all()
    sessions = WorkoutSession.query.order_by(WorkoutSession.id.desc()).limit(limit).all()
    exercises = ExerciseEntry.query.order_by(ExerciseEntry.id.desc()).limit(limit).all()
    meals = Meal.query.order_by(Meal.id.desc()).limit(limit).all()
    prs = PersonalRecord.query.order_by(PersonalRecord.id.desc()).limit(limit).all()
    prediction_logs = PredictionLog.query.order_by(PredictionLog.id.desc()).limit(limit).all()

    orphan_exercises = get_orphan_exercises()

    stats = {
        "users": User.query.count(),
        "sessions": WorkoutSession.query.count(),
        "exercises": ExerciseEntry.query.count(),
        "meals": Meal.query.count(),
        "prs": PersonalRecord.query.count(),
        "predictions": PredictionLog.query.count(),
        "orphan_exercises": len(orphan_exercises),
    }

    delete_form = DeleteForm()

    return render_template(
        "admin_debug.html",
        users=users,
        sessions=sessions,
        exercises=exercises,
        meals=meals,
        prs=prs,
        prediction_logs=prediction_logs,
        orphan_exercises=orphan_exercises,
        stats=stats,
        delete_form=delete_form,
    )


@admin_bp.route("/admin/cleanup-orphans", methods=["POST"])
@login_required
@admin_required
def cleanup_orphans():
    delete_form = DeleteForm()

    if not delete_form.validate_on_submit():
        abort(400)

    deleted_count = delete_orphan_exercises()

    flash(f"Deleted {deleted_count} orphan exercise record(s).")
    return redirect(url_for("admin.admin_debug"))
