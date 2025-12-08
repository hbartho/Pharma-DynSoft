@echo off
echo ========================================
echo Demarrage Frontend DynSoft Pharma
echo ========================================
echo.

REM Vérifier Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERREUR: Node.js n'est pas installe
    pause
    exit /b 1
)

REM Créer .env si nécessaire
if not exist .env (
    echo Creation du fichier .env...
    echo REACT_APP_BACKEND_URL=http://localhost:8001 > .env
)

REM Vérifier si node_modules existe
if not exist node_modules (
    echo Installation des dependances...
    npm install --legacy-peer-deps
    if %errorlevel% neq 0 (
        echo ERREUR: Installation echouee
        pause
        exit /b 1
    )
)

echo.
echo Demarrage du serveur frontend...
echo Accessible sur: http://localhost:3000
echo.
echo Appuyez sur CTRL+C pour arreter
echo.

npm start
