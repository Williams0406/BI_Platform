#!/usr/bin/env bash
set -euo pipefail

: "${DB_NAME:?DB_NAME required}"
: "${DB_USER:?DB_USER required}"
: "${DB_HOST:=127.0.0.1}"
: "${DB_PORT:=5432}"
: "${BACKUP_DIR:=/var/backups/bi-platform}"

mkdir -p "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$BACKUP_DIR/${DB_NAME}_${STAMP}.dump"

pg_dump \
  --format=custom \
  --no-owner \
  --host="$DB_HOST" \
  --port="$DB_PORT" \
  --username="$DB_USER" \
  --file="$OUT" \
  "$DB_NAME"

sha256sum "$OUT" > "${OUT}.sha256"
find "$BACKUP_DIR" -type f -name '*.dump' -mtime +14 -delete
find "$BACKUP_DIR" -type f -name '*.sha256' -mtime +14 -delete

echo "$OUT"
