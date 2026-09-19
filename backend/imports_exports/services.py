import csv
import datetime
import json
import re
import time
from pathlib import Path
from decimal import Decimal

from django.conf import settings
from django.core.files import File
from django.db import connection, transaction
from django.utils import timezone
from openpyxl import Workbook, load_workbook

from connectors.registry import build_connector
from customer_gateway.models import GatewayJob
from customer_gateway.services import queue_job
from data_model.managed_services import create_managed_table
from data_records.validators import validate_record_payload
from dependencies.services import record_change
from dependencies.tasks import propagate_asset_change_task
from governance.services import add_usage, assert_export_rows, assert_import_rows, audit

from .models import ExportJob, ImportJob, SourceSyncPolicy


def quote(name):
    return connection.ops.quote_name(name)


def clean_identifier(value, fallback="column"):
    value = re.sub(r"[^A-Za-z0-9_]+", "_", str(value or "").strip()).strip("_").lower()
    if not value:
        value = fallback
    if value[0].isdigit():
        value = f"c_{value}"
    return value[:63]


def _json_safe(value):
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _read_rows(job):
    path = Path(job.file.path)
    if job.file_type == ImportJob.FileType.CSV:
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                yield row
    else:
        wb = load_workbook(path, read_only=True, data_only=True)
        ws = wb[job.sheet_name] if job.sheet_name else wb.active
        rows = ws.iter_rows(values_only=True)
        try:
            raw_headers = next(rows)
        except StopIteration:
            return
        headers = [str(v) if v is not None else f"column_{i+1}" for i, v in enumerate(raw_headers)]
        for values in rows:
            yield {headers[i]: values[i] for i in range(len(headers))}


def inspect_uploaded_file(upload, sheet_name="", sample_limit=12):
    """Inspect CSV/XLSX before creating an ImportJob. No data is persisted."""
    name = str(getattr(upload, "name", "")).lower()
    rows = []
    sheets = []
    selected_sheet = ""
    if name.endswith(".xlsx"):
        wb = load_workbook(upload, read_only=True, data_only=True)
        sheets = list(wb.sheetnames)
        selected_sheet = sheet_name if sheet_name in sheets else (sheets[0] if sheets else "")
        if not selected_sheet:
            return {"sheets": [], "selected_sheet": "", "columns": [], "rows": []}
        ws = wb[selected_sheet]
        iterator = ws.iter_rows(values_only=True)
        headers_raw = next(iterator, [])
        columns = [str(v) if v is not None else f"column_{i+1}" for i, v in enumerate(headers_raw)]
        for values in iterator:
            rows.append({columns[i]: _json_safe(values[i] if i < len(values) else None) for i in range(len(columns))})
            if len(rows) >= sample_limit: break
    else:
        upload.seek(0)
        text = upload.read().decode("utf-8-sig")
        reader = csv.DictReader(text.splitlines())
        columns = list(reader.fieldnames or [])
        for row in reader:
            rows.append({k: _json_safe(v) for k, v in row.items()})
            if len(rows) >= sample_limit: break
    try: upload.seek(0)
    except Exception: pass
    return {"sheets": sheets, "selected_sheet": selected_sheet, "columns": columns, "rows": rows}


def workbook_sheets(job):
    if job.file_type != ImportJob.FileType.XLSX:
        return []
    wb = load_workbook(Path(job.file.path), read_only=True, data_only=True)
    return list(wb.sheetnames)


def _infer_value_type(values):
    present = [v for v in values if v not in (None, "")]
    if not present:
        return "STRING"
    if all(isinstance(v, bool) or str(v).strip().lower() in {"true", "false", "yes", "no", "si", "sí", "0", "1"} for v in present):
        return "BOOLEAN"
    try:
        for v in present:
            if isinstance(v, bool):
                raise ValueError
            int(str(v))
        return "BIGINT"
    except Exception:
        pass
    try:
        for v in present:
            float(str(v).replace(",", "."))
        return "DECIMAL"
    except Exception:
        pass
    if all(isinstance(v, datetime.datetime) for v in present):
        return "DATETIME"
    if all(isinstance(v, datetime.date) for v in present):
        return "DATE"
    # ISO dates coming from CSV.
    try:
        for v in present:
            datetime.date.fromisoformat(str(v)[:10])
        return "DATE"
    except Exception:
        pass
    max_len = max(len(str(v)) for v in present)
    return "TEXT" if max_len > 255 else "STRING"


