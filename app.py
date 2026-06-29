from flask import Flask, render_template, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
import os
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, FloatField, SelectField
from wtforms.validators import InputRequired, Length, ValidationError, NumberRange, Optional
from flask_bcrypt import Bcrypt
from flask import abort
from functools import wraps
from wtforms import SelectField
from ml.strength_predictor import StrengthPredictor


app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"



# Database Models

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(60), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    workout_sessions = db.relationship('WorkoutSession', backref='user', lazy=True, cascade="all, delete-orphan")
    meals = db.relationship('Meal', backref='user', lazy=True, cascade="all, delete-orphan")
    prs = db.relationship('PersonalRecord', backref='user', lazy=True, cascade="all, delete-orphan")


class WorkoutSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(30), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False, default=0)
    focus = db.Column(db.String(100), nullable=False, default="General")
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exercises = db.relationship('ExerciseEntry', backref='session', lazy=True, cascade="all, delete-orphan")

class ExerciseEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exercise_name = db.Column(db.String(100), nullable=False)
    sets = db.Column(db.Integer, nullable=False, default=0)
    reps = db.Column(db.Integer, nullable=False, default=0)
    weight = db.Column(db.Float, nullable=False, default=0)
    rpe = db.Column(db.Float, nullable=True)
    session_id = db.Column(db.Integer, db.ForeignKey('workout_session.id'), nullable=False)

class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    meal_name = db.Column(db.String(100), nullable=False)
    calories = db.Column(db.Integer, nullable=False, default=0)
    protein = db.Column(db.Integer, nullable=False, default=0)
    carbs = db.Column(db.Integer, nullable=False, default=0)
    fats = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class PersonalRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lift_name = db.Column(db.String(100), nullable=False)
    weight = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class PredictionForm(FlaskForm):
    lift_name = SelectField(
        "Lift",
        choices=[
            ("Squat", "Squat"),
            ("Bench Press", "Bench Press"),
            ("Deadlift", "Deadlift")
        ],
        validators=[InputRequired()]
    )

    submit = SubmitField("Generate Prediction")



# Login Manager

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)  # Forbidden
        return func(*args, **kwargs)
    return wrapper

# Forms

class RegisterForm(FlaskForm):
    username = StringField(
        validators=[InputRequired(), Length(min=4, max=60)],
        render_kw={"placeholder": "Username"}
    )
    password = PasswordField(
        validators=[InputRequired(), Length(min=4, max=60)],
        render_kw={"placeholder": "Password"}
    )
    submit = SubmitField("Register")

    def validate_username(self, username):
        existing_user = User.query.filter_by(username=username.data).first()
        if existing_user:
            raise ValidationError("That username already exists. Please choose a different one.")


class LoginForm(FlaskForm):
    username = StringField(
        validators=[InputRequired(), Length(min=4, max=60)],
        render_kw={"placeholder": "Username"}
    )
    password = PasswordField(
        validators=[InputRequired(), Length(min=4, max=60)],
        render_kw={"placeholder": "Password"}
    )
    submit = SubmitField("Login")

class MealForm(FlaskForm):
    meal_name = StringField("Meal Name", validators=[InputRequired(), Length(min=1, max=100)])
    calories = IntegerField("Calories", validators=[InputRequired(), NumberRange(min=0, max=20000)])
    protein = IntegerField("Protein (g)", validators=[InputRequired(), NumberRange(min=0, max=1000)])
    carbs = IntegerField("Carbs (g)", validators=[InputRequired(), NumberRange(min=0, max=1000)])
    fats = IntegerField("Fats (g)", validators=[InputRequired(), NumberRange(min=0, max=1000)])
    submit = SubmitField("Save Meal")


class WorkoutSessionForm(FlaskForm):
    session_name = StringField("Session Name", validators=[InputRequired(), Length(min=1, max=100)])
    date = StringField("Date", validators=[InputRequired(), Length(min=1, max=30)])
    duration_minutes = IntegerField("Duration (minutes)", validators=[InputRequired(), NumberRange(min=1, max=600)])
    focus = StringField("Focus", validators=[InputRequired(), Length(min=1, max=100)])
    submit = SubmitField("Save Session")


