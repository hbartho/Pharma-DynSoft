@echo off
chcp 65001 >nul
echo.
echo ============================================================
echo    DYNSOFT PHARMA - DEMARRAGE BACKEND
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/5] Verification de Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERREUR: Python n'est pas installe ou pas dans le PATH
    echo Telechargez Python sur https://www.python.org/downloads/
    pause
    exit /b 1
)
echo       Python OK

echo [2/5] Verification/Activation de l'environnement virtuel...
if exist "venv\Scripts\activate.bat" (
    echo       Activation du venv existant...
    call venv\Scripts\activate.bat
) else (
    echo       Creation du venv...
    python -m venv venv
    call venv\Scripts\activate.bat
)
echo       Environnement virtuel OK

echo [3/5] Installation des dependances...
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo ERREUR: Impossible d'installer les dependances
    pause
    exit /b 1
)
echo       Dependances OK

echo [4/5] Creation des utilisateurs de demo...
python create_correct_user.py
echo.

echo [5/5] Demarrage du serveur backend...
echo.
echo ========================================
echo    SERVEUR BACKEND DEMARRE
echo ========================================
echo.
echo    URL: http://localhost:8001
echo    API Docs: http://localhost:8001/docs
echo.
echo    IMPORTANT: MongoDB doit etre demarre!
echo    (CMD admin: net start MongoDB)
echo.
echo    Appuyez sur CTRL+C pour arreter
echo ========================================
echo.

python -m uvicorn server:app --reload --host 0.0.0.0 --port 8001

pause
