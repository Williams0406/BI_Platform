from rest_framework import serializers

from workspaces.models import Membership

from .models import DataAsset, DataSource



SECRET_KEYS = {
    "password",
    "pwd",
    "secret",
    "token",
    "access_token",
    "private_key",
}


def reject_persisted_secrets(metadata):
    lowered = {str(key).lower() for key in (metadata or {}).keys()}
    forbidden = sorted(lowered.intersection(SECRET_KEYS))
    if forbidden:
        raise serializers.ValidationError(
            "connection_metadata no puede almacenar secretos en esta fase: "
            + ", ".join(forbidden)
        )
    return metadata


WRITE_ROLES = [
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.BUILDER,
]


def assert_workspace_write_access(request, workspace):
    allowed = Membership.objects.filter(
        organization=workspace.organization,
        user=request.user,
        is_active=True,
        role__in=WRITE_ROLES,
    ).exists()

    if not allowed:
        raise serializers.ValidationError(
            "No tiene permisos de escritura sobre este workspace."
        )


class DataSourceSerializer(serializers.ModelSerializer):
    query_capabilities = serializers.SerializerMethodField()

    def get_query_capabilities(self, obj):
        from connectors.query_plan import capabilities_for_engine
        caps = capabilities_for_engine(obj.engine)
        result = {"effective": caps, "transport": "direct"}
        if obj.mode == DataSource.Mode.PRIVATE_GATEWAY:
            result["transport"] = "private_gateway"
            try:
                gateway_caps = obj.gateway_binding.gateway.capabilities or {}
                result["gateway_operations"] = gateway_caps.get("operations") or []
                result["gateway_pushdown"] = (gateway_caps.get("query_pushdown") or {}).get(obj.engine, {})
                result["query_plan_ready"] = "QUERY_PLAN" in result["gateway_operations"]
            except Exception:
                result["gateway_operations"] = []
                result["gateway_pushdown"] = {}
                result["query_plan_ready"] = False
        else:
            result["query_plan_ready"] = bool(caps.get("pagination"))
        return result
    class Meta:
        model = DataSource
        fields = [
            "id",
            "workspace",
            "name",
            "mode",
            "engine",
            "status",
            "can_read",
            "can_write",
            "can_ddl",
            "connection_metadata",
            "query_capabilities",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_workspace(self, workspace):
        assert_workspace_write_access(self.context["request"], workspace)
        return workspace

    def validate_connection_metadata(self, value):
        return reject_persisted_secrets(value)

    def validate(self, attrs):
        mode = attrs.get("mode", getattr(self.instance, "mode", None))
        engine = attrs.get("engine", getattr(self.instance, "engine", None))

        if mode == DataSource.Mode.MANAGED and engine != DataSource.Engine.PLATFORM_POSTGRES:
            raise serializers.ValidationError(
                {
                    "engine": (
                        "Un DataSource MANAGED debe usar PLATFORM_POSTGRES "
                        "en esta versión."
                    )
                }
            )
        if mode == DataSource.Mode.MANAGED:
            workspace = attrs.get("workspace", getattr(self.instance, "workspace", None))
            if workspace:
                existing = DataSource.objects.filter(
                    workspace=workspace,
                    mode=DataSource.Mode.MANAGED,
                    engine=DataSource.Engine.PLATFORM_POSTGRES,
                )
                if self.instance:
                    existing = existing.exclude(pk=self.instance.pk)
                if existing.exists():
                    raise serializers.ValidationError(
                        {"mode": "Este workspace ya tiene un almacenamiento Managed / Platform."}
                    )
        return attrs

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        if validated_data.get("mode") in {DataSource.Mode.EXTERNAL, DataSource.Mode.PRIVATE_GATEWAY}:
            # External/private sources enter the platform in source-protected mode.
            # Platform-owned extensions are handled separately and never imply DDL on the source.
            validated_data["can_read"] = True
            validated_data["can_write"] = False
            validated_data["can_ddl"] = False
        return super().create(validated_data)


class DataAssetSerializer(serializers.ModelSerializer):
    data_source_name = serializers.CharField(
        source="data_source.name",
        read_only=True,
    )

    class Meta:
        model = DataAsset
        fields = [
            "id",
            "workspace",
            "data_source",
            "data_source_name",
            "name",
            "asset_type",
            "status",
            "physical_schema",
            "physical_name",
            "metadata",
            "version",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "version", "created_at", "updated_at"]

    def validate_workspace(self, workspace):
        assert_workspace_write_access(self.context["request"], workspace)
        return workspace

    def validate(self, attrs):
        workspace = attrs.get("workspace", getattr(self.instance, "workspace", None))
        data_source = attrs.get(
            "data_source",
            getattr(self.instance, "data_source", None),
        )

        if data_source and workspace and data_source.workspace_id != workspace.id:
            raise serializers.ValidationError(
                {"data_source": "El DataSource pertenece a otro workspace."}
            )
        return attrs

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)

