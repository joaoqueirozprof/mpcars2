#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Uso: ./ops/restore_mpcars2.sh /caminho/do/backup"
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f ".env.production" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env.production"
  set +a
fi

SOURCE_DIR="$1"
DB_CONTAINER="${DB_CONTAINER_NAME:-mpcars2-db}"
API_CONTAINER="${API_CONTAINER_NAME:-mpcars2-api}"
POSTGRES_USER="${POSTGRES_USER:-mpcars2}"
POSTGRES_DB="${POSTGRES_DB:-mpcars2}"

if [[ ! -f "$SOURCE_DIR/database.sql" ]]; then
  echo "Arquivo database.sql nao encontrado em $SOURCE_DIR"
  exit 1
fi

if [[ ! -f "$SOURCE_DIR/assets.tar.gz" ]]; then
  echo "Arquivo assets.tar.gz nao encontrado em $SOURCE_DIR"
  exit 1
fi

echo "Este comando vai sobrescrever banco, uploads e PDFs do ambiente atual."
read -r -p "Digite RESTAURAR para continuar: " CONFIRM
if [[ "$CONFIRM" != "RESTAURAR" ]]; then
  echo "Operacao cancelada."
  exit 1
fi

echo "[1/3] Restaurando banco..."
cat "$SOURCE_DIR/database.sql" | docker exec -i "$DB_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

echo "[2/3] Restaurando uploads e PDFs..."
docker cp "$SOURCE_DIR/assets.tar.gz" "$API_CONTAINER:/tmp/mpcars2_assets_restore.tar.gz"
docker exec "$API_CONTAINER" sh -lc "rm -rf /app/uploads /app/pdfs && mkdir -p /app/uploads /app/pdfs && tar -xzf /tmp/mpcars2_assets_restore.tar.gz -C /app && rm -f /tmp/mpcars2_assets_restore.tar.gz"

echo "[3/3] Restore concluido."