class ExerciseEntryForm(FlaskForm):
    exercise_name = StringField("Exercise Name", validators=[InputRequired(), Length(min=1, max=100)])
    sets = IntegerField("Sets", validators=[InputRequired(), NumberRange(min=1, max=20)])
    reps = IntegerField("Reps", validators=[InputRequired(), NumberRange(min=1, max=100)])
    weight = FloatField("Weight (kg)", validators=[InputRequired(), NumberRange(min=0, max=500)])
    rpe = FloatField("RPE", validators=[Optional(), NumberRange(min=1, max=10)])
    submit = SubmitField("Add Exercise")

class PredictionForm(FlaskForm):
    lift_name = SelectField(
        "Lift",
        choices=[
            ("Squat", "Squat"),
            ("Bench Press", "Bench Press"),
            ("Deadlift", "Deadlift")
        ],
        validators=[InputRequired()]
    )
    submit = SubmitField("Generate Prediction")

class PredictionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lift_name = db.Column(db.String(100), nullable=False)
    current_1rm = db.Column(db.Float, nullable=False)
    predicted_1rm = db.Column(db.Float, nullable=False)
    trend = db.Column(db.String(50), nullable=False)
    records_used = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


with app.app_context():
    db.create_all()

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
        .order_by(WorkoutSession.id.asc())
        .all()
    )


def prepare_prediction_features(user_id, lift_name):
    records = get_user_lift_records(user_id, lift_name)

    valid_records = []
    for exercise, session in records:
        if exercise.weight > 0 and exercise.reps > 0 and exercise.sets > 0:
            estimated_1rm = calculate_estimated_1rm(exercise.weight, exercise.reps)
            volume = exercise.weight * exercise.reps * exercise.sets
            rpe = exercise.rpe if exercise.rpe else 7.0

            valid_records.append({
                "session_number": len(valid_records) + 1,
                "estimated_1rm": float(estimated_1rm),
                "volume": float(volume),
                "rpe": float(rpe)
            })

    if len(valid_records) < 3:
        return None, len(valid_records), valid_records

    latest = valid_records[-1]
    avg_rpe = sum(record["rpe"] for record in valid_records[-3:]) / min(3, len(valid_records))

    features = {
        "lift_name": lift_name,
        "session_number": len(valid_records),
        "estimated_1rm": float(latest["estimated_1rm"]),
        "volume": float(latest["volume"]),
        "avg_rpe": float(avg_rpe),
        "days_since_last_session": 7
    }

    return features, len(valid_records), valid_records

def build_prediction_chart_points(history_points, predicted_1rm):
    recent_points = history_points[-5:]

    chart_values = []

    for index, point in enumerate(recent_points):
        chart_values.append({
            "label": f"Record {index + 1}",
            "value": float(point["estimated_1rm"]),
            "is_prediction": False
        })

    chart_values.append({
        "label": "Predicted",
        "value": float(predicted_1rm),
        "is_prediction": True
    })

    values = [point["value"] for point in chart_values]

    min_value = min(values)
    max_value = max(values)

    if min_value == max_value:
        min_value -= 1
        max_value += 1

    left = 50
    right = 460
    top = 30
    bottom = 170

    chart_width = right - left
    chart_height = bottom - top

    total_points = len(chart_values)

    for index, point in enumerate(chart_values):
        x = left + (chart_width * index / (total_points - 1))
        y = bottom - ((point["value"] - min_value) / (max_value - min_value) * chart_height)

        point["x"] = round(x, 2)
        point["y"] = round(y, 2)
        point["value"] = round(point["value"], 2)

    polyline = " ".join(f"{point['x']},{point['y']}" for point in chart_values)

    return {
        "points": chart_values,
        "polyline": polyline,
        "min_value": round(min_value, 2),
        "max_value": round(max_value, 2)
    }

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
        "weeks_ahead": weeks_ahead
    }

