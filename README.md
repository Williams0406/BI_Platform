# Business Intelligence Platform

Plataforma empresarial de datos, BI, Data Science y optimización.

## Estado
Fases 1–12 completadas: backend integral de datos operativos, BI, Data Science, optimización, governance, Customer Data Gateway y arquitectura de producción/escalabilidad.

## Stack
- Backend: Django + Django REST Framework
- Frontend previsto: Next.js
- Control Plane DB: PostgreSQL
- Sin Docker
- Python recomendado: 3.12–3.14
- Arquitectura preparada para:
  - Managed Database
  - External Database
  - Private Network / Customer Data Gateway

## Inicio rápido en Windows PowerShell

```powershell
cd backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt

Copy-Item .env.example .env
```

Edite `.env` con sus credenciales PostgreSQL.

Luego:

```powershell
python manage.py migrate
python manage.py check
python manage.py runserver
```

Backend:
- http://127.0.0.1:8000/
- http://127.0.0.1:8000/api/v1/health/live/
- http://127.0.0.1:8000/api/v1/health/ready/

## Frontend Next.js

Durante desarrollo se asume por defecto:

```text
http://localhost:3000
```

Puede cambiarse con `CORS_ALLOWED_ORIGINS` en `.env`.

## Estructura

```text
business_intelligence_platform/
├── backend/
│   ├── config/
│   ├── common/
│   ├── identity/
│   ├── workspaces/
│   ├── datasources/
│   ├── connectors/
│   ├── data_model/
│   ├── data_records/
│   ├── views_engine/
│   ├── transformations/
│   ├── metrics/
│   ├── analytics/
│   ├── dependencies/
│   ├── execution/
│   ├── data_science/
│   ├── optimization/
│   ├── governance/
│   └── imports_exports/
└── docs/
```

Los módulos de negocio se irán implementando en las siguientes fases. En Fase 1 se crea la arquitectura base sin adelantar modelos que todavía no corresponden.


## Fase 3
Connectors PostgreSQL/SQL Server y catálogo externo implementados.


## Fase 12 — Roadmap backend completado
Escalabilidad y producción implementadas sin Docker.
