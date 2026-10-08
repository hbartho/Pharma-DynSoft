"""
Modèles Master (schéma public) - Gestion des pharmacies (tenants) et annuaire global des utilisateurs.
"""

from sqlalchemy import Column, String, Boolean, Text, JSON
from database.base import Base, UUIDMixin, TimestampMixin


class Tenant(Base, UUIDMixin, TimestampMixin):
    """Modèle pour les tenants (pharmacies) dans la base master."""
    
    __tablename__ = "tenants"
    __table_args__ = {"schema": "public", "extend_existing": True}
    
    # Identifiant unique du tenant (utilisé pour le nom du schéma)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    
    # Informations de la pharmacie
    name = Column(String(255), nullable=False)
    address = Column(Text, nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    
    # Configuration
    is_active = Column(Boolean, default=True, nullable=False)
    settings = Column(JSON, default=dict, nullable=False)
    
    # Nom du schéma / base de données
    database_name = Column(String(255), nullable=False)
    
    def __repr__(self):
        return f"<Tenant(slug='{self.slug}', name='{self.name}')>"


class UserDirectory(Base, UUIDMixin, TimestampMixin):
    """Annuaire global email -> pharmacie (et comptes super admin plateforme)."""
    
    __tablename__ = "user_directory"
    __table_args__ = {"schema": "public", "extend_existing": True}
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    tenant_slug = Column(String(100), nullable=True, index=True)
    is_super_admin = Column(Boolean, default=False, nullable=False)
    password_hash = Column(String(255), nullable=True)  # uniquement pour les super admins
    name = Column(String(255), nullable=True)
    
    def __repr__(self):
        return f"<UserDirectory(email='{self.email}', tenant='{self.tenant_slug}', super_admin={self.is_super_admin})>"
