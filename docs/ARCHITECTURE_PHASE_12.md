# Arquitectura — Fase 12

## Objetivo

Cerrar el backend con una arquitectura preparada para producción y crecimiento, sin Docker.

## Arquitectura de producción

```text
Internet
   |
   v
Nginx / TLS
   |
   v
Gunicorn / Django API  x N
   |
   +-----------------------+
   |                       |
   v                       v
PostgreSQL              Redis
Control Plane           cache / broker
   |                       |
   |                       v
   |                 Celery workers
   |          fast / sql / imports
   |          python / ml / optimization
   |          maintenance
   |
   +-----------------------+
                           |
                           v
                    Object Storage
                    S3-compatible
```

Django sigue siendo el Control Plane. Los workloads pesados continúan fuera del proceso web.

## Cache

`django-redis` usa:

```text
CACHE_URL=redis://127.0.0.1:6379/2
```

Se mantiene separado de:
- Celery broker DB 0
- Celery result backend DB 1

La capa de métricas de Fase 7 utiliza el cache Django, por lo que automáticamente pasa a Redis en producción.

## PostgreSQL pooling

Se soportan dos estrategias:

### DJANGO

```text
DB_POOL_MODE=DJANGO
DB_CONN_MAX_AGE=60
```

Apropiado para instalación pequeña.

### PGBOUNCER

```text
DB_POOL_MODE=PGBOUNCER
DB_CONN_MAX_AGE=0
DB_HOST=127.0.0.1
DB_PORT=6432
```

PgBouncer se ejecuta como servicio externo a Django.

Esto evita multiplicar conexiones PostgreSQL cuando se escalan instancias API y Celery.

## Object Storage

Se incorporó `platform_ops.storage`.

Backends:

```text
LOCAL
S3
```

S3 puede apuntar a:
- AWS S3
- MinIO
- proveedores S3-compatible

Configuración:

```text
ARTIFACT_STORAGE_BACKEND=S3
ARTIFACT_S3_BUCKET=...
ARTIFACT_S3_PREFIX=business-intelligence
ARTIFACT_S3_REGION=...
ARTIFACT_S3_ENDPOINT_URL=...
```

Las credenciales deben provenir del entorno/secret manager del host.

## Parquet

`pyarrow` se usa para persistir datasets analíticos.

Ahora:
- PythonTransformation output → Parquet
- ML PredictionAsset → Parquet

Esto reduce tamaño y acelera lectura analítica frente a CSV.

Los modelos ML continúan como `joblib` y las soluciones de optimización como JSON, pero todos utilizan el mismo Artifact Store.

## Artifact URI

Los modelos conservan una URI abstracta:

```text
/path/local/file.parquet
```

o:

```text
s3://bucket/business-intelligence/predictions/.../predictions.parquet
```

`materialize()` permite que componentes que necesitan un archivo local temporal, como `joblib.load`, funcionen también sobre S3.

## Workspace Placement

`WorkspacePlacement` deja preparado:

```text
workspace
 → database_cluster
 → compute_pool
 → storage_prefix
 → region
```

Al inicio todos pueden usar:

```text
database_cluster = primary
compute_pool = default
```

Cuando un tenant crezca puede asignarse a otro cluster sin cambiar su identidad lógica.

## Workload isolation

Colas:

```text
fast
sql
imports
python
ml
optimization
maintenance
```

Producción recomendada:
- workers transaccionales
- worker Python
- worker ML
- worker Optimization
- worker Maintenance

Esto evita starvation entre trabajos cortos y modelos pesados.

## Maintenance

Celery Beat programa:
- maintenance cada hora
- snapshot operacional cada 5 minutos

Maintenance:
- marca Executions RUNNING abandonadas como FAILED
- aplica RetentionPolicy a AuditLog
- elimina ExecutionLog antiguos
- elimina import/export artifacts expirados

## Observabilidad

`OperationalMetricSnapshot` guarda:
- database
- executions
- gateways
- storage
- API status

Endpoint admin:

```http
GET /api/v1/ops/status/
```

Readiness comprueba:
- PostgreSQL
- Redis opcionalmente
- Object Storage opcionalmente

Liveness únicamente confirma que el proceso responde.

Cada request recibe:

```text
X-Request-ID
```

que puede propagarse desde Nginx y utilizarse para correlación de logs.

## Database diagnostics

Management command:

```bash
python manage.py db_diagnostics
```

muestra:
- conexiones por estado
- tablas de mayor tamaño
- seq scans
- index scans
- índices menos utilizados

La decisión de crear/eliminar índices sigue siendo explícita; no se automatiza a partir de una métrica aislada.

## Deployment

Se incluyen:
- Gunicorn config
- Nginx config
- systemd units
- Supervisor alternative
- backup scripts
- restore script
- release script

No se incluye Docker.

## Scaling

### Etapa 1

```text
1 Nginx
1 Django/Gunicorn
1 PostgreSQL
1 Redis
workers separados
S3
```

### Etapa 2

```text
Load balancer
N Django nodes
PgBouncer
PostgreSQL primary
read replica
N worker pools
S3
```

### Etapa 3

```text
API cluster
Control Plane DB
workspace placement
multiple managed-data clusters
regional compute pools
object storage
```

## Read replicas

No se enrutan automáticamente lecturas Django a una réplica en Fase 12 porque:
- algunas lecturas deben observar writes inmediatamente;
- los jobs pueden necesitar consistencia fuerte.

La arquitectura documenta añadir un database router por endpoint/workload cuando la réplica exista.

## Backup

Control Plane PostgreSQL:
- `pg_dump --format=custom`
- SHA-256 del backup
- retención configurable a nivel de host
- restauración con `pg_restore`

Object Storage:
- activar versioning/lifecycle en el proveedor.

Los backups deben copiarse fuera del mismo host de PostgreSQL.

## Recovery targets

Definir comercialmente:
- RPO
- RTO

Recomendación inicial:
- RPO ≤ 24 h para entornos pequeños
- RPO menor mediante WAL/PITR en producción empresarial
- probar restore periódicamente

Un backup que nunca se ha restaurado no debe considerarse validado.

## Production security

- HTTPS obligatorio
- `SECURE_PROXY_SSL_HEADER`
- cookies Secure
- HSTS
- secretos fuera del repositorio
- `GOVERNANCE_FERNET_KEY` separada
- DB least privilege
- Customer Gateway outbound-only
- workers Python aislados a nivel OS/host para código no confiable
