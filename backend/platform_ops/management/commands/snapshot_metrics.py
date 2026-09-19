from django.core.management.base import BaseCommand
from platform_ops.services import snapshot_metrics

class Command(BaseCommand):
    help = "Captura un snapshot operacional."

    def handle(self, *args, **options):
        obj = snapshot_metrics()
        self.stdout.write(str(obj.id))
