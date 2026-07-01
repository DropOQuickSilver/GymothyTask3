from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    SubmitField,
    IntegerField,
    FloatField,
    SelectField,
)
from wtforms.validators import (
    InputRequired,
    Length,
    ValidationError,
    NumberRange,
    Optional,
    Regexp,
)


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
        validators=[
            InputRequired(),
            Regexp(r"^\d{4}-\d{2}-\d{2}$", message="Date must be in YYYY-MM-DD format."),
        ],
    )

    duration_minutes = IntegerField(
        "Duration",
        validators=[InputRequired(), NumberRange(min=1, max=600)],
    )

    focus = StringField("Focus", validators=[InputRequired(), Length(min=1, max=100)])

    submit = SubmitField("Save Session")


STANDARD_EXERCISES = ["Squat", "Bench Press", "Deadlift"]


class ExerciseEntryForm(FlaskForm):
    exercise_name = SelectField(
        "Exercise Name",
        choices=[("Squat", "Squat"), ("Bench Press", "Bench Press"), ("Deadlift", "Deadlift"), ("Other", "Other")],
        validators=[InputRequired()],
    )

    custom_exercise_name = StringField(
        "Other Exercise Name",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "e.g. Lat Pulldown, Leg Press, Shoulder Press"},
    )

    sets = IntegerField("Sets", validators=[InputRequired(), NumberRange(min=1, max=20)])
    reps = IntegerField("Reps", validators=[InputRequired(), NumberRange(min=1, max=100)])
    weight = FloatField("Weight (kg)", validators=[InputRequired(), NumberRange(min=0, max=1000)])
    rpe = FloatField("RPE", validators=[Optional(), NumberRange(min=1, max=10)])
    submit = SubmitField("Add Exercise")

    def validate_custom_exercise_name(self, custom_exercise_name):
        if self.exercise_name.data == "Other":
            typed_name = (
                custom_exercise_name.data.strip()
                if custom_exercise_name.data
                else ""
            )

            if not typed_name:
                raise ValidationError("Please enter the name of the other exercise.")


class PredictionForm(FlaskForm):
    lift_name = SelectField(
        "Lift",
        choices=[("Squat", "Squat"), ("Bench Press", "Bench Press"), ("Deadlift", "Deadlift")],
        validators=[InputRequired()],
    )

    submit = SubmitField("Generate Prediction")


class DeleteForm(FlaskForm):
    submit = SubmitField("Delete")


class PersonalRecordForm(FlaskForm):
    lift_name = SelectField(
        "Lift",
        choices=[("Squat", "Squat"), ("Bench Press", "Bench Press"), ("Deadlift", "Deadlift")],
        validators=[InputRequired()],
    )

    weight = FloatField("Weight (kg)", validators=[InputRequired(), NumberRange(min=1, max=1000)])
    submit = SubmitField("Save Personal Record")
