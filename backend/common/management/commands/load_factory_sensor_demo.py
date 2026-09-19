from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Iterable

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from data_model.managed_services import (
    create_managed_table,
    delete_managed_table,
    quote,
)
from data_model.models import TableAsset
from governance.services import add_usage, audit
from workspaces.models import Workspace


TABLE_NAME_DEFAULT = "factory_sensor_readings_2040"
DISPLAY_NAME_DEFAULT = "Factory Sensor Simulator 2040"

CSV_COLUMNS = [
    "Machine_ID",
    "Machine_Type",
    "Installation_Year",
    "Operational_Hours",
    "Temperature_C",
    "Vibration_mms",
    "Sound_dB",
    "Oil_Level_pct",
    "Coolant_Level_pct",
    "Power_Consumption_kW",
    "Last_Maintenance_Days_Ago",
    "Maintenance_History_Count",
    "Failure_History_Count",
    "AI_Supervision",
    "Error_Codes_Last_30_Days",
    "Remaining_Useful_Life_days",
    "Failure_Within_7_Days",
    "Laser_Intensity",
    "Hydraulic_Pressure_bar",
    "Coolant_Flow_L_min",
    "Heat_Index",
    "AI_Override_Events",
]

DB_COLUMNS = [
    "machine_id",
    "machine_type",
    "installation_year",
    "operational_hours",
    "temperature_c",
    "vibration_mms",
    "sound_db",
    "oil_level_pct",
    "coolant_level_pct",
    "power_consumption_kw",
    "last_maintenance_days_ago",
    "maintenance_history_count",
    "failure_history_count",
    "ai_supervision",
    "error_codes_last_30_days",
    "remaining_useful_life_days",
    "failure_within_7_days",
    "laser_intensity",
    "hydraulic_pressure_bar",
    "coolant_flow_l_min",
    "heat_index",
    "ai_override_events",
]

FIELD_SPECS = [
    {"name": "machine_id", "logical_type": "STRING", "max_length": 32, "nullable": False},
    {"name": "machine_type", "logical_type": "STRING", "max_length": 80, "nullable": False},
    {"name": "installation_year", "logical_type": "INTEGER", "nullable": False},
    {"name": "operational_hours", "logical_type": "INTEGER", "nullable": False},
    {"name": "temperature_c", "logical_type": "FLOAT", "nullable": False},
    {"name": "vibration_mms", "logical_type": "FLOAT", "nullable": False},
    {"name": "sound_db", "logical_type": "FLOAT", "nullable": False},
    {"name": "oil_level_pct", "logical_type": "FLOAT", "nullable": False},
    {"name": "coolant_level_pct", "logical_type": "FLOAT", "nullable": False},
    {"name": "power_consumption_kw", "logical_type": "FLOAT", "nullable": False},
    {"name": "last_maintenance_days_ago", "logical_type": "INTEGER", "nullable": False},
    {"name": "maintenance_history_count", "logical_type": "INTEGER", "nullable": False},
    {"name": "failure_history_count", "logical_type": "INTEGER", "nullable": False},
    {"name": "ai_supervision", "logical_type": "BOOLEAN", "nullable": False},
    {"name": "error_codes_last_30_days", "logical_type": "INTEGER", "nullable": False},
    {"name": "remaining_useful_life_days", "logical_type": "FLOAT", "nullable": False},
    {"name": "failure_within_7_days", "logical_type": "BOOLEAN", "nullable": False},
    # These fields only apply to some machine types in the source dataset.
    {"name": "laser_intensity", "logical_type": "FLOAT", "nullable": True},
    {"name": "hydraulic_pressure_bar", "logical_type": "FLOAT", "nullable": True},
    {"name": "coolant_flow_l_min", "logical_type": "FLOAT", "nullable": True},
    {"name": "heat_index", "logical_type": "FLOAT", "nullable": True},
    {"name": "ai_override_events", "logical_type": "INTEGER", "nullable": False},
]

