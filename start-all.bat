@echo off
echo ========================================
echo Lancement complet DynSoft Pharma
echo Backend + Frontend
echo ========================================
echo.

REM Vérifier les dossiers
if not exist "backend\server.py" (
    echo ERREUR: Dossier backend introuvable
    echo Lancez ce script depuis: C:\dev\Pharma\projet\
    pause
    exit /b 1
)

if not exist "frontend\package.json" (
    echo ERREUR: Dossier frontend introuvable
    echo Lancez ce script depuis: C:\dev\Pharma\projet\
    pause
    exit /b 1
)

REM Vérifier MongoDB
echo [1/3] Verification de MongoDB...
sc query MongoDB | findstr "RUNNING" >nul
if %errorlevel% neq 0 (
    echo.
    echo ATTENTION: MongoDB ne semble pas demarrer
    echo.
    echo Voulez-vous le demarrer maintenant ?
    echo (Necessite des droits administrateur)
    echo.
    choice /C YN /M "Demarrer MongoDB"
    if errorlevel 2 goto skip_mongo
    if errorlevel 1 (
        echo Demarrage de MongoDB...
        powershell -Command "Start-Process cmd -ArgumentList '/c net start MongoDB' -Verb RunAs"
        timeout /t 3 >nul
    )
    :skip_mongo
) else (
    echo OK: MongoDB est demarrer
)

echo.
echo [2/3] Lancement du Backend...
echo Ouverture d'une nouvelle fenetre pour le backend...
start "DynSoft Pharma - Backend" cmd /k "cd /d %~dp0backend && script_installation.bat"

REM Attendre que le backend démarre
echo Attente du demarrage du backend (10 secondes)...
timeout /t 10 >nul

echo.
echo [3/3] Lancement du Frontend...
echo Ouverture d'une nouvelle fenetre pour le frontend...
start "DynSoft Pharma - Frontend" cmd /k "cd /d %~dp0frontend && setup-and-run-frontend.bat"

echo.
echo ========================================
echo Services lances !
echo ========================================
echo.
echo Deux fenetres ont ete ouvertes:
echo   1. Backend (port 8001)
echo   2. Frontend (port 3000)
echo.
echo Le navigateur s'ouvrira automatiquement dans ~30 secondes
echo.
echo URLs:
echo   - Application: http://localhost:3000
echo   - API Docs: http://localhost:8001/docs
echo.
echo Identifiants:
echo   - Email: demo@pharmaflow.com
echo   - Mot de passe: demo123
echo.
echo Pour arreter les services:
echo   - Fermez les deux fenetres de commande
echo   - Ou appuyez sur CTRL+C dans chaque fenetre
echo.
pause
