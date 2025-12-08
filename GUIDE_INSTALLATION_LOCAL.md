# Guide d'Installation et de Test en Local - DynSoft Pharma

## 📑 Table des matières
1. [Prérequis](#prérequis)
2. [Configuration initiale](#configuration-initiale)
3. [Installation du Backend](#installation-du-backend)
4. [Installation du Frontend](#installation-du-frontend)
5. [Tests de l'application](#tests-de-lapplication)
6. [Résolution de problèmes](#résolution-de-problèmes)
7. [Commandes utiles](#commandes-utiles)

---

## 📋 Prérequis

Avant de commencer l'installation, assurez-vous d'avoir les éléments suivants installés sur votre machine :

### Logiciels requis
- **Python 3.8 ou supérieur**
  - Vérification : `python --version` ou `python3 --version`
  - Téléchargement : https://www.python.org/downloads/

- **Node.js 14 ou supérieur**
  - Vérification : `node --version`
  - Téléchargement : https://nodejs.org/

- **npm ou yarn** (gestionnaire de paquets JavaScript)
  - npm est inclus avec Node.js
  - Pour yarn : `npm install -g yarn`

- **MongoDB**
  - Vérification : `mongod --version`
  - Téléchargement : https://www.mongodb.com/try/download/community

### Vérification des prérequis
Exécutez les commandes suivantes dans votre terminal pour vérifier que tout est installé :

```bash
python --version
node --version
npm --version
mongod --version
```

---

## 🔧 Configuration initiale

### 1. Démarrage de MongoDB

MongoDB doit être en cours d'exécution avant de lancer l'application.

**Sur Linux/Mac :**
```bash
# Démarrer MongoDB comme service
sudo systemctl start mongod

# Vérifier le statut
sudo systemctl status mongod

# Ou démarrer MongoDB manuellement
mongod
```

**Sur Windows :**
```bash
# Démarrer le service MongoDB
net start MongoDB

# Ou via l'invite de commandes
mongod
```

**Vérification :** MongoDB devrait être accessible sur `mongodb://localhost:27017`

---

## 🎯 Installation du Backend (FastAPI)

Le backend est développé avec FastAPI et gère toute la logique métier et les interactions avec la base de données.

### Étape 1 : Naviguer vers le dossier backend

```bash
cd /app/backend
```

### Étape 2 : Créer un environnement virtuel Python

Il est fortement recommandé d'utiliser un environnement virtuel pour isoler les dépendances du projet.

```bash
# Créer l'environnement virtuel
python -m venv venv
```

**Activer l'environnement virtuel :**

**Sur Linux/Mac :**
```bash
source venv/bin/activate
```

**Sur Windows (Command Prompt) :**
```bash
venv\Scripts\activate
```

**Sur Windows (PowerShell) :**
```bash
venv\Scripts\Activate.ps1
```

Vous devriez voir `(venv)` apparaître au début de votre ligne de commande.

### Étape 3 : Installer les dépendances Python

```bash
pip install -r requirements.txt
```

**⚠️ Note pour les utilisateurs Windows :**

Si vous rencontrez une erreur avec le package `jq` (erreur de compilation C/C++), utilisez le fichier optimisé pour Windows :

```bash
pip install -r requirements-windows.txt
```

Cette commande installe toutes les bibliothèques nécessaires :
- FastAPI
- Motor (driver MongoDB asynchrone)
- Pydantic
- python-jose (JWT)
- passlib (hachage des mots de passe)
- Et autres dépendances

### Étape 4 : Configurer les variables d'environnement

Ouvrez le fichier `/app/backend/.env` et vérifiez qu'il contient :

```env
MONGO_URL=mongodb://localhost:27017/pharma_db
SECRET_KEY=your-secret-key-here-change-in-production
```

**Notes importantes :**
- `MONGO_URL` : URL de connexion à votre base de données MongoDB locale
- `SECRET_KEY` : Clé secrète pour le chiffrement des tokens JWT (changez-la en production !)

### Étape 5 : Lancer le serveur backend

```bash
# Avec uvicorn (recommandé pour le développement)
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Alternative avec Python
python -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

**Paramètres de la commande :**
- `server:app` : fichier `server.py` et application FastAPI `app`
- `--host 0.0.0.0` : rend le serveur accessible depuis toutes les interfaces réseau
- `--port 8001` : port d'écoute du serveur
- `--reload` : redémarrage automatique lors de modifications du code

### ✅ Vérification du backend

Le serveur devrait afficher :
```
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Testez l'API :**
1. Ouvrez votre navigateur
2. Accédez à : `http://localhost:8001/docs`
3. Vous devriez voir la documentation Swagger interactive de l'API

**Endpoints disponibles :**
- Documentation Swagger : `http://localhost:8001/docs`
- Documentation ReDoc : `http://localhost:8001/redoc`

---

## ⚛️ Installation du Frontend (React)

Le frontend est développé avec React et utilise Tailwind CSS pour le style.

### Étape 1 : Ouvrir un nouveau terminal

**Important :** Laissez le terminal du backend ouvert et en cours d'exécution. Ouvrez un **nouveau terminal** pour le frontend.

### Étape 2 : Naviguer vers le dossier frontend

```bash
cd /app/frontend
```

### Étape 3 : Installer les dépendances Node.js

**Avec npm :**
```bash
npm install
```

**Avec yarn (recommandé) :**
```bash
yarn install
```

Cette commande installe toutes les dépendances nécessaires :
- React et React Router
- Tailwind CSS
- Shadcn/UI components
- Axios (pour les appels API)
- IndexedDB (pour le stockage offline)
- Et autres dépendances

**Note :** L'installation peut prendre quelques minutes.

### Étape 4 : Configurer les variables d'environnement

Ouvrez le fichier `/app/frontend/.env` et vérifiez qu'il contient :

```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

**Important :** Cette variable indique au frontend où se trouve le backend. Ne mettez PAS de slash `/` à la fin.

### Étape 5 : Lancer le serveur de développement

**Avec npm :**
```bash
npm start
```

**Avec yarn :**
```bash
yarn start
```

Le serveur démarre et le navigateur devrait s'ouvrir automatiquement.

### ✅ Vérification du frontend

Vous devriez voir :
```
Compiled successfully!

You can now view frontend in the browser.

  Local:            http://localhost:3000
  On Your Network:  http://192.168.x.x:3000
```

**Accédez à l'application :**
- Navigateur : `http://localhost:3000`
- L'application devrait afficher la page de connexion

---

## 🧪 Tests de l'application

### Connexion à l'application

1. **Ouvrez votre navigateur** à `http://localhost:3000`

2. **Page de connexion :** Vous devriez voir l'écran de connexion DynSoft Pharma

3. **Identifiants de démonstration :**
   - **Email :** `demo@pharmaflow.com`
   - **Mot de passe :** `demo123`

4. **Cliquez sur "Se connecter"**

### Fonctionnalités à tester

#### 1. Tableau de bord
- Visualisez les statistiques (ventes, produits, prescriptions)
- Vérifiez que les KPIs s'affichent correctement

#### 2. Gestion des Produits
- **Ajouter un produit :**
  - Cliquez sur "Ajouter un produit"
  - Remplissez le formulaire (nom, prix, stock, etc.)
  - Cliquez sur "Ajouter"
  - Vérifiez que le produit apparaît dans la liste

- **Modifier un produit :**
  - Cliquez sur "Éditer" sur une carte produit
  - Modifiez les informations
  - Cliquez sur "Mettre à jour"
  - Vérifiez que les modifications sont enregistrées

- **Supprimer un produit :** ✨ **NOUVELLE FONCTIONNALITÉ**
  - Cliquez sur l'icône de suppression (poubelle rouge)
  - **Un dialogue de confirmation devrait apparaître**
  - Vous voyez le nom du produit à supprimer
  - Options :
    - "Annuler" : ferme le dialogue sans supprimer
    - "Supprimer" : supprime définitivement le produit
  - Vérifiez que la liste se rafraîchit automatiquement après suppression

#### 3. Gestion des Prescriptions
- **Ajouter une prescription :**
  - Remplissez les informations du patient
  - Ajoutez des médicaments
  - Enregistrez la prescription

- **Modifier le statut :**
  - Changez le statut entre "En attente" et "Remplie"
  - Vérifiez que le badge de couleur change

- **Supprimer une prescription :**
  - Testez également le dialogue de confirmation (similaire aux produits)

#### 4. Autres pages
- **Clients :** Ajouter et gérer les clients
- **Ventes :** Enregistrer des ventes
- **Fournisseurs :** Gérer les fournisseurs
- **Rapports :** Visualiser les statistiques

#### 5. Fonctionnalités offline
- Ouvrez les DevTools (F12)
- Onglet "Network"
- Activez "Offline"
- Testez l'ajout/modification de produits
- Les données devraient être stockées dans IndexedDB

### Tests du dialogue de confirmation de suppression

**Scénario 1 : Annulation**
1. Cliquez sur le bouton de suppression d'un produit
2. Vérifiez que le dialogue apparaît avec :
   - Titre : "Confirmer la suppression"
   - Message : "Êtes-vous sûr de vouloir supprimer le produit "[nom]" ?"
   - Bouton "Annuler" (gris)
   - Bouton "Supprimer" (rouge)
3. Cliquez sur "Annuler"
4. Vérifiez que le produit est toujours dans la liste

**Scénario 2 : Confirmation**
1. Cliquez sur le bouton de suppression d'un produit
2. Cliquez sur "Supprimer" dans le dialogue
3. Vérifiez :
   - Une notification "Produit supprimé" apparaît en haut à droite
   - Le produit disparaît de la liste
   - La liste se rafraîchit automatiquement

---

## 🐛 Résolution de problèmes

### Problème 1 : Le backend ne démarre pas

**Symptôme :** Erreur au lancement de `uvicorn`

**Solutions :**

1. **Vérifier que MongoDB est en cours d'exécution :**
```bash
sudo systemctl status mongod
```

2. **Vérifier que le port 8001 n'est pas déjà utilisé :**
```bash
# Linux/Mac
lsof -i :8001

# Windows
netstat -ano | findstr :8001
```

3. **Réinstaller les dépendances :**
```bash
pip install --upgrade -r requirements.txt
```

4. **Vérifier le fichier .env :**
- Assurez-vous que `MONGO_URL` est correct
- Pas d'espaces avant/après le `=`

### Problème 2 : Le frontend ne se connecte pas au backend

**Symptôme :** Erreurs CORS ou "Network Error" dans la console

**Solutions :**

1. **Vérifier que le backend est bien démarré :**
   - Accédez à `http://localhost:8001/docs`
   - Si ça ne charge pas, le backend n'est pas démarré

2. **Vérifier la variable d'environnement :**
   - Ouvrez `/app/frontend/.env`
   - Vérifiez : `REACT_APP_BACKEND_URL=http://localhost:8001`
   - **PAS de slash à la fin !**

3. **Redémarrer le frontend :**
   - Arrêtez le serveur (Ctrl+C)
   - Relancez : `yarn start`

4. **Vider le cache du navigateur :**
   - Chrome : Ctrl+Shift+Delete
   - Cochez "Images et fichiers en cache"
   - Cliquez sur "Effacer les données"

### Problème 3 : Erreur MongoDB Connection

**Symptôme :** `pymongo.errors.ServerSelectionTimeoutError`

**Solutions :**

1. **Démarrer MongoDB :**
```bash
sudo systemctl start mongod
```

2. **Vérifier la connexion :**
```bash
mongo --eval "db.adminCommand('ping')"
```

3. **Vérifier l'URL dans .env :**
```env
MONGO_URL=mongodb://localhost:27017/pharma_db
```

### Problème 4 : Erreurs de dépendances

**Symptôme :** Erreurs d'import ou modules manquants

**Solutions backend :**
```bash
# Supprimer l'environnement virtuel
rm -rf venv

# Recréer l'environnement
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate sur Windows

# Réinstaller les dépendances
pip install -r requirements.txt
```

#### Problème spécifique Windows : Erreur de compilation `jq`

**Symptôme :** 
```
ERROR: Failed building wheel for jq
error: [WinError 2] Le fichier spécifié est introuvable
```

**Cause :** Le package `jq` nécessite des outils de compilation C/C++ qui ne sont pas installés sur Windows.

**Solutions :**

**Option 1 - Utiliser requirements-windows.txt (Recommandé) :**
```bash
pip install -r requirements-windows.txt
```

**Option 2 - Installer Visual C++ Build Tools :**
1. Téléchargez : https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. Installez "Desktop development with C++"
3. Redémarrez votre PC
4. Relancez `pip install -r requirements.txt`

**Option 3 - Retirer jq manuellement :**
1. Ouvrez `requirements.txt`
2. Supprimez la ligne `jq==1.10.0`
3. Relancez `pip install -r requirements.txt`

**Solutions frontend :**
```bash
# Supprimer node_modules et lock files
rm -rf node_modules package-lock.json yarn.lock

# Réinstaller
yarn install
# ou
npm install
```

### Problème 5 : Le port 3000 est déjà utilisé

**Symptôme :** `Something is already running on port 3000`

**Solutions :**

1. **Utiliser un autre port :**
```bash
PORT=3001 yarn start
```

2. **Tuer le processus sur le port 3000 :**
```bash
# Linux/Mac
lsof -ti:3000 | xargs kill -9

# Windows
netstat -ano | findstr :3000
taskkill /PID [PID_NUMBER] /F
```

### Problème 6 : Dialogue de suppression ne s'affiche pas

**Solutions :**

1. **Vider le cache du navigateur** (Ctrl+Shift+Delete)

2. **Faire un hard refresh :**
   - Chrome/Firefox : Ctrl+Shift+R (ou Cmd+Shift+R sur Mac)

3. **Vérifier la console pour erreurs JavaScript :**
   - Ouvrez DevTools (F12)
   - Onglet "Console"
   - Recherchez des erreurs en rouge

---

## 📝 Commandes utiles

### Backend

```bash
# Démarrer le serveur avec logs détaillés
uvicorn server:app --host 0.0.0.0 --port 8001 --reload --log-level debug

# Voir les logs MongoDB
tail -f /var/log/mongodb/mongod.log

# Tester un endpoint avec curl
curl http://localhost:8001/api/products

# Arrêter le serveur
Ctrl+C
```

### Frontend

```bash
# Démarrer en mode développement
yarn start

# Build de production
yarn build

# Tester le build de production
npx serve -s build

# Nettoyer le cache
yarn cache clean

# Analyser la taille du bundle
yarn build --stats
npx webpack-bundle-analyzer build/bundle-stats.json

# Arrêter le serveur
Ctrl+C
```

### MongoDB

```bash
# Se connecter à MongoDB Shell
mongo

# Afficher les bases de données
show dbs

# Utiliser la base pharma_db
use pharma_db

# Afficher les collections
show collections

# Compter les documents dans une collection
db.products.count()

# Afficher tous les produits
db.products.find().pretty()

# Supprimer tous les produits (ATTENTION)
db.products.deleteMany({})
```

### Gestionnaire de processus

```bash
# Voir les processus Python
ps aux | grep python

# Voir les processus Node
ps aux | grep node

# Tuer un processus par PID
kill -9 [PID]
```

---

## 🎯 Architecture de l'application

### Structure des dossiers

```
/app/
├── backend/
│   ├── server.py           # Application FastAPI principale
│   ├── .env                # Variables d'environnement backend
│   ├── requirements.txt    # Dépendances Python
│   └── venv/              # Environnement virtuel Python
│
└── frontend/
    ├── public/
    │   ├── manifest.json   # Configuration PWA
    │   └── service-worker.js
    ├── src/
    │   ├── components/     # Composants réutilisables
    │   ├── pages/         # Pages de l'application
    │   ├── services/      # API calls et IndexedDB
    │   ├── contexts/      # React Context (Auth, Offline)
    │   └── App.js
    ├── .env               # Variables d'environnement frontend
    ├── package.json       # Dépendances Node.js
    └── tailwind.config.js # Configuration Tailwind CSS
```

### Technologies utilisées

**Backend :**
- FastAPI (framework web Python)
- Motor (driver MongoDB asynchrone)
- Pydantic (validation des données)
- JWT (authentification)
- Passlib (sécurité des mots de passe)

**Frontend :**
- React 18
- React Router (navigation)
- Tailwind CSS (styles)
- Shadcn/UI (composants UI)
- Axios (appels HTTP)
- IndexedDB (stockage offline)

**Base de données :**
- MongoDB (NoSQL)

---

## 📧 Support

Si vous rencontrez des problèmes non couverts par ce guide :

1. **Vérifiez les logs :**
   - Backend : messages dans le terminal où uvicorn tourne
   - Frontend : console du navigateur (F12)
   - MongoDB : `/var/log/mongodb/mongod.log`

2. **Vérifiez les versions :**
   - Python 3.8+
   - Node.js 14+
   - MongoDB 4.0+

3. **Recherchez l'erreur spécifique** dans la documentation officielle

---

## ✅ Checklist de démarrage rapide

- [ ] MongoDB installé et démarré
- [ ] Python 3.8+ installé
- [ ] Node.js 14+ installé
- [ ] Backend : environnement virtuel créé et activé
- [ ] Backend : dépendances installées (`pip install -r requirements.txt`)
- [ ] Backend : fichier .env configuré
- [ ] Backend : serveur démarré sur port 8001
- [ ] Frontend : dépendances installées (`yarn install`)
- [ ] Frontend : fichier .env configuré
- [ ] Frontend : serveur démarré sur port 3000
- [ ] Application accessible sur `http://localhost:3000`
- [ ] Connexion avec identifiants de démo réussie
- [ ] Test de création/modification/suppression de produit

---

## 🎉 Félicitations !

Vous avez maintenant **DynSoft Pharma** qui tourne en local sur votre machine !

Profitez de l'application et n'hésitez pas à explorer toutes les fonctionnalités, notamment le nouveau dialogue de confirmation de suppression des produits.

---

**Document créé le :** 3 décembre 2024  
**Version de l'application :** DynSoft Pharma v1.0  
**Dernière mise à jour :** Ajout du dialogue de confirmation de suppression
