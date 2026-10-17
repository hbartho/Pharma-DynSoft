@echo off
REM Copie les donnees de la pharmacie depuis Supabase (cloud) vers la base locale.
REM Necessite Internet pendant l'export. L'URL n'est jamais enregistree sur le disque.
cd /d "%~dp0"
for /f "tokens=1,* delims==" %%a in ('findstr /R "^POSTGRES_USER= ^POSTGRES_DB=" .env') do set %%a=%%b
if not exist backups mkdir backups

echo Collez l'URL de connexion Supabase (Session pooler, port 5432).
echo Format : postgresql://postgres.xxxx:MOT_DE_PASSE@aws-0-xx.pooler.supabase.com:5432/postgres
echo Si le mot de passe contient # @ / : ou %%, encodez-le (ex. # devient %%23).
set /p SRC_URL=URL Supabase :
if "%SRC_URL%"=="" exit /b 1

for /f "tokens=1-5 delims=/:. " %%d in ("%date% %time%") do set STAMP=%%f%%e%%d_%%g%%h
set FILE=supabase_%STAMP%.dump
echo Export depuis Supabase (schema public + schemas t_* des pharmacies)...
docker compose exec -T -e SRC_URL="%SRC_URL%" db sh -c "pg_dump \"$SRC_URL\" --format=custom --no-owner --no-privileges --schema=public --schema=\"t_*\" -f /backups/%FILE%"
if errorlevel 1 (
  echo Echec de l'export. Verifiez l'URL et la connexion Internet.
  pause
  exit /b 1
)
echo Export termine : backups\%FILE%

echo ATTENTION : les donnees actuelles de la base locale seront remplacees.
set /p OK=Importer maintenant dans la base locale ? (oui/non) :
if /i not "%OK%"=="oui" (
  echo Import annule. Vous pourrez le faire plus tard avec : restore.bat backups\%FILE%
  pause
  exit /b 0
)

docker compose stop backend
docker compose exec -T db pg_restore -U %POSTGRES_USER% -d %POSTGRES_DB% --clean --if-exists --no-owner --no-privileges /backups/%FILE%
docker compose start backend
echo Migration terminee. Connectez-vous avec vos identifiants habituels.
pause
