# Instalación local en Windows — Fase 1

## 1. PostgreSQL

La plataforma no obliga a los futuros clientes a usar PostgreSQL, pero el Control Plane sí utiliza PostgreSQL.

Puede usar:
- PostgreSQL instalado localmente.
- Una instancia PostgreSQL administrada en cloud.

Cree una base:

```sql
CREATE DATABASE business_intelligence_control;
```

## 2. Entorno Python

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Variables

```powershell
Copy-Item .env.example .env
```

Configure al menos:

```text
DB_NAME
DB_USER
DB_PASSWORD
DB_HOST
DB_PORT
DJANGO_SECRET_KEY
```

## 4. Django

```powershell
python manage.py migrate
python manage.py check
python manage.py test
python manage.py runserver
```

## 5. Comprobar

```text
GET http://127.0.0.1:8000/api/v1/health/live/
GET http://127.0.0.1:8000/api/v1/health/ready/
```
