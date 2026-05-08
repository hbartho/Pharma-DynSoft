@echo off
echo ========================================
echo Demarrage Frontend DynSoft Pharma
echo ========================================
echo.

REM Vérifier Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERREUR: Node.js n'est pas installe
    echo Telechargez-le depuis: https://nodejs.org/
    pause
    exit /b 1
)

echo [1/3] Node.js detecte
node --version
npm --version
echo.

REM Créer le fichier .env si nécessaire
if not exist .env (
    echo [2/3] Creation du fichier .env...
    echo REACT_APP_BACKEND_URL=http://localhost:8001 > .env
    echo OK: Fichier .env cree
) else (
    echo [2/3] Fichier .env deja present
)
echo.

REM Vérifier si node_modules existe
if not exist node_modules (
    echo [3/3] Installation des dependances...
    echo Cela peut prendre 3-5 minutes. Patientez...
    echo.
    npm install --legacy-peer-deps
    
    if %errorlevel% neq 0 (
        echo.
        echo ERREUR: Installation echouee
        echo.
        pause
        exit /b 1
    )
) else (
    echo [3/3] Dependances deja installees
)

echo.
echo ========================================
echo Configuration terminee
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
echo   Assurez-vous que le backend est demarre sur port 8001
echo.
echo Appuyez sur CTRL+C pour arreter le serveur
echo.
echo ========================================
echo Demarrage du serveur frontend...
echo ========================================
echo.

REM Démarrer le serveur
npm start

REM Si npm start échoue, garder la fenêtre ouverte
if %errorlevel% neq 0 (
    echo.
    echo ERREUR: Le serveur n'a pas demarre correctement
    pause
)
