#!/bin/bash
# Script pour installer et initialiser PostgreSQL dans l'environnement Kubernetes
# Ce script doit être exécuté à chaque redémarrage du pod pour utiliser PostgreSQL

set -e

echo "=============================================="
echo "🚀 Installation et Configuration PostgreSQL"
echo "=============================================="

# 1. Installer PostgreSQL
echo "📦 Installation de PostgreSQL..."
apt-get update -qq
apt-get install -y -qq postgresql postgresql-contrib

# 2. Démarrer PostgreSQL
echo "🔧 Démarrage de PostgreSQL..."
pg_ctlcluster 15 main start
sleep 2

# 3. Vérifier que PostgreSQL est prêt
echo "✅ Vérification de PostgreSQL..."
pg_isready

# 4. Créer l'utilisateur et les bases de données
echo "🗄️ Création des bases de données..."
sudo -u postgres psql -c "CREATE USER pharmaflow_admin WITH PASSWORD 'PharmaFlow2024!Secure' SUPERUSER;" 2>/dev/null || echo "User already exists"
sudo -u postgres psql -c "CREATE DATABASE pharmaflow_master OWNER pharmaflow_admin;" 2>/dev/null || echo "Master DB already exists"
sudo -u postgres psql -c "CREATE DATABASE tenant_pharmacie_centrale OWNER pharmaflow_admin;" 2>/dev/null || echo "Tenant DB already exists"

# 5. Initialiser les tables
echo "📋 Initialisation des tables..."
cd /app/backend
python database/init_db.py

# 6. Migrer les données depuis MongoDB
echo "🔄 Migration des données MongoDB → PostgreSQL..."
python database/migrate_data.py

# 7. Mettre à jour le fichier .env pour utiliser PostgreSQL
echo "⚙️ Configuration du backend pour PostgreSQL..."
sed -i 's/DATABASE_TYPE="mongodb"/DATABASE_TYPE="postgresql"/' /app/backend/.env

# 8. Redémarrer le backend
echo "🔄 Redémarrage du backend..."
sudo supervisorctl restart backend
sleep 3

echo "=============================================="
echo "✅ PostgreSQL est prêt !"
echo "=============================================="
echo ""
echo "Pour vérifier : pg_isready"
echo "Pour revenir à MongoDB : sed -i 's/DATABASE_TYPE=\"postgresql\"/DATABASE_TYPE=\"mongodb\"/' /app/backend/.env && sudo supervisorctl restart backend"
