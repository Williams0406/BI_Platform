import shutil
from django.core.management.base import BaseCommand, CommandError
from common.models import PythonEnvironment
from common.environment_services import env_root
from common.environment_tasks import install_environment_package

class Command(BaseCommand):
    help = "Rebuild one isolated Python environment at the configured short runtime path and reinstall its recorded packages."

    def add_arguments(self, parser):
        parser.add_argument("--environment", required=True, dest="environment_id")
        parser.add_argument("--yes", action="store_true", help="Required confirmation because the isolated venv is deleted and recreated.")

    def handle(self, *args, **options):
        if not options["yes"]:
            raise CommandError("Re-run with --yes to confirm rebuilding the isolated Python environment.")
        try:
            env=PythonEnvironment.objects.prefetch_related("packages").get(pk=options["environment_id"])
        except PythonEnvironment.DoesNotExist as exc:
            raise CommandError("Python environment not found.") from exc
        root=env_root(env)
        if root.exists(): shutil.rmtree(root)
        packages=list(env.packages.all().order_by("created_at"))
        for package in packages:
            package.status="REQUESTED"; package.installed_version=""; package.log=""
            package.save(update_fields=["status","installed_version","log","updated_at"])
            install_environment_package.apply_async(args=[str(package.id)],queue="python")
            self.stdout.write(f"queued {package.name}")
        self.stdout.write(self.style.SUCCESS(f"Rebuild queued for {env.name} v{env.version} at {root} ({len(packages)} package(s))."))
