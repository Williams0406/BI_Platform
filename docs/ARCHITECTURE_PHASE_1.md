# Arquitectura — Fase 1

## Objetivo

Establecer el esqueleto ejecutable del Control Plane antes de crear modelos empresariales.

## Flujo actual

```text
Next.js (futuro)
       |
       | HTTP / JSON
       v
Django + DRF
       |
       v
Control Plane PostgreSQL
```

## Decisiones

### 1. PostgreSQL para el Control Plane
La base `default` de Django representa la información propia de la plataforma:
usuarios, workspaces, Data Sources, assets, métricas, modelos, ejecuciones, etc.

No debe confundirse con las bases de datos empresariales externas que se incorporarán posteriormente.

### 2. Settings por entorno
- `development.py`
- `production.py`
- `test.py`

Los secretos se reciben por variables de entorno y `.env` solo se usa localmente.

### 3. Apps de dominio
Las carpetas de los futuros módulos ya existen para fijar límites arquitectónicos, pero todavía no se registran como Django apps sin necesidad.

### 4. Health checks
- `health/live/`: proceso vivo.
- `health/ready/`: proceso listo y conexión al Control Plane disponible.

### 5. Sin Docker
No existe Dockerfile, docker-compose ni dependencia de contenedores.

La ejecución local se realiza con Python virtualenv y PostgreSQL instalado o administrado externamente.

## Próxima fase

Fase 2:
- Custom User con email.
- Organization.
- Membership.
- Roles.
- Workspace.
- DataSource / DataAsset Registry.
