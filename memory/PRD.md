# DynSoft Pharma - Product Requirements Document

## Dernière mise à jour: 15 Février 2026

## Architecture
- **Frontend**: React PWA avec Tailwind CSS, Shadcn/UI
- **Backend**: FastAPI avec SQLAlchemy
- **Base de données**: PostgreSQL (Supabase)
- **Authentification**: JWT

## Fonctionnalités Implémentées

### ✅ Core Features (100% fonctionnel après corrections)
| Module | Status | Notes |
|--------|--------|-------|
| Authentification | ✅ | JWT, 3 rôles (admin, pharmacien, caissier) |
| Dashboard | ✅ | Stats ventes, stock, alertes |
| Produits | ✅ | CRUD + 36 produits avec stock |
| Clients | ✅ | CRUD + max_debt_limit ajouté |
| Fournisseurs | ✅ | CRUD complet |
| Ventes | ✅ | Création avec dette, paiements multiples, **rabais** |
| Approvisionnements | ✅ | Création, validation, mise à jour stock |
| Ordonnances | ✅ | CRUD + statut fulfillment |
| Gestion des Dettes Clients | ✅ | Dashboard, remboursements, historique |
| Gestion des Dettes Fournisseurs | ✅ | CRUD, paiements, statuts |
| Shifts | ✅ | Ouverture, fermeture, alertes |
| Stock | ✅ | Mouvements, pertes, alertes |
| Infinite Scroll | ✅ | Toutes les pages de listes |
| **Codes Promo** | ✅ | CRUD, validation, conditions d'utilisation |
| **Règles de Rabais Automatiques** | ✅ | Volume, Fidélité, Catégorie, Péremption |
| **Rabais par Produit** | ✅ | % ou montant, motif optionnel |
| **Rabais dans Dashboard** | ✅ | Affichage dans "Ventes par Mode de Paiement" |
| **Rabais dans Liste Ventes** | ✅ | Colonne Paiement avec montant rabais |

### Système de Rabais Complet (13 Février 2026) - ✅ IMPLÉMENTÉ
**Modèles backend créés:**
- `PromoCode`: Codes promotionnels avec conditions
- `DiscountRule`: Règles de rabais automatiques
- `DiscountHistory`: Historique des rabais accordés
- `PromoCodeUsage`: Suivi d'utilisation par client

**Règles de rabais actives:**
- **Volume**: 3% pour achats > 50,000 GNF
- **Fidélité Client**: 5% pour clients avec 20+ achats
- **Péremption Proche**: 10% pour produits expirant dans 30 jours

**Routes API créées:**
- `POST /api/discounts/promo-codes` - CRUD codes promo
- `POST /api/discounts/promo-codes/validate` - Validation en temps réel
- `POST /api/discounts/rules` - CRUD règles automatiques
- `POST /api/discounts/calculate` - Calcul des rabais applicables
- `GET /api/discounts/history` - Historique des rabais
- `GET /api/reports/today-sales-by-payment` - Retourne discount_info

**Pages Frontend créées:**
- `/promo-codes` - Gestion des codes promo (admin)
- `/discount-rules` - Gestion des règles automatiques (admin)
- `/discount-history` - Historique des rabais avec rapports (admin)

**Intégration dans le formulaire de vente:**
- ✅ Rabais manuel (%, montant)
- ✅ Code promo avec validation en temps réel
- ✅ **Rabais automatiques appliqués en temps réel** (useEffect avec debounce de 500ms)
- ✅ Rabais par produit individuel avec motif
- ✅ Affichage détaillé de tous les rabais dans le récapitulatif
- ✅ Section bleue "Rabais Automatiques" avec indicateur de chargement
- ✅ Toast notification quand des rabais sont appliqués

**Règles de rabais actives:**
- Volume: 3% de rabais pour les achats >= 50000 GNF
- Fidélité: 5% de rabais pour les clients avec >= 20 achats

