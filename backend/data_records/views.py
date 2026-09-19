from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from data_model.models import TableAsset

from .exceptions import (
    RecordConflictError,
    RecordError,
    RecordNotFoundError,
    RecordValidationError,
    UnsupportedRecordOperation,
)
from .permissions import can_read_table, can_write_table
from .services import (
    create_record,
    delete_record,
    get_record,
    list_records,
    update_record,
)


def get_accessible_table(user, pk):
    return (
        TableAsset.objects.filter(
            pk=pk,
            data_source__workspace__organization__memberships__user=user,
            data_source__workspace__organization__memberships__is_active=True,
        )
        .select_related(
            "data_source",
            "data_source__workspace",
            "data_source__workspace__organization",
        )
        .prefetch_related("fields")
        .distinct()
        .first()
    )


def error_response(exc):
    if isinstance(exc, RecordNotFoundError):
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    if isinstance(exc, RecordConflictError):
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
    if isinstance(exc, (RecordValidationError, UnsupportedRecordOperation)):
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class RecordCollectionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, table_pk):
        table = get_accessible_table(request.user, table_pk)
        if not table:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not can_read_table(request.user, table):
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            return Response(list_records(table, request.query_params))
        except RecordError as exc:
            return error_response(exc)

    def post(self, request, table_pk):
        table = get_accessible_table(request.user, table_pk)
        if not table:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not can_write_table(request.user, table):
            return Response(
                {"detail": "No tiene permisos de escritura."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            row = create_record(table, request.data)
            return Response(row, status=status.HTTP_201_CREATED)
        except RecordError as exc:
            return error_response(exc)


class RecordDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, table_pk, record_key):
        table = get_accessible_table(request.user, table_pk)
        if not table:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not can_read_table(request.user, table):
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            return Response(get_record(table, record_key))
        except RecordError as exc:
            return error_response(exc)

    def patch(self, request, table_pk, record_key):
        table = get_accessible_table(request.user, table_pk)
        if not table:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not can_write_table(request.user, table):
            return Response(
                {"detail": "No tiene permisos de escritura."},
                status=status.HTTP_403_FORBIDDEN,
            )

        expected_version = request.headers.get("If-Match-Version")
        if expected_version is None:
            return Response(
                {"detail": "Debe enviar el header If-Match-Version."},
                status=status.HTTP_428_PRECONDITION_REQUIRED,
            )

        try:
            row = update_record(
                table,
                record_key,
                request.data,
                expected_version=expected_version,
            )
            return Response(row)
        except RecordError as exc:
            return error_response(exc)

    def delete(self, request, table_pk, record_key):
        table = get_accessible_table(request.user, table_pk)
        if not table:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not can_write_table(request.user, table):
            return Response(
                {"detail": "No tiene permisos de escritura."},
                status=status.HTTP_403_FORBIDDEN,
            )

        expected_version = request.headers.get("If-Match-Version")
        if expected_version is None:
            return Response(
                {"detail": "Debe enviar el header If-Match-Version."},
                status=status.HTTP_428_PRECONDITION_REQUIRED,
            )

        try:
            result = delete_record(
                table,
                record_key,
                expected_version=expected_version,
            )
            return Response(result)
        except RecordError as exc:
            return error_response(exc)
