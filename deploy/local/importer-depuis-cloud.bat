@echo off
REM Remplace les donnees locales de la pharmacie par la copie du cloud DynSoft (CLOUD_SYNC_* du .env).
cd /d "%~dp0"
echo ATTENTION : les donnees actuelles de la pharmacie sur ce PC seront remplacees par celles du cloud.
set /p OK=Continuer ? (oui/non) :
if /i not "%OK%"=="oui" exit /b 0
docker compose exec backend python scripts/import_from_cloud.py --force
if errorlevel 1 (
  echo Echec de l'import. Verifiez la connexion Internet et les parametres CLOUD_SYNC_* du fichier .env.
) else (
  echo Import termine. Les utilisateurs se connectent avec leurs identifiants du cloud.
)
pause
