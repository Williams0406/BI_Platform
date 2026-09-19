from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("data_model", "0003_platform_fields_and_content_rules"),
    ]

    operations = [
        migrations.AddField(
            model_name="relationasset",
            name="cardinality",
            field=models.CharField(
                choices=[
                    ("ONE_TO_ONE", "One to one"),
                    ("ONE_TO_MANY", "One to many"),
                    ("MANY_TO_ONE", "Many to one"),
                    ("MANY_TO_MANY", "Many to many"),
                ],
                default="ONE_TO_MANY",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="relationasset",
            name="cross_filter_direction",
            field=models.CharField(
                choices=[("SINGLE", "Single"), ("BOTH", "Both")],
                default="SINGLE",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="relationasset",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
    ]
