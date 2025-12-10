@echo off
echo ========================================
echo Reparation complete du frontend
echo DynSoft Pharma
echo ========================================
echo.

echo ATTENTION: Cette operation va:
echo - Supprimer node_modules/
echo - Supprimer package-lock.json et yarn.lock
echo - Nettoyer le cache npm
echo - Reinstaller toutes les dependances
echo.
echo Cela peut prendre 3-5 minutes.
echo.

choice /C YN /M "Voulez-vous continuer"
if errorlevel 2 goto end
if errorlevel 1 goto repair

:repair
echo.
echo [1/5] Suppression de node_modules...
if exist node_modules (
    rmdir /s /q node_modules
    echo OK: node_modules supprime
) else (
    echo INFO: node_modules n'existe pas
)

echo.
echo [2/5] Suppression des fichiers de verrouillage...
if exist package-lock.json (
    del package-lock.json
    echo OK: package-lock.json supprime
)
if exist yarn.lock (
    del yarn.lock
    echo OK: yarn.lock supprime
)

echo.
echo [3/5] Nettoyage du cache npm...
npm cache clean --force
if %errorlevel% neq 0 (
    echo ATTENTION: Erreur lors du nettoyage du cache
) else (
    echo OK: Cache nettoye
)

echo.
echo [4/5] Reinstallation complete des dependances...
echo Cela peut prendre 3-5 minutes. Patientez...
echo.
npm install --legacy-peer-deps

if %errorlevel% neq 0 (
    echo.
    echo ERREUR: L'installation a echoue
    echo.
    echo Solutions possibles:
    echo 1. Verifiez votre connexion internet
    echo 2. Desactivez temporairement votre antivirus
    echo 3. Essayez: npm config set registry https://registry.npmjs.org/
    echo 4. Relancez ce script
    pause
    exit /b 1
)

echo.
echo [5/5] Verification de react-scripts...
npm list react-scripts
if %errorlevel% neq 0 (
    echo.
    echo ATTENTION: react-scripts pourrait ne pas etre installe correctement
    echo Tentative d'installation explicite...
    npm install react-scripts --save --legacy-peer-deps
)

echo.
echo ========================================
echo Reparation terminee avec succes!
echo ========================================
echo.
echo Vous pouvez maintenant demarrer le frontend:
echo   npm start
echo.
echo Ou utilisez:
echo   start-frontend.bat
echo.

choice /C YN /M "Voulez-vous demarrer le frontend maintenant"
if errorlevel 2 goto end
if errorlevel 1 goto start

:start
echo.
echo Demarrage du frontend...
npm start
goto end

:end
echo.
pause
