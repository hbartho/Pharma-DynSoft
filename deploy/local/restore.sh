#!/usr/bin/env bash
# Restaure une sauvegarde (.dump) dans la base locale. Usage : ./restore.sh backups/dynpharma_XXXX.dump
set -e
cd "$(dirname "$0")"
set -a; . ./.env; set +a

if [ -z "$1" ] || [ ! -f "$1" ]; then
  echo "Usage : ./restore.sh backups/<fichier>.dump"
  ls -1 backups/*.dump 2>/dev/null || true
  exit 1
fi
FILE=$(basename "$1")
cp -f "$1" "backups/$FILE" 2>/dev/null || true

echo "ATTENTION : les données actuelles de la base locale seront remplacées par $FILE"
read -r -p "Continuer ? (oui/non) : " OK
[ "$OK" = "oui" ] || exit 1

docker compose stop backend
docker compose exec -T db pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges "/backups/$FILE" || true
docker compose start backend
echo "Restauration terminée."
