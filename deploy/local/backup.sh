#!/usr/bin/env bash
# Sauvegarde complète de la base locale -> deploy/local/backups/dynpharma_AAAAMMJJ_HHMM.dump
set -e
cd "$(dirname "$0")"
set -a; . ./.env; set +a
mkdir -p backups
FILE="dynpharma_$(date +%Y%m%d_%H%M).dump"
docker compose exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-privileges -f "/backups/$FILE"
echo "Sauvegarde créée : backups/$FILE"
# Conserver les 30 dernières sauvegardes
ls -1t backups/dynpharma_*.dump 2>/dev/null | tail -n +31 | xargs -r rm -f