### Corrections Paiements Mixtes (8 Février 2026)
1. **Bug Fix P0**: `is_split_payment` et `split_payments` sont maintenant correctement sauvegardés lors de la création des ventes
2. **Fichier corrigé**: `/app/backend/database/repositories_extended.py` - `SaleRepository.create()` ligne 468
3. **Tests créés**: `/app/backend/tests/test_split_payments_fix.py`
4. **Frontend**: L'affichage des ventes mixtes fonctionne (Espèces + Orange Money affiché correctement)

### Bug Fix TVA Approvisionnements (9 Février 2026) - ✅ CORRIGÉ
**Problème**: Quand on créait un approvisionnement sans TVA puis l'éditait pour ajouter une TVA, la valeur TVA revenait à 0 après réouverture.

**Cause racine**: Les conditions `!= 0` dans les fonctions `create_supply` et `update_supply` empêchaient de sauvegarder une TVA explicitement à 0.

**Fichier corrigé**: `/app/backend/routes/supplies.py`
- Lignes 199-206 (create_supply): Supprimé `!= 0` condition
- Lignes 415-420 (update_supply): Supprimé `!= 0` condition

**Tests créés**: `/app/backend/tests/test_tva_persistence.py` (7 tests passés)
- Test 1: Create TVA=0 → Update TVA=18 → Vérifier persistance ✅
- Test 2: Create TVA=18 → Update TVA=0 → Vérifier persistance ✅  
- Test 3: Create TVA=18 → Re-save sans changement → Vérifier persistance ✅
- Test 4: Vérifier lot_number, shelf_location, date_peremption persistent ✅

### Bug Fix Rabais considéré comme Dette (13 Février 2026) - ✅ CORRIGÉ (v2)
**Problème**: Quand on appliquait un rabais sur une vente (manuel, promo, automatique ou par produit), le montant du rabais était incorrectement enregistré comme une dette client.

**Cause racine (v2)**: La route `/api/sales` n'utilisait que `discount_amount` (rabais manuel) pour calculer le total final, ignorant les autres types de rabais (promo, automatique, par produit).

**Fichier corrigé**: `/app/backend/routes/sales.py` (lignes 245-267)
- Calcul du total de TOUS les rabais: `total_discount_amount = manual_discount + promo_discount + auto_discount + product_discounts`
- Total final correct: `final_total = calculated_subtotal - total_discount_amount`

**Tests créés**:
- `/app/backend/tests/test_discount_debt_bug.py` - Tests unitaires (3 tests)
- `/app/backend/tests/test_discount_debt_api.py` - Tests API (2 tests)
- `/app/backend/tests/test_discount_debt_bug_complete.py` - Tests complets (5 tests)

**Vérification base de données**: 10 ventes récentes avec rabais vérifiées - toutes ont `debt_amount=0` ✅

**Exemple de correction**:
```
Avant (bug): subtotal=11000, discount_calcul=0 (seulement manuel), total_stocké=11000, paid=8500 → dette=2500
Après: subtotal=11000, discount_total=2500, total_stocké=8500, paid=8500 → dette=0 ✅
```

### Affichage Prix Public Modifié dans la bande info (12 Février 2026) - ✅ CORRIGÉ
**Modification**: La bande d'information verte dans le formulaire de modification d'approvisionnement affiche maintenant le "Prix public modifié" au lieu du "Prix public (base)".

**Fichier modifié**: `/app/frontend/src/pages/Supplies.js` (lignes 1108-1117)
- Label changé de "P. Public (base)" à "P. Public Modifié"
- Affiche la valeur de `itemForm.prix_public_modifie` si elle existe
- Sinon, affiche le prix calculé (Prix Cession × Coefficient)

### Gestion des Dettes Fournisseurs (9 Février 2026) - ✅ IMPLÉMENTÉ
**Nouvelle fonctionnalité** permettant de gérer les créances envers les fournisseurs (admin uniquement).

