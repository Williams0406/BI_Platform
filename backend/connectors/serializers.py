from rest_framework import serializers


class RuntimeCredentialsSerializer(serializers.Serializer):
    password = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
        trim_whitespace=False,
    )

    # PostgreSQL
    host = serializers.CharField(required=False)
    port = serializers.IntegerField(required=False, min_value=1, max_value=65535)
    database = serializers.CharField(required=False)
    user = serializers.CharField(required=False)
    sslmode = serializers.CharField(required=False)

    # SQL Server
    server = serializers.CharField(required=False)
    driver = serializers.CharField(required=False)
    trusted_connection = serializers.BooleanField(required=False)
    encrypt = serializers.BooleanField(required=False)
    trust_server_certificate = serializers.BooleanField(required=False)

    connect_timeout = serializers.IntegerField(required=False, min_value=1, max_value=60)


class CatalogRequestSerializer(RuntimeCredentialsSerializer):
    schemas = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
    )
    include_views = serializers.BooleanField(required=False, default=True)


class ReadPageRequestSerializer(RuntimeCredentialsSerializer):
    schema = serializers.CharField()
    table = serializers.CharField()
    columns = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=False,
    )
    limit = serializers.IntegerField(required=False, default=100, min_value=1, max_value=1000)
    offset = serializers.IntegerField(required=False, default=0, min_value=0)
    cursor_field = serializers.CharField(required=False)
    cursor_gt = serializers.JSONField(required=False)
