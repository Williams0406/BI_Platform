from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("execution", "0002_execution_object_types_phase8")]
    operations = [
        migrations.AlterField(
            model_name="execution",
            name="object_type",
            field=models.CharField(
                choices=[
                    ("SQL_TRANSFORMATION", "Transformación SQL"),
                    ("PYTHON_TRANSFORMATION", "Transformación Python"),
                    ("ML_TRAINING", "Entrenamiento ML"),
                    ("ML_INFERENCE", "Inferencia ML"),
                    ("OPTIMIZATION", "Optimización"),
                    ("DEPENDENCY_PROPAGATION", "Propagación de dependencias"),
                    ("GENERIC", "Genérica"),
                ],
                max_length=50,
            ),
        )
    ]
