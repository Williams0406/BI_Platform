# API — Fase 5

## Vistas

```http
GET    /api/v1/views/
POST   /api/v1/views/
GET    /api/v1/views/{id}/
PATCH  /api/v1/views/{id}/
DELETE /api/v1/views/{id}/
```

Filtros:

```text
?workspace=<uuid>
?view_type=KANBAN
```

## Crear Kanban

```json
{
  "workspace": "<uuid>",
  "source_table": "<table-asset-uuid>",
  "name": "Gestión de tareas",
  "view_type": "KANBAN",
  "config": {
    "card_density": "compact"
  }
}
```

## Crear binding

```http
POST /api/v1/views/{view_id}/bindings/
```

```json
{
  "field": "<field-asset-uuid>",
  "role": "STATUS",
  "alias": "Estado",
  "editable": true,
  "position": 2
}
```

## Esquema consumible por Next.js

```http
GET /api/v1/views/{view_id}/schema/
```

Devuelve:
- fuente
- PK
- row version
- bindings
- aliases
- editabilidad
- configuración visual
- contrato de la vista

## Datos

```http
GET /api/v1/views/{view_id}/data/
```

Reutiliza filtros, orden y paginación de Records:

```text
?filter__status=ACTIVE
?order_by=-created_at
?limit=100
```

## Validar contrato

```http
GET /api/v1/views/{view_id}/validate/
```

## Interacción / writeback

```http
POST /api/v1/views/{view_id}/interact/
```

Kanban:

```json
{
  "action": "MOVE_KANBAN",
  "record_key": "125",
  "expected_version": 7,
  "values": {
    "status": "DONE"
  }
}
```

Spreadsheet/Table/Form:

```json
{
  "action": "UPDATE_FIELD",
  "record_key": "125",
  "expected_version": 7,
  "values": {
    "priority": "HIGH"
  }
}
```

Matrix:

```json
{
  "action": "EDIT_CELL",
  "record_key": "9001",
  "expected_version": 2,
  "values": {
    "quantity": 450
  }
}
```

Calendar:

```json
{
  "action": "RESIZE_CALENDAR",
  "record_key": "701",
  "expected_version": 3,
  "values": {
    "start_at": "2026-09-01T08:00:00",
    "end_at": "2026-09-01T12:00:00"
  }
}
```

El backend rechaza modificaciones a campos que no estén autorizados por los bindings.
