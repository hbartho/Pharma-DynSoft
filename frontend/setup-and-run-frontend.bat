@echo off
echo ========================================
echo Configuration et demarrage automatique
echo Frontend DynSoft Pharma
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
echo.

REM Étape 2 : Vérifier si yarn est installé
yarn --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [2/4] Yarn n'est pas installe. Installation en cours...
    npm install -g yarn
    if %errorlevel% neq 0 (
        echo ATTENTION: Installation de Yarn echouee
        echo On utilisera npm avec --legacy-peer-deps
        set USE_NPM=1
    ) else (
        echo Yarn installe avec succes
        set USE_NPM=0
    )
) else (
    echo [2/4] Yarn detecte
    yarn --version
    set USE_NPM=0
)
echo.

REM Étape 3 : Vérifier/Créer le fichier .env
if not exist .env (
    echo [3/4] Creation du fichier .env...
    echo REACT_APP_BACKEND_URL=http://localhost:8001 > .env
    echo Fichier .env cree avec succes
) else (
    echo [3/4] Fichier .env deja present
    type .env
)
echo.

REM Étape 4 : Installer les dépendances
echo [4/4] Installation des dependances...
echo Cela peut prendre quelques minutes...
echo.

if "%USE_NPM%"=="1" (
    echo Utilisation de npm avec --legacy-peer-deps...
    npm install --legacy-peer-deps
) else (
    echo Utilisation de Yarn...
    yarn install
)

if %errorlevel% neq 0 (
    echo.
    echo ERREUR: Installation des dependances echouee
    echo.
    echo Essayez manuellement:
    echo   yarn install
    echo ou
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
echo Appuyez sur CTRL+C pour arreter le serveur
echo.
echo ========================================
echo Demarrage du serveur...
echo ========================================
echo.

REM Démarrer le serveur
if "%USE_NPM%"=="1" (
    npm start
) else (
    yarn start
)
