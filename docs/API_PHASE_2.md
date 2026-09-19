# API — Fase 2

## Authentication

### Registro
`POST /api/v1/auth/register/`

### JWT
`POST /api/v1/auth/token/`

Body:

```json
{
  "email": "user@example.com",
  "password": "password"
}
```

### Refresh
`POST /api/v1/auth/token/refresh/`

### Usuario actual
`GET /api/v1/auth/me/`
`PATCH /api/v1/auth/me/`

---

## Organizations

`GET /api/v1/workspaces/organizations/`
`POST /api/v1/workspaces/organizations/`
`GET /api/v1/workspaces/organizations/{id}/`
`PATCH /api/v1/workspaces/organizations/{id}/`
`DELETE /api/v1/workspaces/organizations/{id}/`

Al crear una organización, el usuario creador se convierte automáticamente en `OWNER`.

---

## Workspaces

`GET /api/v1/workspaces/`
`POST /api/v1/workspaces/`
`GET /api/v1/workspaces/{id}/`
`PATCH /api/v1/workspaces/{id}/`
`DELETE /api/v1/workspaces/{id}/`

---

## Data Sources

`GET /api/v1/data/sources/`
`POST /api/v1/data/sources/`

Filtro:

```text
?workspace=<uuid>
```

---

## Data Assets

`GET /api/v1/data/assets/`
`POST /api/v1/data/assets/`

Filtros:

```text
?workspace=<uuid>
?asset_type=TABLE
```
