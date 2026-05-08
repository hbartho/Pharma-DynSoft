@echo off
echo ========================================
echo Creation de l'utilisateur de demo
echo DynSoft Pharma
echo ========================================
echo.

REM Vérifier si on est dans le bon dossier
if not exist server.py (
    echo ERREUR: Lancez ce script depuis le dossier backend
    pause
    exit /b 1
)

REM Vérifier si l'environnement virtuel existe
if not exist venv (
    echo ERREUR: L'environnement virtuel n'existe pas
    echo Executez d'abord: python -m venv venv
    pause
    exit /b 1
)

REM Activer l'environnement virtuel
call venv\Scripts\activate.bat

REM Vérifier si le script Python existe
if not exist create_demo_user.py (
    echo ERREUR: Le fichier create_demo_user.py n'existe pas
    pause
    exit /b 1
)

REM Exécuter le script Python
python create_demo_user.py

pause
