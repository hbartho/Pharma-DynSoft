#!/usr/bin/env bash
# Installation / mise à jour de DynSoft Pharma en local (Linux / macOS)
set -e
cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker n'est pas installé. Voir le guide : https://docs.docker.com/get-docker/"
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Fichier .env créé à partir de .env.example."
  echo ">>> Ouvrez deploy/local/.env, remplacez toutes les valeurs CHANGEZ_MOI, puis relancez ./install.sh"
  exit 0
fi

if grep -q "CHANGEZ_MOI" .env; then
  echo "Le fichier .env contient encore des valeurs CHANGEZ_MOI. Modifiez-les avant de continuer."
  exit 1
fi

mkdir -p backups
echo "Construction des images et démarrage (première fois : 5 à 15 minutes)..."
docker compose up -d --build

echo
echo "Attente du démarrage du backend..."
for i in $(seq 1 30); do
  if docker compose exec -T backend curl -fsS http://localhost:8001/health >/dev/null 2>&1; then
    break
  fi
  sleep 3
done

PORT=$(grep -E '^APP_PORT=' .env | cut -d= -f2)
IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo
echo "DynSoft Pharma est démarré."
echo "  Sur ce PC        : http://localhost:${PORT:-80}"
[ -n "$IP" ] && echo "  Depuis un autre poste du réseau : http://${IP}:${PORT:-80}"
echo
echo "Journal backend : docker compose logs -f backend"