**Fonctionnalités:**
1. **Création automatique**: Une dette est créée quand un approvisionnement est validé
2. **Paiement partiel ou total**: Modes de paiement (Espèces, Virement, Chèque)
3. **Identification des retards**: Dettes > 3 mois marquées "En retard"
4. **Abandon de dette**: Possibilité d'annuler une dette avec justification

**Fichiers créés:**
- `/app/backend/routes/supplier_debts.py` - API complète (GET, POST payment, POST write-off)
- `/app/backend/database/models_tenant.py` - Modèle `SupplierDebt`
- `/app/frontend/src/pages/SupplierDebts.js` - Interface utilisateur

**API Endpoints:**
- `GET /api/supplier-debts` - Liste avec stats et filtres
- `GET /api/supplier-debts/{id}` - Détails d'une dette
- `POST /api/supplier-debts/{id}/payment` - Enregistrer un paiement
- `POST /api/supplier-debts/{id}/write-off` - Abandonner une dette

### Corrections Migration PostgreSQL (2 Février 2026)
1. **max_debt_limit** ajouté au modèle Customer
2. **Routes Update** corrigées (CustomerUpdate, CategoryUpdate, UnitUpdate)
3. **flag_modified** ajouté pour persistance JSON des dettes
4. **Stock initialisé** via validation des 7 approvisionnements
5. **Approvisionnements** corrigés (purchase_price, suppression lot_number)
6. **_to_dict_customer** mis à jour avec max_debt_limit et updated_at

## Endpoints API Principaux
- `/api/auth/login` - Authentification
- `/api/products`, `/api/products/paginated` - Produits
- `/api/customers` - Clients (avec max_debt_limit)
- `/api/sales` - Ventes
- `/api/supplies`, `/api/supplies/{id}/validate` - Approvisionnements
- `/api/debts`, `/api/debts/payment/bulk` - Dettes
- `/api/shifts/current`, `/api/shifts/open`, `/api/shifts/close` - Shifts
- `/api/reports/dashboard` - Dashboard

## Tâches Futures
### P1 - Priorité haute
- Rapports avancés (TVA collectée vs déductible, marges)
- Guide déploiement production (base de données de production requise)

### P2 - Priorité moyenne
- Intégration réelle Mobile Money API (actuellement **MOCKED**)
- Export PDF/Excel
- Refactoring de `Sales.js` (extraction de hooks personnalisés pour améliorer la maintenabilité)
- Déploiement mobile avec Capacitor
- Rappels automatiques SMS/email pour dettes
- Création suite pytest backend pour prévenir régressions

## Credentials de Test
- **Admin**: admin@pharmaflow.com / admin123
- **Pharmacien**: pharmacien@pharmaflow.com / pharma123
- **Caissier**: caissier@pharmaflow.com / caisse123

## Dernière mise à jour : 2026-02-15

### 🎉 LAYOUT RESPONSIVE (2026-02-15) - ✅ TERMINÉ
**Application entièrement responsive** pour mobile, tablette et desktop.

**Modifications Layout.js:**
- Header mobile avec bouton hamburger (visible < 768px)
- Menu drawer glissant depuis la gauche sur mobile
- Sidebar desktop (visible >= 768px) 
- Indicateur de sync positionné en bas sur mobile, en haut sur desktop
- Indicateur de shift adaptatif selon la taille d'écran

**Breakpoints Tailwind CSS utilisés:**
- Mobile: < 768px (`md:hidden`)
- Tablette/Desktop: >= 768px (`md:flex`)

**Tests effectués:**
- ✅ Mobile (375px): Hamburger, drawer, cartes empilées
- ✅ Tablette (768px): Sidebar complète, grille 2 colonnes
- ✅ Desktop (1920px): Sidebar complète, grille 5 colonnes

### 🆕 SCROLL INFINI - IMPLÉMENTATION COMPLÈTE (2026-02-02) - ✅ TERMINÉ

