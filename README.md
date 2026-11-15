# DynSoft Pharma

Application de gestion de pharmacies (multi-pharmacies, un schéma PostgreSQL par pharmacie).

| Dossier | Contenu |
|---|---|
| `backend/` | API FastAPI + SQLAlchemy (PostgreSQL), migrations Alembic (`migrations/`), scripts d'exploitation (`scripts/`), manuel PDF (`static/`) |
| `frontend/` | Application React (PWA, React Query, Shadcn UI) — **Node ≥ 20** requis en développement (`yarn install`) |
| `deploy/local/` | Installation locale Docker d'une pharmacie (compose, sauvegarde, import cloud, guide PDF) |
| `deploy/windows/` | Installateur Windows `.exe` (Inno Setup, compilé par GitHub Actions) |
| `memory/` | PRD, journal des évolutions, identifiants de test |

Règles métier clés : approvisionnement au prix de cession HT, vente au prix public TTC, coefficient de référence 1,4 ;
le schéma `public` (plateforme) n'est jamais synchronisé local → cloud.
