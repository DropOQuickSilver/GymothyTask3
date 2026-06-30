import os
from functools import wraps

from flask import Flask, render_template, url_for, redirect, flash, abort, request 
from flask_bcrypt import Bcrypt
from flask_login import (UserMixin, login_user, LoginManager, login_required, logout_user, current_user,)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, SubmitField, IntegerField, FloatField, SelectField,)
from wtforms.validators import (InputRequired, Length, ValidationError, NumberRange, Optional)

from ml.strength_predictor import StrengthPredictor
from sqlalchemy import inspect, text

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)

# Secret key:
# - Uses Render environment variable in production
# - Falls back to a local development key when running locally
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

# Database:
# - Uses PostgreSQL on Render if DATABASE_URL exists
# - Uses local SQLite database.db when running locally
database_url = os.environ.get("DATABASE_URL")

if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
        basedir,
        "database.db",
    )

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Session security settings
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = bool(os.environ.get("RENDER"))

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # type: ignore[assignment]


# Database Models

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(60), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

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
    weight = db.Column(db.Integer, nullable=False, default=0)
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


# Forms

class RegisterForm(FlaskForm):
    username = StringField(
        validators=[InputRequired(), Length(min=4, max=60)],
        render_kw={"placeholder": "Username"},
    )

    password = PasswordField(
        validators=[InputRequired(), Length(min=4, max=60)],
        render_kw={"placeholder": "Password"},
    )

    submit = SubmitField("Register")

    def validate_username(self, username):
        existing_user = User.query.filter_by(username=username.data).first()

        if existing_user:
            raise ValidationError(
                "That username already exists. Please choose a different one."
            )


class LoginForm(FlaskForm):
    username = StringField(
        validators=[InputRequired(), Length(min=4, max=60)],
        render_kw={"placeholder": "Username"},
    )

    password = PasswordField(
        validators=[InputRequired(), Length(min=4, max=60)],
        render_kw={"placeholder": "Password"},
    )

    submit = SubmitField("Login")


class MealForm(FlaskForm):
    meal_name = StringField(
        "Meal Name",
        validators=[InputRequired(), Length(min=1, max=100)],
    )

    calories = IntegerField(
        "Calories",
        validators=[InputRequired(), NumberRange(min=0, max=10000)],
    )

    protein = IntegerField(
        "Protein (g)",
        validators=[InputRequired(), NumberRange(min=0, max=1000)],
    )

    carbs = IntegerField(
        "Carbs (g)",
        validators=[InputRequired(), NumberRange(min=0, max=1000)],
    )

    fats = IntegerField(
        "Fats (g)",
        validators=[InputRequired(), NumberRange(min=0, max=1000)],
    )

    submit = SubmitField("Save Meal")


class WorkoutSessionForm(FlaskForm):
    session_name = StringField(
        "Session Name",
        validators=[InputRequired(), Length(min=1, max=100)],
    )

    date = StringField(
        "Date",
        validators=[InputRequired(), Length(min=1, max=30)],
    )

    duration_minutes = IntegerField(
        "Duration",
        validators=[
            InputRequired(),
            NumberRange(
                min=1,
                max=600,
                message="Duration must be between 1 and 600 minutes.",
            ),
        ],
    )

    focus = StringField(
        "Focus",
        validators=[InputRequired(), Length(min=1, max=100)],
    )

    submit = SubmitField("Save Session")

STANDARD_EXERCISES = ["Squat", "Bench Press", "Deadlift"]


