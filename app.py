import os

from flask import Flask, render_template, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func, inspect, text

from extensions import init_extensions, db, login_manager
from models import WorkoutSession, Meal, PersonalRecord, User

# Import blueprints
from routes.auth_routes import auth_bp
from routes.session_routes import session_bp
from routes.meal_routes import meal_bp
from routes.pr_routes import pr_bp
from routes.prediction_routes import prediction_bp
from routes.admin_routes import admin_bp


def create_app(test_config=None):
    app = Flask(__name__)


    # Basic configuration

    basedir = os.path.abspath(os.path.dirname(__file__))

    secret_key = os.environ.get("SECRET_KEY")
    app.config["SECRET_KEY"] = secret_key or "dev-secret-key"

    database_url = os.environ.get("DATABASE_URL")

    if database_url:
        # Render sometimes provides postgres://, but SQLAlchemy expects postgresql://
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

    # Safer session cookie settings
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = bool(os.environ.get("RENDER"))

    app.config["DEBUG_ROW_LIMIT"] = int(os.environ.get("DEBUG_ROW_LIMIT", 50))

    if test_config:
        app.config.update(test_config)


    # Initialise extensions

    init_extensions(app)


    # Register blueprints

    app.register_blueprint(auth_bp)
    app.register_blueprint(session_bp)
    app.register_blueprint(meal_bp)
    app.register_blueprint(pr_bp)
    app.register_blueprint(prediction_bp)
    app.register_blueprint(admin_bp)


    # Login manager

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))


    # Core routes

    @app.route("/")
    def home():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        return render_template("home.html")

    @app.route("/dashboard")
    @login_required
    def dashboard():
        total_sessions = (
            db.session.query(func.count(WorkoutSession.id))
            .filter(WorkoutSession.user_id == current_user.id)
            .scalar()
            or 0
        )

        total_meals, total_calories, total_protein, total_carbs, total_fats = (
            db.session.query(
                func.count(Meal.id),
                func.coalesce(func.sum(Meal.calories), 0),
                func.coalesce(func.sum(Meal.protein), 0),
                func.coalesce(func.sum(Meal.carbs), 0),
                func.coalesce(func.sum(Meal.fats), 0),
            )
            .filter(Meal.user_id == current_user.id)
            .one()
        )

        prs = (
            PersonalRecord.query.filter_by(user_id=current_user.id)
            .order_by(PersonalRecord.id.desc())
            .all()
        )

        recent_sessions = (
            WorkoutSession.query.filter_by(user_id=current_user.id)
            .order_by(WorkoutSession.id.desc())
            .limit(5)
            .all()
        )

        recent_meals = (
            Meal.query.filter_by(user_id=current_user.id)
            .order_by(Meal.id.desc())
            .limit(5)
            .all()
        )

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


    # Database schema migration helper

    def ensure_database_schema():
        """
        Ensures older databases have the newer columns required by Gymothy.

        This handles both local SQLite and Render PostgreSQL.
        PostgreSQL treats 'user' as a reserved keyword, so raw SQL must quote it.
        """
        with db.engine.begin() as connection:
            inspector = inspect(connection)
            table_names = inspector.get_table_names()
            dialect_name = connection.dialect.name


            # prediction_log.created_at

            if "prediction_log" in table_names:
                prediction_columns = {
                    column["name"]
                    for column in inspector.get_columns("prediction_log")
                }

                if "created_at" not in prediction_columns:
                    if dialect_name == "postgresql":
                        connection.execute(
                            text(
                                "ALTER TABLE prediction_log "
                                "ADD COLUMN created_at TIMESTAMP"
                            )
                        )
                    else:
                        connection.execute(
                            text(
                                "ALTER TABLE prediction_log "
                                "ADD COLUMN created_at DATETIME"
                            )
                        )

     
            # user.role and user.is_admin
           
            if "user" in table_names:
                user_columns = {
                    column["name"]
                    for column in inspector.get_columns("user")
                }

                if dialect_name == "postgresql":
                    user_table_name = '"user"'
                    boolean_default = "FALSE"
                else:
                    user_table_name = "user"
                    boolean_default = "0"

                if "role" not in user_columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE {user_table_name} "
                            "ADD COLUMN role VARCHAR(20) DEFAULT 'user'"
                        )
                    )

                if "is_admin" not in user_columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE {user_table_name} "
                            f"ADD COLUMN is_admin BOOLEAN DEFAULT {boolean_default} NOT NULL"
                        )
                    )

   
    # Error handlers

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

    # Create/update database

    with app.app_context():
        db.create_all()
        ensure_database_schema()

    return app


if __name__ == "__main__":
    create_app().run(debug=True)