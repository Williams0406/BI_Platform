from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies=[('governance','0001_initial'),('workspaces','0001_initial')]
    operations=[migrations.CreateModel(name='WorkspacePolicy',fields=[
        ('workspace',models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,primary_key=True,related_name='governance_policy',serialize=False,to='workspaces.workspace')),
        ('allow_import',models.BooleanField(default=True)),('allow_refresh',models.BooleanField(default=True)),
        ('allow_external_write',models.BooleanField(default=False)),('allow_schema_changes',models.BooleanField(default=False)),
        ('allow_operational_writeback',models.BooleanField(default=False)),('allow_delete',models.BooleanField(default=False)),
        ('allow_platform_compute',models.BooleanField(default=True)),('allow_customer_compute',models.BooleanField(default=True)),
        ('allow_customer_packages',models.BooleanField(default=True)),('require_ddl_approval',models.BooleanField(default=True)),
        ('require_bulk_write_approval',models.BooleanField(default=True)),('updated_at',models.DateTimeField(auto_now=True)),
    ])]
