# API disponible — Fase 1

Base URL:

```text
/api/v1/
```

## GET `/api/v1/`

Respuesta:

```json
{
  "service": "business-intelligence-platform-api",
  "status": "ok",
  "api_version": "v1"
}
```

## GET `/api/v1/health/live/`

Liveness check. No depende de PostgreSQL.

## GET `/api/v1/health/ready/`

Readiness check. Ejecuta `SELECT 1` contra la base del Control Plane.

- `200`: Django y PostgreSQL disponibles.
- `503`: el proceso Django responde, pero la BD no está lista.
