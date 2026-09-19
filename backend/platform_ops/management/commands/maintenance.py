import json
from django.core.management.base import BaseCommand
from platform_ops.maintenance import run_maintenance

class Command(BaseCommand):
    help = "Ejecuta retención, limpieza de artifacts y recuperación de executions stale."

    def handle(self, *args, **options):
        self.stdout.write(json.dumps(run_maintenance(), indent=2, ensure_ascii=False))
