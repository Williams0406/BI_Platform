from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("common", "0005_single_environment_per_workspace")]

    operations = [
        migrations.AddConstraint(
            model_name="pythonenvironment",
            constraint=models.UniqueConstraint(
                fields=("workspace",),
                name="unique_python_environment_per_workspace",
            ),
        ),
    ]
