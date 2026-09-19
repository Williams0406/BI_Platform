# Arquitectura — Fase 10

## Objetivo

Agregar entrada/salida empresarial y controles de Governance:

```text
CSV/XLSX
   ↓
ImportJob → validation → imports queue → MANAGED Table
                                   ↓
                              ChangeEvent / lineage

MANAGED Table
   ↓
ExportJob → imports queue → CSV/XLSX artifact

Governance
├── AuditLog
├── WorkspaceQuota
├── WorkspaceUsage
├── ResourcePermission
├── EncryptedSecret
├── DestructiveChangeRequest
└── RetentionPolicy
```

## Imports

Formatos:
- CSV UTF-8/UTF-8 BOM
- XLSX

Modos:
- APPEND
- UPSERT con PK simple

El archivo se registra antes de ejecutar.

Flujo:

```text
upload
 → preview/mapping
 → Execution QUEUED
 → validation de todas las filas
 → si existe error: no insertar
 → bulk insert/upsert por chunks
 → ChangeEvent
 → Dependency propagation
```

`column_mapping` tiene forma:

```json
{
  "Código externo": "code",
  "Descripción": "description",
  "Cantidad": "quantity"
}
```

Las filas usan los mismos validadores de `data_records`.

La importación directa de esta fase se realiza sobre tablas `MANAGED`.

## Exports

Formatos:
- CSV
- XLSX

La definición permite:
- selección de columnas
- filtros simples
- row_limit

Los archivos son jobs asíncronos y luego pueden descargarse.

## Celery

Nueva cola:

```text
imports
```

Import y export no bloquean el API web.

## Quotas

`WorkspaceQuota`:

```text
max_storage_mb
max_import_rows
max_export_rows
max_concurrent_jobs
max_python_runtime_seconds
max_optimization_seconds
```

`WorkspaceUsage` acumula:
- storage
- imported rows
- exported rows
- started executions

La Fase 12 podrá conectar estas métricas a accounting/billing y telemetría.

## Audit

`AuditLog` registra eventos de seguridad/operación, por ejemplo:
- IMPORT_QUEUE
- IMPORT_SUCCESS
- EXPORT_QUEUE
- EXPORT_SUCCESS
- SECRET_SET
- PERMISSION_CREATE
- DESTRUCTIVE_REQUEST
- DESTRUCTIVE_APPROVE
- DESTRUCTIVE_EXECUTED

No se guardan passwords en AuditLog.

## Fine-grained permissions

`ResourcePermission` admite:

```text
workspace
user
resource_type
resource_id
field_name
action
effect = ALLOW / DENY
```

Esto complementa los roles OWNER/ADMIN/BUILDER/ANALYST/VIEWER.

La regla DENY tiene prioridad en el helper de evaluación.

## Secret Store

Las credenciales de DataSource dejan de necesitar ser enviadas en cada request.

Se almacenan mediante `EncryptedSecret`.

Cifrado:
- Fernet authenticated encryption
- master key externa: `GOVERNANCE_FERNET_KEY`
- ciphertext en PostgreSQL
- plaintext nunca se devuelve por API

El Connector Registry de Fase 3 ahora:
1. toma metadata no sensible;
2. intenta obtener credenciales cifradas;
3. descifra solo durante la construcción del connector;
4. deja que runtime credentials explícitas tengan prioridad.

No hay fallback a `SECRET_KEY` de Django. La clave de cifrado debe administrarse por separado.

## Destructive Changes

Se implementa aprobación de dos pasos.

Ejemplo para eliminar tabla MANAGED:

```text
DELETE table
   ↓
¿Approved DestructiveChangeRequest?
   ├── no → 409
   └── sí → DROP + mark EXECUTED
```

Solicitud requerida:

```text
action = DELETE_MANAGED_TABLE
resource_type = TableAsset
resource_id = <uuid>
```

La aprobación expira.

## Retention

`RetentionPolicy` define días de retención para:
- Audit Logs
- Execution Logs
- export artifacts
- import artifacts

La limpieza automática se implementará en producción/maintenance de Fase 12.

## Files

En esta fase los archivos usan `MEDIA_ROOT`.

La arquitectura está intencionalmente encapsulada para migrarlos a Object Storage en Fase 12.
