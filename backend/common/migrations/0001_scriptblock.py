from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid
class Migration(migrations.Migration):
    initial=True
    dependencies=[('workspaces','0001_initial'),migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[migrations.CreateModel(name='ScriptBlock',fields=[('id',models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),('name',models.CharField(max_length=220)),('language',models.CharField(choices=[('SQL','SQL'),('PYTHON','Python'),('DAX','DAX')],max_length=12)),('purpose',models.CharField(choices=[('TRANSFORMATION','Transformation'),('MEASURE','Measure'),('CHART','Chart'),('ML','Machine learning'),('OPTIMIZATION','Optimization'),('FUNCTION','Reusable function'),('FIELD_RULE','Field rule')],max_length=24)),('code',models.TextField()),('context',models.JSONField(blank=True,default=dict)),('linked_object_type',models.CharField(blank=True,max_length=80)),('linked_object_id',models.CharField(blank=True,max_length=80)),('status',models.CharField(default='SAVED',max_length=20)),('created_at',models.DateTimeField(auto_now_add=True)),('updated_at',models.DateTimeField(auto_now=True)),('created_by',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='script_blocks_created',to=settings.AUTH_USER_MODEL)),('workspace',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='script_blocks',to='workspaces.workspace'))],options={'ordering':['created_at']})]