**Backend - Tous les endpoints paginés créés :**
| Module | Endpoint | Total | Status |
|--------|----------|-------|--------|
| Produits | `/api/products/paginated` | 40 | ✅ |
| Clients | `/api/customers/paginated` | 10 | ✅ |
| Fournisseurs | `/api/suppliers/paginated` | 5 | ✅ |
| Approvisionnements | `/api/supplies/paginated` | 7 | ✅ |
| Ordonnances | `/api/prescriptions/paginated` | 15 | ✅ |
| Dettes | `/api/debts/paginated` | 10 | ✅ |
| Mouvements Stock | `/api/stock/movements/paginated` | 117 | ✅ |
| Pertes Stock | `/api/stock/losses/paginated` | 27 | ✅ |
| Historique Shifts | `/api/shifts/paginated` | 1 | ✅ |
| Historique Prix | `/api/prices/history/paginated` | N/A | ✅ |

**Frontend - Pages avec scroll infini intégré :**
| Page | Fichier | Scroll Infini | Status |
|------|---------|---------------|--------|
| Produits | `Products.js` | `useProductsInfinite` | ✅ |
| Clients | `Customers.js` | `useCustomersInfinite` | ✅ |
| Fournisseurs | `Suppliers.js` | `useSuppliersInfinite` | ✅ |
| Approvisionnements | `Supplies.js` | `useSuppliesInfinite` | ✅ |
| Ordonnances | `Prescriptions.js` | `usePrescriptionsInfinite` | ✅ |
| Gestion des Pertes | `StockLosses.js` | `useStockLossesInfinite` | ✅ |
| Mouvements Stock | `StockMovements.js` | `useStockMovementsInfinite` | ✅ |
| Historique Shifts | `ShiftsHistory.js` | `useShiftsInfinite` | ✅ |

**Hooks & Composants créés :**
- `/app/frontend/src/hooks/useInfiniteScroll.js` - Hook générique + 10 hooks spécifiques
- `/app/frontend/src/components/InfiniteScrollLoader.jsx` - Composant UI réutilisable
- Exports ajoutés dans `/app/frontend/src/hooks/index.js`

**Pattern d'utilisation :**
```javascript
import { useCustomersInfinite } from '../hooks/useInfiniteScroll';

const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useCustomersInfinite({
  limit: 20,
  search: debouncedSearch,
  status: filterStatus
});

const items = data?.pages?.flatMap(page => page.items) || [];
const total = data?.pages?.[0]?.total || 0;
```

### SCROLL INFINI PAGE PRODUITS (2026-02-02) - ✅ TERMINÉ
Implémentation du scroll infini sur la page Produits :

**Backend :**
- Nouvel endpoint `/api/products/paginated` avec pagination serveur
- Supporte recherche, filtres par catégorie et statut
- Retourne `{ items, total, page, pages, has_next, has_prev }`

**Frontend :**
- Hook `useProductsInfinite` avec `useInfiniteQuery` de React Query
- `IntersectionObserver` pour chargement automatique au scroll
- Bouton "Charger plus" en fallback
- Indicateur "40 sur 40 produits affichés"
- Message "✓ Tous les produits ont été chargés" en fin de liste

### Corrections récentes
- **Bug Dashboard** : Corrigé l'incohérence de nommage entre API et frontend (by_payment_method vs by_payment)
- **Bug Ouverture Shift** : Supprimé la référence à `data.notes` inexistante dans ShiftOpen
- **Bug Invalid Date** : Normalisé les champs `expires_at` → `expected_end_time` dans l'API shifts
- **Bug Agent N/A** : Régénéré les données de test avec les agents correctement assignés

### 🎉 SUPPRESSION COMPLÈTE MongoDB (2026-02-02) - ✅ TERMINÉE
L'application est maintenant **100% PostgreSQL**. Tout le code MongoDB a été supprimé :

**Fichiers nettoyés :**
- `config.py` - Supprimé `MONGO_URL`, `DB_NAME`
- `auth.py` - Supprimé bloc `else` MongoDB (lignes 111-182)
- `server.py` - Supprimé import/appel `db_connection`
- `services/stock_service.py` - Réécrit en PostgreSQL pur
- `routes/inventory.py` - Supprimé bloc `else` MongoDB

