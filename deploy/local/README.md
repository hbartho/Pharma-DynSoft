# Pack d'installation locale DynSoft Pharma

Tout est dans ce dossier. Lire **GUIDE_INSTALLATION_LOCALE.pdf** (ou .md).

| Fichier | Rôle |
|---|---|
| `install.bat` / `install.sh` | Première installation et mises à jour (`docker compose up -d --build`) |
| `.env.example` | Modèle de configuration → copié en `.env` à la première exécution |
| `docker-compose.yml` | PostgreSQL 17 + backend FastAPI + frontend (nginx, port 80) |
| `backup.bat` / `backup.sh` | Sauvegarde `pg_dump` dans `backups/` |
| `restore.bat` / `restore.sh` | Restauration d'une sauvegarde |
| `migrer-depuis-supabase.bat` / `.sh` | Copie cloud → local (une fois, avec Internet) |
| `build_guide_pdf.py` | Régénère le PDF depuis le Markdown (`python build_guide_pdf.py`) |
