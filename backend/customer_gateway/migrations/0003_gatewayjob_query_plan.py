from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("customer_gateway", "0002_gatewayimportrequest")]
    operations = [
        migrations.AlterField(
            model_name="gatewayjob",
            name="operation",
            field=models.CharField(
                choices=[
                    ("TEST_CONNECTION", "Test connection"),
                    ("CATALOG", "Catalog introspection"),
                    ("READ_PAGE", "Read page"),
                    ("QUERY_PLAN", "Operational query plan"),
                    ("INSERT", "Insert"),
                    ("UPDATE", "Update"),
                    ("DELETE", "Delete"),
                ],
                max_length=30,
            ),
        )
    ]
