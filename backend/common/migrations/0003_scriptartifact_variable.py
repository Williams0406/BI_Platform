from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[('common','0002_universal_scripts_environments')]
    operations=[migrations.AlterField(model_name='scriptartifact',name='artifact_type',field=models.CharField(choices=[('TRANSFORMATION','Transformation'),('FIELD_RULE','Field rule'),('MEASURE','Measure'),('CHART','Chart'),('FUNCTION','Function'),('ML_MODEL','ML model'),('OPTIMIZATION','Optimization'),('DATASET','Dataset'),('VARIABLE','Variable')],max_length=24))]
