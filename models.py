from flask_login import UserMixin

from extensions import db




class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(60), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    role = db.Column(db.String(30), nullable=False, default="user")

    workout_sessions = db.relationship(
        "WorkoutSession",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )

    meals = db.relationship(
        "Meal",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )

    prs = db.relationship(
        "PersonalRecord",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )

    prediction_logs = db.relationship(
        "PredictionLog",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )


class WorkoutSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(30), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False, default=0)
    focus = db.Column(db.String(100), nullable=False, default="General")
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    exercises = db.relationship(
        "ExerciseEntry",
        backref="session",
        lazy=True,
        cascade="all, delete-orphan",
    )


class ExerciseEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exercise_name = db.Column(db.String(100), nullable=False)
    sets = db.Column(db.Integer, nullable=False, default=0)
    reps = db.Column(db.Integer, nullable=False, default=0)
    weight = db.Column(db.Float, nullable=False, default=0)
    rpe = db.Column(db.Float, nullable=True)
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("workout_session.id"),
        nullable=False,
    )


class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    meal_name = db.Column(db.String(100), nullable=False)
    calories = db.Column(db.Integer, nullable=False, default=0)
    protein = db.Column(db.Integer, nullable=False, default=0)
    carbs = db.Column(db.Integer, nullable=False, default=0)
    fats = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class PersonalRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lift_name = db.Column(db.String(100), nullable=False)
    weight = db.Column(db.Float, nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class PredictionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lift_name = db.Column(db.String(100), nullable=False)
    current_1rm = db.Column(db.Float, nullable=False)
    predicted_1rm = db.Column(db.Float, nullable=False)
    trend = db.Column(db.String(50), nullable=False)
    records_used = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
