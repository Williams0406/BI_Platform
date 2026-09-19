from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("data_model", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="tableasset",
            name="row_version_column",
            field=models.CharField(blank=True, max_length=180),
        ),
    ]
