@echo off
echo ========================================
echo DynSoft Pharma - Backend
echo ========================================
echo.

REM Vérifier Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERREUR: Python n'est pas installe
    echo Telechargez-le: https://python.org/
    pause
    exit /b 1
)

echo Python:
python --version
echo.

REM Vérifier venv
if not exist venv (
    echo Creation environnement virtuel...
    python -m venv venv
    echo OK
    echo.
)

REM Activer venv
call venv\Scripts\activate.bat

REM Vérifier dépendances
python -c "import fastapi, uvicorn" 2>nul
if %errorlevel% neq 0 (
    echo Installation des dependances...
    pip install --upgrade pip --quiet
    pip install -r requirements-windows.txt
    echo OK
    echo.
)

REM Vérifier .env
if not exist .env (
    echo Creation du fichier .env...
    (
        echo MONGO_URL=mongodb://localhost:27017/pharma_db
        echo SECRET_KEY=dev-secret-key-change-in-production
        echo DB_NAME=pharma_db
    ) > .env
    echo OK
    echo.
)

echo ========================================
echo Demarrage du serveur backend...
echo ========================================
echo.
echo Accessible sur: http://localhost:8001
echo Documentation: http://localhost:8001/docs
echo.
echo IMPORTANT: MongoDB doit etre demarre
echo   (CMD admin: net start MongoDB)
echo.
echo CTRL+C pour arreter
echo.

REM Démarrer
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
