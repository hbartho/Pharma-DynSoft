# 🪟 Guide d'Installation Rapide - Windows

## Installation Automatique (Recommandé)

### Backend

1. **Ouvrir le terminal** dans le dossier `backend`
   - Clic droit sur le dossier → "Ouvrir dans le Terminal" 
   - Ou CMD : `cd C:\chemin\vers\app\backend`

2. **Lancer l'installation automatique** :
   ```cmd
   install-windows.bat
   ```

3. **Démarrer le serveur** :
   ```cmd
   start-server.bat
   ```

✅ Le backend devrait maintenant tourner sur : http://localhost:8001

---

### Frontend

1. **Ouvrir un nouveau terminal** dans le dossier `frontend`
   ```cmd
   cd C:\chemin\vers\app\frontend
   ```

2. **Installer les dépendances** :
   ```cmd
   npm install
   ```
   ou
   ```cmd
   yarn install
   ```

3. **Démarrer le serveur** :
   ```cmd
   npm start
   ```
   ou
   ```cmd
   yarn start
   ```

✅ Le frontend devrait s'ouvrir automatiquement sur : http://localhost:3000

---

## ⚠️ Problèmes Courants sur Windows

### 1. Erreur "jq" lors de l'installation

**Erreur :**
```
ERROR: Failed building wheel for jq
```

**Solution :** Le script `install-windows.bat` utilise automatiquement `requirements-windows.txt` qui n'inclut pas `jq`.

Si vous installez manuellement :
```cmd
pip install -r requirements-windows.txt
```

---

### 2. MongoDB n'est pas démarré

**Erreur :**
```
pymongo.errors.ServerSelectionTimeoutError
```

**Solution :**
```cmd
net start MongoDB
```

Ou démarrez MongoDB manuellement depuis les Services Windows (Win+R → `services.msc` → cherchez "MongoDB")

---

### 3. Port déjà utilisé

**Erreur :**
```
Address already in use
```

**Solution pour le port 8001 (backend) :**
```cmd
netstat -ano | findstr :8001
taskkill /PID [NUMERO_PID] /F
```

**Solution pour le port 3000 (frontend) :**
```cmd
netstat -ano | findstr :3000
taskkill /PID [NUMERO_PID] /F
```

---

### 4. Erreur PowerShell "scripts désactivés"

**Erreur :**
```
running scripts is disabled on this system
```

**Solution :**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Puis relancez l'installation.

---

### 5. Python n'est pas dans le PATH

**Erreur :**
```
'python' is not recognized as an internal or external command
```

**Solution :**
1. Réinstallez Python depuis : https://www.python.org/downloads/
2. ✅ Cochez "Add Python to PATH" lors de l'installation
3. Redémarrez votre terminal

---

## 📝 Commandes Manuelles (Si les scripts ne fonctionnent pas)

### Backend

```cmd
cd backend

REM Créer l'environnement virtuel
python -m venv venv

REM Activer l'environnement virtuel
venv\Scripts\activate.bat

REM Installer les dépendances
pip install -r requirements-windows.txt

REM Démarrer le serveur
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend

```cmd
cd frontend

REM Installer les dépendances
npm install

REM Démarrer le serveur
npm start
```

---

## 🎯 Vérification Rapide

**Backend fonctionne ?**
- Ouvrez : http://localhost:8001/docs
- Vous devriez voir la documentation Swagger

**Frontend fonctionne ?**
- Ouvrez : http://localhost:3000
- Vous devriez voir la page de connexion

**Identifiants de test :**
- Email : `demo@pharmaflow.com`
- Mot de passe : `demo123`

---

## 💡 Astuces Windows

### Désactiver l'antivirus temporairement
Certains antivirus bloquent l'installation de packages Python. Désactivez-le temporairement si vous avez des problèmes.

### Utiliser Git Bash
Si vous préférez un terminal Linux-like sur Windows, installez Git Bash : https://git-scm.com/downloads

### Utiliser Windows Terminal
Pour une meilleure expérience, installez Windows Terminal depuis le Microsoft Store.

---

## 📧 Besoin d'aide ?

Consultez le guide complet : `GUIDE_INSTALLATION_LOCAL.md`

---

**Version :** DynSoft Pharma v1.0  
**Plateforme :** Windows 10/11  
**Date :** Décembre 2024
