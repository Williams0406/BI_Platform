import re
from rest_framework import serializers
from .managed_types import supported_logical_types
from .models import FieldAsset, TableAsset

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

class PlatformFieldCreateSerializer(serializers.Serializer):
    table = serializers.PrimaryKeyRelatedField(queryset=TableAsset.objects.all())
    name = serializers.CharField(max_length=63)
    logical_type = serializers.ChoiceField(choices=supported_logical_types())
    nullable = serializers.BooleanField(default=True)
    business_name = serializers.CharField(max_length=180, required=False, allow_blank=True)
    max_length = serializers.IntegerField(required=False, min_value=1)
    numeric_precision = serializers.IntegerField(required=False, min_value=1)
    numeric_scale = serializers.IntegerField(required=False, min_value=0)

    def validate_name(self, value):
        if not IDENTIFIER_RE.fullmatch(value):
            raise serializers.ValidationError("Use letras, números y guion bajo; no puede comenzar con número.")
        return value

    def validate(self, attrs):
        table = attrs["table"]
        if table.fields.filter(name=attrs["name"]).exists():
            raise serializers.ValidationError({"name": "Ya existe un campo con ese nombre."})
        if attrs["logical_type"] == "STRING" and not attrs.get("max_length"):
            attrs["max_length"] = 255
        if attrs["logical_type"] == "DECIMAL":
            attrs.setdefault("numeric_precision", 18)
            attrs.setdefault("numeric_scale", 2)
            if attrs["numeric_scale"] > attrs["numeric_precision"]:
                raise serializers.ValidationError("numeric_scale no puede superar numeric_precision.")
        return attrs
