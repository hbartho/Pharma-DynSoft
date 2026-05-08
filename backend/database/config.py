"""
PostgreSQL Multi-Tenant Database Configuration

Architecture:
- pharmaflow_master: Base de données centrale pour gérer les tenants
- tenant_<slug>: Une base de données séparée par pharmacie (tenant)

Chaque tenant a sa propre base de données pour une isolation maximale.
Pour Supabase: utilise une seule base avec schémas séparés.
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from contextlib import contextmanager, asynccontextmanager
from typing import Optional, Generator, AsyncGenerator
import logging

logger = logging.getLogger(__name__)

# Configuration PostgreSQL - Support Supabase et local
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "pharmaflow_admin")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "PharmaFlow2024!Secure")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")

# Déterminer si on utilise Supabase
USE_SUPABASE = bool(SUPABASE_URL and "supabase" in SUPABASE_URL)

# Base de données master pour la gestion des tenants
MASTER_DB_NAME = "pharmaflow_master"

def get_database_url(db_name: str = None, async_mode: bool = False) -> str:
    """Génère l'URL de connexion pour une base de données spécifique."""
    if USE_SUPABASE:
        # Pour Supabase, on utilise la même base pour tout (pas de multi-DB)
        base_url = SUPABASE_URL
        if async_mode:
            # Remplacer postgresql:// par postgresql+asyncpg://
            return base_url.replace("postgresql://", "postgresql+asyncpg://")
        else:
            return base_url.replace("postgresql://", "postgresql+psycopg2://")
    else:
        # Configuration locale avec bases séparées
        driver = "postgresql+asyncpg" if async_mode else "postgresql+psycopg2"
        return f"{driver}://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{db_name}"

def get_tenant_db_name(tenant_slug: str) -> str:
    """Génère le nom de la base de données pour un tenant."""
    if USE_SUPABASE:
        # Supabase: une seule base, on retourne "postgres"
        return "postgres"
    # Nettoyer le slug pour le nom de la BD
    clean_slug = tenant_slug.lower().replace(" ", "_").replace("-", "_")
    return f"tenant_{clean_slug}"