**Fichiers supprimés (obsolètes) :**
- `database/data_access.py` - Couche abstraction dual-DB plus nécessaire
- `database/migrate_data.py` - Script migration MongoDB→PG
- `database/migrate_to_supabase.py` - Script migration Supabase
- `diagnose_login.py` - Script diagnostic MongoDB
- `create_demo_user.py` - Création user MongoDB
- `create_correct_user.py` - Création données démo MongoDB
- `create_demo_data.py` - Script données MongoDB
- `create_today_sales.py` - Ventes test MongoDB

**Résultat final :**
- 0 références `mongodb`, `pymongo`, `MongoClient`, `MONGO_URL`, `db_connection`
- Backend 100% PostgreSQL (Supabase)
- 107 ventes, 40 produits, 10 clients - données complètes

### Migration PostgreSQL (2026-02-02) - ✅ COMPLÉTÉE
- **Migration complète** : Toutes les routes MongoDB migrées vers PostgreSQL
- Routes migrées : `payment_methods.py`, `returns.py`, `stock.py`, `prices.py`, `stock_lots.py`, `sync.py`
- Nouvelle table créée : `sale_returns` pour les retours de ventes
- 18 tables PostgreSQL au total dans Supabase
- Toutes les APIs testées : ✅ 200 OK

## Énoncé du problème
Application de gestion de pharmacie multi-tenant, offline-first avec PWA React et backend FastAPI.

## Architecture technique
- **Frontend**: React PWA avec Shadcn/UI, TailwindCSS, React Query
- **Backend**: FastAPI avec **Supabase PostgreSQL** (migré depuis MongoDB, MongoDB complètement supprimé)
- **Base de données**: Supabase PostgreSQL (cloud persistant) - MongoDB supprimé
- **Auth**: JWT avec rôles (Admin, Pharmacien, Caissier)

## Configuration Supabase (NOUVEAU - 1er Fév 2026)
- **Projet**: DynSoftPharma
- **Région**: US West 2
- **Connection pooler**: aws-0-us-west-2.pooler.supabase.com:6543
- **Tables créées**: 17 tables (users, products, sales, categories, etc.)
- **Données migrées**: 5 users, 40 produits, 158 ventes, 10 catégories, 10 clients

## Fonctionnalités Principales

### Gestion des Produits
- CRUD produits avec catégories et TVA
- Gestion des stocks avec mouvements
- Alertes stock bas
- Coefficients de marge par catégorie

### Gestion des Ventes
- Panier avec calcul automatique des prix
- Multiple modes de paiement (Espèces, Carte, Orange Money, MTN Money, Chèque)
- Ventes à crédit avec gestion des dettes
- Ventes mixtes (paiement partiel + crédit)
- **NOUVEAU** : Ventes en attente (mise en pause et reprise)

### Ventes en Attente (NOUVEAU - 31 Jan 2026)
- Mettre une vente en attente pour y revenir plus tard
- Le stock n'est PAS affecté (uniquement à la finalisation)
- Ventes partagées entre tous les utilisateurs
- Expiration automatique après 24 heures
- Bouton "Mettre en attente" dans le formulaire
- Modale dédiée pour gérer les ventes en attente
- Actions : Reprendre, Supprimer

### Gestion des Approvisionnements
- Enregistrement des achats fournisseurs
- Calcul automatique des prix de vente (coefficient)
- Gestion TVA déductible

### Gestion des Dettes
- Suivi des créances clients
- Encaissement des remboursements
- Abandon de dettes (write-off)

### Gestion des Shifts
- Ouverture/fermeture de caisse obligatoire
- Blocage UI pour shifts expirés (non-admin)
- Extension de shift par l'admin

### Planification des Shifts (NOUVEAU - 1er Fév 2026)
- Calendrier de planification accessible uniquement par l'admin
- **Vues disponibles** :
  - Vue mensuelle (style Google Calendar)
  - Vue semaine (par utilisateur)
