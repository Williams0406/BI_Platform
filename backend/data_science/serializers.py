from rest_framework import serializers
from data_model.models import FieldAsset
from workspaces.models import Membership
from .models import DatasetDefinition, ModelDefinition, ModelRun, ModelVersion, PredictionAsset, PythonTransformation, PythonTransformationInput

WRITE_ROLES={Membership.Role.OWNER,Membership.Role.ADMIN,Membership.Role.BUILDER}
def can_build(user,workspace):
    return Membership.objects.filter(organization=workspace.organization,user=user,is_active=True,role__in=WRITE_ROLES).exists()

class PythonTransformationInputSerializer(serializers.ModelSerializer):
    asset_name=serializers.CharField(source="asset.name",read_only=True)
    class Meta:
        model=PythonTransformationInput
        fields=["id","asset","asset_name","alias"]; read_only_fields=["id"]

class PythonTransformationSerializer(serializers.ModelSerializer):
    inputs=PythonTransformationInputSerializer(many=True,read_only=True)
    class Meta:
        model=PythonTransformation
        fields=["id","workspace","name","description","code","output_name","output_asset","allowed_packages","timeout_seconds","memory_limit_mb","max_input_rows","enabled","inputs","created_at","updated_at"]
        read_only_fields=["id","output_asset","created_at","updated_at"]
    def create(self,validated_data):
        request=self.context["request"]
        if not can_build(request.user,validated_data["workspace"]): raise serializers.ValidationError("No tiene permisos para crear transformaciones Python.")
        return PythonTransformation.objects.create(created_by=request.user,**validated_data)

class DatasetDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model=DatasetDefinition
        fields=["id","workspace","name","description","source_table","filter_config","sample_limit","enabled","created_at","updated_at"]
        read_only_fields=["id","created_at","updated_at"]
    def validate(self,attrs):
        workspace=attrs.get("workspace",getattr(self.instance,"workspace",None)); table=attrs.get("source_table",getattr(self.instance,"source_table",None))
        if workspace and table and table.data_source.workspace_id!=workspace.id: raise serializers.ValidationError("Dataset y tabla fuente deben pertenecer al mismo workspace.")
        return attrs
    def create(self,validated_data):
        request=self.context["request"]
        if not can_build(request.user,validated_data["workspace"]): raise serializers.ValidationError("No tiene permisos para crear datasets.")
        return DatasetDefinition.objects.create(created_by=request.user,**validated_data)

class ModelDefinitionSerializer(serializers.ModelSerializer):
    features=serializers.PrimaryKeyRelatedField(queryset=FieldAsset.objects.all(),many=True)
    class Meta:
        model=ModelDefinition
        fields=["id","workspace","dataset","name","description","task_type","algorithm","features","target","parameters","test_size","random_state","enabled","data_asset","created_at","updated_at"]
        read_only_fields=["id","data_asset","created_at","updated_at"]
    def validate(self,attrs):
        workspace=attrs.get("workspace",getattr(self.instance,"workspace",None))
        dataset=attrs.get("dataset",getattr(self.instance,"dataset",None))
        features=attrs.get("features",None); target=attrs.get("target",getattr(self.instance,"target",None))
        test_size=attrs.get("test_size",getattr(self.instance,"test_size",0.2))
        if not 0.05<=float(test_size)<=0.5: raise serializers.ValidationError("test_size debe estar entre 0.05 y 0.5.")
        if workspace and dataset and dataset.workspace_id!=workspace.id: raise serializers.ValidationError("Dataset y modelo deben pertenecer al mismo workspace.")
        if dataset:
            table_id=dataset.source_table_id
            if target and target.table_asset_id!=table_id: raise serializers.ValidationError("Target debe pertenecer a la tabla del Dataset.")
            if features is not None:
                bad=[f.name for f in features if f.table_asset_id!=table_id]
                if bad: raise serializers.ValidationError("Features fuera de la tabla del Dataset: "+", ".join(bad))
                if target and target in features: raise serializers.ValidationError("Target no puede incluirse como feature.")
        return attrs
    def create(self,validated_data):
        features=validated_data.pop("features"); request=self.context["request"]
        if not can_build(request.user,validated_data["workspace"]): raise serializers.ValidationError("No tiene permisos para crear modelos.")
        obj=ModelDefinition.objects.create(created_by=request.user,**validated_data); obj.features.set(features); return obj

class ModelRunSerializer(serializers.ModelSerializer):
    class Meta:
        model=ModelRun
        fields=["id","model","execution_id","status","metrics","parameters_snapshot","input_asset_versions","row_count","train_row_count","test_row_count","started_at","finished_at","error_message","created_at"]

class ModelVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model=ModelVersion
        fields=["id","model","run","version","artifact_path","metrics","feature_names","target_name","algorithm","sklearn_version","created_at"]

class PredictionAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model=PredictionAsset
        fields=["id","model_version","source_dataset","data_asset","artifact_path","row_count","created_at"]

class InferenceRequestSerializer(serializers.Serializer):
    dataset=serializers.PrimaryKeyRelatedField(queryset=DatasetDefinition.objects.all())