class ExerciseEntryForm(FlaskForm):
    exercise_name = SelectField(
        "Exercise Name",
        choices=[
            ("Squat", "Squat"),
            ("Bench Press", "Bench Press"),
            ("Deadlift", "Deadlift"),
            ("Other", "Other"),
        ],
        validators=[InputRequired()],
    )

    custom_exercise_name = StringField(
        "Other Exercise Name",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "e.g. Lat Pulldown, Leg Press, Shoulder Press"},
    )

    sets = IntegerField(
        "Sets",
        validators=[InputRequired(), NumberRange(min=1, max=20)],
    )

    reps = IntegerField(
        "Reps",
        validators=[InputRequired(), NumberRange(min=1, max=100)],
    )

    weight = FloatField(
        "Weight (kg)",
        validators=[InputRequired(), NumberRange(min=0, max=1000)],
    )

    rpe = FloatField(
        "RPE",
        validators=[Optional(), NumberRange(min=1, max=10)],
    )

    submit = SubmitField("Add Exercise")

    def validate_custom_exercise_name(self, custom_exercise_name):
        if self.exercise_name.data == "Other":
            typed_name = custom_exercise_name.data.strip() if custom_exercise_name.data else ""

            if not typed_name:
                raise ValidationError("Please enter the name of the other exercise.")


class PredictionForm(FlaskForm):
    lift_name = SelectField(
        "Lift",
        choices=[
            ("Squat", "Squat"),
            ("Bench Press", "Bench Press"),
            ("Deadlift", "Deadlift"),
        ],
        validators=[InputRequired()],
    )

    submit = SubmitField("Generate Prediction")


class DeleteForm(FlaskForm):
    submit = SubmitField("Delete")

class PersonalRecordForm(FlaskForm):
    lift_name = SelectField(
        "Lift",
        choices=[
            ("Squat", "Squat"),
            ("Bench Press", "Bench Press"),
            ("Deadlift", "Deadlift"),
        ],
        validators=[InputRequired()],
    )

    weight = FloatField(
        "Weight (kg)",
        validators=[InputRequired(), NumberRange(min=1, max=500)],
    )

    submit = SubmitField("Save Personal Record")


# Login Manager / Access Control

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)

        return func(*args, **kwargs)

    return wrapper


# Helper Functions

def get_exercise_name_from_form(form):
    if form.exercise_name.data == "Other":
        return form.custom_exercise_name.data.strip()

    return form.exercise_name.data

def calculate_estimated_1rm(weight, reps):
    if weight <= 0 or reps <= 0:
        return 0

    return round(weight * (1 + reps / 30), 2)


def get_user_lift_records(user_id, lift_name):
    return (
        db.session.query(ExerciseEntry, WorkoutSession)
        .join(WorkoutSession, ExerciseEntry.session_id == WorkoutSession.id)
        .filter(WorkoutSession.user_id == user_id)
        .filter(ExerciseEntry.exercise_name == lift_name)
        .order_by(
            WorkoutSession.date.asc(),
            WorkoutSession.id.asc(),
            ExerciseEntry.id.asc(),
        )
        .all()
    )


def prepare_prediction_features(user_id, lift_name):
    records = get_user_lift_records(user_id, lift_name)

    valid_records = []

    for exercise, session in records:
        if exercise.weight > 0 and exercise.reps > 0 and exercise.sets > 0:
            estimated_1rm = calculate_estimated_1rm(
                exercise.weight,
                exercise.reps,
            )

            volume = exercise.weight * exercise.reps * exercise.sets
            rpe = exercise.rpe if exercise.rpe else 7.0

            valid_records.append(
                {
                    "session_number": len(valid_records) + 1,
                    "estimated_1rm": float(estimated_1rm),
                    "volume": float(volume),
                    "rpe": float(rpe),
                }
            )

    if len(valid_records) < 3:
        return None, len(valid_records), valid_records

    latest = valid_records[-1]

    avg_rpe = sum(record["rpe"] for record in valid_records[-3:]) / min(
        3,
        len(valid_records),
    )

    features = {
        "lift_name": lift_name,
        "session_number": len(valid_records),
        "estimated_1rm": float(latest["estimated_1rm"]),
        "volume": float(latest["volume"]),
        "avg_rpe": float(avg_rpe),
        "days_since_last_session": 7,
    }

    return features, len(valid_records), valid_records