- **Informations planifiées** :
  - Date + horaires (début/fin)
  - Durée maximale du shift
  - Notes optionnelles
- **Contrôles à la connexion** :
  - Admin exempt (peut toujours ouvrir un shift)
  - Caissier/Pharmacien : vérification de planification ET horaires
  - **Restriction horaire** : impossible d'ouvrir avant l'heure de début ou après l'heure de fin
  - Bouton "Ouvrir le shift" grisé si non planifié ou hors horaires
  - Messages explicatifs différenciés :
    - Rouge : "Non planifié aujourd'hui"
    - Orange : "Hors horaires de travail" (avec horaires prévus affichés)
- **Fonctionnalités** :
  - Création individuelle ou en masse (planification rapide)
  - Modification/suppression des planifications
  - Heure de fin pré-remplie depuis la planification
- **Restrictions d'accès hors horaires** (NOUVEAU) :
  - Caissiers: pages `/sales`, `/pending-sales`, `/sales-history`, `/supplies`, `/customers`, `/stock-losses` restreintes
  - Pharmaciens: pages `/products`, `/suppliers`, `/prescriptions` restreintes
  - Bannière "Accès restreint - Hors horaires de travail" affichée
  - Tableau de bord toujours accessible
  - Admin exempt de toutes restrictions

### Tableau de Bord
- Statistiques temps réel
- Ventes par mode de paiement (différenciation Orange/MTN)
- Ventes partielles affichées séparément
- Graphiques 7 jours
- Alertes et informations rapides

## Changelog

### 4 Février 2026 - Correction Mobile Money (✅ COMPLÉTÉE)
- ✅ **Bug fix: Champs Mobile Money manquants**
  - Les champs "N° Destinataire" et "Réf. Paiement Marchand" apparaissent maintenant
  - Correction: Les données `required_fields` dans la table `payment_methods` étaient nulles
  - Orange Money et MTN Money fonctionnent correctement dans le formulaire de vente
  - Vérification OTP toujours fonctionnelle

### 1er Février 2026 - Migration Supabase PostgreSQL (✅ COMPLÉTÉE)
- ✅ **SUPABASE CLOUD CONFIGURÉ**
  - Projet: DynSoftPharma (US West 2)
  - 17 tables créées dans PostgreSQL cloud
  - Persistance garantie (données cloud)
  - Scripts: `init_supabase.py`, `migrate_to_supabase.py`

- ✅ **TOUTES LES ROUTES MIGRÉES (17/17)** :
  - Core: `auth.py`, `sales.py`, `products.py`, `shifts.py`, `settings.py`
  - CRUD: `categories.py`, `units.py`, `customers.py`, `suppliers.py`
  - Gestion: `users.py`, `prescriptions.py`, `debts.py`, `pending_sales.py`, `shift_schedules.py`
  - Opérations: `supplies.py`, `inventory.py`, `reports.py`

- **Données disponibles**: 5 users, 40 produits, 158 ventes, 9 clients, 10 catégories, 5 fournisseurs
  - Modèles SQLAlchemy complets (`/app/backend/database/models_tenant.py`)
  - Gestionnaire de connexions multi-tenant (`/app/backend/database/config.py`)
- ✅ **MIGRATION: Données MongoDB → PostgreSQL**
  - Script de migration exécuté (`/app/backend/database/migrate_data.py`)
  - Données migrées: 5 users, 10 catégories, 7 unités, 40 produits, 10 clients, 5 fournisseurs, 158 ventes, 7 approvisionnements, 11 ventes en attente
  - Conversion des ObjectID MongoDB en UUID PostgreSQL
  - Intégrité référentielle préservée (clés étrangères)
- ⏳ **EN COURS: Phase 2 - Adaptation du Backend**
  - Créer les repositories PostgreSQL
  - Adapter les routes API pour utiliser PostgreSQL
  - Tests de régression

