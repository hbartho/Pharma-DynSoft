@echo off
echo ========================================
echo Configuration et demarrage automatique
echo Frontend DynSoft Pharma (avec npm)
echo ========================================
echo.

REM Étape 1 : Vérifier Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERREUR: Node.js n'est pas installe
    echo Telechargez-le depuis: https://nodejs.org/
    pause
    exit /b 1
)

echo [1/4] Node.js detecte
node --version
npm --version
echo.

REM Étape 2 : Nettoyer les anciennes installations (optionnel)
if exist node_modules (
    echo [2/4] Nettoyage des anciennes dependances...
    choice /C YN /M "Voulez-vous supprimer node_modules existant"
    if errorlevel 2 goto skip_clean
    if errorlevel 1 (
        echo Suppression de node_modules...
        rmdir /s /q node_modules 2>nul
        del package-lock.json 2>nul
        echo Nettoyage termine
    )
    :skip_clean
) else (
    echo [2/4] Aucun node_modules existant
)
echo.

REM Étape 3 : Vérifier/Créer le fichier .env
if not exist .env (
    echo [3/4] Creation du fichier .env...
    echo REACT_APP_BACKEND_URL=http://localhost:8001 > .env
    echo Fichier .env cree avec succes
    echo.
) else (
    echo [3/4] Fichier .env deja present
    type .env
    echo.
)

REM Étape 4 : Installer les dépendances avec npm
echo [4/4] Installation des dependances avec npm...
echo Cela peut prendre quelques minutes...
echo.

npm install --legacy-peer-deps

if %errorlevel% neq 0 (
    echo.
    echo ERREUR: Installation des dependances echouee
    echo.
    echo Essayez manuellement:
    echo   npm cache clean --force
    echo   npm install --legacy-peer-deps
    pause
    exit /b 1
)

echo.
echo ========================================
echo Installation terminee avec succes!
echo ========================================
echo.
echo Frontend sera accessible sur:
echo   - http://localhost:3000
echo.
echo Identifiants de demo:
echo   - Email: demo@pharmaflow.com
echo   - Mot de passe: demo123
echo.
echo REMARQUE:
echo   Assurez-vous que le backend est demarré sur le port 8001
echo   avant d'utiliser l'application.
echo.
echo Appuyez sur CTRL+C pour arreter le serveur
echo.
echo ========================================
echo Demarrage du serveur...
echo ========================================
echo.

REM Démarrer le serveur avec npm
npm start
