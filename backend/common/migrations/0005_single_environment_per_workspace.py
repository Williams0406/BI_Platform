from django.db import migrations


def consolidate_environments(apps, schema_editor):
    PythonEnvironment = apps.get_model("common", "PythonEnvironment")
    EnvironmentPackage = apps.get_model("common", "EnvironmentPackage")
    ScriptBlock = apps.get_model("common", "ScriptBlock")

    workspace_ids = list(PythonEnvironment.objects.values_list("workspace_id", flat=True).distinct())
    rank = {"INSTALLED": 5, "INSTALLING": 4, "REQUESTED": 3, "FAILED": 2, "UNINSTALLING": 1}
    for workspace_id in workspace_ids:
        envs = list(PythonEnvironment.objects.filter(workspace_id=workspace_id).order_by("created_at", "id"))
        if not envs:
            continue
        primary = envs[0]
        primary.name = "Python"
        primary.status = "ACTIVE"
        primary.save(update_fields=["name", "status", "updated_at"])
        # Canonicalize the historical PyPI alias before merging environments.
        legacy_sklearn = EnvironmentPackage.objects.filter(environment=primary, name__iexact="sklearn").first()
        canonical_sklearn = EnvironmentPackage.objects.filter(environment=primary, name__iexact="scikit-learn").first()
        if legacy_sklearn and canonical_sklearn:
            if rank.get(legacy_sklearn.status, 0) > rank.get(canonical_sklearn.status, 0):
                canonical_sklearn.version_spec = legacy_sklearn.version_spec
                canonical_sklearn.status = legacy_sklearn.status
                canonical_sklearn.source = legacy_sklearn.source
                canonical_sklearn.installed_version = legacy_sklearn.installed_version
                canonical_sklearn.log = legacy_sklearn.log
                canonical_sklearn.save()
            legacy_sklearn.delete()
        elif legacy_sklearn:
            legacy_sklearn.name = "scikit-learn"
            legacy_sklearn.save(update_fields=["name", "updated_at"])

        for extra in envs[1:]:
            for package in list(EnvironmentPackage.objects.filter(environment=extra)):
                package_name = "scikit-learn" if package.name.lower() == "sklearn" else package.name
                existing = EnvironmentPackage.objects.filter(environment=primary, name__iexact=package_name).first()
                if existing:
                    if rank.get(package.status, 0) > rank.get(existing.status, 0):
                        existing.version_spec = package.version_spec
                        existing.status = package.status
                        existing.source = package.source
                        existing.installed_version = package.installed_version
                        existing.log = package.log
                        existing.save(update_fields=["version_spec", "status", "source", "installed_version", "log", "updated_at"])
                    package.delete()
                else:
                    package.environment = primary
                    package.name = package_name
                    package.save(update_fields=["environment", "name", "updated_at"])
            extra.delete()
        # Remove stale per-block environment selection. Runtime resolution is workspace-scoped.
        for block in ScriptBlock.objects.filter(workspace_id=workspace_id):
            context = dict(block.context or {})
            if "python_environment_id" in context:
                context.pop("python_environment_id", None)
                block.context = context
                block.save(update_fields=["context", "updated_at"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    # Data consolidation must commit before PostgreSQL adds the table constraint.
    # Otherwise deleting duplicate environments leaves deferred FK trigger events
    # pending and ALTER TABLE fails with ObjectInUse.
    atomic = False

    dependencies = [("common", "0004_environmentpackage_runtime_fields")]
    operations = [
        migrations.RunPython(consolidate_environments, noop_reverse),
    ]
