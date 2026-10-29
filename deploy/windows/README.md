# Installateur Windows (.exe) — DynSoft Pharma serveur local

Produit `Setup-DynSoftPharma-<version>.exe` qui installe de bout en bout le serveur local d'une pharmacie
(Docker Desktop doit être installé au préalable ; PostgreSQL tourne **dans** Docker, inutile de l'installer).

## Ce que fait l'installateur
1. Vérifie Docker Desktop (lien de téléchargement si absent).
2. Assistant : nom + identifiant (slug) de la pharmacie, compte super-admin local, URL cloud + jeton de synchronisation,
   heure de la remontée nocturne, port (80).
3. Génère `deploy\local\.env` (mots de passe base et clé JWT aléatoires, `TENANT_SCHEMA=t_<slug>`, `CLOUD_IMPORT_ON_START=1`).
4. Copie le code (`backend`, `frontend`, `deploy\local`) dans `C:\DynSoftPharma`, lance `docker compose up -d --build`,
   attend l'API puis ouvre le navigateur.
5. Au premier démarrage, le backend **importe la pharmacie depuis le cloud** (schéma `t_<slug>` + fiche pharmacie + comptes),
   via `GET /api/cloud-sync/<slug>/export` authentifié par le jeton. Le schéma `public` du cloud (autres pharmacies) n'est pas copié.
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