def infer_import_schema(job, sample_limit=250):
    sample = []
    for i, row in enumerate(_read_rows(job)):
        if i >= sample_limit:
            break
        sample.append(row)
    if not sample:
        return []
    original_headers = list(sample[0].keys())
    used = set()
    schema = []
    for idx, source_name in enumerate(original_headers, start=1):
        base = clean_identifier(source_name, f"column_{idx}")
        target = base
        suffix = 2
        while target in used:
            target = f"{base[:58]}_{suffix}"
            suffix += 1
        used.add(target)
        values = [row.get(source_name) for row in sample]
        logical = _infer_value_type(values)
        item = {
            "source_name": source_name,
            "name": target,
            "logical_type": logical,
            "nullable": any(v in (None, "") for v in values),
        }
        if logical == "STRING":
            item["max_length"] = min(max(32, max((len(str(v)) for v in values if v not in (None, "")), default=32)), 4096)
        if logical == "DECIMAL":
            item["numeric_precision"] = 24
            item["numeric_scale"] = 6
        schema.append(item)
    return schema


def preview_import(job, limit=50):
    rows = []
    for i, row in enumerate(_read_rows(job)):
        if i >= limit:
            break
        rows.append({key: _json_safe(value) for key, value in row.items()})
    inferred = infer_import_schema(job)
    if inferred != (job.inferred_schema or []):
        job.inferred_schema = inferred
        job.save(update_fields=["inferred_schema"])
    return {
        "rows": rows,
        "mapping": job.column_mapping,
        "inferred_schema": inferred,
        "sheets": workbook_sheets(job),
        "selected_sheet": job.sheet_name,
    }


def _mapped(row, mapping, inferred_schema=None):
    if mapping:
        return {target: row.get(source) for source, target in mapping.items() if target}
    if inferred_schema:
        return {item["name"]: row.get(item["source_name"]) for item in inferred_schema}
    return dict(row)


def _insert_validated_rows(table, rows, mode="APPEND", execution=None):
    if not rows:
        return 0
    fields = list(rows[0])
    cols = ", ".join(quote(f) for f in fields)
    placeholders = ", ".join(["%s"] * len(fields))
    pk = list(table.primary_key_columns or [])
    conflict = ""
    if mode == ImportJob.Mode.UPSERT:
        if len(pk) != 1:
            raise ValueError("UPSERT requiere PK simple.")
        update_fields = [f for f in fields if f != pk[0]]
        if update_fields:
            conflict = f" ON CONFLICT ({quote(pk[0])}) DO UPDATE SET " + ", ".join(
                f"{quote(f)}=EXCLUDED.{quote(f)}" for f in update_fields
            )
        else:
            conflict = f" ON CONFLICT ({quote(pk[0])}) DO NOTHING"
    sql = f"INSERT INTO {quote(table.schema_name)}.{quote(table.table_name)} ({cols}) VALUES ({placeholders}){conflict}"
    chunk = settings.IMPORT_EXPORT_CHUNK_SIZE
    with connection.cursor() as cursor:
        for start in range(0, len(rows), chunk):
            batch = rows[start:start + chunk]
            cursor.executemany(sql, [[row.get(f) for f in fields] for row in batch])
            if execution:
                from execution.services import update_progress
                update_progress(execution, 35 + int(55 * (start + len(batch)) / len(rows)))
    return len(rows)


