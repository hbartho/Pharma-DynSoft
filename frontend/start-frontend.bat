@echo off
echo ========================================
echo DynSoft Pharma - Frontend
echo ========================================
echo.

REM Vérifier Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERREUR: Node.js n'est pas installe
    echo Telechargez-le: https://nodejs.org/
    pause
    exit /b 1
)

echo Node.js: 
node --version
echo npm:
npm --version
echo.

REM Créer .env si nécessaire
if not exist .env (
    echo Creation du fichier .env...
    echo REACT_APP_BACKEND_URL=http://localhost:8001 > .env
    echo OK
    echo.
)

REM Vérifier node_modules
if not exist node_modules (
    echo Installation des dependances...
    echo Cela peut prendre 3-5 minutes...
    echo.
    npm install --legacy-peer-deps
    
    if %errorlevel% neq 0 (
        echo.
        echo ERREUR: Installation echouee
        pause
        exit /b 1
    )
    echo.
)

echo ========================================
echo Demarrage du serveur frontend...
echo ========================================
echo.
echo Accessible sur: http://localhost:3000
echo.
echo Identifiants:
echo   Email: demo@pharmaflow.com
echo   Mot de passe: demo123
echo.
echo CTRL+C pour arreter
echo.

REM Démarrer
npm start
