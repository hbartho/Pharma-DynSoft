@echo off
echo ========================================
echo Installation Backend DynSoft Pharma
echo Pour Windows
echo ========================================
echo.

REM Vérifier si Python est installé
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERREUR: Python n'est pas installe ou pas dans le PATH
    echo Telechargez Python depuis: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] Creation de l'environnement virtuel...
python -m venv venv
if %errorlevel% neq 0 (
    echo ERREUR: Impossible de creer l'environnement virtuel
    pause
    exit /b 1
)

echo [2/4] Activation de l'environnement virtuel...
call venv\Scripts\activate.bat

echo [3/4] Installation des dependances...
echo Tentative avec requirements-windows.txt (sans jq)...
pip install -r requirements-windows.txt
if %errorlevel% neq 0 (
    echo.
    echo ERREUR: L'installation a echoue
    echo Essayez manuellement: pip install -r requirements-windows.txt
    pause
    exit /b 1
)

echo.
echo [4/4] Verification de l'installation...
python -c "import fastapi; import motor; import pymongo; print('OK: Tous les packages essentiels sont installes')"
if %errorlevel% neq 0 (
    echo ERREUR: Certains packages essentiels manquent
    pause
    exit /b 1
)

echo.
echo ========================================
echo Installation terminee avec succes!
echo ========================================
echo.
echo Pour demarrer le serveur backend:
echo   1. Assurez-vous que MongoDB est en cours d'execution
echo   2. Executez: start-server.bat
echo.
echo Ou manuellement:
echo   venv\Scripts\activate.bat
echo   uvicorn server:app --host 0.0.0.0 --port 8001 --reload
echo.
pause
