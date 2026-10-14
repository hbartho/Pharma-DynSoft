"""Crée les tables master (public) et le compte Super Admin DynSoft.
Usage: python scripts/seed_super_admin.py [email] [password]
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def main():
    from database.config import db_manager, USE_SUPABASE
    from database.base import Base
    from database.models_master import Tenant, UserDirectory
    from database.directory import upsert_directory_entry
    from auth import hash_password

    if len(sys.argv) < 3:
        print("Usage: python scripts/seed_super_admin.py <email> <mot_de_passe>")
        print("Aucun mot de passe par défaut n'est accepté : il doit être fourni explicitement.")
        raise SystemExit(1)
    email = sys.argv[1].strip().lower()
    password = sys.argv[2]
    if len(password) < 8:
        raise SystemExit("Le mot de passe du super admin doit contenir au moins 8 caractères")

    engine = db_manager._engines["supabase"] if USE_SUPABASE else db_manager._engines["master"]
    Base.metadata.create_all(engine, tables=[Tenant.__table__, UserDirectory.__table__], checkfirst=True)
    print("Tables master OK (tenants, user_directory)")

    ok = upsert_directory_entry(
        email,
        tenant_slug=None,
        is_super_admin=True,
        password_hash=hash_password(password),
        name="DynSoft",
    )
    if not ok:
        raise SystemExit("Echec de la création du super admin")
    print(f"Super admin prêt: {email}")


if __name__ == "__main__":
    main()
