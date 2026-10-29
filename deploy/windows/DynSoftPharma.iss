; Installateur Windows DynSoft Pharma (Inno Setup 6) - serveur local d'une pharmacie (Docker Desktop requis)
; Compilation : iscc DynSoftPharma.iss /DAppVersion=1.2.0   (ou via GitHub Actions : .github/workflows/build-installer.yml)

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "DynSoft Pharma"
#define AppPublisher "DynSoft"
#define AppURL "https://pharmacy-deploy.emergent.host"
#define RepoRoot "..\.."

[Setup]
AppId={{7E1C4C8B-2B6D-4F0A-9A5B-3C9D1E2F4A61}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
DefaultDirName=C:\DynSoftPharma
DisableDirPage=no
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=Setup-DynSoftPharma-{#AppVersion}
SetupIconFile=dynsoft.ico
UninstallDisplayIcon={app}\dynsoft.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=no
UsePreviousAppDir=yes

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Files]
Source: "{#RepoRoot}\deploy\local\*"; DestDir: "{app}\deploy\local"; Excludes: ".env,backups\*,*.pdf"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#RepoRoot}\deploy\local\GUIDE_INSTALLATION_LOCALE.pdf"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#RepoRoot}\backend\*"; DestDir: "{app}\backend"; Excludes: ".env,__pycache__,*.pyc,venv,.venv,tests,*.log"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#RepoRoot}\frontend\*"; DestDir: "{app}\frontend"; Excludes: ".env,node_modules,build,.cache"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "scripts\*.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "dynsoft.ico"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\deploy\local\backups"; Flags: uninsneveruninstall

[Icons]
Name: "{group}\Ouvrir {#AppName}"; Filename: "{app}\ouvrir.bat"; IconFilename: "{app}\dynsoft.ico"
Name: "{group}\Démarrer le serveur"; Filename: "{app}\demarrer.bat"; IconFilename: "{app}\dynsoft.ico"
Name: "{group}\Arrêter le serveur"; Filename: "{app}\arreter.bat"; IconFilename: "{app}\dynsoft.ico"
Name: "{group}\Sauvegarder la base"; Filename: "{app}\deploy\local\backup.bat"; WorkingDir: "{app}\deploy\local"
Name: "{group}\Importer depuis le cloud"; Filename: "{app}\deploy\local\importer-depuis-cloud.bat"; WorkingDir: "{app}\deploy\local"
Name: "{group}\Journal du serveur"; Filename: "{app}\journal.bat"
Name: "{group}\Guide d'installation (PDF)"; Filename: "{app}\GUIDE_INSTALLATION_LOCALE.pdf"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\ouvrir.bat"; IconFilename: "{app}\dynsoft.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le Bureau"; GroupDescription: "Raccourcis :"

[Run]
Filename: "{app}\post-install.bat"; StatusMsg: "Construction et démarrage des conteneurs Docker (5 à 15 min la première fois)..."; Flags: runhidden waituntilterminated; Check: DockerAvailable
Filename: "{app}\ouvrir.bat"; Description: "Ouvrir {#AppName} dans le navigateur"; Flags: postinstall nowait skipifsilent; Check: DockerAvailable

[UninstallRun]
Filename: "{app}\desinstaller.bat"; Parameters: "{code:UninstallMode}"; Flags: runhidden waituntilterminated; RunOnceId: "StopContainers"

[Code]
var
  PharmacyPage: TInputQueryWizardPage;
  AdminPage: TInputQueryWizardPage;
  CloudPage: TInputQueryWizardPage;
  ImportCheck: TNewCheckBox;
  PortPage: TInputQueryWizardPage;
  HasDocker: Boolean;
  EnvExists: Boolean;

function DockerAvailable: Boolean;
begin
  Result := HasDocker;
end;

function EnvPath: String;
begin
  Result := ExpandConstant('{app}\deploy\local\.env');
end;

function RandomToken(Len: Integer): String;
var
  Chars: String;
  I: Integer;
begin
  Chars := 'abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  Result := '';
  for I := 1 to Len do
    Result := Result + Chars[Random(Length(Chars)) + 1];
end;

function IsValidSlug(S: String): Boolean;
var
  I: Integer;
begin
  Result := (Length(S) >= 2) and (Length(S) <= 50);
  for I := 1 to Length(S) do
    if Pos(S[I], 'abcdefghijklmnopqrstuvwxyz0123456789_') = 0 then
      Result := False;
end;

function InitializeSetup: Boolean;
var
  ResultCode: Integer;
begin
  HasDocker := Exec(ExpandConstant('{cmd}'), '/c docker --version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
  Result := True;
  if not HasDocker then
    Result := MsgBox('Docker Desktop n''est pas installé (ou pas dans le PATH).' + #13#10 +
      'Téléchargez-le : https://www.docker.com/products/docker-desktop/' + #13#10#13#10 +
      'Les fichiers seront copiés, mais le serveur ne sera pas démarré. Continuer ?', mbConfirmation, MB_YESNO) = IDYES;
end;

procedure InitializeWizard;
begin
  PharmacyPage := CreateInputQueryPage(wpSelectDir, 'Pharmacie',
    'Identification de la pharmacie installée sur ce PC',
    'L''identifiant (slug) est celui attribué par DynSoft sur la plateforme cloud (ex. noormin). ' +
    'Il détermine le schéma de base de données dédié t_<slug>.');
  PharmacyPage.Add('Nom de la pharmacie :', False);
  PharmacyPage.Add('Identifiant (slug, minuscules sans espaces) :', False);

  AdminPage := CreateInputQueryPage(PharmacyPage.ID, 'Compte super-administrateur local',
    'Compte DynSoft de supervision du serveur local',
    'Ce compte permet d''accéder à la page /platform du serveur local. ' +
    'Les comptes des employés de la pharmacie sont récupérés depuis le cloud.');
  AdminPage.Add('Email :', False);
  AdminPage.Add('Mot de passe (8 caractères minimum) :', True);
  AdminPage.Values[0] := 'admin@dynsoft.local';

  CloudPage := CreateInputQueryPage(AdminPage.ID, 'Synchronisation cloud',
    'Liaison avec la plateforme DynSoft',
    'Le jeton est généré par DynSoft sur la plateforme cloud (/platform > pharmacie > jeton de synchronisation). ' +
    'Il sert à importer la pharmacie au premier démarrage et à remonter les ventes chaque nuit.');
  CloudPage.Add('URL du cloud :', False);
  CloudPage.Add('Jeton de synchronisation :', False);
  CloudPage.Add('Heure de la remontée nocturne (0-23) :', False);
  CloudPage.Values[0] := '{#AppURL}';
  CloudPage.Values[2] := '2';
  ImportCheck := TNewCheckBox.Create(CloudPage);
  ImportCheck.Parent := CloudPage.Surface;
  ImportCheck.Top := CloudPage.Edits[2].Top + CloudPage.Edits[2].Height + ScaleY(16);
  ImportCheck.Left := CloudPage.Edits[2].Left;
  ImportCheck.Width := CloudPage.SurfaceWidth;
  ImportCheck.Caption := 'Importer les données de la pharmacie depuis le cloud au premier démarrage';
  ImportCheck.Checked := True;

  PortPage := CreateInputQueryPage(CloudPage.ID, 'Accès réseau',
    'Port d''accès à l''application',
    'Laissez 80 pour ouvrir http://localhost (et http://ADRESSE_IP_DU_PC depuis les autres postes). ' +
    'Choisissez un autre port (ex. 8080) uniquement si le 80 est déjà utilisé.');
  PortPage.Add('Port :', False);
  PortPage.Values[0] := '80';
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  { Mise à jour : .env déjà présent dans le dossier choisi, on ne redemande pas la configuration }
  Result := EnvExists and ((PageID = PharmacyPage.ID) or (PageID = AdminPage.ID) or (PageID = CloudPage.ID) or (PageID = PortPage.ID));
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Port: Integer;
begin
  Result := True;
  if CurPageID = wpSelectDir then
    EnvExists := FileExists(EnvPath)
  else if CurPageID = PharmacyPage.ID then begin
    PharmacyPage.Values[1] := Lowercase(Trim(PharmacyPage.Values[1]));
    if Trim(PharmacyPage.Values[0]) = '' then begin MsgBox('Indiquez le nom de la pharmacie.', mbError, MB_OK); Result := False; end
    else if not IsValidSlug(PharmacyPage.Values[1]) then begin MsgBox('Identifiant invalide : 2 à 50 caractères parmi a-z, 0-9 et _ (ex. noormin).', mbError, MB_OK); Result := False; end;
  end
  else if CurPageID = AdminPage.ID then begin
    if Pos('@', AdminPage.Values[0]) = 0 then begin MsgBox('Email invalide.', mbError, MB_OK); Result := False; end
    else if Length(AdminPage.Values[1]) < 8 then begin MsgBox('Le mot de passe doit contenir au moins 8 caractères.', mbError, MB_OK); Result := False; end;
  end
  else if CurPageID = CloudPage.ID then begin
    if (Trim(CloudPage.Values[1]) = '') and ImportCheck.Checked then begin
      MsgBox('Le jeton de synchronisation est requis pour importer la pharmacie depuis le cloud. ' +
             'Collez-le, ou décochez l''import (installation vide).', mbError, MB_OK);
      Result := False;
    end
    else if (StrToIntDef(Trim(CloudPage.Values[2]), -1) < 0) or (StrToIntDef(Trim(CloudPage.Values[2]), -1) > 23) then begin
      MsgBox('Heure invalide (0 à 23).', mbError, MB_OK); Result := False;
    end;
  end
  else if CurPageID = PortPage.ID then begin
    Port := StrToIntDef(Trim(PortPage.Values[0]), 0);
    if (Port < 1) or (Port > 65535) then begin MsgBox('Port invalide.', mbError, MB_OK); Result := False; end;
  end;
end;

procedure WriteEnv;
var
  L: TStringList;
  Slug, Token, Import: String;
begin
  Slug := PharmacyPage.Values[1];
  Token := Trim(CloudPage.Values[1]);
  if ImportCheck.Checked and (Token <> '') then Import := '1' else Import := '0';
  L := TStringList.Create;
  try
    L.Add('POSTGRES_USER=dynpharma');
    L.Add('POSTGRES_PASSWORD=' + RandomToken(28));
    L.Add('POSTGRES_DB=dynpharma');
    L.Add('JWT_SECRET_KEY=' + RandomToken(64));
    L.Add('SUPERADMIN_EMAIL=' + Trim(AdminPage.Values[0]));
    L.Add('SUPERADMIN_PASSWORD=' + AdminPage.Values[1]);
    L.Add('APP_PORT=' + Trim(PortPage.Values[0]));
    L.Add('UVICORN_WORKERS=2');
    L.Add('TENANT_SCHEMA=t_' + Slug);
    L.Add('CLOUD_SYNC_URL=' + Trim(CloudPage.Values[0]));
    L.Add('CLOUD_SYNC_SLUG=' + Slug);
    L.Add('CLOUD_SYNC_TOKEN=' + Token);
    L.Add('CLOUD_SYNC_HOUR=' + Trim(CloudPage.Values[2]));
    L.Add('CLOUD_IMPORT_ON_START=' + Import);
    L.SaveToFile(EnvPath);
  finally
    L.Free;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and (not EnvExists) then
    WriteEnv;
end;

function UninstallMode(Param: String): String;
begin
  if MsgBox('Supprimer aussi la base de données de la pharmacie (toutes les ventes, stocks, clients) ?' + #13#10#13#10 +
            'Oui = suppression définitive des données.' + #13#10 +
            'Non = les conteneurs sont arrêtés mais les données sont conservées pour une réinstallation.', mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
    Result := 'purge'
  else
    Result := 'keep';
end;