### 1er Février 2026 - Migration PostgreSQL/Supabase (COMPLÉTÉE)
- ✅ **SUPABASE CONFIGURÉ ET FONCTIONNEL**
  - Projet Supabase créé: DynSoftPharma (US West 2)
  - 17 tables créées dans PostgreSQL cloud
  - Données migrées: 5 users, 40 produits, 158 ventes, 9 clients
  - Scripts créés: `init_supabase.py`, `migrate_to_supabase.py`
- ✅ **Routes critiques migrées (dual-database)** :
  - `auth.py` ✅ - Login, register, session
  - `sales.py` ✅ - Ventes (create, list, get)
  - `products.py` ✅ - Produits CRUD
  - `categories.py` ✅ - Catégories CRUD
  - `units.py` ✅ - Unités CRUD
  - `customers.py` ✅ - Clients CRUD
  - `suppliers.py` ✅ - Fournisseurs CRUD
  - `settings.py` ✅ - Paramètres
  - `shifts.py` ✅ - Shifts (ouverture/fermeture caisse)
  - `prescriptions.py` ✅ - Ordonnances
  - `users.py` ✅ - Gestion utilisateurs
- ⏳ **Routes restantes (fonctionnent en MongoDB)** :
  - `supplies.py` - Approvisionnements
  - `pending_sales.py` - Ventes en attente
  - `debts.py` - Dettes
  - `inventory.py` - Inventaire
  - `reports.py` - Rapports
  - `shift_schedules.py` - Planification shifts

### 1er Février 2026 - Migration PostgreSQL Phase 2 (TERMINÉE)
- ✅ **Couche d'abstraction créée** (`/app/backend/database/data_access.py`)
  - Classes DataAccess pour MongoDB et PostgreSQL
  - Basculement automatique via `DATABASE_TYPE` dans .env
  - Testé: les deux modes fonctionnent
- ✅ **Refactoring imports** 
  - Renommé `database.py` → `db_connection.py` (éviter conflit avec dossier)
  - Tous les imports mis à jour dans les routes
- ⏳ **EN COURS**: Adapter les routes pour utiliser DataAccess au lieu de `db` direct
  - Actuellement: routes utilisent encore MongoDB direct
  - Prochaine étape: migration progressive route par route
- **Note**: L'app fonctionne avec `DATABASE_TYPE=mongodb` (comportement actuel)
  - Pour activer PostgreSQL: changer à `DATABASE_TYPE=postgresql` dans .env
  - Nécessite d'adapter les routes une par une

### 1er Février 2026 - Restrictions d'accès Pharmaciens
- ✅ **Bug fix: Déclaration dupliquée isAdmin dans Products.js**
  - Suppression de la ligne 425 (déclaration en double)
  - Page Products fonctionne à nouveau
- ✅ **FEATURE: Restrictions d'accès pour Pharmaciens**
  - Pages `/products`, `/suppliers`, `/prescriptions` restreintes hors horaires
  - Bannière "Accès restreint - Hors horaires de travail" affichée
  - Tests automatisés: 7/7 passés (iteration_30.json)

### 1er Février 2026 - Planification des Shifts
- ✅ **FEATURE: Calendrier de planification des shifts**
  - Backend: Modèle `ShiftSchedule` + API complète (`/api/shift-schedules/*`)
  - Frontend: Page `/shift-schedules` avec vues mois/semaine
  - Hook `useShiftEligibility` pour vérification à l'ouverture de caisse
  - Modal d'ouverture modifié pour bloquer les non-planifiés
  - Tests automatisés: 15/15 passés

### 1er Février 2026 - Bug Fix Ventes en attente
- ✅ **Bug fix: Ventes en attente - Affichage agent**
  - Correction de l'affichage du code employé (ex: ADM-001) au lieu de l'email
  - Correction du calcul du total pour les nouvelles ventes en attente
  - Script de migration créé: `/app/backend/migrations/fix_pending_sales_data.py`
  - Tests automatisés: `/app/backend/tests/test_pending_sales.py`

