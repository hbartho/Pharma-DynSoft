#!/bin/sh
set -e

if [ -z "$DATABASE_URL" ]; then
  if [ -z "$POSTGRES_PASSWORD" ]; then
    echo "DATABASE_URL ou POSTGRES_PASSWORD requis" >&2
    exit 1
  fi
  DATABASE_URL=$(python - <<'EOF'
import os
from urllib.parse import quote_plus
u = quote_plus(os.environ.get("POSTGRES_USER", "dynpharma"))
p = quote_plus(os.environ["POSTGRES_PASSWORD"])
h = os.environ.get("POSTGRES_HOST", "db")
port = os.environ.get("POSTGRES_PORT", "5432")
db = os.environ.get("POSTGRES_DB", "dynpharma")
print(f"postgresql://{u}:{p}@{h}:{port}/{db}")
EOF
)
  export DATABASE_URL
fi

python scripts/init_local_db.py

exec uvicorn server:app --host 0.0.0.0 --port 8001 --workers "${UVICORN_WORKERS:-2}"
