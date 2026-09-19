from .base import *  # noqa: F403,F401
from .env import env_bool


DEBUG = env_bool("DJANGO_DEBUG", True)

# Browsable API is useful during development.
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa: F405
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]
