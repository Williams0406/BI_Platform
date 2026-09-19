# Celery + Redis en Windows — desarrollo sin Docker

## Redis

La aplicación espera por defecto:

```text
redis://127.0.0.1:6379/0
```

Puede utilizar:
- Redis ejecutándose mediante WSL.
- Un servidor Redis remoto.
- Un servicio Redis administrado.

Configure `.env`:

```text
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1
```

## Worker SQL

Desde `backend/`:

```powershell
celery -A config worker -l INFO -Q sql --pool=solo
```

## Worker fast

En otra consola:

```powershell
celery -A config worker -l INFO -Q fast --pool=solo
```

`--pool=solo` se utiliza como configuración simple para desarrollo Windows.

En un servidor Linux de producción se podrán usar pools multiproceso y workers separados.

## Django

En otra consola:

```powershell
python manage.py runserver
```

## Flujo

```text
Django
  |
  v
Redis
  |
  +--> fast worker
  |
  +--> sql worker
```
