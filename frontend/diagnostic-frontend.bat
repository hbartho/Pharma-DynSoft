@echo off
echo ========================================
echo Diagnostic Frontend DynSoft Pharma
echo ========================================
echo.

echo [1/5] Verification de Node.js...
node --version
if %errorlevel% neq 0 (
    echo ERREUR: Node.js non installe
    pause
    exit /b 1
)
echo OK
echo.

echo [2/5] Verification de npm...
npm --version
if %errorlevel% neq 0 (
    echo ERREUR: npm non installe
    pause
    exit /b 1
)
echo OK
echo.

echo [3/5] Verification du dossier...
if not exist package.json (
    echo ERREUR: package.json introuvable
    echo Etes-vous dans le bon dossier ?
    pause
    exit /b 1
)
echo OK
echo.

echo [4/5] Verification de node_modules...
if exist node_modules (
    echo OK: node_modules existe
) else (
    echo ATTENTION: node_modules n'existe pas
    echo Les dependances doivent etre installees
)
echo.

echo [5/5] Verification du fichier .env...
if exist .env (
    echo OK: .env existe
    echo Contenu:
    type .env
) else (
    echo ATTENTION: .env n'existe pas
    echo Creation automatique...
    echo REACT_APP_BACKEND_URL=http://localhost:8001 > .env
    echo OK: .env cree
)
echo.

echo ========================================
echo Diagnostic termine
echo ========================================
echo.
echo Pour demarrer le frontend:
echo   start-frontend-simple.bat
echo.
pause
