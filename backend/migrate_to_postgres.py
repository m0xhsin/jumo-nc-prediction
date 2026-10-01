"""Copy the bundled SQLite data to an empty hosted PostgreSQL database.

Run once from the project root with DATABASE_URL set:
    .venv/bin/python backend/migrate_to_postgres.py
Existing target data is never overwritten.
"""
from pathlib import Path

from sqlalchemy import create_engine, func, select

from app.database import Base, engine
from app.models import sensor  # Register all tables with Base.


def migrate():
    if engine.dialect.name != "postgresql":
        raise RuntimeError("Set DATABASE_URL to your hosted PostgreSQL connection string.")
    source_path = Path(__file__).resolve().parent / "nc_prediction.db"
    if not source_path.is_file():
        raise RuntimeError("The original nc_prediction.db is required; database files are not included in Git.")
    source = create_engine(f"sqlite:///file:{source_path}?mode=ro&uri=true")
    Base.metadata.create_all(engine)
    with source.connect() as old, engine.begin() as new:
        tables = Base.metadata.sorted_tables
        for table in tables:
            if new.scalar(select(func.count()).select_from(table)):
                raise RuntimeError(f"Target table {table.name} is not empty; no data copied.")
        for table in tables:
            rows = [dict(row) for row in old.execute(select(table)).mappings()]
            # Let PostgreSQL assign IDs so its sequences remain correct.
            # These tables have no foreign keys.
            for row in rows:
                row.pop("id", None)
            if rows:
                new.execute(table.insert(), rows)
            print(f"Copied {len(rows)} rows into {table.name}.")
    print("Migration complete.")


if __name__ == "__main__":
    migrate()
