import uuid
from django.conf import settings
from django.db import migrations,models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial=True
    dependencies=[
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("workspaces","0001_initial"),
        ("datasources","0001_initial"),
    ]
    operations=[
        migrations.CreateModel(
            name="GatewayRegistration",
            fields=[
                ("id",models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),
                ("name",models.CharField(max_length=180)),
                ("status",models.CharField(choices=[("PENDING","Pending enrollment"),("ONLINE","Online"),("OFFLINE","Offline"),("REVOKED","Revoked")],default="PENDING",max_length=20)),
                ("enrollment_code_hash",models.CharField(blank=True,max_length=64)),
                ("enrollment_expires_at",models.DateTimeField(blank=True,null=True)),
                ("agent_token_hash",models.CharField(blank=True,max_length=64)),
                ("token_version",models.PositiveIntegerField(default=0)),
                ("agent_version",models.CharField(blank=True,max_length=80)),
                ("platform",models.CharField(blank=True,max_length=120)),
                ("hostname",models.CharField(blank=True,max_length=255)),
                ("last_seen_at",models.DateTimeField(blank=True,null=True)),
                ("last_ip",models.GenericIPAddressField(blank=True,null=True)),
                ("capabilities",models.JSONField(blank=True,default=dict)),
                ("created_at",models.DateTimeField(auto_now_add=True)),
                ("updated_at",models.DateTimeField(auto_now=True)),
                ("created_by",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="gateways_created",to=settings.AUTH_USER_MODEL)),
                ("workspace",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="gateways",to="workspaces.workspace")),
            ],
            options={"ordering":["name"]},
        ),
        migrations.CreateModel(
            name="GatewayDataSourceBinding",
            fields=[
                ("id",models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),
                ("local_connection_name",models.CharField(max_length=180)),
                ("enabled",models.BooleanField(default=True)),
                ("created_at",models.DateTimeField(auto_now_add=True)),
                ("data_source",models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,related_name="gateway_binding",to="datasources.datasource")),
                ("gateway",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="bindings",to="customer_gateway.gatewayregistration")),
            ],
        ),
        migrations.CreateModel(
            name="GatewayHeartbeat",
            fields=[
                ("id",models.BigAutoField(primary_key=True,serialize=False)),
                ("agent_version",models.CharField(blank=True,max_length=80)),
                ("metrics",models.JSONField(blank=True,default=dict)),
                ("created_at",models.DateTimeField(auto_now_add=True)),
                ("gateway",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="heartbeats",to="customer_gateway.gatewayregistration")),
            ],
            options={"ordering":["-created_at"]},
        ),
        migrations.CreateModel(
            name="GatewayJob",
            fields=[
                ("id",models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),
                ("operation",models.CharField(choices=[("TEST_CONNECTION","Test connection"),("CATALOG","Catalog introspection"),("READ_PAGE","Read page"),("INSERT","Insert"),("UPDATE","Update"),("DELETE","Delete")],max_length=30)),
                ("payload",models.JSONField(blank=True,default=dict)),
                ("status",models.CharField(choices=[("QUEUED","Queued"),("CLAIMED","Claimed"),("SUCCESS","Success"),("FAILED","Failed"),("CANCELLED","Cancelled"),("EXPIRED","Expired")],default="QUEUED",max_length=20)),
                ("claimed_at",models.DateTimeField(blank=True,null=True)),
                ("lease_expires_at",models.DateTimeField(blank=True,null=True)),
                ("finished_at",models.DateTimeField(blank=True,null=True)),
                ("result",models.JSONField(blank=True,default=dict)),
                ("error_message",models.TextField(blank=True)),
                ("created_at",models.DateTimeField(auto_now_add=True)),
                ("data_source",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="gateway_jobs",to="datasources.datasource")),
                ("gateway",models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name="jobs",to="customer_gateway.gatewayregistration")),
                ("requested_by",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name="gateway_jobs_requested",to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering":["created_at"]},
        ),
        migrations.AddConstraint(model_name="gatewayregistration",constraint=models.UniqueConstraint(fields=("workspace","name"),name="unique_gateway_name_per_workspace")),
        migrations.AddConstraint(model_name="gatewaydatasourcebinding",constraint=models.UniqueConstraint(fields=("gateway","local_connection_name"),name="unique_gateway_local_connection_name")),
        migrations.AddIndex(model_name="gatewayjob",index=models.Index(fields=["gateway","status","created_at"],name="customer_ga_gateway_4dcf35_idx")),
    ]
