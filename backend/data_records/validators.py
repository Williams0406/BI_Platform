import datetime
import decimal
import uuid

from .exceptions import RecordValidationError


def coerce_value(field, value):
    if value is None:
        if not field.nullable:
            raise RecordValidationError(f"{field.name} no permite NULL.")
        return None

    logical_type = field.logical_type

    try:
        if logical_type in {"INTEGER", "BIGINT"}:
            return int(value)

        if logical_type in {"DECIMAL", "FLOAT"}:
            return decimal.Decimal(str(value)) if logical_type == "DECIMAL" else float(value)

        if logical_type == "BOOLEAN":
            if isinstance(value, bool):
                return value
            if str(value).lower() in {"true", "1", "yes", "si", "sí"}:
                return True
            if str(value).lower() in {"false", "0", "no"}:
                return False
            raise ValueError

        if logical_type == "UUID":
            return uuid.UUID(str(value))

        if logical_type == "DATE":
            if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
                return value
            return datetime.date.fromisoformat(str(value))

        if logical_type in {"DATETIME", "DATETIME_TZ"}:
            if isinstance(value, datetime.datetime):
                return value
            return datetime.datetime.fromisoformat(str(value))

        if logical_type == "TIME":
            if isinstance(value, datetime.time):
                return value
            return datetime.time.fromisoformat(str(value))

        if logical_type in {"STRING", "TEXT"}:
            value = str(value)
            if field.max_length and len(value) > field.max_length:
                raise RecordValidationError(
                    f"{field.name} excede max_length={field.max_length}."
                )
            return value

        if logical_type in {"JSON", "BINARY"}:
            return value

        return value
    except (ValueError, TypeError, decimal.InvalidOperation):
        raise RecordValidationError(
            f"Valor inválido para {field.name} ({logical_type})."
        )


def validate_record_payload(table_asset, payload, partial=False):
    fields = {
        field.name: field
        for field in table_asset.fields.all()
    }

    unknown = sorted(set(payload) - set(fields))
    if unknown:
        raise RecordValidationError(
            "Campos desconocidos: " + ", ".join(unknown)
        )

    output = {}
    for name, value in payload.items():
        output[name] = coerce_value(fields[name], value)

    if not partial:
        for field in fields.values():
            if field.name in output:
                continue
            if field.is_identity:
                continue
            if not field.nullable and not field.default_value:
                raise RecordValidationError(
                    f"El campo obligatorio {field.name} no fue proporcionado."
                )

    return output
