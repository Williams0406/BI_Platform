from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("metrics", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="metricdefinition",
            name="expression_type",
            field=models.CharField(
                choices=[("SIMPLE", "Simple"), ("SQL", "SQL"), ("DAX", "DAX"), ("PYTHON", "Python")],
                default="SIMPLE",
                max_length=20,
            ),
        ),
    ]
