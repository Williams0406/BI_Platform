from .base import *  # noqa: F403,F401
from .env import env_bool


DEBUG = False

SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Reverse proxy / production security
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SECURE_REFERRER_POLICY = "same-origin"

# In production behind PgBouncer transaction pooling set DB_CONN_MAX_AGE=0.
if DB_POOL_MODE == "PGBOUNCER":  # noqa: F405
    DATABASES["default"]["CONN_MAX_AGE"] = 0  # noqa: F405