class DatabaseManager:
    """Gestionnaire de connexions multi-tenant PostgreSQL."""
    
    def __init__(self):
        self._engines: dict = {}
        self._async_engines: dict = {}
        self._session_factories: dict = {}
        self._async_session_factories: dict = {}
        
        # Initialiser la connexion (master pour local, postgres pour Supabase)
        self._init_connection()
    
    def _init_connection(self):
        """Initialise la connexion à la base de données."""
        if USE_SUPABASE:
            # Supabase: une seule connexion pour tout
            main_url = get_database_url()
            main_async_url = get_database_url(async_mode=True)
            key = "supabase"
        else:
            # Local: connexion master
            main_url = get_database_url(MASTER_DB_NAME)
            main_async_url = get_database_url(MASTER_DB_NAME, async_mode=True)
            key = "master"
        
        self._engines[key] = create_engine(main_url, pool_pre_ping=True)
        self._async_engines[key] = create_async_engine(main_async_url, pool_pre_ping=True)
        
        self._session_factories[key] = sessionmaker(
            bind=self._engines[key],
            autocommit=False,
            autoflush=False
        )
        self._async_session_factories[key] = async_sessionmaker(
            bind=self._async_engines[key],
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Alias pour compatibilité
        if USE_SUPABASE:
            self._engines["master"] = self._engines["supabase"]
            self._session_factories["master"] = self._session_factories["supabase"]
            self._async_engines["master"] = self._async_engines["supabase"]
            self._async_session_factories["master"] = self._async_session_factories["supabase"]
    
    def get_tenant_engine(self, tenant_slug: str):
        """Récupère ou crée le moteur SQLAlchemy pour un tenant."""
        if USE_SUPABASE:
            # Supabase: réutiliser la même connexion
            return self._engines.get("supabase") or self._engines.get("master")
        
        db_name = get_tenant_db_name(tenant_slug)
        
        if db_name not in self._engines:
            url = get_database_url(db_name)
            self._engines[db_name] = create_engine(url, pool_pre_ping=True)
            self._session_factories[db_name] = sessionmaker(
                bind=self._engines[db_name],
                autocommit=False,
                autoflush=False
            )
        
        return self._engines[db_name]
    
    def get_tenant_async_engine(self, tenant_slug: str):
        """Récupère ou crée le moteur async SQLAlchemy pour un tenant."""
        if USE_SUPABASE:
            # Supabase: réutiliser la même connexion
            return self._async_engines.get("supabase") or self._async_engines.get("master")
        
        db_name = get_tenant_db_name(tenant_slug)
        
        if db_name not in self._async_engines:
            url = get_database_url(db_name, async_mode=True)
            self._async_engines[db_name] = create_async_engine(url, pool_pre_ping=True)
            self._async_session_factories[db_name] = async_sessionmaker(
                bind=self._async_engines[db_name],
                class_=AsyncSession,
                expire_on_commit=False
            )
        
        return self._async_engines[db_name]
    
    @contextmanager
    def get_master_session(self) -> Generator[Session, None, None]:
        """Context manager pour une session master synchrone."""
        key = "supabase" if USE_SUPABASE else "master"
        session = self._session_factories[key]()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @asynccontextmanager
    async def get_master_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Context manager pour une session master asynchrone."""
        key = "supabase" if USE_SUPABASE else "master"
        session = self._async_session_factories[key]()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    @contextmanager
    def get_tenant_session(self, tenant_slug: str) -> Generator[Session, None, None]:
        """Context manager pour une session tenant synchrone."""
        if USE_SUPABASE:
            # Supabase: réutiliser la session principale
            key = "supabase"
        else:
            db_name = get_tenant_db_name(tenant_slug)
            self.get_tenant_engine(tenant_slug)  # S'assurer que l'engine existe
            key = db_name
        
        session = self._session_factories[key]()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    @asynccontextmanager
    async def get_tenant_async_session(self, tenant_slug: str) -> AsyncGenerator[AsyncSession, None]:
        """Context manager pour une session tenant asynchrone."""
        if USE_SUPABASE:
            # Supabase: réutiliser la session principale
            key = "supabase"
        else:
            db_name = get_tenant_db_name(tenant_slug)
            self.get_tenant_async_engine(tenant_slug)  # S'assurer que l'engine existe
            key = db_name
        
        session = self._async_session_factories[key]()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    def create_tenant_database(self, tenant_slug: str) -> bool:
        """Crée une nouvelle base de données pour un tenant."""
        db_name = get_tenant_db_name(tenant_slug)
        
        # Utiliser une connexion directe pour créer la BD
        # (CREATE DATABASE ne peut pas être dans une transaction)
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        try:
            conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                database="postgres"
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Vérifier si la BD existe déjà
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (db_name,)
            )
            if cursor.fetchone():
                logger.info(f"Database {db_name} already exists")
                return True
            
            # Créer la BD
            cursor.execute(f'CREATE DATABASE "{db_name}" OWNER {POSTGRES_USER}')
            logger.info(f"Created database {db_name}")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error creating database {db_name}: {e}")
            return False
    
    def drop_tenant_database(self, tenant_slug: str) -> bool:
        """Supprime la base de données d'un tenant (avec précaution)."""
        db_name = get_tenant_db_name(tenant_slug)
        
        # Fermer les connexions existantes
        if db_name in self._engines:
            self._engines[db_name].dispose()
            del self._engines[db_name]
        if db_name in self._async_engines:
            del self._async_engines[db_name]
        if db_name in self._session_factories:
            del self._session_factories[db_name]
        if db_name in self._async_session_factories:
            del self._async_session_factories[db_name]
        
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        try:
            conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                database="postgres"
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Terminer les connexions actives
            cursor.execute(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = %s
                AND pid <> pg_backend_pid()
            """, (db_name,))
            
            # Supprimer la BD
            cursor.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
            logger.info(f"Dropped database {db_name}")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error dropping database {db_name}: {e}")
            return False


# Instance globale du gestionnaire
db_manager = DatabaseManager()
