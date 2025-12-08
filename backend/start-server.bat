@echo off
echo ========================================
echo Demarrage du serveur Backend
echo DynSoft Pharma
echo ========================================
echo.

REM Vérifier si l'environnement virtuel existe
if not exist venv (
    echo ERREUR: L'environnement virtuel n'existe pas
    echo Executez d'abord: install-windows.bat
    pause
    exit /b 1
)

REM Activer l'environnement virtuel
call venv\Scripts\activate.bat

REM Vérifier si le fichier .env existe
if not exist .env (
    echo ATTENTION: Le fichier .env n'existe pas
    echo Creation d'un fichier .env par defaut...
    echo MONGO_URL=mongodb://localhost:27017/pharma_db > .env
    echo SECRET_KEY=your-secret-key-here-change-in-production >> .env
    echo.
    echo Fichier .env cree. Vous pouvez le modifier si necessaire.
    echo.
)

echo Demarrage du serveur sur http://localhost:8001
echo Documentation API: http://localhost:8001/docs
echo.
echo Appuyez sur CTRL+C pour arreter le serveur
echo.

REM Démarrer le serveur
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
