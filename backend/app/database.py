import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

def _load_env_file() -> None:
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    if os.getenv("VERCEL"):
        raise RuntimeError("Set DATABASE_URL to a hosted PostgreSQL database in Vercel project settings.")
    SQLALCHEMY_DATABASE_URL = "sqlite:///./nc_prediction.db"

# Hosted providers commonly supply postgres:// or postgresql:// URLs.
# Select the psycopg 3 driver installed by the deployment requirements.
for prefix in ("postgres://", "postgresql://"):
    if SQLALCHEMY_DATABASE_URL.startswith(prefix):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace(prefix, "postgresql+psycopg://", 1)
        break

connect_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args, pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get db session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