def build_projection_chart_points(history_points, projected_1rm):
    recent_points = history_points[-5:]

    chart_values = []

    for index, point in enumerate(recent_points):
        chart_values.append({
            "label": f"S{index + 1}",
            "value": float(point["estimated_1rm"]),
            "is_projection": False
        })

    chart_values.append({
        "label": "+3w",
        "value": float(projected_1rm),
        "is_projection": True
    })

    values = [point["value"] for point in chart_values]

    raw_min = min(values)
    raw_max = max(values)

    y_min = int(raw_min // 50) * 50
    y_max = int((raw_max + 49) // 50) * 50

    if y_min == y_max:
        y_min -= 50
        y_max += 50

    # SVG graph boundaries
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
        y_ticks.append({
            "value": tick,
            "y": round(y, 2)
        })
        tick += 50

    polyline = " ".join(f"{point['x']},{point['y']}" for point in chart_values)

    return {
        "points": chart_values,
        "polyline": polyline,
        "min_value": y_min,
        "max_value": y_max,
        "y_ticks": y_ticks
    }

# Route Pages

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))

    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(username=form.username.data, password=hashed_password)

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/dashboard')
@login_required
def dashboard():
    workout_sessions = WorkoutSession.query.filter_by(user_id=current_user.id).order_by(WorkoutSession.id.desc()).all()
    meals = Meal.query.filter_by(user_id=current_user.id).order_by(Meal.id.desc()).all()
    prs = PersonalRecord.query.filter_by(user_id=current_user.id).order_by(PersonalRecord.id.desc()).all()

    total_sessions = len(workout_sessions)
    total_meals = len(meals)
    total_calories = sum(meal.calories for meal in meals)
    total_protein = sum(meal.protein for meal in meals)
    total_carbs = sum(meal.carbs for meal in meals)
    total_fats = sum(meal.fats for meal in meals)

    recent_sessions = workout_sessions[:5]
    recent_meals = meals[:5]

    return render_template(
        'dashboard.html',
        total_sessions=total_sessions,
        prs=prs,
        total_meals=total_meals,
        total_calories=total_calories,
        total_protein=total_protein,
        total_carbs=total_carbs,
        total_fats=total_fats,
        recent_sessions=recent_sessions,
        recent_meals=recent_meals
    )

@app.route('/prediction', methods=['GET', 'POST'])
@login_required
def prediction():
    form = PredictionForm()
    result = None
    error = None

    if form.validate_on_submit():
        lift_name = form.lift_name.data

        features, record_count, valid_records = prepare_prediction_features(current_user.id, lift_name)

        if features is None:
            error = (
                f"Not enough valid {lift_name} records to generate a reliable prediction. "
                f"At least 3 valid records are required."
            )
        else:
            try:
                predictor = StrengthPredictor()
                predictor.load_model()

                ml_next_1rm = predictor.predict_next_1rm(features)

                projection = calculate_three_week_projection(valid_records, weeks_ahead=3)

                if projection is None:
                    error = "Not enough progression data to calculate a 3-week projection."
                else:
                    chart = build_projection_chart_points(
                        valid_records,
                        projection["projected_1rm"]
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
                        "chart": chart
                    }

            except FileNotFoundError:
                error = "The prediction model has not been trained yet."
            except Exception as e:
                error = f"Prediction could not be generated: {str(e)}"

    return render_template(
        "prediction.html",
        form=form,
        result=result,
        error=error
    )

@app.route('/sessions')
@login_required
def sessions():
    workout_sessions = WorkoutSession.query.filter_by(user_id=current_user.id).order_by(WorkoutSession.id.desc()).all()
    return render_template('sessions.html', workout_sessions=workout_sessions)


@app.route('/macros')
@login_required
def macros():
    meals = Meal.query.filter_by(user_id=current_user.id).order_by(Meal.id.desc()).all()

    total_calories = sum(meal.calories for meal in meals)
    total_protein = sum(meal.protein for meal in meals)
    total_carbs = sum(meal.carbs for meal in meals)
    total_fats = sum(meal.fats for meal in meals)

    return render_template(
        'macros.html',
        meals=meals,
        total_calories=total_calories,
        total_protein=total_protein,
        total_carbs=total_carbs,
        total_fats=total_fats
    )


