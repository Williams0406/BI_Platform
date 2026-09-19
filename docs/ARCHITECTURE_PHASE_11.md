# Arquitectura — Fase 11

## Objetivo

Implementar `PRIVATE_GATEWAY` para acceder a bases de datos dentro de redes privadas sin exponerlas directamente a Internet.

## Arquitectura

```text
PLATFORM CLOUD
     |
     | HTTPS jobs / heartbeat
     |
     v
Customer Data Gateway
     |
     +------------------+
     |                  |
     v                  v
SQL Server          PostgreSQL
private LAN         private LAN
```

El Gateway inicia todas las conexiones hacia la plataforma.

No requiere:
- port forwarding
- IP pública para la BD
- abrir SQL Server/PostgreSQL a Internet
- conexión inbound desde la nube

## Control Plane

### GatewayRegistration

Registra:
- workspace
- nombre
- estado
- hash del enrollment code
- expiración
- hash del agent token
- token version
- agent version
- hostname
- platform
- capabilities
- last_seen_at

Estados:
- PENDING
- ONLINE
- OFFLINE
- REVOKED

## Enrollment / Pairing

1. Usuario crea un Gateway.
2. Plataforma genera un código temporal.
3. El código se muestra una sola vez.
4. Agente llama `/agent/enroll/`.
5. Backend valida hash + TTL.
6. Se devuelve un agent token.
7. La plataforma conserva únicamente SHA-256 del token.
8. El enrollment code queda invalidado.

El token puede rotarse desde el propio agente.

Un administrador puede usar `renew-enrollment`; esto invalida el token anterior y genera un nuevo pairing code.

## Heartbeat

El agente envía heartbeat periódicamente.

La plataforma registra:
- agent version
- OS/platform
- hostname
- capabilities
- métricas básicas

Si `last_seen_at` supera `GATEWAY_OFFLINE_AFTER_SECONDS`, el estado efectivo pasa a OFFLINE.

## DataSource Binding

Un `DataSource` con:

```text
mode = PRIVATE_GATEWAY
```

se vincula a:

```text
GatewayRegistration
+
local_connection_name
```

Ejemplo cloud:

```text
DataSource: ERP Producción
engine: SQLSERVER
mode: PRIVATE_GATEWAY
```

Binding:

```text
Gateway: Lima Plant
local_connection_name: erp-sqlserver
```

El backend cloud nunca recibe la contraseña local.

## Local Agent Configuration

El agente mantiene localmente:

```json
{
  "connections": {
    "erp-sqlserver": {
      "engine": "SQLSERVER",
      "config": {
        "server": "...",
        "database": "...",
        "user": "...",
        "password": "${ERP_GATEWAY_PASSWORD}"
      }
    }
  }
}
```

Se soportan referencias a variables de entorno `${NAME}` para evitar passwords en el JSON.

## Job Protocol

`GatewayJob` soporta:

- TEST_CONNECTION
- CATALOG
- READ_PAGE
- INSERT
- UPDATE
- DELETE

No se expone ejecución SQL arbitraria.

Las operaciones write son estructuradas y requieren `DataSource.can_write=true`.

DDL no se habilita por este protocolo en Fase 11; `can_ddl` permanece reservado para una implementación con controles destructivos explícitos.

## Lease

Al reclamar un job:

```text
QUEUED → CLAIMED
```

se define `lease_expires_at`.

Si el Gateway desaparece antes de terminarlo, un claim posterior puede devolver el job vencido a QUEUED.

Esto reduce pérdida de trabajos por fallos transitorios.

## Catalog

El flujo de catálogo privado es:

```text
User queues CATALOG
      ↓
Gateway claims
      ↓
Local connector introspects DB
      ↓
Agent returns TableInfo JSON
      ↓
Cloud sync_gateway_catalog
      ↓
DataAsset / TableAsset / FieldAsset / RelationAsset
```

Por tanto una fuente privada aparece en el mismo catálogo lógico que una fuente EXTERNAL.

## READ

`READ_PAGE` reutiliza el Connector local y está limitado a 1000 filas por job.

Ejemplo:

```json
{
  "schema": "dbo",
  "table": "orders",
  "columns": ["id", "status", "total"],
  "limit": 100,
  "offset": 0
}
```

## Writeback

INSERT:

```json
{
  "schema": "dbo",
  "table": "tasks",
  "values": {
    "name": "Inspection",
    "status": "PENDING"
  }
}
```

UPDATE:

```json
{
  "schema": "dbo",
  "table": "tasks",
  "values": {
    "status": "DONE"
  },
  "where": {
    "id": 125
  }
}
```

DELETE requiere obligatoriamente un `where` no vacío.

Esto evita un `DELETE FROM table` accidental.

## Seguridad

Cloud:
- agent token no se almacena en plaintext
- enrollment code hasheado
- enrollment TTL
- revocation
- token rotation
- audit trail

Customer environment:
- DB credentials permanecen locales
- variables de entorno soportadas
- Gateway hace conexiones outbound
- agent config debe tener permisos de filesystem restringidos

Transport:
- producción debe usar HTTPS válido
- TLS termination/reverse proxy se completa en Fase 12

## Agent

Archivo:

```text
backend/customer_gateway/agent.py
```

No usa una librería HTTP adicional; emplea Python stdlib para la comunicación con la plataforma.

Los Connectors PostgreSQL/SQL Server se reutilizan localmente, evitando mantener una segunda implementación de introspection/read logic.

## No Docker

El agente puede ejecutarse como:
- proceso Python
- Windows Task Scheduler/service wrapper
- Linux systemd service

La instalación productiva como servicio se formaliza en Fase 12.
