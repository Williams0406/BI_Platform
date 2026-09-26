from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[("data_science","0001_initial")]
    operations=[migrations.AlterField(model_name="modeldefinition",name="algorithm",field=models.CharField(choices=[("LOGISTIC_REGRESSION","Logistic Regression"),("RANDOM_FOREST_CLASSIFIER","Random Forest Classifier"),("LINEAR_REGRESSION","Linear Regression"),("RANDOM_FOREST_REGRESSOR","Random Forest Regressor"),("XGBOOST_CLASSIFIER","XGBoost Classifier"),("XGBOOST_REGRESSOR","XGBoost Regressor"),("PYTHON_ESTIMATOR","Python Estimator")],max_length=40))]
