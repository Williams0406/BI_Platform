import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Organization",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=180)),
                ("slug", models.SlugField(max_length=180, unique=True)),
                ("status", models.CharField(choices=[("ACTIVE", "Activa"), ("SUSPENDED", "Suspendida"), ("ARCHIVED", "Archivada")], default="ACTIVE", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="organizations_created", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Membership",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("role", models.CharField(choices=[("OWNER", "Propietario"), ("ADMIN", "Administrador"), ("BUILDER", "Constructor"), ("ANALYST", "Analista"), ("VIEWER", "Visualizador")], default="VIEWER", max_length=20)),
                ("is_active", models.BooleanField(default=True)),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="workspaces.organization")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="organization_memberships", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="Workspace",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=180)),
                ("slug", models.SlugField(max_length=180)),
                ("description", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("ACTIVE", "Activo"), ("ARCHIVED", "Archivado")], default="ACTIVE", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="workspaces_created", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="workspaces", to="workspaces.organization")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddConstraint(
            model_name="membership",
            constraint=models.UniqueConstraint(fields=("organization", "user"), name="unique_membership_per_organization_user"),
        ),
        migrations.AddConstraint(
            model_name="workspace",
            constraint=models.UniqueConstraint(fields=("organization", "slug"), name="unique_workspace_slug_per_organization"),
        ),
    ]
