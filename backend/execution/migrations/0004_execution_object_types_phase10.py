from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("execution", "0003_execution_object_type_optimization")]
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
                    ("IMPORT", "Importación"),
                    ("EXPORT", "Exportación"),
                    ("DEPENDENCY_PROPAGATION", "Propagación de dependencias"),
                    ("GENERIC", "Genérica"),
                ],
                max_length=50,
            ),
        )
    ]
