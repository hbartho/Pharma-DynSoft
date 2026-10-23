# DynSoft Pharma – Guide d'installation locale (sans Internet)

Ce guide explique comment installer DynSoft Pharma sur un PC de la pharmacie afin que
l'application fonctionne **sans connexion Internet**, accessible depuis tous les postes
du réseau local (Wi-Fi ou câble).

## 1. Principe

```
┌──────────────── PC serveur de la pharmacie ────────────────┐
│  Docker                                                     │
│   ├─ db        PostgreSQL 17 (données, 1 schéma / pharmacie)│
│   ├─ backend   API FastAPI (port interne 8001)              │
│   └─ frontend  Interface web + proxy (port 80)              │
└───────────────────────────┬─────────────────────────────────┘
                            │ Wi-Fi / câble local
        ┌───────────┬───────┴───────┬───────────┐
     Caisse 1    Caisse 2       Bureau       Tablette
   http://192.168.x.x       (même adresse sur tous les postes)
```

- Une seule commande (`install.bat` / `install.sh`) construit et démarre tout.
- Les données restent dans la pharmacie, sur le disque du PC serveur.
- Même fonctionnement et mêmes comptes que la version cloud (multi-pharmacies, super admin, admins locaux).

## 2. Matériel recommandé

| Élément | Minimum | Recommandé |
|---|---|---|
| PC serveur | 4 Go RAM, 2 cœurs, 40 Go disque | Mini-PC 8 Go RAM, SSD 120 Go |
| Système | Windows 10/11 64 bits ou Ubuntu 22.04 | Ubuntu 22.04/24.04 (plus stable en serveur) |
| Alimentation | – | Onduleur (coupures de courant) |
| Réseau | Box Wi-Fi / switch | Adresse IP fixe pour le PC serveur |

Le PC serveur doit rester allumé pendant les heures d'ouverture.

## 3. Installer Docker

