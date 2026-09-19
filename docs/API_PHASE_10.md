# API — Fase 10

## Import

```http
POST /api/v1/import-export/imports/
```

multipart/form-data:
- workspace
- target_table
- file
- file_type=CSV|XLSX
- sheet_name opcional
- mode=APPEND|UPSERT
- column_mapping JSON

Preview:

```http
GET /api/v1/import-export/imports/{id}/preview/
```

Ejecutar:

```http
POST /api/v1/import-export/imports/{id}/run/
```

## Export

```http
POST /api/v1/import-export/exports/
```

```json
{
  "workspace":"<uuid>",
  "source_table":"<uuid>",
  "file_type":"XLSX",
  "columns":["id","customer","total"],
  "filters":[
    {"field":"status","operator":"eq","value":"ACTIVE"}
  ],
  "row_limit":100000
}
```

La creación encola automáticamente el job.

Download:

```http
GET /api/v1/import-export/exports/{id}/download/
```

## Audit

```http
GET /api/v1/governance/audit/?workspace=<uuid>
```

## Quotas

```http
GET   /api/v1/governance/workspaces/{workspace_id}/quota/
PATCH /api/v1/governance/workspaces/{workspace_id}/quota/
```

## Usage

```http
GET /api/v1/governance/workspaces/{workspace_id}/usage/
```

## Retention

```http
GET   /api/v1/governance/workspaces/{workspace_id}/retention/
PATCH /api/v1/governance/workspaces/{workspace_id}/retention/
```

## Fine-grained permissions

```http
GET  /api/v1/governance/permissions/
POST /api/v1/governance/permissions/
```

## DataSource Secret

Guardar/reemplazar:

```http
POST /api/v1/governance/datasource-secrets/
```

```json
{
  "data_source":"<uuid>",
  "credentials":{
    "user":"readonly_user",
    "password":"secret"
  }
}
```

Consultar solo estado, nunca plaintext:

```http
GET /api/v1/governance/datasource-secrets/{data_source_id}/
```

## Destructive requests

```http
POST /api/v1/governance/destructive-requests/
```

```json
{
  "workspace":"<uuid>",
  "action":"DELETE_MANAGED_TABLE",
  "resource_type":"TableAsset",
  "resource_id":"<table-uuid>",
  "reason":"Tabla obsoleta"
}
```

Aprobar:

```http
POST /api/v1/governance/destructive-requests/{id}/approve/
```

Después de la aprobación, el DELETE de la tabla puede ejecutarse una vez.
