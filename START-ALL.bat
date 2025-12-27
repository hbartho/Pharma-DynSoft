@echo off
echo ========================================
echo DynSoft Pharma - Lancement Complet
echo ========================================
echo.

REM Vérifier les dossiers
if not exist backend\server.py (
    echo ERREUR: Dossier backend introuvable
    echo Lancez depuis: C:\dev\Pharma\projet\
    pause
    exit /b 1
)

if not exist frontend\package.json (
    echo ERREUR: Dossier frontend introuvable
    echo Lancez depuis: C:\dev\Pharma\projet\
    pause
    exit /b 1
)

REM Vérifier MongoDB
echo [1/3] Verification MongoDB...
sc query MongoDB | findstr "RUNNING" >nul
if %errorlevel% neq 0 (
    echo MongoDB n'est pas demarre
    echo.
    echo Voulez-vous le demarrer ? (Necessite admin)
    choice /C YN /M "Demarrer MongoDB"
    if errorlevel 2 goto skip_mongo
    if errorlevel 1 (
        powershell -Command "Start-Process cmd -ArgumentList '/c net start MongoDB && pause' -Verb RunAs"
        timeout /t 3 >nul
    )
    :skip_mongo
) else (
    echo OK: MongoDB demarre
)
echo.

REM Lancer Backend
echo [2/3] Lancement Backend...
start "DynSoft Pharma - Backend" cmd /k "cd /d %~dp0backend && start-backend.bat"
timeout /t 10 >nul

REM Lancer Frontend
echo [3/3] Lancement Frontend...
start "DynSoft Pharma - Frontend" cmd /k "cd /d %~dp0frontend && start-frontend.bat"

echo.
echo ========================================
echo Services lances !
echo ========================================
echo.
echo Deux fenetres ont ete ouvertes:
echo   1. Backend (port 8001)
echo   2. Frontend (port 3000)
echo.
echo Le navigateur s'ouvrira dans ~30 secondes
echo.
echo URLs:
echo   Application: http://localhost:3000
echo   API Docs: http://localhost:8001/docs
echo.
echo Identifiants:
echo   Email: demo@pharmaflow.com
echo   Mot de passe: demo123
echo.
pause
