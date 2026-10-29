@echo off
cd /d "%~dp0deploy\local"
docker compose stop
echo Serveur arrete. Les donnees sont conservees.
pause
