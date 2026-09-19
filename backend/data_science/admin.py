from django.contrib import admin
from .models import DatasetDefinition, ModelDefinition, ModelRun, ModelVersion, PredictionAsset, PythonTransformation, PythonTransformationInput

class PythonTransformationInputInline(admin.TabularInline):
    model=PythonTransformationInput
    extra=0

@admin.register(PythonTransformation)
class PythonTransformationAdmin(admin.ModelAdmin):
    list_display=["name","workspace","enabled","timeout_seconds","updated_at"]
    list_filter=["enabled"]; search_fields=["name"]; inlines=[PythonTransformationInputInline]

@admin.register(DatasetDefinition)
class DatasetDefinitionAdmin(admin.ModelAdmin):
    list_display=["name","workspace","source_table","enabled","updated_at"]
    list_filter=["enabled"]; search_fields=["name"]

@admin.register(ModelDefinition)
class ModelDefinitionAdmin(admin.ModelAdmin):
    list_display=["name","workspace","task_type","algorithm","enabled"]
    list_filter=["task_type","algorithm","enabled"]; search_fields=["name"]

@admin.register(ModelRun)
class ModelRunAdmin(admin.ModelAdmin):
    list_display=["model","status","row_count","created_at"]; list_filter=["status"]

@admin.register(ModelVersion)
class ModelVersionAdmin(admin.ModelAdmin):
    list_display=["model","version","algorithm","sklearn_version","created_at"]

@admin.register(PredictionAsset)
class PredictionAssetAdmin(admin.ModelAdmin):
    list_display=["model_version","source_dataset","row_count","created_at"]
