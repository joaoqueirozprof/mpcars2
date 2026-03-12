#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f ".env.production" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env.production"
  set +a
fi

BACKUP_ROOT="${BACKUP_DIRECTORY_HOST:-$ROOT_DIR/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
DB_CONTAINER="${DB_CONTAINER_NAME:-mpcars2-db}"
API_CONTAINER="${API_CONTAINER_NAME:-mpcars2-api}"
POSTGRES_USER="${POSTGRES_USER:-mpcars2}"
POSTGRES_DB="${POSTGRES_DB:-mpcars2}"
CONTAINER_BACKUP_ROOT="${BACKUP_DIRECTORY_CONTAINER:-${BACKUP_DIRECTORY:-/backups}}"
GOOGLE_DRIVE_BACKUP_ENABLED="${GOOGLE_DRIVE_BACKUP_ENABLED:-false}"
GOOGLE_DRIVE_SYNC_ON_BACKUP="${GOOGLE_DRIVE_SYNC_ON_BACKUP:-true}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
TARGET_DIR="$BACKUP_ROOT/$TIMESTAMP"

mkdir -p "$TARGET_DIR"

echo "[1/4] Gerando dump do banco..."
docker exec "$DB_CONTAINER" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" > "$TARGET_DIR/database.sql"

echo "[2/4] Compactando uploads e PDFs..."
docker exec "$API_CONTAINER" sh -lc "tar -czf /tmp/mpcars2_assets_${TIMESTAMP}.tar.gz -C /app uploads pdfs"
docker cp "$API_CONTAINER:/tmp/mpcars2_assets_${TIMESTAMP}.tar.gz" "$TARGET_DIR/assets.tar.gz"
docker exec "$API_CONTAINER" rm -f "/tmp/mpcars2_assets_${TIMESTAMP}.tar.gz"

echo "[3/4] Salvando manifesto..."
cat > "$TARGET_DIR/manifest.txt" <<EOF
timestamp=$TIMESTAMP
database_container=$DB_CONTAINER
api_container=$API_CONTAINER
postgres_db=$POSTGRES_DB
postgres_user=$POSTGRES_USER
backup_directory=$TARGET_DIR
EOF

if [[ "$GOOGLE_DRIVE_BACKUP_ENABLED" == "true" && "$GOOGLE_DRIVE_SYNC_ON_BACKUP" == "true" ]]; then
  echo "[3.5/4] Sincronizando com Google Drive..."
  docker exec "$API_CONTAINER" sh -lc "PYTHONPATH=/app python -m app.scripts.sync_backup_to_google_drive '$CONTAINER_BACKUP_ROOT/$TIMESTAMP'" || true
fi

echo "[4/4] Limpando backups antigos..."
find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime +"$RETENTION_DAYS" -exec rm -rf {} +

echo "Backup concluido em: $TARGET_DIR"
