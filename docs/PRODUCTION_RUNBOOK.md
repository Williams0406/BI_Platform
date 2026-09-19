# Production Runbook

## Release

1. Crear backup.
2. Instalar dependencias.
3. Ejecutar:

```bash
python manage.py check --deploy --settings=config.settings.production
python manage.py migrate
python manage.py collectstatic --noinput
```

4. Reiniciar API/workers.
5. Verificar:
   - `/api/v1/health/live/`
   - `/api/v1/health/ready/`
   - `/api/v1/ops/status/`

## Incident: API 503 readiness

Revisar en orden:
1. PostgreSQL.
2. Redis.
3. Object Storage si `OPS_READY_CHECK_STORAGE=true`.
4. Nginx → Gunicorn.
5. logs systemd.

## Incident: queue growth

Separar por queue:
- fast/sql/imports
- python
- ml
- optimization
- maintenance

No aumente indiscriminadamente concurrency de ML/Optimization sin comprobar RAM.

## Incident: PostgreSQL connections

```bash
python manage.py db_diagnostics
```

Si el número crece con nodos:
- habilitar PgBouncer;
- usar `DB_CONN_MAX_AGE=0` detrás de transaction pooling;
- revisar concurrencia de Celery.

## Restore drill

1. Restaurar dump a una BD aislada.
2. Ejecutar migrations/check.
3. Ejecutar smoke tests.
4. Comparar tablas críticas.
5. Documentar duración real del restore.

## Gateway

Si aparece OFFLINE:
- revisar salida HTTPS;
- revisar token;
- heartbeat;
- DNS;
- certificado TLS;
- log del agente.

No abrir puertos de SQL Server/PostgreSQL a Internet como workaround.