**Windows** : télécharger et installer Docker Desktop (https://www.docker.com/products/docker-desktop/),
redémarrer le PC, puis lancer Docker Desktop (icône baleine en bas à droite).

**Ubuntu / Debian** :
```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER   # puis se déconnecter / reconnecter
```

## 4. Récupérer le code

1. Depuis Emergent : bouton **Save to GitHub**, puis télécharger le dépôt (ZIP) depuis GitHub.
2. Décompresser dans un dossier simple, par exemple `C:\DynPharma` ou `/opt/dynpharma`.
3. Le pack d'installation se trouve dans `deploy/local/`.

## 5. Première installation

1. Ouvrir le dossier `deploy/local`.
2. Lancer `install.bat` (Windows) ou `./install.sh` (Linux). À la première exécution,
   un fichier `.env` est créé (et ouvert dans le Bloc-notes sous Windows) puis le script s'arrête.
3. Ouvrir `.env` avec le Bloc-notes et remplacer **toutes** les valeurs `CHANGEZ_MOI` :

   | Variable | Rôle |
   |---|---|
   | `POSTGRES_PASSWORD` | Mot de passe de la base locale (évitez `#`, `@`, `/`, `:` et `%`) |
   | `JWT_SECRET_KEY` | Clé secrète des sessions (longue et aléatoire, 32 caractères et plus) |
   | `SUPERADMIN_EMAIL` | Email du super admin DynSoft créé au premier démarrage |
   | `SUPERADMIN_PASSWORD` | Son mot de passe (8 caractères minimum) |
   | `APP_PORT` | Port d'accès (80 par défaut → `http://IP` sans préciser de port) |

   Le super admin n'est créé que si la base est vide (pas de compte super admin existant).
4. Relancer `install.bat` / `./install.sh`. La première construction prend 5 à 15 minutes
   (téléchargement des images Docker : Internet nécessaire **une seule fois**).
5. Ouvrir `http://localhost` sur le PC serveur : la page de connexion s'affiche.

## 6. Créer la pharmacie

1. Se connecter avec le compte super admin défini dans `.env`.
2. Aller sur `/platform` → **Nouvelle pharmacie** : nom, slug, compte admin local.
3. L'admin local se connecte ensuite et crée ses employés, produits, fournisseurs…

Si vous migrez une pharmacie existante depuis le cloud, passez directement à la section 8.

## 7. Accès depuis les autres postes

1. Trouver l'adresse IP du PC serveur : `ipconfig` (Windows) ou `hostname -I` (Linux),
   par exemple `192.168.1.20`.
2. Fixer cette IP dans la box (réservation DHCP) pour qu'elle ne change pas.
3. Sur chaque caisse / tablette connectée au même Wi-Fi, ouvrir `http://192.168.1.20`.
4. Dans le navigateur, utiliser **Installer l'application** (bannière PWA) pour avoir une
   icône sur le bureau comme un logiciel classique.
5. Windows : si la page ne s'ouvre pas depuis les autres postes, autoriser Docker Desktop
   dans le pare-feu ou ouvrir le port 80 (réseau privé).

## 8. Migrer les données depuis Supabase (cloud → local)

À faire une seule fois, avec Internet, depuis le PC serveur :

1. Dans Supabase : **Project Settings → Database → Connection string**, mode
   **Session pooler** (port 5432), copier l'URL `postgresql://...`.
   Si le mot de passe contient `#`, le remplacer par `%23` dans l'URL (`@` → `%40`, `/` → `%2F`).
2. Lancer `migrer-depuis-supabase.bat` / `./migrer-depuis-supabase.sh` et coller l'URL
   (elle n'est pas enregistrée).
3. Le script exporte le schéma `public` et tous les schémas `t_*` (une pharmacie = un schéma)
   avec `pg_dump`, puis propose l'import local avec `pg_restore`.
4. Après l'import, tous les comptes (super admin, admins, employés) fonctionnent avec
   leurs mots de passe habituels.

Des messages d'avertissement `pg_restore` sur des objets déjà existants sont normaux.

Pour ne garder qu'une seule pharmacie en local, le super admin peut supprimer les autres
depuis `/platform` après la migration.

## 9. Dédier le serveur à une seule pharmacie (`TENANT_SCHEMA`)

Par défaut, le serveur local se comporte comme le cloud : chaque utilisateur est routé vers
sa pharmacie (`public` pour la pharmacie historique, `t_<slug>` pour les autres).

Si ce PC ne sert **qu'une seule pharmacie**, indiquez son schéma dans `.env` :

```
TENANT_SCHEMA=t_noormin
```

Effets :
- toutes les connexions et toutes les opérations utilisent ce schéma, quel que soit le compte ;
- les comptes d'autres pharmacies présents dans une sauvegarde importée ne peuvent plus se connecter ;
- la création / suppression de pharmacies depuis `/platform` est bloquée sur ce serveur ;
- si le schéma n'existe pas encore, il est créé (vide) au démarrage.

Trouver le nom du schéma : `/platform` (colonne « Schéma ») ou `t_` + slug de la pharmacie ;
`public` pour la pharmacie historique. Après modification de `.env` : `docker compose up -d`.

Pour un **nouveau** serveur sans migration : laissez `TENANT_SCHEMA` vide, créez la pharmacie
depuis `/platform`, puis renseignez `TENANT_SCHEMA=t_<slug>` et relancez.

## 10. Sauvegardes (indispensable)

- `backup.bat` / `./backup.sh` crée `backups/dynpharma_AAAAMMJJ_HHMM.dump` (les 30 dernières
  sont conservées sous Linux).
- Copier régulièrement le dossier `backups/` sur une clé USB ou un disque externe.
- Restaurer : `restore.bat backups\fichier.dump` ou `./restore.sh backups/fichier.dump`.

Automatiser (Windows) : Planificateur de tâches → tâche quotidienne 20h → programme
`C:\DynPharma\deploy\local\backup.bat`.
Automatiser (Linux) : `crontab -e` puis `0 20 * * * /opt/dynpharma/deploy/local/backup.sh`.

## 11. Exploitation quotidienne

| Action | Commande (dans `deploy/local`) |
|---|---|
| Démarrer | `docker compose up -d` (automatique au démarrage du PC) |
| Arrêter | `docker compose down` |
| Voir les journaux | `docker compose logs -f backend` |
| Mettre à jour après un nouveau code | `install.bat` / `./install.sh` |
| État des services | `docker compose ps` |

Les données sont conservées dans le volume Docker `dynpharma_pgdata` : arrêter ou
reconstruire les conteneurs ne les efface pas. **Ne jamais** exécuter `docker compose down -v`
(le `-v` supprime les données).

**Mise à jour du code sans perte de données** : `backup` → remplacer le code → `install`.
Au démarrage, le backend applique automatiquement les migrations de base (Alembic) à
`public` **et à chaque schéma de pharmacie** : nouvelles tables, nouvelles colonnes, etc.
Le journal affiche `Migrations BD : {... 'upgraded' ...}`. Aucune opération manuelle.

## 12. Dépannage

| Symptôme | Cause probable / solution |
|---|---|
| `install` échoue immédiatement | Docker Desktop n'est pas lancé |
| Backend : `exec ./docker-entrypoint.sh: no such file or directory` | Fins de ligne Windows dans le script : relancer `install` avec la version à jour du code (le Dockerfile corrige le fichier au build) |
| Page blanche ou « Network Error » | Backend pas encore prêt : attendre 1 min, `docker compose logs backend` |
| Accès impossible depuis une caisse | Mauvaise IP, Wi-Fi différent, ou pare-feu Windows (port 80) |
| « Mot de passe incorrect » après migration | Vérifier que l'import s'est terminé (`docker compose logs backend`) |
| Disque plein | Supprimer les anciens fichiers dans `backups/` |
| Port 80 déjà utilisé | Changer `APP_PORT=8080` dans `.env` puis relancer `install` ; accès via `http://IP:8080` |

## 13. Synchronisation automatique vers le cloud DynSoft

Chaque pharmacie peut remonter **tout son schéma** (`t_<slug>` : ventes, stocks, clients,
dettes…) vers le cloud DynSoft, **chaque nuit, dès qu'Internet est disponible**. Le schéma
`public` du cloud (pharmacies, comptes) n'est jamais modifié.

Principe : local → cloud uniquement. Le serveur de la pharmacie fait foi ; la copie cloud
sert à DynSoft (statistiques, consultation) et passe en **consultation seule**.

1. Sur le cloud, le super-admin ouvre `/platform`, clique sur l'icône nuage de la pharmacie
   puis **Générer le jeton** : un bloc de 4 lignes s'affiche (à copier immédiatement).
2. Sur le serveur local, coller ces lignes dans `deploy/local/.env` :
   ```
   CLOUD_SYNC_URL=https://adresse-du-cloud
   CLOUD_SYNC_SLUG=noormin
   CLOUD_SYNC_TOKEN=le-jeton
   CLOUD_SYNC_HOUR=2
   ```
3. Relancer : `docker compose up -d`.
4. Vérifier dans **Paramètres** (admin) : la carte « Synchronisation vers DynSoft cloud »
   affiche la dernière réussite ; le bouton **Synchroniser maintenant** force un envoi.

Fonctionnement : première synchronisation complète, puis chaque nuit seulement ce qui a
changé ; une copie complète est refaite toutes les semaines (rattrapage des suppressions).
Si Internet est absent à l'heure prévue, une nouvelle tentative a lieu toutes les 15 minutes.
Le super-admin voit sur `/platform` la date de dernière réception de chaque pharmacie.
Pour revenir à un fonctionnement 100 % cloud : `/platform` → nuage → **Désactiver la synchro**.
