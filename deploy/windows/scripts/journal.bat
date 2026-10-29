@echo off
cd /d "%~dp0deploy\local"
docker compose logs -f --tail=200 backend
