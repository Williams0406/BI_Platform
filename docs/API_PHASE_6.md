# API — Fase 6

## SQL Transformations

```http
GET    /api/v1/transformations/
POST   /api/v1/transformations/
GET    /api/v1/transformations/{id}/
PATCH  /api/v1/transformations/{id}/
DELETE /api/v1/transformations/{id}/
```

Crear:

```json
{
  "workspace": "<uuid>",
  "name": "Ventas por cliente",
  "sql": "SELECT customer_id, SUM(total) AS revenue FROM {{asset:<uuid>}} GROUP BY customer_id",
  "output_mode": "TABLE",
  "refresh_policy": "MANUAL"
}
```

Preview:

```http
POST /api/v1/transformations/{id}/preview/
```

```json
{
  "limit": 100
}
```

Run:

```http
POST /api/v1/transformations/{id}/run/
```

Respuesta:

```json
{
  "execution_id": "...",
  "celery_task_id": "...",
  "status": "QUEUED"
}
```

## Executions

```http
GET /api/v1/executions/
GET /api/v1/executions/{id}/
POST /api/v1/executions/{id}/cancel/
```

Filtros:

```text
?workspace=<uuid>
?status=RUNNING
?object_type=SQL_TRANSFORMATION
```

## Dependencies

```http
GET  /api/v1/dependencies/edges/
POST /api/v1/dependencies/edges/
```

Ejemplo:

```json
{
  "workspace": "<uuid>",
  "upstream": "<asset-a>",
  "downstream": "<asset-b>",
  "dependency_type": "CALCULATION",
  "refresh_policy": "MARK_STALE"
}
```

## Asset states

```http
GET /api/v1/dependencies/states/
```

## Change Events

```http
GET /api/v1/dependencies/events/
```

## Lineage

```http
GET /api/v1/dependencies/lineage/{asset_id}/
```