FIELD_METADATA = {
    "machine_id": ("Machine ID", "Unique machine identifier. Primary key of the demo table."),
    "machine_type": ("Machine Type", "Industrial equipment category."),
    "installation_year": ("Installation Year", "Year in which the machine was installed."),
    "operational_hours": ("Operational Hours", "Accumulated operating hours."),
    "temperature_c": ("Temperature (°C)", "Observed operating temperature in Celsius."),
    "vibration_mms": ("Vibration (mm/s)", "Observed vibration velocity."),
    "sound_db": ("Sound (dB)", "Observed operating sound pressure level."),
    "oil_level_pct": ("Oil Level (%)", "Current oil level percentage."),
    "coolant_level_pct": ("Coolant Level (%)", "Current coolant level percentage."),
    "power_consumption_kw": ("Power Consumption (kW)", "Observed electrical power consumption."),
    "last_maintenance_days_ago": ("Days Since Maintenance", "Days elapsed since the latest maintenance event."),
    "maintenance_history_count": ("Maintenance Count", "Number of recorded historical maintenance events."),
    "failure_history_count": ("Failure Count", "Number of historical failures."),
    "ai_supervision": ("AI Supervision", "Whether AI-based supervision is active for the machine."),
    "error_codes_last_30_days": ("Errors in Last 30 Days", "Number of error codes recorded during the last 30 days."),
    "remaining_useful_life_days": ("Remaining Useful Life (Days)", "Estimated remaining useful life in days."),
    "failure_within_7_days": ("Failure Within 7 Days", "Binary predictive target indicating whether failure is expected within seven days."),
    "laser_intensity": ("Laser Intensity", "Machine-specific laser intensity; NULL when not applicable."),
    "hydraulic_pressure_bar": ("Hydraulic Pressure (bar)", "Machine-specific hydraulic pressure; NULL when not applicable."),
    "coolant_flow_l_min": ("Coolant Flow (L/min)", "Machine-specific coolant flow; NULL when not applicable."),
    "heat_index": ("Heat Index", "Machine-specific heat index; NULL when not applicable."),
    "ai_override_events": ("AI Override Events", "Number of recorded AI override events."),
}


def resolve_workspace(value: str) -> Workspace:
    try:
        return Workspace.objects.get(id=value)
    except (Workspace.DoesNotExist, ValueError):
        matches = Workspace.objects.filter(slug=value)
        count = matches.count()
        if count == 1:
            return matches.first()
        if count > 1:
            raise CommandError(
                f'El slug de workspace "{value}" existe en más de una organización. '
                "Usa el UUID del workspace."
            )
        raise CommandError(f'No se encontró el workspace "{value}".')


def resolve_user(workspace: Workspace, email: str | None):
    User = get_user_model()

    if email:
        try:
            return User.objects.get(email__iexact=email)
        except User.DoesNotExist as exc:
            raise CommandError(f'No existe un usuario con email "{email}".') from exc

    # Prefer the workspace creator because create_managed_table requires created_by.
    if workspace.created_by_id:
        return workspace.created_by

    membership = (
        workspace.organization.memberships
        .filter(is_active=True, role__in=["OWNER", "ADMIN", "BUILDER"])
        .select_related("user")
        .first()
    )
    if membership:
        return membership.user

    raise CommandError(
        "No se pudo determinar el usuario creador. Usa --user-email."
    )


def validate_csv_header(csv_path: Path) -> None:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise CommandError("El CSV está vacío.") from exc

    if header != CSV_COLUMNS:
        missing = [name for name in CSV_COLUMNS if name not in header]
        extra = [name for name in header if name not in CSV_COLUMNS]
        raise CommandError(
            "El CSV no coincide con factory_sensor_simulator_2040.csv.\n"
            f"Columnas faltantes: {missing or 'ninguna'}\n"
            f"Columnas adicionales: {extra or 'ninguna'}\n"
            f"Orden esperado: {CSV_COLUMNS}"
        )


def copy_all_rows(csv_path: Path, copy_obj, *, chunk_bytes: int = 1024 * 1024) -> None:
    # COPY ... CSV HEADER lets PostgreSQL ignore the original CSV header while the
    # target column list below defines the actual snake_case managed-table columns.
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        while True:
            data = handle.read(chunk_bytes)
            if not data:
                break
            copy_obj.write(data)


def copy_limited_rows(csv_path: Path, copy_obj, rows: int, *, flush_rows: int = 5000) -> int:
    copied = 0
    with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source)
        header = next(reader)

        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(header)

        for row in reader:
            if copied >= rows:
                break
            writer.writerow(row)
            copied += 1

            if copied % flush_rows == 0:
                copy_obj.write(buffer.getvalue())
                buffer.seek(0)
                buffer.truncate(0)

        if buffer.tell():
            copy_obj.write(buffer.getvalue())

    return copied


