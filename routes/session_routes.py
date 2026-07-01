from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user

from extensions import db
from forms import WorkoutSessionForm, ExerciseEntryForm, DeleteForm, STANDARD_EXERCISES
from models import WorkoutSession, ExerciseEntry
from utils import get_exercise_name_from_form

session_bp = Blueprint("session", __name__)


@session_bp.route("/sessions")
@login_required
def sessions():
    workout_sessions = (
        WorkoutSession.query.filter_by(user_id=current_user.id)
        .order_by(WorkoutSession.id.desc())
        .all()
    )

    delete_form = DeleteForm()

    return render_template(
        "sessions.html",
        workout_sessions=workout_sessions,
        delete_form=delete_form,
    )


@session_bp.route("/new-session", methods=["GET", "POST"])
@login_required
def new_session():
    form = WorkoutSessionForm()

    if form.validate_on_submit():
        new_workout_session = WorkoutSession()
        new_workout_session.session_name = form.session_name.data
        new_workout_session.date = form.date.data
        new_workout_session.duration_minutes = form.duration_minutes.data
        new_workout_session.focus = form.focus.data
        new_workout_session.user_id = current_user.id

        db.session.add(new_workout_session)
        db.session.commit()

        flash("Workout session created successfully.")
        return redirect(url_for("session.sessions"))

    return render_template("new_session.html", form=form)


@session_bp.route("/session/<int:session_id>")
@login_required
def view_session(session_id):
    workout_session = WorkoutSession.query.filter_by(
        id=session_id,
        user_id=current_user.id,
    ).first()

    if workout_session is None:
        abort(404)

    delete_form = DeleteForm()

    return render_template(
        "view_session.html",
        session=workout_session,
        delete_form=delete_form,
    )


@session_bp.route("/session/<int:session_id>/add-exercise", methods=["GET", "POST"])
@login_required
def add_exercise(session_id):
    workout_session = WorkoutSession.query.filter_by(
        id=session_id,
        user_id=current_user.id,
    ).first()

    if workout_session is None:
        abort(404)

    form = ExerciseEntryForm()

    if form.validate_on_submit():
        new_exercise = ExerciseEntry()
        new_exercise.exercise_name = get_exercise_name_from_form(form)
        new_exercise.sets = form.sets.data
        new_exercise.reps = form.reps.data
        new_exercise.weight = form.weight.data
        new_exercise.rpe = form.rpe.data
        new_exercise.session_id = workout_session.id

        db.session.add(new_exercise)
        db.session.commit()

        flash("Exercise added successfully.")
        return redirect(url_for("session.view_session", session_id=workout_session.id))

    return render_template(
        "add_exercise.html",
        form=form,
        session=workout_session,
    )


@session_bp.route("/exercise/<int:exercise_id>/edit", methods=["GET", "POST"])
@login_required
def edit_exercise(exercise_id):
    exercise = (
        db.session.query(ExerciseEntry)
        .join(WorkoutSession, ExerciseEntry.session_id == WorkoutSession.id)
        .filter(ExerciseEntry.id == exercise_id)
        .filter(WorkoutSession.user_id == current_user.id)
        .first()
    )

    if exercise is None:
        abort(404)

    form = ExerciseEntryForm(obj=exercise)

    if request.method == "GET" and exercise.exercise_name not in STANDARD_EXERCISES:
        form.exercise_name.data = "Other"
        form.custom_exercise_name.data = exercise.exercise_name

    if form.validate_on_submit():
        exercise.exercise_name = get_exercise_name_from_form(form)
        exercise.sets = form.sets.data
        exercise.reps = form.reps.data
        exercise.weight = form.weight.data
        exercise.rpe = form.rpe.data

        db.session.commit()

        flash("Exercise updated successfully.")
        return redirect(url_for("session.view_session", session_id=exercise.session_id))

    return render_template(
        "edit_exercise.html",
        form=form,
        exercise=exercise,
    )


@session_bp.route("/exercise/<int:exercise_id>/delete", methods=["POST"])
@login_required
def delete_exercise(exercise_id):
    delete_form = DeleteForm()

    if not delete_form.validate_on_submit():
        abort(400)

    exercise = (
        db.session.query(ExerciseEntry)
        .join(WorkoutSession, ExerciseEntry.session_id == WorkoutSession.id)
        .filter(ExerciseEntry.id == exercise_id)
        .filter(WorkoutSession.user_id == current_user.id)
        .first()
    )

    if exercise is None:
        abort(404)

    session_id = exercise.session_id

    db.session.delete(exercise)
    db.session.commit()

    flash("Exercise deleted successfully.")
    return redirect(url_for("session.view_session", session_id=session_id))


@session_bp.route("/session/<int:session_id>/edit", methods=["GET", "POST"])
@login_required
def edit_session(session_id):
    workout_session = WorkoutSession.query.filter_by(
        id=session_id,
        user_id=current_user.id,
    ).first()

    if workout_session is None:
        abort(404)

    form = WorkoutSessionForm(obj=workout_session)

    if form.validate_on_submit():
        workout_session.session_name = form.session_name.data
        workout_session.date = form.date.data
        workout_session.duration_minutes = form.duration_minutes.data
        workout_session.focus = form.focus.data

        db.session.commit()

        flash("Workout session updated successfully.")
        return redirect(url_for("session.sessions"))

    return render_template(
        "edit_session.html",
        form=form,
        session=workout_session,
    )


@session_bp.route("/session/<int:session_id>/delete", methods=["POST"])
@login_required
def delete_session(session_id):
    delete_form = DeleteForm()

    if not delete_form.validate_on_submit():
        abort(400)

    workout_session = WorkoutSession.query.filter_by(
        id=session_id,
        user_id=current_user.id,
    ).first()

    if workout_session is None:
        abort(404)

    for exercise in list(workout_session.exercises):
        db.session.delete(exercise)

    db.session.delete(workout_session)
    db.session.commit()

    flash("Workout session and related exercises deleted successfully.")
    return redirect(url_for("session.sessions"))


@session_bp.route("/start-workout")
@login_required
def start_workout():
    return redirect(url_for("session.new_session"))
