# Arquitectura — Fase 3

## Objetivo

Permitir que un `DataSource EXTERNAL` se conecte a PostgreSQL o Microsoft SQL Server y convierta el esquema físico descubierto en un catálogo lógico consumible por toda la plataforma.

## Capas

```text
DataSource
   |
   v
Connector Registry
   |
   +--> PostgreSQLConnector
   |
   +--> SQLServerConnector
   |
   v
Introspection
   |
   v
Catalog Sync
   |
   +--> DataAsset
   +--> TableAsset
   +--> FieldAsset
   +--> RelationAsset
```

## Contrato BaseConnector

Los módulos superiores no interactúan directamente con psycopg o pyodbc.

```text
test_connection()
list_schemas()
list_tables()
get_columns()
get_primary_key()
get_foreign_keys()
introspect_catalog()
read_page()
```

## PostgreSQL

Utiliza `psycopg` y consulta `information_schema`.

Descubre:
- schemas
- tablas
- vistas
- tipos
- PK
- FK
- identity
- nullability
- precision / scale

## SQL Server

Utiliza `pyodbc`, `INFORMATION_SCHEMA` y `sys.*`.

Requisito del sistema operativo:
debe existir un Microsoft ODBC Driver for SQL Server instalado en el equipo que ejecute el connector.

Driver predeterminado:

```text
ODBC Driver 18 for SQL Server
```

Puede cambiarse mediante `connection_metadata.driver`.

## Credenciales

En Fase 3:
- host/server, port, database, user y opciones no secretas pueden persistirse.
- password no se persiste.
- el password se recibe como runtime credential en el request.

Esto es deliberado. El Secret Store cifrado se incorporará con Governance.

## Catálogo

### TableAsset
Extiende el `DataAsset` genérico para representar un objeto tabular.

### FieldAsset
Representa la columna física y su tipo lógico normalizado.

### RelationAsset
Representa una FK física.

## Normalización de tipos

Los connectors traduccen tipos nativos a tipos lógicos comunes:

```text
INTEGER
BIGINT
DECIMAL
FLOAT
BOOLEAN
STRING
TEXT
DATE
DATETIME
DATETIME_TZ
TIME
UUID
JSON
BINARY
OTHER
```

Esto permitirá que Views, Metrics, Data Science y Optimization trabajen independientemente del motor físico.

## Sincronización

La sincronización:
1. introspecta la fuente;
2. crea/actualiza `DataAsset`;
3. crea/actualiza `TableAsset`;
4. crea/actualiza `FieldAsset`;
5. elimina campos catalogados que ya no existen;
6. crea/actualiza relaciones FK.

Una FK cuyo target esté fuera de los schemas seleccionados no genera una relación incompleta.
