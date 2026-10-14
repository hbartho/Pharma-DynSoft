import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# JWT configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY manquant dans .env — refus de démarrer avec une clé par défaut")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# CORS configuration
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
