import os

try:
    import redis  # type: ignore[import]
except ImportError:
    redis = None

from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()


def init_extensions(app):
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "login"  # type: ignore[assignment]


def get_redis_client():
    url = os.environ.get("REDIS_URL")

    if not url or redis is None:
        return None

    return redis.from_url(url)