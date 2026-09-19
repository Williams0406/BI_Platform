# API — Fase 4

## Crear tabla MANAGED

```http
POST /api/v1/catalog/managed-tables/
```

Ejemplo:

```json
{
  "workspace": "<workspace-uuid>",
  "name": "orders",
  "display_name": "Pedidos",
  "fields": [
    {
      "name": "id",
      "logical_type": "BIGINT",
      "nullable": false,
      "is_identity": true
    },
    {
      "name": "customer_id",
      "logical_type": "BIGINT",
      "nullable": false
    },
    {
      "name": "total",
      "logical_type": "DECIMAL",
      "numeric_precision": 14,
      "numeric_scale": 2,
      "nullable": false
    },
    {
      "name": "status",
      "logical_type": "STRING",
      "max_length": 40,
      "nullable": false
    }
  ],
  "primary_key": ["id"],
  "foreign_keys": []
}
```

La plataforma crea automáticamente:
- DataSource MANAGED si el workspace todavía no lo tiene.
- schema del workspace.
- tabla física.
- DataAsset.
- TableAsset.
- FieldAsset.
- RelationAsset para FK.
- `__row_version`.

## Eliminar tabla MANAGED

```http
DELETE /api/v1/catalog/managed-tables/{table_asset_id}/
```

## Insertar registro

```http
POST /api/v1/records/tables/{table_asset_id}/
```

```json
{
  "customer_id": 100,
  "total": 420.50,
  "status": "NEW"
}
```

## Consultar

```http
GET /api/v1/records/tables/{table_asset_id}/?limit=100&offset=0
```

Filtros:

```text
filter__status=NEW
filter__total__gte=100
```

## Actualizar

```http
PATCH /api/v1/records/tables/{table_asset_id}/{pk}/
If-Match-Version: 3
```

```json
{
  "status": "PROCESSING"
}
```

La respuesta devuelve `__row_version=4`.

## Eliminar registro

```http
DELETE /api/v1/records/tables/{table_asset_id}/{pk}/
If-Match-Version: 4
```

## Concurrencia

Si la versión actual ya no coincide:

```http
409 Conflict
```
