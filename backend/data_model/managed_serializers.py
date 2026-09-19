import re

from rest_framework import serializers

from datasources.models import DataSource
from workspaces.models import Membership, Workspace

from .managed_types import supported_logical_types
from .models import TableAsset


IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_identifier(value):
    if not IDENTIFIER_RE.fullmatch(value):
        raise serializers.ValidationError(
            "Use solo letras, números y guion bajo; el nombre no puede comenzar con número."
        )
    return value


class ManagedFieldDefinitionSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=63, validators=[validate_identifier])
    logical_type = serializers.ChoiceField(choices=supported_logical_types())
    nullable = serializers.BooleanField(default=True)
    unique = serializers.BooleanField(default=False)
    default = serializers.JSONField(required=False)
    max_length = serializers.IntegerField(required=False, min_value=1, max_value=10485760)
    numeric_precision = serializers.IntegerField(required=False, min_value=1, max_value=1000)
    numeric_scale = serializers.IntegerField(required=False, min_value=0, max_value=1000)
    is_identity = serializers.BooleanField(default=False)

    def validate(self, attrs):
        logical_type = attrs["logical_type"]
        if logical_type == "STRING" and not attrs.get("max_length"):
            attrs["max_length"] = 255

        if logical_type == "DECIMAL":
            precision = attrs.get("numeric_precision", 18)
            scale = attrs.get("numeric_scale", 2)
            if scale > precision:
                raise serializers.ValidationError(
                    "numeric_scale no puede ser mayor que numeric_precision."
                )
            attrs["numeric_precision"] = precision
            attrs["numeric_scale"] = scale

        if attrs.get("is_identity") and logical_type not in {"INTEGER", "BIGINT"}:
            raise serializers.ValidationError(
                "is_identity solo está permitido para INTEGER o BIGINT."
            )

        return attrs


class ManagedForeignKeyDefinitionSerializer(serializers.Serializer):
    columns = serializers.ListField(
        child=serializers.CharField(max_length=63, validators=[validate_identifier]),
        min_length=1,
    )
    target_table_asset = serializers.PrimaryKeyRelatedField(
        queryset=TableAsset.objects.all()
    )
    target_columns = serializers.ListField(
        child=serializers.CharField(max_length=63, validators=[validate_identifier]),
        min_length=1,
    )
    on_delete = serializers.ChoiceField(
        choices=["NO ACTION", "RESTRICT", "CASCADE", "SET NULL"],
        default="NO ACTION",
    )

    def validate(self, attrs):
        if len(attrs["columns"]) != len(attrs["target_columns"]):
            raise serializers.ValidationError(
                "columns y target_columns deben tener la misma cantidad de elementos."
            )
        return attrs


class ManagedTableCreateSerializer(serializers.Serializer):
    workspace = serializers.PrimaryKeyRelatedField(queryset=Workspace.objects.all())
    name = serializers.CharField(max_length=63, validators=[validate_identifier])
    display_name = serializers.CharField(max_length=180, required=False, allow_blank=True)
    fields = ManagedFieldDefinitionSerializer(many=True, min_length=1)
    primary_key = serializers.ListField(
        child=serializers.CharField(max_length=63, validators=[validate_identifier]),
        required=False,
        allow_empty=True,
    )
    foreign_keys = ManagedForeignKeyDefinitionSerializer(
        many=True,
        required=False,
    )

    def validate_workspace(self, workspace):
        request = self.context["request"]
        allowed = Membership.objects.filter(
            organization=workspace.organization,
            user=request.user,
            is_active=True,
            role__in=[
                Membership.Role.OWNER,
                Membership.Role.ADMIN,
                Membership.Role.BUILDER,
            ],
        ).exists()
        if not allowed:
            raise serializers.ValidationError(
                "No tiene permisos para crear tablas en este workspace."
            )
        return workspace

    def validate(self, attrs):
        field_names = [item["name"] for item in attrs["fields"]]
        if len(field_names) != len(set(field_names)):
            raise serializers.ValidationError("Hay nombres de campos duplicados.")

        primary_key = attrs.get("primary_key", [])
        missing = [name for name in primary_key if name not in field_names]
        if missing:
            raise serializers.ValidationError(
                {"primary_key": f"Campos inexistentes: {', '.join(missing)}"}
            )

        identity_fields = [f["name"] for f in attrs["fields"] if f.get("is_identity")]
        if len(identity_fields) > 1:
            raise serializers.ValidationError(
                "Solo se permite una columna identity por tabla."
            )

        for fk in attrs.get("foreign_keys", []):
            source_missing = [name for name in fk["columns"] if name not in field_names]
            if source_missing:
                raise serializers.ValidationError(
                    {"foreign_keys": f"Campos origen inexistentes: {', '.join(source_missing)}"}
                )

            target = fk["target_table_asset"]
            target_field_names = set(target.fields.values_list("name", flat=True))
            target_missing = [
                name for name in fk["target_columns"] if name not in target_field_names
            ]
            if target_missing:
                raise serializers.ValidationError(
                    {"foreign_keys": f"Campos destino inexistentes: {', '.join(target_missing)}"}
                )

            if target.data_source.mode != DataSource.Mode.MANAGED:
                raise serializers.ValidationError(
                    "En Fase 4 las FK creadas por el builder solo pueden apuntar a tablas MANAGED."
                )

            if target.data_source.workspace_id != attrs["workspace"].id:
                raise serializers.ValidationError(
                    "La FK debe apuntar a una tabla del mismo workspace."
                )

        return attrs
