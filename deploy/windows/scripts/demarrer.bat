@echo off
REM Demarre les conteneurs DynSoft Pharma (apres un arret manuel ou si Docker Desktop vient d'etre lance)
cd /d "%~dp0deploy\local"
docker info >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop n'est pas lance. Ouvrez Docker Desktop, attendez qu'il soit pret, puis relancez.
  if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
  if not "%1"=="nopause" pause
  exit /b 1
)
docker compose up -d
for /f "tokens=1,* delims==" %%a in ('findstr /B "APP_PORT=" .env') do set APP_PORT=%%b
if "%APP_PORT%"=="" set APP_PORT=80
echo Attente du serveur...
set /a N=0
:wait
curl -fsS http://localhost:%APP_PORT%/api/health >nul 2>&1 && goto ok
set /a N+=1
if %N% GEQ 60 (echo Le serveur ne repond pas. Consultez "Journal du serveur". & if not "%1"=="nopause" pause & exit /b 1)
timeout /t 3 /nobreak >nul
goto wait
:ok
echo DynSoft Pharma est pret : http://localhost:%APP_PORT%
if not "%1"=="nopause" pause
