# Arquitectura — Fase 2

## Objetivo

Crear el núcleo multiempresa y el registro lógico de fuentes/activos de datos.

## Jerarquía

```text
User
  |
  v
Membership
  |
  v
Organization
  |
  v
Workspace
  |
  +------> DataSource
  |           |
  |           v
  |        DataAsset
  |
  +------> futuros Views / Metrics / Models
```

## Roles

- OWNER: control total de la organización.
- ADMIN: administración operativa.
- BUILDER: puede construir workspaces y recursos.
- ANALYST: lectura/analítica; permisos avanzados se ampliarán después.
- VIEWER: consulta.

La autorización fina por tabla/campo/acción llegará en Governance.

## DataSource

Representa dónde viven físicamente los datos.

### Mode
- `MANAGED`
- `EXTERNAL`
- `PRIVATE_GATEWAY`

### Engine inicial
- `PLATFORM_POSTGRES`
- `POSTGRESQL`
- `SQLSERVER`
- `OTHER`

### Capabilities
- `can_read`
- `can_write`
- `can_ddl`

Esto permite que una fuente externa sea, por ejemplo:

```text
ERP SQL Server
READ = true
WRITE = false
DDL = false
```

mientras una fuente administrada por la plataforma puede permitir:

```text
READ = true
WRITE = true
DDL = true
```

## DataAsset

Es una identidad lógica independiente del motor físico.

Ejemplos:
- TABLE
- VIEW
- DERIVED_TABLE
- DATASET
- METRIC
- DASHBOARD
- REPORT
- ML_MODEL
- OPTIMIZATION_MODEL

El resto de la plataforma deberá trabajar con `DataAsset.id`, no con nombres físicos de SQL Server/PostgreSQL.

## Seguridad de conexiones

En esta fase `connection_metadata` NO debe contener contraseñas.

Credenciales, cifrado y Connector Secret Store se incorporarán en las fases 3 y 10.
