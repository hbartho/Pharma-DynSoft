@echo off
REM Restaure une sauvegarde (.dump) dans la base locale. Glissez le fichier .dump sur ce script ou : restore.bat backups\fichier.dump
cd /d "%~dp0"
for /f "tokens=1,* delims==" %%a in ('findstr /R "^POSTGRES_USER= ^POSTGRES_DB=" .env') do set %%a=%%b

if "%~1"=="" (
  echo Usage : restore.bat backups\fichier.dump
  dir /b backups\*.dump 2>nul
  pause
  exit /b 1
)
if not exist "%~1" (
  echo Fichier introuvable : %~1
  pause
  exit /b 1
)
if not exist backups mkdir backups
copy /y "%~1" "backups\%~nx1" >nul

echo ATTENTION : les donnees actuelles de la base locale seront remplacees par %~nx1
set /p OK=Continuer ? (oui/non) :
if /i not "%OK%"=="oui" exit /b 1

docker compose stop backend
docker compose exec -T db pg_restore -U %POSTGRES_USER% -d %POSTGRES_DB% --clean --if-exists --no-owner --no-privileges /backups/%~nx1
docker compose start backend
echo Restauration terminee.
pause
