from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("execution", "0001_initial")]
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
                    ("DEPENDENCY_PROPAGATION", "Propagación de dependencias"),
                    ("GENERIC", "Genérica"),
                ],
                max_length=50,
            ),
        ),
    ]
