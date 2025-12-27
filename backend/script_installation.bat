@echo off
echo ========================================
echo Demarrage Backend DynSoft Pharma
echo ========================================
echo.

REM Vérifier si on est dans le bon dossier
if not exist server.py (
    echo ERREUR: Lancez ce script depuis le dossier backend
    echo Usage: cd C:\dev\Pharma\projet\backend
    echo        script_installation.bat
    pause
    exit /b 1
)

REM Vérifier si l'environnement virtuel existe
if not exist venv (
    echo [1/4] Creation de l'environnement virtuel...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ERREUR: Impossible de creer l'environnement virtuel
        pause
        exit /b 1
    )
    echo OK: Environnement virtuel cree
) else (
    echo [1/4] Environnement virtuel deja present
)

REM Activer l'environnement virtuel
echo [2/4] Activation de l'environnement virtuel...
call venv\Scripts\activate.bat

REM Vérifier si les dépendances sont installées
echo [3/4] Verification des dependances...
python -c "import fastapi" 2>nul
if %errorlevel% neq 0 (
    echo Installation des dependances necessaires...
    pip install --upgrade pip --quiet
    if exist requirements-windows.txt (
        pip install -r requirements-windows.txt
    ) else (
        pip install -r requirements.txt
    )
    if %errorlevel% neq 0 (
        echo ERREUR: Installation des dependances echouee
        pause
        exit /b 1
    )
)
echo OK: Dependances installees

REM Vérifier le fichier .env
if not exist .env (
    echo [4/4] Creation du fichier .env...
    (
        echo MONGO_URL=mongodb://localhost:27017/pharma_db
        echo SECRET_KEY=dev-secret-key-change-this-in-production
        echo DB_NAME=pharma_db
    ) > .env
    echo OK: Fichier .env cree
) else (
    echo [4/4] Fichier .env deja present
)

echo.
echo ========================================
echo Configuration terminee
echo ========================================
echo.
echo Backend sera accessible sur:
echo   - API: http://localhost:8001
echo   - Documentation: http://localhost:8001/docs
echo.
echo IMPORTANT:
echo   Assurez-vous que MongoDB est demarre
echo   (Commande admin: net start MongoDB)
echo.
echo Appuyez sur CTRL+C pour arreter le serveur
echo.
echo ========================================
echo Demarrage du serveur backend...
echo ========================================
echo.

REM Démarrer le serveur
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
