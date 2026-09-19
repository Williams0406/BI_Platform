# API — Fase 11

## Registrar Gateway

```http
POST /api/v1/gateway/registrations/register/
```

```json
{
  "workspace": "<uuid>",
  "name": "Lima Plant Gateway"
}
```

Respuesta incluye el `enrollment_code` una sola vez.

## Renovar Pairing

```http
POST /api/v1/gateway/registrations/{id}/renew-enrollment/
```

Invalida el token anterior.

## Revocar

```http
POST /api/v1/gateway/registrations/{id}/revoke/
```

## Binding

```http
POST /api/v1/gateway/bindings/
```

```json
{
  "gateway": "<gateway-uuid>",
  "data_source": "<private-gateway-datasource-uuid>",
  "local_connection_name": "erp-sqlserver",
  "enabled": true
}
```

El `DataSource` debe tener:

```text
mode = PRIVATE_GATEWAY
```

## Queue Job

```http
POST /api/v1/gateway/jobs/sources/{data_source_id}/queue/
```

Test:

```json
{
  "operation": "TEST_CONNECTION",
  "payload": {}
}
```

Catalog:

```json
{
  "operation": "CATALOG",
  "payload": {
    "schemas": ["dbo"],
    "include_views": true
  }
}
```

Read:

```json
{
  "operation": "READ_PAGE",
  "payload": {
    "schema": "dbo",
    "table": "orders",
    "columns": ["id", "status", "total"],
    "limit": 100,
    "offset": 0
  }
}
```

Update:

```json
{
  "operation": "UPDATE",
  "payload": {
    "schema": "dbo",
    "table": "tasks",
    "values": {
      "status": "DONE"
    },
    "where": {
      "id": 125
    }
  }
}
```

## Job Status

```http
GET /api/v1/gateway/jobs/{id}/
```

## Agent Enrollment

No requiere sesión de usuario.

```http
POST /api/v1/gateway/agent/enroll/
```

```json
{
  "gateway_id": "<uuid>",
  "enrollment_code": "...",
  "agent_version": "1.0.0",
  "platform": "Windows-...",
  "hostname": "SERVER01"
}
```

## Agent Heartbeat

Bearer agent token:

```http
POST /api/v1/gateway/agent/heartbeat/
Authorization: Bearer <agent-token>
```

## Claim Job

```http
POST /api/v1/gateway/agent/jobs/claim/
Authorization: Bearer <agent-token>
```

Devuelve 204 si no hay trabajo.

## Complete Job

```http
POST /api/v1/gateway/agent/jobs/{job_id}/complete/
Authorization: Bearer <agent-token>
```

```json
{
  "success": true,
  "result": {
    "...": "..."
  }
}
```

## Rotate Token

```http
POST /api/v1/gateway/agent/token/rotate/
Authorization: Bearer <current-token>
```

Devuelve el nuevo token una sola vez.
