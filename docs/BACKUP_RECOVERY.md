# Backup & Recovery

## PostgreSQL

Backup:

```bash
deploy/scripts/backup_postgres.sh
```

Restore:

```bash
deploy/scripts/restore_postgres.sh /path/file.dump
```

## Recommended production evolution

Pequeño:
- pg_dump diario
- copia off-host

Empresarial:
- base backup
- WAL archiving
- Point-in-Time Recovery
- réplica
- restore drills

## Object Storage

Habilitar:
- bucket versioning
- encryption at rest
- lifecycle
- cross-region replication cuando el RPO lo justifique

## Secrets

Los backups de PostgreSQL incluyen ciphertext pero no deben incluir la master key Fernet.
La master key debe tener backup separado, controlado y auditado.
