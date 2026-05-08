# 🎨 Installation du Frontend - DynSoft Pharma

## 🚀 Installation Rapide (Windows)

### Méthode Automatique

1. **Copiez les fichiers** de `/app/frontend/` vers votre dossier local
2. **Double-cliquez** sur `setup-and-run-frontend.bat`

Ou en ligne de commande :

```cmd
cd C:\dev\Pharma\projet\frontend
setup-and-run-frontend.bat
```

---

## 🛠️ Installation Manuelle

### Prérequis

- **Node.js 14+** : https://nodejs.org/
- **npm** (inclus avec Node.js) ou **yarn**

### Étapes

#### 1. Naviguer vers le dossier

```cmd
cd C:\dev\Pharma\projet\frontend
```

#### 2. Créer le fichier .env

```cmd
echo REACT_APP_BACKEND_URL=http://localhost:8001 > .env
```

#### 3. Installer les dépendances

**Option A - Avec Yarn (Recommandé) :**

```cmd
npm install -g yarn
yarn install
```

**Option B - Avec npm :**

```cmd
npm install --legacy-peer-deps
```

#### 4. Démarrer l'application

**Avec Yarn :**
```cmd
yarn start
```

**Avec npm :**
```cmd
npm start
```

---

## ⚠️ Résolution de l'erreur date-fns

Si vous rencontrez l'erreur :
```
ERESOLVE unable to resolve dependency tree
peer date-fns@"^2.28.0 || ^3.0.0"
```

### Solution 1 : Utiliser --legacy-peer-deps

```cmd
npm install --legacy-peer-deps
npm start
```

### Solution 2 : Corriger package.json

Ouvrez `package.json` et modifiez :

```json
"date-fns": "^3.6.0",
```

Au lieu de :
```json
"date-fns": "^4.1.0",
```

Puis :
```cmd
npm install
```

### Solution 3 : Utiliser Yarn

```cmd
npm install -g yarn
yarn install
yarn start
```

---

## ✅ Vérification

Après le démarrage, vous devriez voir :

```
Compiled successfully!

You can now view frontend in the browser.

  Local:            http://localhost:3000
  On Your Network:  http://192.168.x.x:3000
```

Le navigateur devrait s'ouvrir automatiquement.

---

## 🧪 Test de l'application

1. **Page de connexion** : http://localhost:3000
2. **Identifiants de test :**
   - Email : `demo@pharmaflow.com`
   - Mot de passe : `demo123`

---

## 🐛 Problèmes Courants

### Port 3000 déjà utilisé

**Erreur :**
```
Something is already running on port 3000
```

**Solution 1 - Utiliser un autre port :**
```cmd
set PORT=3001
npm start
```

**Solution 2 - Tuer le processus :**
```cmd
netstat -ano | findstr :3000
taskkill /PID [NUMERO_PID] /F
```

---

### Erreur "Module not found"

**Solution :**

```cmd
rmdir /s /q node_modules
del package-lock.json
del yarn.lock
yarn install
```

Ou avec npm :
```cmd
rmdir /s /q node_modules
del package-lock.json
npm install --legacy-peer-deps
```

---

### Le backend n'est pas accessible

**Vérifiez :**
1. Le backend est démarré sur http://localhost:8001
2. Le fichier `.env` contient : `REACT_APP_BACKEND_URL=http://localhost:8001`
3. Redémarrez le frontend après modification du `.env`

---

### Erreur CORS

Si vous voyez des erreurs CORS dans la console :

1. **Vérifiez que le backend tourne** : http://localhost:8001/docs
2. **Vérifiez le .env** : `REACT_APP_BACKEND_URL=http://localhost:8001` (sans slash final)
3. **Videz le cache** : Ctrl+Shift+Delete dans le navigateur

---

## 📁 Structure des fichiers importants

```
frontend/
├── .env                          # Variables d'environnement
├── package.json                  # Dépendances
├── public/
│   ├── manifest.json            # Configuration PWA
│   └── service-worker.js        # Service worker offline
├── src/
│   ├── components/              # Composants réutilisables
│   │   ├── Layout.js
│   │   └── ui/                  # Shadcn components
│   ├── pages/                   # Pages de l'application
│   │   ├── Dashboard.js
│   │   ├── Products.js
│   │   ├── Prescriptions.js
│   │   └── ...
│   ├── services/
│   │   ├── api.js              # Appels API
│   │   └── indexedDB.js        # Stockage offline
│   ├── contexts/
│   │   ├── AuthContext.js      # Gestion authentification
│   │   └── OfflineContext.js   # Gestion offline
│   └── App.js
└── setup-and-run-frontend.bat   # Script d'installation automatique
```

---

## 🎯 Checklist

- [ ] Node.js installé (v14+)
- [ ] Dossier frontend copié/cloné
- [ ] Fichier `.env` créé avec `REACT_APP_BACKEND_URL`
- [ ] Dépendances installées (yarn ou npm)
- [ ] Backend démarré sur port 8001
- [ ] Frontend démarré sur port 3000
- [ ] Connexion réussie avec identifiants démo

---

## 📧 Support

Pour plus d'informations, consultez :
- Guide complet : `/app/GUIDE_INSTALLATION_LOCAL.md`
- Guide Windows : `/app/README-WINDOWS.md`

---

**Version :** DynSoft Pharma v1.0  
**Date :** Décembre 2024
