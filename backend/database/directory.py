"""Annuaire global des utilisateurs (email -> pharmacie) stocké dans le schéma public."""
import uuid
import logging
from sqlalchemy import func

from database.config import db_manager
from database.models_master import UserDirectory, Tenant

logger = logging.getLogger(__name__)


def _entry_to_dict(entry: UserDirectory) -> dict:
    return {
        "id": str(entry.id),
        "email": entry.email,
        "tenant_slug": entry.tenant_slug,
        "is_super_admin": entry.is_super_admin,
        "password_hash": entry.password_hash,
        "name": entry.name,
    }


def get_directory_entry(email: str) -> dict:
    """Retourne l'entrée annuaire pour un email (ou None). Tolérant aux erreurs (table absente)."""
    if not email:
        return None
    try:
        with db_manager.get_master_session() as session:
            entry = session.query(UserDirectory).filter(
                func.lower(UserDirectory.email) == email.strip().lower()
            ).first()
            return _entry_to_dict(entry) if entry else None
    except Exception as e:
        logger.warning(f"directory lookup failed (fallback legacy): {e}")
        return None


def upsert_directory_entry(email: str, tenant_slug: str, is_super_admin: bool = False,
                           password_hash: str = None, name: str = None) -> bool:
    try:
        with db_manager.get_master_session() as session:
            entry = session.query(UserDirectory).filter(
                func.lower(UserDirectory.email) == email.strip().lower()
            ).first()
            if entry:
                entry.tenant_slug = tenant_slug
                entry.is_super_admin = is_super_admin
                if password_hash is not None:
                    entry.password_hash = password_hash
                if name is not None:
                    entry.name = name
            else:
                session.add(UserDirectory(
                    id=uuid.uuid4(),
                    email=email.strip().lower(),
                    tenant_slug=tenant_slug,
                    is_super_admin=is_super_admin,
                    password_hash=password_hash,
                    name=name,
                ))
            session.commit()
        return True
    except Exception as e:
        logger.error(f"directory upsert failed: {e}")
        return False


def remove_directory_entry(email: str) -> bool:
    try:
        with db_manager.get_master_session() as session:
            session.query(UserDirectory).filter(
                func.lower(UserDirectory.email) == email.strip().lower()
            ).delete(synchronize_session=False)
            session.commit()
        return True
    except Exception as e:
        logger.error(f"directory remove failed: {e}")
        return False


def remove_directory_entries_for_tenant(tenant_slug: str) -> bool:
    try:
        with db_manager.get_master_session() as session:
            session.query(UserDirectory).filter(
                UserDirectory.tenant_slug == tenant_slug
            ).delete(synchronize_session=False)
            session.commit()
        return True
    except Exception as e:
        logger.error(f"directory tenant cleanup failed: {e}")
        return False


def is_tenant_active(tenant_slug: str) -> bool:
    """Vérifie que la pharmacie est active. True par défaut si introuvable (legacy)."""
    try:
        with db_manager.get_master_session() as session:
            tenant = session.query(Tenant).filter(Tenant.slug == tenant_slug).first()
            if tenant is None:
                return True
            return bool(tenant.is_active)
    except Exception as e:
        logger.warning(f"tenant active check failed: {e}")
        return True