@transaction.atomic
def execute_import(job, execution):
    from execution.services import mark_running, mark_success, update_progress
    mark_running(execution)
    job.status = ImportJob.Status.RUNNING
    job.save(update_fields=["status"])

    inferred = job.inferred_schema or infer_import_schema(job)
    if not inferred:
        raise ValueError("El archivo no contiene filas importables.")
    job.inferred_schema = inferred
    job.save(update_fields=["inferred_schema"])

    table = job.target_table
    if job.mode == ImportJob.Mode.CREATE:
        result = create_managed_table(
            workspace=job.workspace,
            name=clean_identifier(job.target_table_name, "imported_data"),
            display_name=job.target_display_name or job.target_table_name,
            fields=[{k: v for k, v in item.items() if k != "source_name"} for item in inferred],
            primary_key=[],
            foreign_keys=[],
            user=job.created_by,
        )
        table = result.table_asset
        job.target_table = table
        job.save(update_fields=["target_table"])
    if not table or table.data_source.mode != "MANAGED":
        raise ValueError("La importación solo puede escribir en una tabla MANAGED.")

    rows = list(_read_rows(job))
    job.rows_total = len(rows)
    assert_import_rows(job.workspace, len(rows))
    valid, errors = [], []
    for idx, row in enumerate(rows, start=2):
        try:
            valid.append(validate_record_payload(table, _mapped(row, job.column_mapping, inferred if job.mode == ImportJob.Mode.CREATE else None), partial=False))
        except Exception as exc:
            errors.append({"row": idx, "error": str(exc)})
    job.rows_valid = len(valid)
    job.rows_failed = len(errors)
    job.error_report = errors[:1000]
    job.save(update_fields=["rows_total", "rows_valid", "rows_failed", "error_report"])
    update_progress(execution, 30, "Validación de archivo completada.")
    if errors:
        raise ValueError(f"Importación detenida: {len(errors)} filas inválidas.")
    if not valid:
        raise ValueError("El archivo no contiene filas válidas.")

    if job.mode == ImportJob.Mode.REPLACE:
        with connection.cursor() as cursor:
            cursor.execute(f"TRUNCATE TABLE {quote(table.schema_name)}.{quote(table.table_name)} RESTART IDENTITY")

    imported = _insert_validated_rows(table, valid, mode=job.mode, execution=execution)
    job.rows_imported = imported
    job.status = ImportJob.Status.SUCCESS
    job.finished_at = timezone.now()
    job.save(update_fields=["rows_imported", "status", "finished_at"])
    event = record_change(table.data_asset, "REFRESH", user=job.created_by, metadata={"import_job_id": str(job.id), "rows": imported})
    transaction.on_commit(lambda: propagate_asset_change_task.apply_async(args=[str(event.id)], queue="fast"))
    size = Path(job.file.path).stat().st_size if Path(job.file.path).exists() else 0
    add_usage(job.workspace, storage_bytes=size, import_rows=imported, executions=1)
    audit(job.workspace, "IMPORT_SUCCESS", "ImportJob", job.id, job.created_by, {"rows": imported, "table": str(table.id), "mode": job.mode})
    result = {"import_job_id": str(job.id), "rows_imported": imported, "table_id": str(table.id), "change_event_id": str(event.id)}
    mark_success(execution, result)
    return result


def _source_fields_for_managed(source_table):
    fields = []
    for field in source_table.fields.order_by("ordinal_position"):
        logical = field.logical_type if field.logical_type in {
            "INTEGER", "BIGINT", "DECIMAL", "FLOAT", "BOOLEAN", "STRING", "TEXT", "DATE",
            "DATETIME", "DATETIME_TZ", "TIME", "UUID", "JSON", "BINARY"
        } else "TEXT"
        item = {"name": clean_identifier(field.name), "logical_type": logical, "nullable": True}
        if logical == "STRING":
            item["max_length"] = min(field.max_length or 1024, 10485760)
        if logical == "DECIMAL":
            item["numeric_precision"] = min(field.numeric_precision or 24, 1000)
            item["numeric_scale"] = min(field.numeric_scale or 6, item["numeric_precision"])
        fields.append(item)
    return fields


def _wait_gateway_job(job, timeout_seconds=90):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        job.refresh_from_db()
        if job.status == GatewayJob.Status.SUCCESS:
            return job.result or {}
        if job.status in {GatewayJob.Status.FAILED, GatewayJob.Status.CANCELLED, GatewayJob.Status.EXPIRED}:
            raise ValueError(job.error_message or f"Gateway job {job.status}.")
        time.sleep(1.0)
    raise TimeoutError("El Gateway no completó la lectura dentro del tiempo permitido.")


