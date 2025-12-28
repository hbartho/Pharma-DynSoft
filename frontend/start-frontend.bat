@echo off
chcp 65001 >nul
echo.
echo ============================================================
echo    DYNSOFT PHARMA - DEMARRAGE FRONTEND
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/3] Verification de Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo ERREUR: Node.js n'est pas installe ou pas dans le PATH
    echo Telechargez Node.js sur https://nodejs.org/
    pause
    exit /b 1
)
echo       Node.js OK

echo [2/3] Installation des dependances...
if not exist "node_modules" (
    echo       Installation en cours (peut prendre quelques minutes)...
    call yarn install
    if errorlevel 1 (
        echo       Tentative avec npm...
        call npm install
    )
) else (
    echo       node_modules existe deja
)
echo       Dependances OK

echo [3/3] Demarrage du serveur frontend...
echo.
echo ========================================
echo    SERVEUR FRONTEND DEMARRE
echo ========================================
echo.
echo    URL: http://localhost:3000
echo.
echo    Identifiants de connexion:
echo    ---------------------------
echo    Admin:      admin@pharmaflow.com / admin123
echo    Pharmacien: pharmacien@pharmaflow.com / pharma123
echo    Caissier:   caissier@pharmaflow.com / caisse123
echo.
echo    Appuyez sur CTRL+C pour arreter
echo ========================================
echo.

set BROWSER=none
yarn start
if errorlevel 1 (
    npm start
)

pause
