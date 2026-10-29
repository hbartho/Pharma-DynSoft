@echo off
cd /d "%~dp0deploy\local"
for /f "tokens=1,* delims==" %%a in ('findstr /B "APP_PORT=" .env') do set APP_PORT=%%b
if "%APP_PORT%"=="" set APP_PORT=80
curl -fsS http://localhost:%APP_PORT%/api/health >nul 2>&1
if errorlevel 1 (
  echo Le serveur n'est pas demarre : lancement en cours...
  call "%~dp0demarrer.bat" nopause
)
start http://localhost:%APP_PORT%
