# Arquitectura — Fase 4

## Objetivo

Agregar dos capacidades:

1. Data Model Builder para tablas administradas por la plataforma.
2. Records API para CRUD dinámico y writeback.

## Separación física

```text
PostgreSQL
│
├── public / tablas Django
│   ├── identity_*
│   ├── workspaces_*
│   ├── datasources_*
│   └── ...
│
├── ws_<workspace A>
│   ├── customers
│   ├── orders
│   └── products
│
└── ws_<workspace B>
    ├── assets
    └── activities
```

Las tablas de negocio creadas por clientes no se mezclan con las tablas del Control Plane.

## Data Model Builder

`POST /api/v1/catalog/managed-tables/`

Permite definir:
- campos
- tipos
- nullable
- unique
- default
- identity
- PK
- FK
- on_delete

Tipos lógicos:
- INTEGER
- BIGINT
- DECIMAL
- FLOAT
- BOOLEAN
- STRING
- TEXT
- DATE
- DATETIME
- DATETIME_TZ
- TIME
- UUID
- JSON
- BINARY

## DDL seguro

No se acepta SQL DDL arbitrario desde la API.

La plataforma construye DDL desde una lista blanca de tipos y reglas.
Los identificadores deben cumplir un patrón seguro.

## Concurrencia optimista

Cada tabla MANAGED recibe automáticamente:

```text
__row_version bigint NOT NULL DEFAULT 1
```

Un PATCH/DELETE debe enviar:

```text
If-Match-Version: <versión cargada por el frontend>
```

Si otro usuario modificó el registro:
- HTTP 409 Conflict
- el frontend debe recargar

## API de Records

Colección:

```text
GET  /api/v1/records/tables/{table_asset_id}/
POST /api/v1/records/tables/{table_asset_id}/
```

Registro individual:

```text
GET    /api/v1/records/tables/{table_asset_id}/{record_key}/
PATCH  /api/v1/records/tables/{table_asset_id}/{record_key}/
DELETE /api/v1/records/tables/{table_asset_id}/{record_key}/
```

En Fase 4, las operaciones individuales requieren PK simple.

## Filtros

Ejemplos:

```text
?filter__status=ACTIVE
?filter__total__gte=100
?filter__customer__contains=corp
```

Operadores:
- eq
- ne
- gt
- gte
- lt
- lte
- contains

## Orden

```text
?order_by=created_at
?order_by=-created_at
```

## Límites

Máximo 1000 registros por request.

## Alcance

- CRUD completo: MANAGED.
- Lectura de EXTERNAL: permanece en Connector API.
- Writeback externo: se integrará sobre la misma abstracción en fases posteriores.
