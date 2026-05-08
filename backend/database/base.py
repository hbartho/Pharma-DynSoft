"""
SQLAlchemy Models - Base et Mixins

Définit les classes de base et mixins pour tous les modèles PostgreSQL.
"""

from sqlalchemy import Column, String, DateTime, Boolean, func
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone

Base = declarative_base()


class TimestampMixin:
    """Mixin pour ajouter created_at et updated_at à tous les modèles."""
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )


class UUIDMixin:
    """Mixin pour utiliser UUID comme clé primaire."""
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )


class SoftDeleteMixin:
    """Mixin pour la suppression logique (soft delete)."""
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
