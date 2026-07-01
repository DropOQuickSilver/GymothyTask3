import os
from datetime import datetime
from typing import List, Tuple, Optional

from extensions import db, get_redis_client
from ml.strength_predictor import StrengthPredictor
from models import ExerciseEntry, WorkoutSession, PredictionLog

# Lockout constants and in-memory fallback
LOGIN_ATTEMPTS = {}
MAX_LOGIN_ATTEMPTS = int(os.environ.get("MAX_LOGIN_ATTEMPTS", "3"))
LOGIN_WINDOW_SECONDS = int(os.environ.get("LOGIN_WINDOW_SECONDS", "300"))
LOCKOUT_SECONDS = int(os.environ.get("LOCKOUT_SECONDS", "180"))


def get_exercise_name_from_form(form):
    if form.exercise_name.data == "Other":
        return form.custom_exercise_name.data.strip()

    return form.exercise_name.data


def calculate_estimated_1rm(weight: float, reps: int) -> float:
    if weight <= 0 or reps <= 0:
        return 0.0

    return round(weight * (1 + reps / 30), 2)


def get_user_lift_records(user_id: int, lift_name: str):
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


def prepare_prediction_features(user_id: int, lift_name: str):
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
                    "date": session.date,
                }
            )

    if len(valid_records) < 3:
        return None, len(valid_records), valid_records

    latest = valid_records[-1]

    avg_rpe = sum(record["rpe"] for record in valid_records[-3:]) / min(
        3,
        len(valid_records),
    )

    days_since_last_session = 7
    if len(valid_records) >= 2:
        try:
            last_date = datetime.strptime(valid_records[-1]["date"], "%Y-%m-%d")
            previous_date = datetime.strptime(valid_records[-2]["date"], "%Y-%m-%d")
            days_since_last_session = max(0, (last_date - previous_date).days)
        except ValueError:
            days_since_last_session = 7

    features = {
        "lift_name": lift_name,
        "session_number": len(valid_records),
        "estimated_1rm": float(latest["estimated_1rm"]),
        "volume": float(latest["volume"]),
        "avg_rpe": float(avg_rpe),
        "days_since_last_session": int(days_since_last_session),
    }

    return features, len(valid_records), valid_records


def calculate_three_week_projection(history_points: List[dict], weeks_ahead: int = 3):
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

    max_weekly_change = current_1rm * 0.05

    average_weekly_change = max(
        -max_weekly_change,
        min(average_weekly_change, max_weekly_change),
    )

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


def build_projection_chart_points(history_points: List[dict], projected_1rm: float):
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
    actual_values = [float(point["estimated_1rm"]) for point in recent_points]

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

    average_1rm = sum(actual_values) / len(actual_values)
    average_y = bottom - ((average_1rm - y_min) / (y_max - y_min) * chart_height)

    x_values = list(range(len(actual_values)))
    y_values = actual_values
    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(y_values) / len(y_values)

    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
    denominator = sum((x - x_mean) ** 2 for x in x_values)

    slope = numerator / denominator if denominator else 0
    intercept = y_mean - slope * x_mean

    trend_y_start = intercept
    trend_y_end = intercept + slope * (len(x_values) - 1)

    trend_plot_y1 = bottom - ((trend_y_start - y_min) / (y_max - y_min) * chart_height)
    trend_plot_y2 = bottom - ((trend_y_end - y_min) / (y_max - y_min) * chart_height)

    first_real_point = chart_values[0]
    last_real_point = chart_values[-2]

    return {
        "points": chart_values,
        "polyline": polyline,
        "min_value": y_min,
        "max_value": y_max,
        "y_ticks": y_ticks,
        "average_1rm": round(average_1rm, 2),
        "average_line": {
            "x1": left,
            "x2": right,
            "y": round(average_y, 2),
            "label_x": round((left + right) / 2, 2),
            "label_y": round(average_y - 8, 2),
        },
        "trend_line": {
            "x1": first_real_point["x"],
            "y1": round(trend_plot_y1, 2),
            "x2": last_real_point["x"],
            "y2": round(trend_plot_y2, 2),
            "label_x": round((first_real_point["x"] + last_real_point["x"]) / 2, 2),
            "label_y": round(min(trend_plot_y1, trend_plot_y2) - 12, 2),
        },
    }


cached_strength_predictor: Optional[StrengthPredictor] = None


def get_strength_predictor() -> StrengthPredictor:
    global cached_strength_predictor

    if cached_strength_predictor is None:
        cached_strength_predictor = StrengthPredictor()
        cached_strength_predictor.load_model()

    return cached_strength_predictor


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
