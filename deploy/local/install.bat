@echo off
REM Installation / mise a jour de DynSoft Pharma en local (Windows - Docker Desktop)
cd /d "%~dp0"

where docker >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop n'est pas installe. Telechargez-le : https://www.docker.com/products/docker-desktop/
  pause
  exit /b 1
)

if not exist .env (
  copy .env.example .env >nul
  echo Fichier .env cree a partir de .env.example.
  echo ^>^>^> Ouvrez deploy\local\.env avec le Bloc-notes, remplacez toutes les valeurs CHANGEZ_MOI, puis relancez install.bat
  pause
  exit /b 0
)

findstr /C:"CHANGEZ_MOI" .env >nul
if not errorlevel 1 (
  echo Le fichier .env contient encore des valeurs CHANGEZ_MOI. Modifiez-les avant de continuer.
  pause
  exit /b 1
)

if not exist backups mkdir backups
echo Construction des images et demarrage (premiere fois : 5 a 15 minutes)...
docker compose up -d --build
if errorlevel 1 (
  echo Echec du demarrage. Verifiez que Docker Desktop est lance.
  pause
  exit /b 1
)

echo.
echo DynSoft Pharma est demarre.
echo   Sur ce PC : http://localhost
echo   Depuis un autre poste du reseau : http://ADRESSE_IP_DE_CE_PC   (voir ipconfig)
echo.
echo Journal backend : docker compose logs -f backend
pause
