@echo off
REM Lance (ou met a jour) DynSoft Pharma apres l'installation : build des images, demarrage, attente de l'API.
REM %1 = install | update
set MODE=%1
cd /d "%~dp0deploy\local"
set LOG=%~dp0install.log
set STATUS=%~dp0import-status.txt
if exist "%STATUS%" del "%STATUS%"
echo ==== %date% %time% post-install (%MODE%) ==== >> "%LOG%"

where docker >nul 2>&1 || (echo Docker introuvable >> "%LOG%" & exit /b 1)
docker info >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop n'est pas lance : demarrage... >> "%LOG%"
  if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
  set /a N=0
  :waitdocker
  docker info >nul 2>&1 && goto dockerok
  set /a N+=1
  if %N% GEQ 36 (echo Docker Desktop ne repond pas >> "%LOG%" & echo Docker Desktop ne repond pas : lancez-le puis utilisez le raccourci "Demarrer le serveur". > "%STATUS%" & exit /b 1)
  timeout /t 5 /nobreak >nul
  goto waitdocker
)
:dockerok
if not exist backups mkdir backups
docker compose up -d --build >> "%LOG%" 2>&1
if errorlevel 1 (echo Echec docker compose up >> "%LOG%" & echo Echec du demarrage des conteneurs : consultez install.log. > "%STATUS%" & exit /b 1)

for /f "tokens=1,* delims==" %%a in ('findstr /B "APP_PORT=" .env') do set APP_PORT=%%b
if "%APP_PORT%"=="" set APP_PORT=80
set /a N=0
:waitapi
curl -fsS http://localhost:%APP_PORT%/api/health >nul 2>&1 && goto apiok
set /a N+=1
if %N% GEQ 120 (echo API non joignable apres 10 min >> "%LOG%" & echo Le serveur ne repond pas apres 10 min : consultez "Journal du serveur". > "%STATUS%" & exit /b 1)
timeout /t 5 /nobreak >nul
goto waitapi
:apiok
echo Serveur pret sur http://localhost:%APP_PORT% >> "%LOG%"

if /i "%MODE%"=="update" (
  echo Mise a jour terminee. Le serveur est pret : http://localhost:%APP_PORT% > "%STATUS%"
  exit /b 0
)
REM Premiere installation : resultat de l'import cloud (execute avant le demarrage de l'API)
docker compose logs --no-color backend 2>nul | findstr /C:"Import termin" /C:"ECHEC import" /C:"Import ignor" > "%TEMP%\dyn_import.txt"
findstr /C:"Import termin" "%TEMP%\dyn_import.txt" >nul 2>&1 && (
  echo Installation terminee. Les donnees de la pharmacie ont ete importees depuis le cloud. Les employes se connectent avec leurs identifiants habituels : http://localhost:%APP_PORT% > "%STATUS%"
  goto end
)
findstr /C:"Import ignor" "%TEMP%\dyn_import.txt" >nul 2>&1 && (
  echo Installation terminee, mais l'import cloud a ete ignore : la base locale contenait deja des donnees (ancienne installation). Utilisez "Importer depuis le cloud" pour les remplacer. > "%STATUS%"
  goto end
)
echo ATTENTION : l'import des donnees depuis le cloud a echoue (jeton invalide, pharmacie inconnue ou pas d'Internet). Verifiez le jeton dans deploy\local\.env puis lancez "Importer depuis le cloud". Detail dans "Journal du serveur". > "%STATUS%"
:end
type "%TEMP%\dyn_import.txt" >> "%LOG%" 2>nul
exit /b 0
