#!/usr/bin/env bash
# Copie les données de la pharmacie depuis Supabase (cloud) vers la base locale.
# Nécessite Internet pendant l'export. L'URL n'est jamais enregistrée sur le disque.
set -e
cd "$(dirname "$0")"
set -a; . ./.env; set +a
mkdir -p backups

echo "Collez l'URL de connexion Supabase (Session pooler, port 5432)."
echo "Format : postgresql://postgres.xxxx:MOT_DE_PASSE@aws-0-xx.pooler.supabase.com:5432/postgres"
echo "Si le mot de passe contient # @ / : ou %, encodez-le (ex. # devient %23)."
read -r -s -p "URL Supabase : " SRC_URL; echo
[ -n "$SRC_URL" ] || exit 1

FILE="supabase_$(date +%Y%m%d_%H%M).dump"
echo "Export depuis Supabase (schéma public + schémas t_* des pharmacies)..."
docker compose exec -T -e SRC_URL="$SRC_URL" db sh -c \
  'pg_dump "$SRC_URL" --format=custom --no-owner --no-privileges --schema=public --schema="t_*" -f /backups/'"$FILE"
echo "Export terminé : backups/$FILE"

echo "ATTENTION : les données actuelles de la base locale seront remplacées."
read -r -p "Importer maintenant dans la base locale ? (oui/non) : " OK
[ "$OK" = "oui" ] || { echo "Import annulé. Vous pourrez le faire plus tard avec ./restore.sh backups/$FILE"; exit 0; }

docker compose stop backend
docker compose exec -T db pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges "/backups/$FILE" || true
docker compose start backend
echo "Migration terminée. Connectez-vous avec vos identifiants habituels."
