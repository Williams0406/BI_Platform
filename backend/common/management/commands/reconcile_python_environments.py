from django.core.management.base import BaseCommand
from common.models import EnvironmentPackage
from common.environment_tasks import install_environment_package

class Command(BaseCommand):
    help = "Requeue REQUESTED/FAILED Python environment packages for installation."

    def add_arguments(self, parser):
        parser.add_argument("--environment", dest="environment_id")

    def handle(self, *args, **options):
        qs=EnvironmentPackage.objects.select_related("environment").filter(status__in=["REQUESTED","FAILED"])
        if options.get("environment_id"):
            qs=qs.filter(environment_id=options["environment_id"])
        count=0
        for package in qs:
            package.status="REQUESTED"; package.log=""; package.save(update_fields=["status","log","updated_at"])
            install_environment_package.apply_async(args=[str(package.id)],queue="python")
            count+=1
            self.stdout.write(f"queued {package.environment.name} v{package.environment.version}: {package.name}")
        self.stdout.write(self.style.SUCCESS(f"Queued {count} package installation(s)."))