def _read_sync_page(policy, offset, limit, cursor_value=None):
    source = policy.source_data_source
    payload = {
        "schema": policy.source_table.schema_name,
        "table": policy.source_table.table_name,
        "limit": limit,
        "offset": offset,
    }
    if policy.strategy == SourceSyncPolicy.Strategy.INCREMENTAL and cursor_value is not None:
        payload["cursor_field"] = policy.incremental_field
        payload["cursor_gt"] = cursor_value
    if source.mode == "PRIVATE_GATEWAY":
        job = queue_job(source, "READ_PAGE", payload, user=policy.created_by)
        return _wait_gateway_job(job)
    connector = build_connector(source)
    return connector.read_page(**payload)


def _calculate_next_run(policy, base=None):
    base = base or timezone.now()
    if policy.schedule == SourceSyncPolicy.Schedule.MANUAL or not policy.enabled:
        return None
    if policy.schedule == SourceSyncPolicy.Schedule.HOURLY:
        return base + datetime.timedelta(hours=1)
    if policy.schedule == SourceSyncPolicy.Schedule.DAILY:
        return base + datetime.timedelta(days=1)
    if policy.schedule == SourceSyncPolicy.Schedule.WEEKLY:
        return base + datetime.timedelta(days=7)
    return base + datetime.timedelta(minutes=max(5, int(policy.custom_interval_minutes or 60)))


def initialize_policy_schedule(policy):
    policy.next_run_at = _calculate_next_run(policy)
    policy.save(update_fields=["next_run_at", "updated_at"])
    return policy


@transaction.atomic
def _ensure_sync_target(policy):
    if policy.target_table_id:
        return policy.target_table
    result = create_managed_table(
        workspace=policy.workspace,
        name=clean_identifier(policy.target_table_name, "synced_data"),
        display_name=policy.target_display_name or policy.target_table_name,
        fields=_source_fields_for_managed(policy.source_table),
        primary_key=[],
        foreign_keys=[],
        user=policy.created_by,
    )
    policy.target_table = result.table_asset
    policy.save(update_fields=["target_table", "updated_at"])
    return result.table_asset


def execute_source_sync(policy, execution):
    from execution.services import mark_running, mark_success, update_progress
    mark_running(execution)
    policy.status = SourceSyncPolicy.Status.RUNNING
    policy.last_error = ""
    policy.save(update_fields=["status", "last_error", "updated_at"])
    target = _ensure_sync_target(policy)
    cursor_value = policy.last_cursor_value if policy.strategy == SourceSyncPolicy.Strategy.INCREMENTAL else None

    if policy.strategy == SourceSyncPolicy.Strategy.FULL:
        with connection.cursor() as cursor:
            cursor.execute(f"TRUNCATE TABLE {quote(target.schema_name)}.{quote(target.table_name)} RESTART IDENTITY")

    page_size = 1000
    offset = 0
    total = 0
    newest_cursor = cursor_value
    target_field_names = {f.name for f in target.fields.all()}
    source_name_map = {f.name: clean_identifier(f.name) for f in policy.source_table.fields.all()}
    max_rows = settings.IMPORT_EXPORT_MAX_SYNC_ROWS if hasattr(settings, "IMPORT_EXPORT_MAX_SYNC_ROWS") else 2_000_000

    while True:
        data = _read_sync_page(policy, offset, page_size, cursor_value=cursor_value)
        rows = data.get("rows") or []
        if not rows:
            break
        normalized = []
        for row in rows:
            mapped = {source_name_map.get(k, clean_identifier(k)): v for k, v in row.items()}
            mapped = {k: v for k, v in mapped.items() if k in target_field_names}
            normalized.append(validate_record_payload(target, mapped, partial=False))
            if policy.strategy == SourceSyncPolicy.Strategy.INCREMENTAL:
                raw = row.get(policy.incremental_field)
                # Incremental connector reads are ordered by cursor_field, so the
                # last non-null value processed is the high-water mark.
                if raw is not None:
                    newest_cursor = _json_safe(raw)
        _insert_validated_rows(target, normalized, mode=ImportJob.Mode.APPEND)
        total += len(normalized)
        if total > max_rows:
            raise ValueError(f"La sincronización superó el límite de {max_rows:,} filas por ejecución.")
        returned = int(data.get("returned", len(rows)))
        if returned < page_size:
            break
        offset += returned
        update_progress(execution, min(90, 10 + int(total / max_rows * 80)), f"{total:,} filas copiadas")

    now = timezone.now()
    policy.last_rows = total
    policy.last_sync_at = now
    policy.last_cursor_value = newest_cursor
    policy.status = SourceSyncPolicy.Status.SUCCESS
    policy.next_run_at = _calculate_next_run(policy, now)
    policy.save(update_fields=["last_rows", "last_sync_at", "last_cursor_value", "status", "next_run_at", "updated_at"])
    event = record_change(target.data_asset, "REFRESH", user=policy.created_by, metadata={"sync_policy_id": str(policy.id), "rows": total, "strategy": policy.strategy})
    transaction.on_commit(lambda: propagate_asset_change_task.apply_async(args=[str(event.id)], queue="fast"))
    add_usage(policy.workspace, import_rows=total, executions=1)
    audit(policy.workspace, "SOURCE_SYNC_SUCCESS", "SourceSyncPolicy", policy.id, policy.created_by, {"rows": total, "source": str(policy.source_table_id), "target": str(target.id), "strategy": policy.strategy})
    result = {"sync_policy_id": str(policy.id), "rows_imported": total, "target_table_id": str(target.id), "last_cursor_value": newest_cursor}
    mark_success(execution, result)
    return result


