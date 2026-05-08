"""
Modèle Tenant - Base de données Master

Gère la liste des pharmacies (tenants) dans le système.
"""

from sqlalchemy import Column, String, Boolean, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from database.base import Base, UUIDMixin, TimestampMixin


class Tenant(Base, UUIDMixin, TimestampMixin):
    """Modèle pour les tenants (pharmacies) dans la base master."""
    
    __tablename__ = "tenants"
    
    # Identifiant unique du tenant (utilisé pour le nom de la BD)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    
    # Informations de la pharmacie
    name = Column(String(255), nullable=False)
    address = Column(Text, nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    
    # Configuration
    is_active = Column(Boolean, default=True, nullable=False)
    settings = Column(JSON, default=dict, nullable=False)
    
    # Nom de la base de données (généré automatiquement)
    database_name = Column(String(255), nullable=False)
    
    def __repr__(self):
        return f"<Tenant(slug='{self.slug}', name='{self.name}')>"