from .models import SourceBinding, PublishPlan, WritebackPolicy

class SourceBindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceBinding
        fields = ["id","workspace","source","source_schema","source_table","platform_asset","access_mode","primary_key_fields","cursor_field","last_refresh_at","created_at","updated_at"]
        read_only_fields = ["id","last_refresh_at","created_at","updated_at"]
    def validate(self, attrs):
        ws=attrs.get("workspace",getattr(self.instance,"workspace",None)); src=attrs.get("source",getattr(self.instance,"source",None))
        if ws: assert_workspace_write_access(self.context["request"],ws)
        if src and ws and src.workspace_id != ws.id: raise serializers.ValidationError({"source":"La fuente pertenece a otro workspace."})
        return attrs
    def create(self, validated_data):
        validated_data["created_by"]=self.context["request"].user
        obj=super().create(validated_data)
        try:
            from governance.models import DataCopyEvent
            DataCopyEvent.objects.create(workspace=obj.workspace,source=obj.source,binding=obj,kind=DataCopyEvent.Kind.INITIAL_SNAPSHOT,title="Initial Platform copy",summary=f"{obj.source_schema + '.' if obj.source_schema else ''}{obj.source_table} copied to Platform",detail={"source_schema":obj.source_schema,"source_table":obj.source_table,"platform_asset":str(obj.platform_asset_id or "")},version=1,actor=self.context["request"].user)
        except Exception:
            pass
        return obj

class PublishPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublishPlan
        fields = ["id","workspace","source","binding","name","scope","status","schema_changes","data_changes","generated_sql","created_at","updated_at"]
        read_only_fields = ["id","created_at","updated_at"]
    def validate(self, attrs):
        ws=attrs.get("workspace",getattr(self.instance,"workspace",None)); src=attrs.get("source",getattr(self.instance,"source",None)); scope=attrs.get("scope",getattr(self.instance,"scope",PublishPlan.Scope.DATA))
        if ws: assert_workspace_write_access(self.context["request"],ws)
        if src and ws and src.workspace_id != ws.id: raise serializers.ValidationError({"source":"La fuente pertenece a otro workspace."})
        if src and scope in {PublishPlan.Scope.SCHEMA,PublishPlan.Scope.SCHEMA_DATA} and not src.can_ddl: raise serializers.ValidationError({"scope":"DDL debe habilitarse explícitamente antes de publicar cambios de estructura."})
        if src and scope in {PublishPlan.Scope.DATA,PublishPlan.Scope.SCHEMA_DATA} and not src.can_write: raise serializers.ValidationError({"scope":"WRITE debe habilitarse explícitamente antes de publicar datos."})
        return attrs
    def create(self, validated_data):
        validated_data["created_by"]=self.context["request"].user
        obj=super().create(validated_data)
        try:
            from governance.models import DataCopyEvent
            DataCopyEvent.objects.create(workspace=obj.workspace,source=obj.source,binding=obj.binding,kind=DataCopyEvent.Kind.PUBLISH,title=obj.name,summary=f"Publish plan created · {obj.scope}",detail={"publish_plan":str(obj.id),"scope":obj.scope,"schema_changes":obj.schema_changes,"data_changes":obj.data_changes},version=1,published=obj.status in {"SUCCEEDED"},actor=self.context["request"].user)
        except Exception:
            pass
        return obj

class WritebackPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = WritebackPolicy
        fields = ["id","workspace","source","source_schema","source_table","allowed_operations","allowed_fields","key_fields","validation_rules","enabled","created_at","updated_at"]
        read_only_fields = ["id","created_at","updated_at"]
    def validate(self, attrs):
        ws=attrs.get("workspace",getattr(self.instance,"workspace",None)); src=attrs.get("source",getattr(self.instance,"source",None)); ops=attrs.get("allowed_operations",getattr(self.instance,"allowed_operations",[]))
        if ws: assert_workspace_write_access(self.context["request"],ws)
        if src and not src.can_write and ops: raise serializers.ValidationError({"allowed_operations":"WRITE debe estar habilitado en la fuente."})
        invalid=set(ops)-{"INSERT","UPDATE","DELETE"}
        if invalid: raise serializers.ValidationError({"allowed_operations":f"Operaciones no permitidas: {', '.join(sorted(invalid))}"})
        return attrs
    def create(self, validated_data): validated_data["created_by"]=self.context["request"].user; return super().create(validated_data)
