"""Backfill idempotent : annuaire user_directory + enregistrement Tenant pour la pharmacie centrale.
Usage: python scripts/backfill_directory.py
"""
import sys
import os
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def main():
    from database.config import db_manager, USE_SUPABASE
    from database.base import Base
    from database.models_master import Tenant, UserDirectory
    from database.models_tenant import User
    from database.repositories import SettingsRepository
    from database.tenant_context import DEFAULT_TENANT
    from sqlalchemy import func

    engine = db_manager._engines["supabase"] if USE_SUPABASE else db_manager._engines["master"]
    Base.metadata.create_all(engine, tables=[Tenant.__table__, UserDirectory.__table__], checkfirst=True)

    # 1. Enregistrer la pharmacie centrale comme tenant (schéma public)
    pharmacy_name = SettingsRepository(DEFAULT_TENANT).get("pharmacy_name") or "Pharmacie Centrale"
    with db_manager.get_master_session() as session:
        tenant = session.query(Tenant).filter(Tenant.slug == DEFAULT_TENANT).first()
        if not tenant:
            session.add(Tenant(
                id=uuid.uuid4(),
                slug=DEFAULT_TENANT,
                name=pharmacy_name,
                is_active=True,
                settings={},
                database_name="public",
            ))
            session.commit()
            print(f"Tenant '{DEFAULT_TENANT}' enregistré ({pharmacy_name})")
        else:
            print(f"Tenant '{DEFAULT_TENANT}' déjà présent")

    # 2. Backfill des utilisateurs de la pharmacie centrale dans l'annuaire
    added, fixed, skipped = 0, 0, 0
    with db_manager.get_tenant_session(DEFAULT_TENANT) as session:
        users = session.query(User).all()
        emails = [u.email for u in users if u.email]

    with db_manager.get_master_session() as session:
        for email in emails:
            norm = email.strip().lower()
            entry = session.query(UserDirectory).filter(func.lower(UserDirectory.email) == norm).first()
            if entry is None:
                session.add(UserDirectory(
                    id=uuid.uuid4(), email=norm, tenant_slug=DEFAULT_TENANT, is_super_admin=False,
                ))
                added += 1
            elif entry.is_super_admin:
                skipped += 1
            elif entry.tenant_slug != DEFAULT_TENANT:
                entry.tenant_slug = DEFAULT_TENANT
                fixed += 1
            else:
                skipped += 1
        session.commit()

    print(f"Annuaire: {added} ajouté(s), {fixed} corrigé(s), {skipped} déjà OK")


if __name__ == "__main__":
    main()
