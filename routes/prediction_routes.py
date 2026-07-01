from flask import Blueprint, render_template
from flask_login import login_required, current_user

from forms import PredictionForm
from models import PredictionLog
from utils import (
    prepare_prediction_features,
    get_strength_predictor,
    calculate_three_week_projection,
    build_projection_chart_points,
)
from extensions import db

prediction_bp = Blueprint("prediction", __name__)


@prediction_bp.route("/prediction", methods=["GET", "POST"])
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
                predictor = get_strength_predictor()
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
