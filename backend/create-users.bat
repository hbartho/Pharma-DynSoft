@echo off
chcp 65001 >nul
echo.
echo ============================================================
echo    CRÉATION DES UTILISATEURS DYNSOFT PHARMA
echo ============================================================
echo.
echo Ce script va créer les utilisateurs de démonstration:
echo    - Admin: admin@pharmaflow.com / admin123
echo    - Pharmacien: pharmacien@pharmaflow.com / pharma123
echo    - Caissier: caissier@pharmaflow.com / caisse123
echo.
pause

cd /d "%~dp0"
python create_correct_user.py

echo.
pause
