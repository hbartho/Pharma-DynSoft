@echo off
REM Sauvegarde complete de la base locale -> deploy\local\backups\dynpharma_AAAAMMJJ_HHMM.dump
cd /d "%~dp0"
for /f "tokens=1,* delims==" %%a in ('findstr /R "^POSTGRES_USER= ^POSTGRES_DB=" .env') do set %%a=%%b
if not exist backups mkdir backups
for /f "tokens=1-5 delims=/:. " %%d in ("%date% %time%") do set STAMP=%%f%%e%%d_%%g%%h
set FILE=dynpharma_%STAMP%.dump
docker compose exec -T db pg_dump -U %POSTGRES_USER% -d %POSTGRES_DB% --format=custom --no-owner --no-privileges -f /backups/%FILE%
if errorlevel 1 (
  echo Echec de la sauvegarde.
) else (
  echo Sauvegarde creee : backups\%FILE%
)
pause
