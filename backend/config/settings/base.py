from pathlib import Path

from .env import env, env_int, env_list


BASE_DIR = Path(__file__).resolve().parents[2]

SECRET_KEY = env("DJANGO_SECRET_KEY", "unsafe-development-key-change-me")

DEBUG = False

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["127.0.0.1", "localhost"])

INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "corsheaders",
    "rest_framework",

    # Local apps
    "common",
    "identity",
    "workspaces",
    "datasources",
    "connectors",
    "data_model",
    "data_records",
    "views_engine",
    "transformations",
    "dependencies",
    "execution",
    "metrics",
    "analytics",
    "data_science",
    "optimization",
    "imports_exports",
    "platform_ops",
    "customer_gateway",
    "governance",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "platform_ops.middleware.RequestIDMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ------------------------------------------------------------
# Control Plane Database
# ------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", "business_intelligence_control"),
        "USER": env("DB_USER", "postgres"),
        "PASSWORD": env("DB_PASSWORD", ""),
        "HOST": env("DB_HOST", "127.0.0.1"),
        "PORT": env("DB_PORT", "5432"),
        "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 60),
        "OPTIONS": {
            "connect_timeout": env_int("DB_CONNECT_TIMEOUT", 5),
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "es-pe"
TIME_ZONE = "America/Lima"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "identity.User"

# ------------------------------------------------------------
# Django REST Framework
# ------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
}

# ------------------------------------------------------------
# CORS
# ------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    ["http://localhost:3000", "http://127.0.0.1:3000"],
)
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    ["http://localhost:3000", "http://127.0.0.1:3000"],
)

# ------------------------------------------------------------
# Security defaults
# ------------------------------------------------------------
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False

# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------
LOG_LEVEL = env("LOG_LEVEL", "INFO")
DJANGO_LOG_LEVEL = env("DJANGO_LOG_LEVEL", "INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "{asctime} | {levelname:<8} | {name} | {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": DJANGO_LOG_LEVEL,
            "propagate": False,
        },
        "platform": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}


# ------------------------------------------------------------
# JWT
# ------------------------------------------------------------
from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": True,
}


# ------------------------------------------------------------
# Celery / Redis
# ------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/1")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = env_int("CELERY_TASK_TIME_LIMIT", 1800)
CELERY_TASK_SOFT_TIME_LIMIT = env_int("CELERY_TASK_SOFT_TIME_LIMIT", 1740)
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

CELERY_TASK_ROUTES = {
    "execution.tasks.execute_job": {"queue": "fast"},
    "transformations.tasks.run_sql_transformation_task": {"queue": "sql"},
    "dependencies.tasks.propagate_asset_change_task": {"queue": "fast"},
    "data_science.tasks.run_python_transformation_task": {"queue": "python"},
    "data_science.tasks.train_model_task": {"queue": "ml"},
    "data_science.tasks.batch_inference_task": {"queue": "ml"},
    "optimization.tasks.run_optimization_task": {"queue": "optimization"},
    "imports_exports.tasks.run_import_task": {"queue": "imports"},
    "imports_exports.tasks.run_export_task": {"queue": "imports"},
    "platform_ops.tasks.run_maintenance_task": {"queue": "maintenance"},
    "platform_ops.tasks.snapshot_operational_metrics_task": {"queue": "maintenance"},
}

# Python Runtime / Data Science
PYTHON_RUNTIME_ROOT = BASE_DIR / "runtime_artifacts"
PYTHON_RUNTIME_TIMEOUT_SECONDS = env_int("PYTHON_RUNTIME_TIMEOUT_SECONDS", 300)
PYTHON_RUNTIME_MAX_ROWS = env_int("PYTHON_RUNTIME_MAX_ROWS", 100000)
PYTHON_RUNTIME_MEMORY_MB = env_int("PYTHON_RUNTIME_MEMORY_MB", 1024)
PYTHON_RUNTIME_ALLOWED_PACKAGES = ["pandas", "numpy", "math", "statistics", "datetime", "json"]

