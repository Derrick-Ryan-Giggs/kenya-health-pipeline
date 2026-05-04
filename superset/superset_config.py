# ============================================================
# Kenya Health Facility Mapping Pipeline
# superset/superset_config.py
#
# All sensitive values come from environment variables.
# Never hardcode secrets here.
# Mounted into the container at:
#   /app/pythonpath/superset_config.py
# ============================================================

import os

# ── Core security ─────────────────────────────────────────────
SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]

# ── Metadata database (Superset internal state) ───────────────
SQLALCHEMY_DATABASE_URI = os.environ["DATABASE_URL"]

# ── Feature flags ─────────────────────────────────────────────
FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,    # allows {{ }} in SQL queries
    "DASHBOARD_NATIVE_FILTERS": True,      # cross-filter between charts
    "DASHBOARD_CROSS_FILTERS": True,
    "DRILL_TO_DETAIL": True,               # Nairobi sub-county drill-down
}

# ── Security ──────────────────────────────────────────────────
WTF_CSRF_ENABLED = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False              # set True when behind HTTPS

# ── Trino connection (shown as default DB in UI) ──────────────
SQLALCHEMY_EXAMPLES_URI = (
    "trino://{user}@{host}:{port}/{catalog}/{schema}".format(
        user=os.environ["TRINO_USER"],
        host=os.environ["TRINO_HOST"],
        port=os.environ["TRINO_PORT"],
        catalog=os.environ["TRINO_CATALOG"],
        schema=os.environ["TRINO_SCHEMA"],
    )
)

# ── Cache (uses filesystem by default — upgrade to Redis later) ─
CACHE_CONFIG = {
    "CACHE_TYPE": "FileSystemCache",
    "CACHE_DIR": "/app/superset_home/cache",
}

# ── Timeout for long-running Trino queries ────────────────────
SUPERSET_WEBSERVER_TIMEOUT = 300          # 5 minutes