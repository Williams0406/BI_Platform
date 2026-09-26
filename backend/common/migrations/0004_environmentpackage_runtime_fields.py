from django.db import migrations, models
class Migration(migrations.Migration):
    dependencies=[('common','0003_scriptartifact_variable')]
    operations=[
        migrations.AddField(model_name='environmentpackage',name='installed_version',field=models.CharField(blank=True,default='',max_length=80)),
        migrations.AddField(model_name='environmentpackage',name='log',field=models.TextField(blank=True,default='')),
        migrations.AddField(model_name='environmentpackage',name='updated_at',field=models.DateTimeField(auto_now=True)),
    ]