# ------------------------------------------------------------
# Customer Data Gateway
# ------------------------------------------------------------
GATEWAY_ENROLLMENT_TTL_MINUTES = env_int("GATEWAY_ENROLLMENT_TTL_MINUTES", 15)
GATEWAY_OFFLINE_AFTER_SECONDS = env_int("GATEWAY_OFFLINE_AFTER_SECONDS", 120)
GATEWAY_JOB_LEASE_SECONDS = env_int("GATEWAY_JOB_LEASE_SECONDS", 120)
GATEWAY_MAX_RESULT_ROWS = env_int("GATEWAY_MAX_RESULT_ROWS", 1000)

# ------------------------------------------------------------
# Phase 12 — Scalability / cache / storage / observability
# ------------------------------------------------------------
CACHE_URL = env("CACHE_URL", "redis://127.0.0.1:6379/2")
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": CACHE_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": env_int("REDIS_CONNECT_TIMEOUT", 3),
            "SOCKET_TIMEOUT": env_int("REDIS_SOCKET_TIMEOUT", 3),
            "IGNORE_EXCEPTIONS": True,
        },
        "KEY_PREFIX": env("CACHE_KEY_PREFIX", "bi-platform"),
        "TIMEOUT": env_int("CACHE_DEFAULT_TIMEOUT", 300),
    }
}

# Runtime artifacts can use LOCAL or S3-compatible storage.
ARTIFACT_STORAGE_BACKEND = env("ARTIFACT_STORAGE_BACKEND", "LOCAL").upper()
ARTIFACT_LOCAL_ROOT = BASE_DIR / env("ARTIFACT_LOCAL_DIR", "runtime_artifacts")
ARTIFACT_S3_BUCKET = env("ARTIFACT_S3_BUCKET", "")
ARTIFACT_S3_PREFIX = env("ARTIFACT_S3_PREFIX", "business-intelligence")
ARTIFACT_S3_REGION = env("ARTIFACT_S3_REGION", "")
ARTIFACT_S3_ENDPOINT_URL = env("ARTIFACT_S3_ENDPOINT_URL", "")
ARTIFACT_S3_ACCESS_KEY_ID = env("ARTIFACT_S3_ACCESS_KEY_ID", "")
ARTIFACT_S3_SECRET_ACCESS_KEY = env("ARTIFACT_S3_SECRET_ACCESS_KEY", "")

# Keep legacy setting as local working/cache area.
PYTHON_RUNTIME_ROOT = ARTIFACT_LOCAL_ROOT

OPS_STALE_EXECUTION_MINUTES = env_int("OPS_STALE_EXECUTION_MINUTES", 120)
OPS_READY_CHECK_REDIS = env("OPS_READY_CHECK_REDIS", "true").lower() in {"1","true","yes","on"}
OPS_READY_CHECK_STORAGE = env("OPS_READY_CHECK_STORAGE", "false").lower() in {"1","true","yes","on"}

# PostgreSQL / PgBouncer guidance.
DB_POOL_MODE = env("DB_POOL_MODE", "DJANGO").upper()

CELERY_BEAT_SCHEDULE = {
    "platform-maintenance-hourly": {
        "task": "platform_ops.tasks.run_maintenance_task",
        "schedule": 3600.0,
        "options": {"queue": "maintenance"},
    },
    "operational-metrics-every-5-minutes": {
        "task": "platform_ops.tasks.snapshot_operational_metrics_task",
        "schedule": 300.0,
        "options": {"queue": "maintenance"},
    },
    "source-sync-dispatch-every-minute": {
        "task": "imports_exports.tasks.dispatch_due_source_syncs",
        "schedule": 60.0,
        "options": {"queue": "maintenance"},
    },
}

IMPORT_EXPORT_MAX_SYNC_ROWS = env_int("IMPORT_EXPORT_MAX_SYNC_ROWS", 2000000)