def calculate_three_week_projection(history_points, weeks_ahead=3):
    recent_points = history_points[-5:]
    estimated_maxes = [float(point["estimated_1rm"]) for point in recent_points]

    if len(estimated_maxes) < 3:
        return None

    changes = []

    for index in range(1, len(estimated_maxes)):
        change = estimated_maxes[index] - estimated_maxes[index - 1]
        changes.append(change)

    recent_changes = changes[-3:]
    average_weekly_change = sum(recent_changes) / len(recent_changes)

    current_1rm = estimated_maxes[-1]
    projected_1rm = current_1rm + (average_weekly_change * weeks_ahead)

    total_change = projected_1rm - current_1rm
    percent_change = (total_change / current_1rm) * 100 if current_1rm > 0 else 0

    if percent_change >= 2.5:
        trend = "Improving"
    elif percent_change <= -2.5:
        trend = "Declining"
    else:
        trend = "Stable"

    return {
        "current_1rm": round(current_1rm, 2),
        "projected_1rm": round(projected_1rm, 2),
        "average_weekly_change": round(average_weekly_change, 2),
        "total_change": round(total_change, 2),
        "percent_change": round(percent_change, 2),
        "trend": trend,
        "weeks_ahead": weeks_ahead,
    }


def build_projection_chart_points(history_points, projected_1rm):
    recent_points = history_points[-5:]

    chart_values = []

    for index, point in enumerate(recent_points):
        chart_values.append(
            {
                "label": f"S{index + 1}",
                "value": float(point["estimated_1rm"]),
                "is_projection": False,
            }
        )

    chart_values.append(
        {
            "label": "+3w",
            "value": float(projected_1rm),
            "is_projection": True,
        }
    )

    values = [point["value"] for point in chart_values]

    raw_min = min(values)
    raw_max = max(values)

    y_min = int(raw_min // 50) * 50
    y_max = int((raw_max + 49) // 50) * 50

    if y_min == y_max:
        y_min -= 50
        y_max += 50

    left = 80
    right = 540
    top = 30
    bottom = 220

    chart_width = right - left
    chart_height = bottom - top
    total_points = len(chart_values)

    for index, point in enumerate(chart_values):
        x = left + (chart_width * index / (total_points - 1))
        y = bottom - ((point["value"] - y_min) / (y_max - y_min) * chart_height)

        point["x"] = round(x, 2)
        point["y"] = round(y, 2)
        point["value"] = round(point["value"], 2)

    y_ticks = []

    tick = y_min

    while tick <= y_max:
        y = bottom - ((tick - y_min) / (y_max - y_min) * chart_height)

        y_ticks.append(
            {
                "value": tick,
                "y": round(y, 2),
            }
        )

        tick += 50

    polyline = " ".join(f"{point['x']},{point['y']}" for point in chart_values)

    return {
        "points": chart_values,
        "polyline": polyline,
        "min_value": y_min,
        "max_value": y_max,
        "y_ticks": y_ticks,
    }


def get_orphan_exercises():
    return (
        db.session.query(ExerciseEntry)
        .outerjoin(WorkoutSession, ExerciseEntry.session_id == WorkoutSession.id)
        .filter(WorkoutSession.id.is_(None))
        .all()
    )


def delete_orphan_exercises():
    orphan_exercises = get_orphan_exercises()

    for exercise in orphan_exercises:
        db.session.delete(exercise)

    db.session.commit()

    return len(orphan_exercises)


# Routes

@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    return render_template("home.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.")

    return render_template("login.html", form=form)


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(
            form.password.data
        ).decode("utf-8")

        new_user = User()
        new_user.username = form.username.data
        new_user.password = hashed_password

        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully. Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html", form=form)


@app.route("/dashboard")
@login_required
def dashboard():
    workout_sessions = (
        WorkoutSession.query.filter_by(user_id=current_user.id)
        .order_by(WorkoutSession.id.desc())
        .all()
    )

    meals = (
        Meal.query.filter_by(user_id=current_user.id)
        .order_by(Meal.id.desc())
        .all()
    )

    prs = (
        PersonalRecord.query.filter_by(user_id=current_user.id)
        .order_by(PersonalRecord.id.desc())
        .all()
    )

    total_sessions = len(workout_sessions)
    total_meals = len(meals)

    total_calories = sum(meal.calories for meal in meals)
    total_protein = sum(meal.protein for meal in meals)
    total_carbs = sum(meal.carbs for meal in meals)
    total_fats = sum(meal.fats for meal in meals)

    recent_sessions = workout_sessions[:5]
    recent_meals = meals[:5]

    return render_template(
        "dashboard.html",
        total_sessions=total_sessions,
        prs=prs,
        total_meals=total_meals,
        total_calories=total_calories,
        total_protein=total_protein,
        total_carbs=total_carbs,
        total_fats=total_fats,
        recent_sessions=recent_sessions,
        recent_meals=recent_meals,
    )


@app.route("/prediction", methods=["GET", "POST"])
@login_required
def prediction():
    form = PredictionForm()
    result = None
    error = None

    if form.validate_on_submit():
        lift_name = form.lift_name.data

        features, record_count, valid_records = prepare_prediction_features(
            current_user.id,
            lift_name,
        )

        if features is None:
            error = (
                f"Not enough valid {lift_name} records to generate a reliable "
                "prediction. At least 3 valid records are required."
            )
        else:
            try:
                predictor = StrengthPredictor()
                predictor.load_model()

                ml_next_1rm = predictor.predict_next_1rm(features)

                projection = calculate_three_week_projection(
                    valid_records,
                    weeks_ahead=3,
                )

                if projection is None:
                    error = "Not enough progression data to calculate a 3-week projection."
                else:
                    chart = build_projection_chart_points(
                        valid_records,
                        projection["projected_1rm"],
                    )

                    result = {
                        "lift_name": lift_name,
                        "record_count": record_count,
                        "current_1rm": projection["current_1rm"],
                        "projected_3_week_1rm": projection["projected_1rm"],
                        "average_weekly_change": projection["average_weekly_change"],
                        "change": projection["total_change"],
                        "percent_change": projection["percent_change"],
                        "trend": projection["trend"],
                        "weeks_ahead": projection["weeks_ahead"],
                        "ml_next_1rm": ml_next_1rm,
                        "metrics": predictor.metrics,
                        "chart": chart,
                    }

                    prediction_log = PredictionLog()
                    prediction_log.lift_name = lift_name
                    prediction_log.current_1rm = projection["current_1rm"]
                    prediction_log.predicted_1rm = projection["projected_1rm"]
                    prediction_log.trend = projection["trend"]
                    prediction_log.records_used = record_count
                    prediction_log.user_id = current_user.id

                    db.session.add(prediction_log)
                    db.session.commit()

            except FileNotFoundError:
                db.session.rollback()
                error = "The prediction model has not been trained yet."
            except Exception as e:
                db.session.rollback()
                error = f"Prediction could not be generated: {str(e)}"

    return render_template(
        "prediction.html",
        form=form,
        result=result,
        error=error,
    )


@app.route("/sessions")
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


@app.route("/macros")
@login_required
def macros():
    meals = (
        Meal.query.filter_by(user_id=current_user.id)
        .order_by(Meal.id.desc())
        .all()
    )

    total_calories = sum(meal.calories for meal in meals)
    total_protein = sum(meal.protein for meal in meals)
    total_carbs = sum(meal.carbs for meal in meals)
    total_fats = sum(meal.fats for meal in meals)

    delete_form = DeleteForm()

    return render_template(
        "macros.html",
        meals=meals,
        total_calories=total_calories,
        total_protein=total_protein,
        total_carbs=total_carbs,
        total_fats=total_fats,
        delete_form=delete_form,
    )

@app.route("/prs")
@login_required
def prs():
    personal_records = (
        PersonalRecord.query.filter_by(user_id=current_user.id)
        .order_by(PersonalRecord.id.desc())
        .all()
    )

    delete_form = DeleteForm()

    return render_template(
        "prs.html",
        personal_records=personal_records,
        delete_form=delete_form,
    )


@app.route("/pr/new", methods=["GET", "POST"])
@login_required
def new_pr():
    form = PersonalRecordForm()

    if form.validate_on_submit():
        new_record = PersonalRecord()
        new_record.lift_name = form.lift_name.data
        new_record.weight = form.weight.data
        new_record.user_id = current_user.id

        db.session.add(new_record)
        db.session.commit()

        flash("Personal record added successfully.")
        return redirect(url_for("prs"))

    return render_template("new_pr.html", form=form)


@app.route("/pr/<int:pr_id>/edit", methods=["GET", "POST"])
@login_required
def edit_pr(pr_id):
    personal_record = PersonalRecord.query.filter_by(
        id=pr_id,
        user_id=current_user.id,
    ).first_or_404()

    form = PersonalRecordForm(obj=personal_record)

    if form.validate_on_submit():
        personal_record.lift_name = form.lift_name.data
        personal_record.weight = form.weight.data

        db.session.commit()

        flash("Personal record updated successfully.")
        return redirect(url_for("prs"))

    return render_template(
        "edit_pr.html",
        form=form,
        personal_record=personal_record,
    )


@app.route("/pr/<int:pr_id>/delete", methods=["POST"])
@login_required
def delete_pr(pr_id):
    delete_form = DeleteForm()

    if not delete_form.validate_on_submit():
        abort(400)

    personal_record = PersonalRecord.query.filter_by(
        id=pr_id,
        user_id=current_user.id,
    ).first_or_404()

    db.session.delete(personal_record)
    db.session.commit()

    flash("Personal record deleted successfully.")
    return redirect(url_for("prs"))

@app.route("/new-session", methods=["GET", "POST"])
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
        return redirect(url_for("sessions"))

    return render_template("new_session.html", form=form)


@app.route("/session/<int:session_id>")
@login_required
def view_session(session_id):
    workout_session = WorkoutSession.query.filter_by(
        id=session_id,
        user_id=current_user.id,
    ).first_or_404()

    delete_form = DeleteForm()

    return render_template(
        "view_session.html",
        session=workout_session,
        delete_form=delete_form,
    )


@app.route("/session/<int:session_id>/add-exercise", methods=["GET", "POST"])
@login_required
def add_exercise(session_id):
    workout_session = WorkoutSession.query.filter_by(
        id=session_id,
        user_id=current_user.id,
    ).first_or_404()

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
        return redirect(url_for("view_session", session_id=workout_session.id))

    return render_template(
        "add_exercise.html",
        form=form,
        session=workout_session,
    )


@app.route("/exercise/<int:exercise_id>/edit", methods=["GET", "POST"])
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
        return redirect(url_for("view_session", session_id=exercise.session_id))

    return render_template(
        "edit_exercise.html",
        form=form,
        exercise=exercise,
    )


@app.route("/exercise/<int:exercise_id>/delete", methods=["POST"])
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
    return redirect(url_for("view_session", session_id=session_id))

@app.route("/session/<int:session_id>/edit", methods=["GET", "POST"])
@login_required
def edit_session(session_id):
    workout_session = WorkoutSession.query.filter_by(
        id=session_id,
        user_id=current_user.id,
    ).first_or_404()

    form = WorkoutSessionForm(obj=workout_session)

    if form.validate_on_submit():
        workout_session.session_name = form.session_name.data
        workout_session.date = form.date.data
        workout_session.duration_minutes = form.duration_minutes.data
        workout_session.focus = form.focus.data

        db.session.commit()

        flash("Workout session updated successfully.")
        return redirect(url_for("sessions"))

    return render_template(
        "edit_session.html",
        form=form,
        session=workout_session,
    )


@app.route("/session/<int:session_id>/delete", methods=["POST"])
@login_required
def delete_session(session_id):
    delete_form = DeleteForm()

    if not delete_form.validate_on_submit():
        abort(400)

    workout_session = WorkoutSession.query.filter_by(
        id=session_id,
        user_id=current_user.id,
    ).first_or_404()

    for exercise in list(workout_session.exercises):
        db.session.delete(exercise)

    db.session.delete(workout_session)
    db.session.commit()

    flash("Workout session and related exercises deleted successfully.")
    return redirect(url_for("sessions"))


@app.route("/add-meal", methods=["GET", "POST"])
@login_required
def add_meal():
    form = MealForm()

    if form.validate_on_submit():
        new_meal = Meal()
        new_meal.meal_name = form.meal_name.data
        new_meal.calories = form.calories.data
        new_meal.protein = form.protein.data
        new_meal.carbs = form.carbs.data
        new_meal.fats = form.fats.data
        new_meal.user_id = current_user.id

        db.session.add(new_meal)
        db.session.commit()

        flash("Meal added successfully.")
        return redirect(url_for("macros"))

    return render_template("add_meal.html", form=form)


@app.route("/meal/<int:meal_id>/edit", methods=["GET", "POST"])
@login_required
def edit_meal(meal_id):
    meal = Meal.query.filter_by(
        id=meal_id,
        user_id=current_user.id,
    ).first_or_404()

    form = MealForm(obj=meal)

    if form.validate_on_submit():
        meal.meal_name = form.meal_name.data
        meal.calories = form.calories.data
        meal.protein = form.protein.data
        meal.carbs = form.carbs.data
        meal.fats = form.fats.data

        db.session.commit()

        flash("Meal updated successfully.")
        return redirect(url_for("macros"))

    return render_template(
        "edit_meal.html",
        form=form,
        meal=meal,
    )


@app.route("/meal/<int:meal_id>/delete", methods=["POST"])
@login_required
def delete_meal(meal_id):
    delete_form = DeleteForm()

    if not delete_form.validate_on_submit():
        abort(400)

    meal = Meal.query.filter_by(
        id=meal_id,
        user_id=current_user.id,
    ).first_or_404()

    db.session.delete(meal)
    db.session.commit()

    flash("Meal deleted successfully.")
    return redirect(url_for("macros"))


@app.route("/start-workout")
@login_required
def start_workout():
    return redirect(url_for("new_session"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/admin/debug")
@login_required
@admin_required
def admin_debug():
    users = User.query.order_by(User.id.asc()).all()
    sessions = WorkoutSession.query.order_by(WorkoutSession.id.desc()).all()
    exercises = ExerciseEntry.query.order_by(ExerciseEntry.id.desc()).all()
    meals = Meal.query.order_by(Meal.id.desc()).all()
    prs = PersonalRecord.query.order_by(PersonalRecord.id.desc()).all()
    prediction_logs = PredictionLog.query.order_by(PredictionLog.id.desc()).all()

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

@app.route("/admin/cleanup-orphans", methods=["POST"])
@login_required
@admin_required
def cleanup_orphans():
    delete_form = DeleteForm()

    if not delete_form.validate_on_submit():
        abort(400)

    deleted_count = delete_orphan_exercises()

    flash(f"Deleted {deleted_count} orphan exercise record(s).")
    return redirect(url_for("admin_debug"))

def ensure_database_schema():
    inspector = inspect(db.engine)

    if "prediction_log" in inspector.get_table_names():
        columns = [
            column["name"]
            for column in inspector.get_columns("prediction_log")
        ]

        if "created_at" not in columns:
            with db.engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE prediction_log ADD COLUMN created_at DATETIME")
                )

# Error Handlers

@app.errorhandler(403)
def forbidden(error):
    return render_template("403.html"), 403


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(error):
    db.session.rollback()
    return render_template("500.html"), 500


with app.app_context():
    db.create_all()
    ensure_database_schema()


if __name__ == "__main__":
    app.run(debug=True)