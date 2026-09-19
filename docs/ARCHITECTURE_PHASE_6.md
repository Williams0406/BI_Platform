# Arquitectura — Fase 6

## Objetivo

Integrar:

1. SQL Transformation Engine
2. Dependency / Lineage Engine
3. Execution Engine con Celery + Redis

## Arquitectura

```text
Next.js
   |
   v
Django / DRF --------------- Control Plane
   |
   +--> SQLTransformation
   +--> AssetDependency
   +--> AssetState
   +--> Execution
   |
   v
Redis Broker
   |
   +--> fast queue
   +--> sql queue
   |
   v
Celery Workers ------------- Execution Plane
   |
   v
PostgreSQL / Data Assets
```

Django registra y coordina.
Los workers ejecutan.

## Transformations

En Fase 6 se implementa SQL sobre assets MANAGED.

La transformación acepta exclusivamente `SELECT` o `WITH`.

No acepta:
- INSERT
- UPDATE
- DELETE
- DROP
- ALTER
- CREATE
- GRANT
- REVOKE
- múltiples sentencias

Los Data Assets se referencian por UUID:

```sql
SELECT
    customer_id,
    SUM(total) AS revenue
FROM {{asset:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx}}
GROUP BY customer_id
```

El backend resuelve el token a:

```text
"ws_...".orders
```

De ese modo una transformación no almacena nombres físicos.

## Outputs

- VIEW
- TABLE

VIEW:
`CREATE VIEW ... AS SELECT ...`

TABLE:
`CREATE TABLE ... AS SELECT ...`

El output se registra como:
- DataAsset
- TableAsset
- FieldAsset

## Dependency DAG

Ejemplo:

```text
ORDERS
   |
   v
SALES_BY_CUSTOMER
   |
   v
REVENUE_METRIC
```

`AssetDependency` registra los edges.

Antes de crear un edge:
- comprueba mismo workspace
- prohíbe self-loop
- comprueba ciclos

## Asset State

Estados:

```text
FRESH
STALE
RUNNING
FAILED
BLOCKED
ARCHIVED
```

Además cada Asset mantiene una versión.

## Change Event

Los INSERT / UPDATE / DELETE ejecutados mediante Records generan:

```text
ChangeEvent
```

después del COMMIT.

Luego Celery encola propagación.

Esto evita disparar lineage sobre una transacción que posteriormente haga rollback.

## Propagación

Al cambiar un asset upstream:
- aumenta su versión
- crea ChangeEvent
- downstream pasa a STALE

La política del edge se registra como:
- AUTO
- MARK_STALE
- MANUAL

La ejecución automática de cascadas complejas se ampliará progresivamente sobre este mismo DAG.

## Execution

Cada trabajo pesado tiene:

```text
Execution
- workspace
- object_type
- object_id
- queue
- status
- progress
- celery_task_id
- parameters
- result
- error
- timestamps
- duration
```

Logs:

```text
ExecutionLog
```

## Queues

Inicialmente:

```text
fast
sql
```

La configuración ya deja la arquitectura preparada para:

```text
python
metrics
ml
optimization
reports
imports
```

## Cancelación

La API permite solicitar cancelación.

Celery revoke se usa sin `terminate=True` en esta fase para evitar matar procesos de forma insegura.

## Redis

Redis se usa como:
- Celery broker
- Celery result backend

No se usa como base primaria de metadatos.