def _export_query(job):
    table = job.source_table
    allowed = set(table.fields.values_list("name", flat=True))
    columns = job.columns or list(allowed)
    unknown = set(columns) - allowed
    if unknown:
        raise ValueError("Columnas desconocidas: " + ", ".join(sorted(unknown)))
    clauses, params = [], []
    ops = {"eq": "=", "ne": "<>", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
    for item in job.filters or []:
        field = item.get("field")
        op = item.get("operator", "eq")
        value = item.get("value")
        if field not in allowed or op not in ops:
            raise ValueError("Filtro inválido.")
        clauses.append(f"{quote(field)} {ops[op]} %s")
        params.append(value)
    query = f"SELECT {', '.join(quote(c) for c in columns)} FROM {quote(table.schema_name)}.{quote(table.table_name)}"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " LIMIT %s"
    params.append(job.row_limit)
    return query, params, columns


def execute_export(job, execution):
    from execution.services import mark_running, mark_success, update_progress
    mark_running(execution)
    job.status = ExportJob.Status.RUNNING
    job.save(update_fields=["status"])
    if job.source_table.data_source.mode != "MANAGED":
        raise ValueError("Export directo requiere tabla MANAGED; sincronice primero una fuente externa.")
    assert_export_rows(job.workspace, job.row_limit)
    query, params, columns = _export_query(job)
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()
    assert_export_rows(job.workspace, len(rows))
    update_progress(execution, 50, "Datos consultados.")
    root = Path(settings.MEDIA_ROOT) / "exports" / str(job.workspace_id)
    root.mkdir(parents=True, exist_ok=True)
    suffix = ".csv" if job.file_type == ExportJob.FileType.CSV else ".xlsx"
    path = root / f"{job.id}{suffix}"
    if job.file_type == ExportJob.FileType.CSV:
        with path.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(columns)
            writer.writerows(rows)
    else:
        wb = Workbook(write_only=True)
        ws = wb.create_sheet("Data")
        ws.append(columns)
        for row in rows:
            ws.append(list(row))
        wb.save(path)
    with path.open("rb") as fh:
        job.output_file.save(path.name, File(fh), save=False)
    job.rows_exported = len(rows)
    job.status = ExportJob.Status.SUCCESS
    job.finished_at = timezone.now()
    job.save(update_fields=["output_file", "rows_exported", "status", "finished_at"])
    add_usage(job.workspace, storage_bytes=path.stat().st_size, export_rows=len(rows), executions=1)
    audit(job.workspace, "EXPORT_SUCCESS", "ExportJob", job.id, job.created_by, {"rows": len(rows), "table": str(job.source_table_id)})
    result = {"export_job_id": str(job.id), "rows_exported": len(rows), "file": job.output_file.name}
    mark_success(execution, result)
    return result
