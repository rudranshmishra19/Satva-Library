import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "fallback_secret"

    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_POOL_RECYCLE = 280
    SQLALCHEMY_POOL_TIMEOUT = 10
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}
