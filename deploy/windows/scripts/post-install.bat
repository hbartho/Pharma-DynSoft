@echo off
REM Lance (ou met a jour) DynSoft Pharma apres l'installation : build des images, demarrage, attente de l'API.
cd /d "%~dp0deploy\local"
set LOG=%~dp0install.log
echo ==== %date% %time% post-install ==== >> "%LOG%"

where docker >nul 2>&1 || (echo Docker introuvable >> "%LOG%" & exit /b 1)
docker info >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop n'est pas lance : demarrage... >> "%LOG%"
  if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
  set /a N=0
  :waitdocker
  docker info >nul 2>&1 && goto dockerok
  set /a N+=1
  if %N% GEQ 36 (echo Docker Desktop ne repond pas >> "%LOG%" & exit /b 1)
  timeout /t 5 /nobreak >nul
  goto waitdocker
)
:dockerok
if not exist backups mkdir backups
docker compose up -d --build >> "%LOG%" 2>&1
if errorlevel 1 (echo Echec docker compose up >> "%LOG%" & exit /b 1)

for /f "tokens=1,* delims==" %%a in ('findstr /B "APP_PORT=" .env') do set APP_PORT=%%b
if "%APP_PORT%"=="" set APP_PORT=80
set /a N=0
:waitapi
curl -fsS http://localhost:%APP_PORT%/api/health >nul 2>&1 && goto apiok
set /a N+=1
if %N% GEQ 120 (echo API non joignable apres 10 min >> "%LOG%" & exit /b 1)
timeout /t 5 /nobreak >nul
goto waitapi
:apiok
echo Serveur pret sur http://localhost:%APP_PORT% >> "%LOG%"
exit /b 0
