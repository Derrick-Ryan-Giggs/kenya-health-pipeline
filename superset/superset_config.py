import os
from datetime import timedelta

SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]
SQLALCHEMY_DATABASE_URI = os.environ["DATABASE_URL"]

PERMANENT_SESSION_LIFETIME = timedelta(days=30)
SESSION_PERMANENT = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False

WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = None

SQLALCHEMY_EXAMPLES_URI = (
    "trino://{user}@{host}:{port}/{catalog}/{schema}".format(
        user=os.environ["TRINO_USER"],
        host=os.environ["TRINO_HOST"],
        port=os.environ["TRINO_PORT"],
        catalog=os.environ["TRINO_CATALOG"],
        schema=os.environ["TRINO_SCHEMA"],
    )
)

FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
    "DASHBOARD_NATIVE_FILTERS": True,
    "DASHBOARD_CROSS_FILTERS": True,
    "DRILL_TO_DETAIL": True,
}

PREVENT_UNSAFE_DEFAULT_URLS_ON_DATASET = False
SUPERSET_WEBSERVER_TIMEOUT = 300