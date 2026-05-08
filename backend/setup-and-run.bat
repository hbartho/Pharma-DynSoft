@echo off
echo ========================================
echo Configuration et demarrage automatique
echo Backend DynSoft Pharma
echo ========================================
echo.

REM Étape 1 : Vérifier Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERREUR: Python n'est pas installe
    pause
    exit /b 1
)

REM Étape 2 : Créer l'environnement virtuel s'il n'existe pas
if not exist venv (
    echo [1/5] Creation de l'environnement virtuel...
    python -m venv venv
) else (
    echo [1/5] Environnement virtuel deja present
)

REM Étape 3 : Activer l'environnement virtuel
echo [2/5] Activation de l'environnement virtuel...
call venv\Scripts\activate.bat

REM Étape 4 : Vérifier quelle version de Python est utilisée
echo [3/5] Verification de l'environnement...
where python
echo.

REM Étape 5 : Installer/Mettre à jour les dépendances
echo [4/5] Installation des dependances...
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

REM Étape 6 : Créer le fichier .env s'il n'existe pas
if not exist .env (
    echo [5/5] Creation du fichier .env...
    echo MONGO_URL=mongodb://localhost:27017/pharma_db > .env
    echo SECRET_KEY=dev-secret-key-change-this-in-production >> .env
    echo DB_NAME=pharma_db >> .env
    echo Fichier .env cree avec succes
    echo.
) else (
    echo [5/5] Fichier .env deja present
)

REM Afficher les informations
echo.
echo ========================================
echo Configuration terminee avec succes!
echo ========================================
echo.
echo Backend sera accessible sur:
echo   - http://localhost:8001
echo   - Documentation API: http://localhost:8001/docs
echo.
echo Appuyez sur CTRL+C pour arreter le serveur
echo.
echo ========================================
echo Demarrage du serveur...
echo ========================================
echo.

REM Démarrer le serveur
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
