import argparse
import os
import re
from pathlib import Path
from urllib.parse import quote_plus


ROOT_DIR = Path(__file__).resolve().parents[2]
APP_DIR = ROOT_DIR / "app"
ENV_PATH = APP_DIR / ".env"
INIT_SQL_PATH = APP_DIR / "migrations" / "init.sql"
RAW_DATA_DIR = ROOT_DIR / "raw_data"
CSV_FILENAME_FALLBACKS = {
    "partnumbers-utf8.csv": "Teilenummer-Part Number.csv",
}
CSV_ENCODINGS = {
    "Teilenummer-Part Number.csv": "cp850",
}

COPY_RE = re.compile(
    r"""
    COPY\s+(?P<table>[A-Za-z_][A-Za-z0-9_]*)\s*
    FROM\s+'(?P<source>[^']+)'\s*
    DELIMITER\s+'(?P<delimiter>[^']+)'\s*
    CSV\s+HEADER\s*;
    """,
    re.IGNORECASE | re.VERBOSE,
)


def load_env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_PATH.exists():
        return values

    unnamed_lines: list[str] = []
    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            unnamed_lines.append(line)
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

    # Some early project .env files stored the Supabase database password as
    # the first bare line. Prefer an explicit variable, but keep this fallback.
    if unnamed_lines and "SUPABASE_DB_PASSWORD" not in values:
        values["SUPABASE_DB_PASSWORD"] = unnamed_lines[0]

    for key, value in values.items():
        os.environ.setdefault(key, value)
    return values


def get_database_urls() -> list[str]:
    env = load_env_file()
    database_url = os.getenv("SUPABASE_URL") or env.get("SUPABASE_URL")
    if database_url:
        return [database_url]

    project_id = (
        os.getenv("SUPABASE_PROJECT_ID")
        or env.get("SUPABASE_PROJECT_ID")
        or env.get("SUPABASER_PROJECT_ID")
    )
    password = os.getenv("SUPABASE_DB_PASSWORD") or env.get("SUPABASE_DB_PASSWORD")
    region = os.getenv("SUPABASE_PROJECT_REGION") or env.get("SUPABASE_PROJECT_REGION")

    if not project_id or not password or not region:
        raise RuntimeError(
            "Missing database connection details. Add DATABASE_URL to app/.env, "
            "or set SUPABASE_PROJECT_ID, SUPABASE_PROJECT_REGION, and "
            "SUPABASE_DB_PASSWORD."
        )

    encoded_password = quote_plus(password)
    return [
        f"postgresql://postgres.{project_id}:{encoded_password}"
        f"@aws-0-{region}.pooler.supabase.com:6543/postgres?sslmode=require",
        f"postgresql://postgres:{encoded_password}"
        f"@db.{project_id}.supabase.co:5432/postgres?sslmode=require",
    ]


def local_csv_path(copy_source: str) -> Path:
    filename = Path(copy_source).name
    path = RAW_DATA_DIR / filename
    if not path.exists() and filename in CSV_FILENAME_FALLBACKS:
        path = RAW_DATA_DIR / CSV_FILENAME_FALLBACKS[filename]
    if not path.exists():
        raise FileNotFoundError(f"Could not find CSV for COPY source {copy_source}: {path}")
    return path


def iter_sql_parts(sql: str):
    cursor = 0
    for match in COPY_RE.finditer(sql):
        before = sql[cursor : match.start()].strip()
        if before:
            yield ("sql", before)
        yield ("copy", match.groupdict())
        cursor = match.end()

    remaining = sql[cursor:].strip()
    if remaining:
        yield ("sql", remaining)


def apply_migration(dry_run: bool = False) -> None:
    sql = INIT_SQL_PATH.read_text(encoding="utf-8")
    parts = list(iter_sql_parts(sql))

    if dry_run:
        sql_blocks = sum(1 for kind, _ in parts if kind == "sql")
        copy_blocks = sum(1 for kind, _ in parts if kind == "copy")
        print(f"Parsed {sql_blocks} SQL blocks and {copy_blocks} CSV imports.")
        for kind, payload in parts:
            if kind == "copy":
                csv_path = local_csv_path(payload["source"])
                print(f"Would import {csv_path} into {payload['table']}.")
        return

    import psycopg

    last_error: Exception | None = None
    for database_url in get_database_urls():
        try:
            conn = psycopg.connect(database_url)
            break
        except psycopg.OperationalError as exc:
            last_error = exc
    else:
        raise RuntimeError("Could not connect to Supabase Postgres.") from last_error

    with conn:
        with conn.cursor() as cur:
            for kind, payload in parts:
                if kind == "sql":
                    cur.execute(payload)
                    continue

                csv_path = local_csv_path(payload["source"])
                copy_sql = (
                    f"COPY {payload['table']} FROM STDIN "
                    f"WITH (FORMAT CSV, HEADER TRUE, DELIMITER '{payload['delimiter']}')"
                )
                print(f"Importing {csv_path.name} into {payload['table']}...")
                with cur.copy(copy_sql) as copy:
                    encoding = CSV_ENCODINGS.get(csv_path.name)
                    if encoding:
                        with csv_path.open("r", encoding=encoding, newline="") as file_obj:
                            while chunk := file_obj.read(1024 * 1024):
                                copy.write(chunk)
                    else:
                        with csv_path.open("rb") as file_obj:
                            while chunk := file_obj.read(1024 * 1024):
                                copy.write(chunk)
        conn.commit()

    print("Supabase init migration applied successfully.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply app/migrations/init.sql to Supabase and stream local CSV files."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse the migration and verify local CSV paths without connecting to Supabase.",
    )
    args = parser.parse_args()
    apply_migration(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