@app.route('/new-session', methods=['GET', 'POST'])
@login_required
def new_session():
    form = WorkoutSessionForm()

    if form.validate_on_submit():
        session = WorkoutSession(
            session_name=form.session_name.data,
            date=form.date.data,
            duration_minutes=form.duration_minutes.data,
            focus=form.focus.data,
            user_id=current_user.id
        )
        db.session.add(session)
        db.session.commit()
        return redirect(url_for('sessions'))

    return render_template('new_session.html', form=form)

@app.route('/session/<int:session_id>/add-exercise', methods=['GET', 'POST'])
@login_required
def add_exercise(session_id):
    session = WorkoutSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    form = ExerciseEntryForm()

    if form.validate_on_submit():
        exercise = ExerciseEntry(
            exercise_name=form.exercise_name.data,
            sets=form.sets.data,
            reps=form.reps.data,
            weight=form.weight.data,
            rpe=form.rpe.data,
            session_id=session.id
        )
        db.session.add(exercise)
        db.session.commit()
        return redirect(url_for('view_session', session_id=session.id))

    return render_template('add_exercise.html', form=form, session=session)

@app.route('/session/<int:session_id>')
@login_required
def view_session(session_id):
    session = WorkoutSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    return render_template('view_session.html', session=session)


@app.route('/add-meal', methods=['GET', 'POST'])
@login_required
def add_meal():
    form = MealForm()

    if form.validate_on_submit():
        meal = Meal(
            meal_name=form.meal_name.data,
            calories=form.calories.data,
            protein=form.protein.data,
            carbs=form.carbs.data,
            fats=form.fats.data,
            user_id=current_user.id
        )
        db.session.add(meal)
        db.session.commit()
        return redirect(url_for('macros'))

    return render_template('add_meal.html', form=form)


@app.route('/start-workout')
@login_required
def start_workout():
    return redirect(url_for('new_session'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin/debug')
@login_required
@admin_required
def admin_debug():
    users = User.query.all()
    workout_sessions = WorkoutSession.query.all()
    meals = Meal.query.all()
    exercises = ExerciseEntry.query.all()

    return render_template(
        'admin_debug.html',
        users=users,
        workout_sessions=workout_sessions,
        meals=meals,
        exercises=exercises
    )

@app.route('/session/<int:session_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_session(session_id):
    session = WorkoutSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    form = WorkoutSessionForm(obj=session)

    if form.validate_on_submit():
        session.session_name = form.session_name.data
        session.date = form.date.data
        session.duration_minutes = form.duration_minutes.data
        session.focus = form.focus.data

        db.session.commit()
        return redirect(url_for('sessions'))

    return render_template('edit_session.html', form=form, session=session)


@app.route('/session/<int:session_id>/delete', methods=['POST'])
@login_required
def delete_session(session_id):
    session = WorkoutSession.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()

    db.session.delete(session)
    db.session.commit()
    return redirect(url_for('sessions'))


@app.route('/meal/<int:meal_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_meal(meal_id):
    meal = Meal.query.filter_by(id=meal_id, user_id=current_user.id).first_or_404()
    form = MealForm(obj=meal)

    if form.validate_on_submit():
        meal.meal_name = form.meal_name.data
        meal.calories = form.calories.data
        meal.protein = form.protein.data
        meal.carbs = form.carbs.data
        meal.fats = form.fats.data

        db.session.commit()
        return redirect(url_for('macros'))

    return render_template('edit_meal.html', form=form, meal=meal)


@app.route('/meal/<int:meal_id>/delete', methods=['POST'])
@login_required
def delete_meal(meal_id):
    meal = Meal.query.filter_by(id=meal_id, user_id=current_user.id).first_or_404()

    db.session.delete(meal)
    db.session.commit()
    return redirect(url_for('macros'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
