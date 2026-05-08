# 🪟 Guide Complet d'Installation - Windows
## DynSoft Pharma - Application de Gestion Pharmaceutique

---

## 📋 Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Prérequis](#prérequis)
3. [Installation Backend](#installation-backend)
4. [Installation Frontend](#installation-frontend)
5. [Scripts automatiques](#scripts-automatiques)
6. [Tests de l'application](#tests-de-lapplication)
7. [Résolution de problèmes](#résolution-de-problèmes)

---

## 🎯 Vue d'ensemble

**DynSoft Pharma** est une application complète de gestion de pharmacie avec :
- **Backend** : Python FastAPI + MongoDB (port 8001)
- **Frontend** : React + Tailwind CSS (port 3000)

**Architecture :**
```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   Frontend      │  HTTP   │    Backend      │  DB     │    MongoDB      │
│   React         │ ──────> │    FastAPI      │ ──────> │   Database      │
│   Port 3000     │         │    Port 8001    │         │   Port 27017    │
└─────────────────┘         └─────────────────┘         └─────────────────┘
```

---

## 📦 Prérequis

### Logiciels requis

| Logiciel | Version minimum | Téléchargement |
|----------|----------------|----------------|
| Python | 3.8+ | https://www.python.org/downloads/ |
| Node.js | 14+ | https://nodejs.org/ |
| MongoDB | 4.0+ | https://www.mongodb.com/try/download/community |

### Vérification

Ouvrez **CMD** et vérifiez :

```cmd
python --version
node --version
npm --version
mongod --version
```

---

## 🔧 Installation Backend

### Méthode Automatique (Recommandée)

1. **Copiez les fichiers** de `/app/backend/` vers `C:\dev\Pharma\projet\backend\`

2. **Créez les fichiers nécessaires** :

**requirements-windows.txt** (liste des dépendances Python)
**setup-and-run.bat** (script d'installation automatique)

3. **Double-cliquez** sur `setup-and-run.bat`

Ou en ligne de commande :

```cmd
cd C:\dev\Pharma\projet\backend
setup-and-run.bat
```

### Méthode Manuelle

```cmd
cd C:\dev\Pharma\projet\backend

REM 1. Créer l'environnement virtuel
python -m venv venv

REM 2. Activer l'environnement virtuel
venv\Scripts\activate.bat

REM 3. Installer les dépendances
pip install -r requirements-windows.txt

REM 4. Créer le fichier .env
(
echo MONGO_URL=mongodb://localhost:27017/pharma_db
echo SECRET_KEY=dev-secret-key-change-this-in-production
echo DB_NAME=pharma_db
) > .env

REM 5. Démarrer le serveur
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### Vérification Backend

✅ Ouvrez : **http://localhost:8001/docs**

Vous devriez voir la documentation Swagger de l'API.

---

## ⚛️ Installation Frontend

### Scripts Disponibles

Le frontend dispose de **3 scripts** npm :

| Script | Usage | Commande |
|--------|-------|----------|
| `setup-and-run-frontend.bat` | Installation complète + démarrage | Double-clic ou `setup-and-run-frontend.bat` |
| `start-frontend.bat` | Démarrage rapide | Double-clic ou `start-frontend.bat` |
| `clean-install.bat` | Nettoyage + réinstallation | Double-clic ou `clean-install.bat` |

### Première Installation

1. **Copiez les fichiers** de `/app/frontend/` vers `C:\dev\Pharma\projet\frontend\`

2. **Double-cliquez** sur `setup-and-run-frontend.bat`

Ou en ligne de commande :

```cmd
cd C:\dev\Pharma\projet\frontend
setup-and-run-frontend.bat
```

Le script va :
- ✅ Vérifier Node.js
- ✅ Créer le fichier `.env`
- ✅ Installer les dépendances avec npm
- ✅ Démarrer le serveur de développement

### Méthode Manuelle

```cmd
cd C:\dev\Pharma\projet\frontend

REM 1. Créer le fichier .env
echo REACT_APP_BACKEND_URL=http://localhost:8001 > .env

REM 2. Installer les dépendances
npm install --legacy-peer-deps

REM 3. Démarrer le serveur
npm start
```

### Vérification Frontend

✅ Le navigateur devrait s'ouvrir automatiquement sur : **http://localhost:3000**

Vous devriez voir la page de connexion de DynSoft Pharma.

---

## 🚀 Scripts Automatiques

### Backend : `setup-and-run.bat`

**Ce qu'il fait :**
1. Vérifie Python
2. Crée l'environnement virtuel
3. Installe les dépendances
4. Crée le fichier `.env`
5. Démarre le serveur

**Usage :**
```cmd
cd C:\dev\Pharma\projet\backend
setup-and-run.bat
```

---

### Frontend : 3 Scripts NPM

#### 1. `setup-and-run-frontend.bat` - Installation Complète

**Première utilisation uniquement**

**Ce qu'il fait :**
- Vérifie Node.js et npm
- Propose de nettoyer l'ancienne installation
- Crée le fichier `.env`
- Installe les dépendances avec `--legacy-peer-deps`
- Démarre le serveur

**Usage :**
```cmd
cd C:\dev\Pharma\projet\frontend
setup-and-run-frontend.bat
```

---

#### 2. `start-frontend.bat` - Démarrage Rapide

**Usage quotidien**

**Ce qu'il fait :**
- Vérifie Node.js
- Crée `.env` si nécessaire
- Installe les dépendances si manquantes
- Démarre le serveur

**Usage :**
```cmd
cd C:\dev\Pharma\projet\frontend
start-frontend.bat
```

---

#### 3. `clean-install.bat` - Nettoyage Complet

**En cas de problèmes**

**Ce qu'il fait :**
- Supprime `node_modules/`
- Supprime `package-lock.json`
- Nettoie le cache npm
- Réinstalle toutes les dépendances

**Usage :**
```cmd
cd C:\dev\Pharma\projet\frontend
clean-install.bat
```

---

## 🧪 Tests de l'application

### Démarrage Complet

**Terminal 1 - Backend :**
```cmd
cd C:\dev\Pharma\projet\backend
setup-and-run.bat
```

**Terminal 2 - Frontend :**
```cmd
cd C:\dev\Pharma\projet\frontend
start-frontend.bat
```

### Connexion

1. Ouvrez : **http://localhost:3000**
2. **Identifiants de test :**
   - Email : `demo@pharmaflow.com`
   - Mot de passe : `demo123`

### Fonctionnalités à tester

#### ✅ Gestion des Produits

**Test de création :**
1. Cliquez sur "Ajouter un produit"
2. Remplissez le formulaire
3. Cliquez sur "Ajouter"
4. ✅ Le produit apparaît dans la liste

**Test de modification :**
1. Cliquez sur "Éditer" sur un produit
2. Modifiez les informations
3. Cliquez sur "Mettre à jour"
4. ✅ Les modifications sont enregistrées

**Test de suppression avec dialogue de confirmation :**
1. Cliquez sur l'icône de suppression (poubelle rouge)
2. ✅ Un dialogue de confirmation apparaît
3. Vous voyez le nom du produit
4. Options disponibles :
   - "Annuler" : ferme le dialogue sans supprimer
   - "Supprimer" : supprime définitivement
5. ✅ La liste se rafraîchit automatiquement

#### ✅ Gestion des Prescriptions

- Ajouter une prescription
- Modifier le statut (En attente / Remplie)
- Supprimer avec dialogue de confirmation

#### ✅ Autres Pages

- Dashboard : Visualiser les statistiques
- Clients : Gérer les clients
- Ventes : Enregistrer des ventes
- Fournisseurs : Gérer les fournisseurs
- Rapports : Consulter les rapports

---

## 🐛 Résolution de problèmes

### Problème 1 : Erreur "No module named uvicorn"

**Cause :** L'environnement virtuel n'est pas activé

**Solution :**
```cmd
cd C:\dev\Pharma\projet\backend
venv\Scripts\activate.bat
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

---

### Problème 2 : Erreur "KeyError: 'DB_NAME'"

**Cause :** Le fichier `.env` est incomplet

**Solution :**
```cmd
cd C:\dev\Pharma\projet\backend
(
echo MONGO_URL=mongodb://localhost:27017/pharma_db
echo SECRET_KEY=dev-secret-key-change-this-in-production
echo DB_NAME=pharma_db
) > .env
```

---

### Problème 3 : Erreur "ERESOLVE unable to resolve" (date-fns)

**Cause :** Conflit de versions npm

**Solution 1 (Rapide) :**
```cmd
cd C:\dev\Pharma\projet\frontend
npm install --legacy-peer-deps
```

**Solution 2 (Nettoyage complet) :**
```cmd
cd C:\dev\Pharma\projet\frontend
clean-install.bat
```

---

### Problème 4 : MongoDB ne se connecte pas

**Erreur :**
```
pymongo.errors.ServerSelectionTimeoutError
```

**Solution :**
```cmd
REM Démarrer MongoDB
net start MongoDB

REM Ou vérifier le statut
sc query MongoDB
```

---

### Problème 5 : Port déjà utilisé

**Port 8001 (Backend) :**
```cmd
netstat -ano | findstr :8001
taskkill /PID [NUMERO_PID] /F
```

**Port 3000 (Frontend) :**
```cmd
netstat -ano | findstr :3000
taskkill /PID [NUMERO_PID] /F
```

Ou démarrer sur un autre port :
```cmd
set PORT=3001
npm start
```

---

### Problème 6 : Scripts PowerShell désactivés

**Erreur :**
```
running scripts is disabled on this system
```

**Solution :**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 📁 Structure des Fichiers

```
C:\dev\Pharma\projet\
│
├── backend\
│   ├── server.py                        # Application FastAPI
│   ├── requirements-windows.txt         # Dépendances Python (sans jq)
│   ├── .env                            # Variables d'environnement
│   ├── setup-and-run.bat               # Script installation + démarrage
│   └── venv\                           # Environnement virtuel Python
│
└── frontend\
    ├── public\
    ├── src\
    │   ├── components\                 # Composants React
    │   ├── pages\                      # Pages de l'application
    │   └── services\                   # API + IndexedDB
    ├── package.json                    # Dépendances npm
    ├── .env                            # Variables d'environnement
    ├── setup-and-run-frontend.bat      # Installation complète
    ├── start-frontend.bat              # Démarrage rapide
    ├── clean-install.bat               # Nettoyage complet
    └── LIRE-MOI-SCRIPTS.txt            # Documentation scripts
```

---

## ✅ Checklist Complète

### Backend

- [ ] Python 3.8+ installé
- [ ] MongoDB installé et démarré
- [ ] Dossier backend copié
- [ ] Fichier `requirements-windows.txt` présent
- [ ] Environnement virtuel créé (`venv`)
- [ ] Dépendances installées
- [ ] Fichier `.env` avec 3 variables (MONGO_URL, SECRET_KEY, DB_NAME)
- [ ] Serveur démarré sur port 8001
- [ ] Documentation accessible sur http://localhost:8001/docs

### Frontend

- [ ] Node.js 14+ installé
- [ ] npm disponible
- [ ] Dossier frontend copié
- [ ] Scripts `.bat` présents
- [ ] Fichier `.env` avec REACT_APP_BACKEND_URL
- [ ] Dépendances installées avec `--legacy-peer-deps`
- [ ] Serveur démarré sur port 3000
- [ ] Application accessible sur http://localhost:3000

### Tests

- [ ] Backend répond sur http://localhost:8001/docs
- [ ] Frontend charge sur http://localhost:3000
- [ ] Connexion réussie avec identifiants démo
- [ ] Ajout de produit fonctionne
- [ ] Modification de produit fonctionne
- [ ] Dialogue de confirmation de suppression fonctionne
- [ ] Suppression de produit fonctionne

---

## 🎉 Félicitations !

Si vous avez suivi toutes les étapes, vous avez maintenant :

✅ **Backend FastAPI** fonctionnel avec MongoDB  
✅ **Frontend React** avec interface moderne  
✅ **Application complète** DynSoft Pharma opérationnelle  
✅ **Scripts automatiques** pour faciliter l'utilisation  

---

## 📚 Documentation Complémentaire

- **Guide complet** : `GUIDE_INSTALLATION_LOCAL.md`
- **README Windows** : `README-WINDOWS.md`
- **Scripts frontend** : `frontend/LIRE-MOI-SCRIPTS.txt`
- **Installation frontend** : `frontend/README-INSTALLATION.md`

---

## 📧 Support

Pour toute question ou problème non résolu, consultez les guides de dépannage dans les documents mentionnés ci-dessus.

---

**Version :** DynSoft Pharma v1.0  
**Plateforme :** Windows 10/11  
**Date :** Décembre 2024  
**Technologies :** Python FastAPI + React + MongoDB