def relation_size_bytes(schema: str, table: str) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_total_relation_size(%s::regclass)",
            [f'{schema}.{table}'],
        )
        return int(cursor.fetchone()[0] or 0)


class Command(BaseCommand):
    help = (
        "Carga factory_sensor_simulator_2040.csv como una tabla MANAGED de demo "
        "para probar Catalog, Prepare, Explore, Dashboards y Machine Learning."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            required=True,
            help="Ruta a factory_sensor_simulator_2040.csv.",
        )
        parser.add_argument(
            "--workspace",
            required=True,
            help="UUID del workspace o slug si es único.",
        )
        parser.add_argument(
            "--user-email",
            default="",
            help="Usuario que figurará como creador. Por defecto usa workspace.created_by.",
        )
        parser.add_argument(
            "--table-name",
            default=TABLE_NAME_DEFAULT,
            help=f"Nombre físico de tabla. Default: {TABLE_NAME_DEFAULT}",
        )
        parser.add_argument(
            "--display-name",
            default=DISPLAY_NAME_DEFAULT,
            help=f"Nombre visible en Catalog. Default: {DISPLAY_NAME_DEFAULT}",
        )
        parser.add_argument(
            "--rows",
            type=int,
            default=0,
            help="Número máximo de filas a cargar. 0 = todo el CSV.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Elimina y recrea la tabla demo si ya existe.",
        )
        parser.add_argument(
            "--no-indexes",
            action="store_true",
            help="No crea índices auxiliares para filtros/ML.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv"]).expanduser().resolve()
        if not csv_path.exists():
            raise CommandError(f"No existe el archivo: {csv_path}")
        if not csv_path.is_file():
            raise CommandError(f"La ruta no es un archivo: {csv_path}")
        if options["rows"] < 0:
            raise CommandError("--rows no puede ser negativo.")

        validate_csv_header(csv_path)

        workspace = resolve_workspace(options["workspace"])
        user = resolve_user(workspace, options["user_email"] or None)
        table_name = options["table_name"].strip().lower()
        display_name = options["display_name"].strip()

        if not table_name:
            raise CommandError("--table-name no puede estar vacío.")

        existing = (
            TableAsset.objects
            .filter(
                data_source__workspace=workspace,
                data_source__mode="MANAGED",
                table_name=table_name,
            )
            .select_related("data_asset", "data_source")
            .first()
        )

        if existing:
            if not options["reset"]:
                raise CommandError(
                    f"La tabla MANAGED {existing.schema_name}.{existing.table_name} "
                    "ya existe. Usa --reset para recrearla."
                )
            self.stdout.write(
                self.style.WARNING(
                    f"Eliminando demo existente: {existing.schema_name}.{existing.table_name}"
                )
            )
            delete_managed_table(existing)

        self.stdout.write(
            f"Creando tabla MANAGED '{table_name}' en workspace '{workspace.name}'..."
        )

        result = create_managed_table(
            workspace=workspace,
            name=table_name,
            display_name=display_name,
            fields=FIELD_SPECS,
            primary_key=["machine_id"],
            foreign_keys=[],
            user=user,
        )
        table_asset = result.table_asset

        # Add business-friendly catalog metadata after the managed builder creates
        # the physical schema and FieldAsset records.
        for field in table_asset.fields.all():
            business_name, description = FIELD_METADATA[field.name]
            field.business_name = business_name
            field.description = description
            field.save(update_fields=["business_name", "description"])

        asset = table_asset.data_asset
        asset.metadata = {
            **(asset.metadata or {}),
            "demo_dataset": "factory_sensor_simulator_2040",
            "source_filename": csv_path.name,
            "domain": "predictive_maintenance",
            "grain": "one simulated machine snapshot per row",
            "primary_key": "machine_id",
            "ml_target": "failure_within_7_days",
            "recommended_dimensions": [
                "machine_type",
                "installation_year",
                "ai_supervision",
                "failure_within_7_days",
            ],
            "recommended_measures": [
                "temperature_c",
                "vibration_mms",
                "sound_db",
                "power_consumption_kw",
                "remaining_useful_life_days",
                "failure_history_count",
                "error_codes_last_30_days",
            ],
        }
        asset.save(update_fields=["metadata", "updated_at"])

        columns_sql = ", ".join(quote(name) for name in DB_COLUMNS)
        copy_sql = (
            f"COPY {quote(table_asset.schema_name)}.{quote(table_asset.table_name)} "
            f"({columns_sql}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE, NULL '')"
        )

        load_label = (
            "todo el CSV"
            if options["rows"] == 0
            else f"máximo {options['rows']:,} filas"
        )
        self.stdout.write(
            f"Cargando registros con PostgreSQL COPY ({load_label})..."
        )

        try:
            with connection.cursor() as django_cursor:
                raw_cursor = getattr(django_cursor, "cursor", django_cursor)
                with raw_cursor.copy(copy_sql) as copy_obj:
                    if options["rows"] == 0:
                        copy_all_rows(csv_path, copy_obj)
                    else:
                        copy_limited_rows(csv_path, copy_obj, options["rows"])
        except Exception:
            # Avoid leaving an empty/partially loaded demo table when COPY fails.
            try:
                delete_managed_table(table_asset)
            except Exception:
                pass
            raise

        with connection.cursor() as cursor:
            cursor.execute(
                f"ANALYZE {quote(table_asset.schema_name)}.{quote(table_asset.table_name)}"
            )

            if not options["no_indexes"]:
                indexes = [
                    ("machine_type", "machine_type"),
                    ("failure_7d", "failure_within_7_days"),
                    ("ai_supervision", "ai_supervision"),
                    ("remaining_life", "remaining_useful_life_days"),
                    ("maintenance_age", "last_maintenance_days_ago"),
                ]
                for suffix, column in indexes:
                    index_name = f"idx_{table_name}_{suffix}"[:63]
                    cursor.execute(
                        f"CREATE INDEX IF NOT EXISTS {quote(index_name)} "
                        f"ON {quote(table_asset.schema_name)}.{quote(table_asset.table_name)} "
                        f"({quote(column)})"
                    )

            cursor.execute(
                f"SELECT COUNT(*) FROM {quote(table_asset.schema_name)}."
                f"{quote(table_asset.table_name)}"
            )
            row_count = int(cursor.fetchone()[0])

            cursor.execute(
                f"SELECT COUNT(DISTINCT {quote('machine_type')}), "
                f"SUM(CASE WHEN {quote('failure_within_7_days')} THEN 1 ELSE 0 END) "
                f"FROM {quote(table_asset.schema_name)}.{quote(table_asset.table_name)}"
            )
            machine_types, failures = cursor.fetchone()

        size_bytes = relation_size_bytes(table_asset.schema_name, table_asset.table_name)

        # Keep governance usage/audit useful for a demo loaded outside ImportJob.
        add_usage(workspace, storage_bytes=size_bytes, import_rows=row_count)
        audit(
            workspace,
            action="DEMO_DATA_LOADED",
            resource_type="TABLE",
            resource_id=table_asset.id,
            actor=user,
            detail={
                "dataset": "factory_sensor_simulator_2040",
                "rows": row_count,
                "machine_types": int(machine_types or 0),
                "failure_within_7_days_positive": int(failures or 0),
                "storage_bytes": size_bytes,
                "table": f"{table_asset.schema_name}.{table_asset.table_name}",
            },
        )

        positive_rate = (float(failures or 0) / row_count * 100.0) if row_count else 0.0

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Demo cargada correctamente."))
        self.stdout.write(f"Workspace:       {workspace.name} ({workspace.id})")
        self.stdout.write(f"DataAsset:       {asset.name} ({asset.id})")
        self.stdout.write(
            f"Tabla:           {table_asset.schema_name}.{table_asset.table_name}"
        )
        self.stdout.write(f"Filas:           {row_count:,}")
        self.stdout.write(f"Tipos máquina:   {int(machine_types or 0):,}")
        self.stdout.write(
            f"Failure 7d:      {int(failures or 0):,} ({positive_rate:.2f}%)"
        )
        self.stdout.write(f"Tamaño DB aprox: {size_bytes / 1024 / 1024:.1f} MB")
        self.stdout.write("")
        self.stdout.write("Pruebas recomendadas en la plataforma:")
        self.stdout.write("  1. Data → Catalog: inspecciona schema, NULLs y metadata.")
        self.stdout.write("  2. Analyze → crea KPIs por machine_type / ai_supervision.")
        self.stdout.write("  3. Dashboard → compara temperatura, vibración y fallas.")
        self.stdout.write(
            "  4. ML → Classification; target = failure_within_7_days."
        )
        self.stdout.write(
            "  5. ML → Regression; target = remaining_useful_life_days."
        )
