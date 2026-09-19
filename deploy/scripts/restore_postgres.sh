#!/usr/bin/env bash
set -euo pipefail

BACKUP_FILE="${1:?Usage: restore_postgres.sh BACKUP_FILE}"
: "${DB_NAME:?DB_NAME required}"
: "${DB_USER:?DB_USER required}"
: "${DB_HOST:=127.0.0.1}"
: "${DB_PORT:=5432}"

pg_restore \
  --clean \
  --if-exists \
  --no-owner \
  --host="$DB_HOST" \
  --port="$DB_PORT" \
  --username="$DB_USER" \
  --dbname="$DB_NAME" \
  "$BACKUP_FILE"
