@echo off
REM Appele par le desinstalleur : "purge" supprime aussi la base (volume), "keep" conserve les donnees.
cd /d "%~dp0deploy\local"
if not exist docker-compose.yml exit /b 0
if /i "%1"=="purge" (
  docker compose down -v --rmi local --remove-orphans
) else (
  docker compose down --rmi local --remove-orphans
)
exit /b 0
