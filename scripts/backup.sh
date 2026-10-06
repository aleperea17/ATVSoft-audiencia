#!/bin/bash
set -euo pipefail

BACKUP_DIR=/opt/atv-audiencia/backups
mkdir -p "$BACKUP_DIR"
stamp="$(date +%Y-%m-%d_%H%M%S)"
dest="$BACKUP_DIR/audiencia_${stamp}.sql.gz"

docker exec audiencia-db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-acl' | gzip > "$dest"

find "$BACKUP_DIR" -type f -name 'audiencia_*.sql.gz' -mtime +14 -delete
