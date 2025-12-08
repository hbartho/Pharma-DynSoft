@echo off
echo ========================================
echo Nettoyage et reinstallation complete
echo Frontend DynSoft Pharma
echo ========================================
echo.

echo ATTENTION: Cette operation va supprimer:
echo   - node_modules/
echo   - package-lock.json
echo.
choice /C YN /M "Voulez-vous continuer"
if errorlevel 2 goto end
if errorlevel 1 goto clean

:clean
echo.
echo [1/3] Suppression de node_modules...
if exist node_modules (
    rmdir /s /q node_modules
    echo node_modules supprime
) else (
    echo node_modules n'existe pas
)

echo.
echo [2/3] Suppression de package-lock.json...
if exist package-lock.json (
    del package-lock.json
    echo package-lock.json supprime
) else (
    echo package-lock.json n'existe pas
)

echo.
echo [3/3] Reinstallation des dependances...
npm cache clean --force
npm install --legacy-peer-deps

if %errorlevel% neq 0 (
    echo.
    echo ERREUR: Reinstallation echouee
    pause
    exit /b 1
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