### 31 Janvier 2026 - Session 2
- ✅ **Feature: Ventes en attente**
  - Backend: Modèle `PendingSale` + API complète
  - Frontend: Bouton "Mettre en attente" + Modale gestion
  - Expiration automatique 24h
  - Stock non affecté jusqu'à finalisation
  - Ventes partagées entre utilisateurs

### 31 Janvier 2026 - Session 1
- ✅ Bug fix: Bouton "Confirmer l'abandon" en vert
- ✅ Bug fix: Rafraîchissement automatique du solde après paiement
- ✅ Feature: Différenciation Orange Money / MTN Money
- ✅ Feature: Répartition des ventes mixtes par mode réel
- ✅ Bug fix: Affichage correct ventes partielles (X partielles vs X ventes)
- ✅ Data migration: ventes "mobile_money" converties

### Sessions Précédentes
- ✅ Gestion avancée des shifts (blocage UI, extension par admin)
- ✅ Inventaire physique avec filtre catégorie et impression
- ✅ Fix intégrité données script démo
- ✅ Fix mise à jour approvisionnements (520 error)
- ✅ Fix gestion des prix bulk update (route ordering)
- ✅ Fix calcul stocks théoriques inventaire
- ✅ Fix affichage employee_code dans mouvements stock

## Roadmap

### ✅ P0 - Critique (COMPLÉTÉ)
- [x] Migration backend vers PostgreSQL multi-tenant (100% MongoDB supprimé)
- [x] Scroll infini page Ventes
- [x] Scroll infini page Produits
- [x] Backend paginé pour TOUS les modules (10 endpoints)
- [x] Frontend scroll infini sur 7 pages principales

### P1 - Important
- [ ] Rapports avancés (TVA collectée vs déductible, marges)
- [ ] Export PDF/Excel des rapports
- [ ] Scroll infini sur pages restantes (Dettes dashboard, Pertes)

### P2 - Souhaitable
- [ ] Intégration réelle API Mobile Money (remplacer simulation OTP)
- [ ] Déploiement mobile (Capacitor)
- [ ] Rappels automatiques dettes en retard
- [ ] Notifications expiration ventes en attente
- [ ] Coefficient personnalisé par produit

## Credentials Test
- **Admin**: admin@pharmaflow.com / admin123
- **Pharmacien**: pharmacien@pharmaflow.com / pharma123
- **Caissier**: caissier@pharmaflow.com / caisse123

## Fichiers Clés
- `/app/frontend/src/pages/Sales.js` - Page ventes avec infinite scroll
- `/app/frontend/src/hooks/useSales.js` - Hook infinite scroll pour les ventes
- `/app/frontend/src/pages/ShiftSchedules.js` - Page calendrier planification shifts
- `/app/frontend/src/hooks/usePendingSales.js` - Hooks ventes en attente
- `/app/frontend/src/hooks/useShiftSchedules.js` - Hooks planification shifts
- `/app/frontend/src/components/ShiftModals.jsx` - Modal ouverture caisse avec vérification éligibilité
- `/app/backend/routes/pending_sales.py` - API ventes en attente
- `/app/backend/routes/shift_schedules.py` - API planification shifts
- `/app/backend/models/pending_sale.py` - Modèle ventes en attente
- `/app/backend/models/shift_schedule.py` - Modèle planification shifts
- `/app/backend/database/config.py` - Configuration PostgreSQL (Supabase)
- `/app/backend/database/repositories.py` - Repositories PostgreSQL
- `/app/backend/database/repositories_extended.py` - Repositories étendus (pagination)
- `/app/backend/scripts/generate_all_test_data.py` - Générateur de données PostgreSQL
- `/app/backend/scripts/create_indexes.py` - Script création index DB
- `/app/frontend/src/pages/Dashboard.js` - Tableau de bord
- `/app/backend/routes/reports.py` - API statistiques
- `/app/backend/routes/shifts.py` - API shifts
