# Customer Data Gateway — Windows

## 1. Preparar config

Desde `backend/`:

```powershell
Copy-Item customer_gateway\gateway_config.example.json gateway_config.json
```

Configurar `platform_url` y los nombres de conexiones.

Para passwords se recomienda:

```powershell
$env:ERP_GATEWAY_PASSWORD="..."
```

y en JSON:

```json
"password": "${ERP_GATEWAY_PASSWORD}"
```

## 2. Crear Gateway en la plataforma

Use:

```http
POST /api/v1/gateway/registrations/register/
```

Guarde:
- gateway_id
- enrollment_code

## 3. Enroll

```powershell
python -m customer_gateway.agent --config gateway_config.json enroll `
  --gateway-id "<uuid>" `
  --code "<enrollment-code>"
```

El token resultante se guarda en el config local.

Proteja ese archivo mediante permisos NTFS y no lo suba a Git.

## 4. Ejecutar

```powershell
python -m customer_gateway.agent --config gateway_config.json run
```

## 5. Rotar token

```powershell
python -m customer_gateway.agent --config gateway_config.json rotate-token
```

## Servicio

En Fase 11 se ejecuta como proceso normal.

En Fase 12 se documentará deployment persistente como servicio de Windows o systemd.

## Red

El agente requiere solo salida HTTPS hacia la plataforma.

No abra:
- 1433
- 5432
- puertos internos de base de datos

hacia Internet.
