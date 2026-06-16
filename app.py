from flask import Flask, render_template, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
import os
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, FloatField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
from flask import abort
from functools import wraps

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
    calories = IntegerField("Calories", validators=[InputRequired()])
    protein = IntegerField("Protein (g)", validators=[InputRequired()])
    carbs = IntegerField("Carbs (g)", validators=[InputRequired()])
    fats = IntegerField("Fats (g)", validators=[InputRequired()])
    submit = SubmitField("Save Meal")


class WorkoutSessionForm(FlaskForm):
    session_name = StringField("Session Name", validators=[InputRequired(), Length(min=1, max=100)])
    date = StringField("Date", validators=[InputRequired(), Length(min=1, max=30)])
    duration_minutes = IntegerField("Duration (minutes)", validators=[InputRequired()])
    focus = StringField("Focus", validators=[InputRequired(), Length(min=1, max=100)])
    submit = SubmitField("Save Session")


class ExerciseEntryForm(FlaskForm):
    exercise_name = StringField("Exercise Name", validators=[InputRequired(), Length(min=1, max=100)])
    sets = IntegerField("Sets", validators=[InputRequired()])
    reps = IntegerField("Reps", validators=[InputRequired()])
    weight = FloatField("Weight (kg)", validators=[InputRequired()])
    rpe = FloatField("RPE")
    submit = SubmitField("Add Exercise")

# ---> ADD THIS CODE BLOCK HERE <---
# This checks and builds your database tables on Render automatically when the app boots
with app.app_context():
    db.create_all()

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
