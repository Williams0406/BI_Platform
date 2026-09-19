# API — Fase 3

## Probar conexión

```http
POST /api/v1/connectors/sources/{datasource_id}/test/
```

Ejemplo PostgreSQL:

```json
{
  "password": "runtime-secret"
}
```

El resto puede residir en `connection_metadata`.

## Preview del catálogo

```http
POST /api/v1/connectors/sources/{datasource_id}/catalog/
```

```json
{
  "password": "runtime-secret",
  "schemas": ["public"],
  "include_views": true
}
```

No persiste cambios.

## Sincronizar catálogo

```http
POST /api/v1/catalog/sources/{datasource_id}/sync/
```

```json
{
  "password": "runtime-secret",
  "schemas": ["public"],
  "include_views": true
}
```

## Consultar tablas catalogadas

```http
GET /api/v1/catalog/tables/
GET /api/v1/catalog/tables/?data_source={uuid}
GET /api/v1/catalog/tables/?schema=public
```

## Relaciones

```http
GET /api/v1/catalog/relations/
GET /api/v1/catalog/relations/?data_source={uuid}
```

## Preview paginado de datos

```http
POST /api/v1/connectors/sources/{datasource_id}/read/
```

```json
{
  "password": "runtime-secret",
  "schema": "public",
  "table": "orders",
  "columns": ["id", "customer_id", "total"],
  "limit": 100,
  "offset": 0
}
```

Máximo actual: 1000 filas por request.
