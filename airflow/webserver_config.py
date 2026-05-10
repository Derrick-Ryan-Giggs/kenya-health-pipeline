from __future__ import annotations
import os
from datetime import timedelta
from flask_appbuilder.const import AUTH_DB

AUTH_TYPE = AUTH_DB
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = None

# flask-session 0.5.0 syntax — string URL works here
SESSION_TYPE = "redis"
SESSION_REDIS = "redis://redis:6379/2"
SESSION_PERMANENT = True
SESSION_USE_SIGNER = True
PERMANENT_SESSION_LIFETIME = timedelta(days=730)
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False