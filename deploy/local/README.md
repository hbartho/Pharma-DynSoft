# Pack d'installation locale DynSoft Pharma

Tout est dans ce dossier. Lire **GUIDE_INSTALLATION_LOCALE.pdf** (ou .md).

| Fichier | Rôle |
|---|---|
| `install.bat` / `install.sh` | Première installation et mises à jour (`docker compose up -d --build`) |
| `env.example.txt` | Exemple de configuration (le `.env` réel est généré par `install`) |
| `docker-compose.yml` | PostgreSQL 17 + backend FastAPI + frontend (nginx, port 80) |
| `backup.bat` / `backup.sh` | Sauvegarde `pg_dump` dans `backups/` |
| `restore.bat` / `restore.sh` | Restauration d'une sauvegarde |
| `importer-depuis-cloud.bat` | Copie cloud → local de la pharmacie via le jeton de synchro (`CLOUD_SYNC_*`), sans accès direct à la base cloud |
| `migrer-depuis-supabase.bat` / `.sh` | Copie cloud → local par pg_dump (ancienne méthode, URL base requise) |
| `build_guide_pdf.py` | Régénère le PDF depuis le Markdown (`python build_guide_pdf.py`) |
