# Installateur Windows (.exe) — DynSoft Pharma serveur local

Produit `Setup-DynSoftPharma-<version>.exe` qui installe de bout en bout le serveur local d'une pharmacie
(Docker Desktop doit être installé au préalable ; PostgreSQL tourne **dans** Docker, inutile de l'installer).

## Ce que fait l'installateur
1. Vérifie Docker Desktop (lien de téléchargement si absent).
2. **Première installation** ou **Mise à jour** (choix exclusif) :
   - Première installation refusée si un `.env` existe déjà dans le dossier (protection des données) ;
   - Mise à jour refusée si aucune installation n'est trouvée dans le dossier.
3. Première installation → assistant : nom + identifiant (slug), compte super-admin local, URL cloud + **jeton obligatoire**,
   heure de la remontée nocturne, port (80). Génère `deploy\local\.env` (secrets aléatoires, `TENANT_SCHEMA=t_<slug>`,
   `CLOUD_IMPORT_ON_START=1`) → import automatique de la pharmacie au premier démarrage, pharmacie forcée **active** en local.
   Mise à jour → aucune question, `.env` conservé, `CLOUD_IMPORT_ON_START=0` (jamais de réimport).
4. Copie le code (`backend`, `frontend`, `deploy\local`) dans `C:\DynSoftPharma`, lance `docker compose up -d --build`,
   attend l'API puis ouvre le navigateur.
5. Au premier démarrage, le backend **importe la pharmacie depuis le cloud** (schéma `t_<slug>` + fiche pharmacie + comptes),
   via `GET /api/cloud-sync/<slug>/export` authentifié par le jeton. Le schéma `public` du cloud (autres pharmacies) n'est pas copié.
   À la fin, l'installateur affiche le résultat de l'import (réussi / ignoré car base déjà remplie / échec avec consigne).
6. Raccourcis : Ouvrir, Démarrer, Arrêter, Sauvegarder, Importer depuis le cloud, Journal, Guide PDF.
7. Mise à jour : relancer un `.exe` plus récent sur le même dossier → le `.env` est conservé, les images sont reconstruites, les migrations s'appliquent.
8. Désinstallation : arrêt des conteneurs, question « supprimer aussi la base ? ».

## Produire le .exe
- **Automatique (GitHub Actions)** : pousser un tag `v1.2.0` (ou lancer manuellement le workflow « Installateur Windows »).
  Le fichier est publié dans la *Release* du tag et en artefact du workflow.
- **Manuel** : installer [Inno Setup 6](https://jrsoftware.org/isdl.php), placer un `dynsoft.ico` ici, puis
  `"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /DAppVersion=1.2.0 deploy\windows\DynSoftPharma.iss`.

## Prérequis côté cloud (une fois par pharmacie, super-admin DynSoft)
- `/platform` → pharmacie → **Générer un jeton de synchronisation** (active le mode miroir) → donner le jeton à l'installateur.
