# Celery autodiscovery entrypoint for common app tasks.
from .environment_tasks import install_environment_package, uninstall_environment_package
__all__=["install_environment_package","uninstall_environment_package"]
