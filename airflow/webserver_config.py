from __future__ import annotations
import os
from datetime import timedelta
from flask_appbuilder.const import AUTH_DB

basedir = os.path.abspath(os.path.dirname(__file__))
AUTH_TYPE = AUTH_DB
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = None
PERMANENT_SESSION_LIFETIME = timedelta(days=30)
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False