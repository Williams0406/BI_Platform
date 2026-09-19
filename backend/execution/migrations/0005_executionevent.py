from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("execution", "0004_execution_object_types_phase10")]
    operations = [
        migrations.CreateModel(
            name="ExecutionEvent",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("sequence", models.PositiveBigIntegerField()),
                ("family", models.CharField(choices=[("EXECUTION","Execution"),("METRIC","Metric"),("ML","Machine Learning"),("OPTIMIZATION","Optimization"),("ARTIFACT","Artifact"),("LOG","Log")], max_length=24)),
                ("event_type", models.CharField(max_length=80)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("execution", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="execution.execution")),
            ],
            options={"ordering":["sequence","id"]},
        ),
        migrations.AddConstraint(model_name="executionevent", constraint=models.UniqueConstraint(fields=("execution","sequence"), name="unique_execution_event_sequence")),
        migrations.AddIndex(model_name="executionevent", index=models.Index(fields=["execution","sequence"], name="execution_e_executi_7e4d2a_idx")),
        migrations.AddIndex(model_name="executionevent", index=models.Index(fields=["event_type"], name="execution_e_event_t_a9c317_idx")),
    ]
