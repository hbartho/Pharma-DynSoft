@echo off
echo ========================================
echo Nettoyage et reinstallation complete
echo Frontend DynSoft Pharma
echo ========================================
echo.

echo ATTENTION: Cette operation va supprimer:
echo   - node_modules/
echo   - package-lock.json
echo   - yarn.lock
echo.
echo Et reinstaller toutes les dependances (3-5 min)
echo.
choice /C YN /M "Voulez-vous continuer"
if errorlevel 2 goto end
if errorlevel 1 goto clean

:clean
echo.
echo [1/4] Suppression de node_modules...
if exist node_modules (
    rmdir /s /q node_modules
    echo OK: node_modules supprime
) else (
    echo INFO: node_modules n'existe pas
)

echo.
echo [2/4] Suppression des fichiers de verrouillage...
if exist package-lock.json (
    del package-lock.json
    echo OK: package-lock.json supprime
)
if exist yarn.lock (
    del yarn.lock
    echo OK: yarn.lock supprime
)

echo.
echo [3/4] Nettoyage du cache npm...
npm cache clean --force

echo.
echo [4/4] Reinstallation des dependances...
echo Cela peut prendre 3-5 minutes...
echo.
npm install --legacy-peer-deps

if %errorlevel% neq 0 (
    echo.
    echo ERREUR: Reinstallation echouee
    echo.
    echo Verifiez:
    echo - Votre connexion internet
    echo - Que Node.js est bien installe
    echo.
    pause
    exit /b 1
)

echo.
echo Verification de react-scripts...
npm list react-scripts >nul 2>&1
if %errorlevel% neq 0 (
    echo Installation explicite de react-scripts...
    npm install react-scripts --save --legacy-peer-deps
)

echo.
echo ========================================
echo Reinstallation terminee avec succes!
echo ========================================
echo.
echo Vous pouvez maintenant lancer:
echo   start-frontend.bat
echo ou
echo   npm start
echo.

:end
pause
