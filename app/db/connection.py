"""SQLite connection management, transaction boundaries, and schema initialization."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_ORG_ID = "org_aarav"
DEFAULT_ORG_NAME = "Aarav Stores Demo Pvt. Ltd."
DEFAULT_STORES = [
    ("store_indiranagar", "Indiranagar Demo Store", "Indiranagar, Bengaluru"),
    ("store_koramangala", "Koramangala Demo Store", "Koramangala, Bengaluru"),
]
DEFAULT_BANK_ACCOUNTS = [
    ("bank_acc_4092", "Demo Business Account •••• 4092"),
]


def resolve_sqlite_path(database_url: str | None = None) -> str:
    """Extract and validate the SQLite file path or in-memory specifier from a URL."""
    url = database_url or get_settings().database_url
    if not url:
        url = "sqlite:///./data/settlesaathi.db"

    if url in (":memory:", "sqlite:///:memory:"):
        return ":memory:"

    if url.startswith("sqlite:///"):
        path_str = url[len("sqlite:///") :]
    elif url.startswith("sqlite://"):
        path_str = url[len("sqlite://") :]
    else:
        path_str = url

    # Remove query string if any without urlparse (which corrupts Windows drive letters like C:)
    raw_path = path_str.split("?")[0]

    path = Path(raw_path)
    if not path.is_absolute():
        path = Path.cwd() / path

    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


def get_db_path(database_url: str | None = None) -> str:
    """Return the resolved database path."""
    return resolve_sqlite_path(database_url)


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Create a new configured SQLite connection with foreign keys and WAL mode."""
    resolved_path = resolve_sqlite_path(db_path)
    conn = sqlite3.connect(
        resolved_path,
        isolation_level=None,  # Autocommit mode by default; manual transactions with BEGIN/COMMIT
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row

    # Enforce foreign keys and concurrency options
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    if resolved_path != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL;")

    return conn


@contextmanager
def db_session(db_path: str | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Provide a transactional database session that commits on success or rolls back on error."""
    conn = get_connection(db_path)
    try:
        conn.execute("BEGIN;")
        yield conn
        conn.execute("COMMIT;")
    except Exception:
        try:
            conn.execute("ROLLBACK;")
        except sqlite3.OperationalError:
            pass
        raise
    finally:
        conn.close()


def init_db(db_path: str | None = None) -> None:
    """Initialize schema tables and default demo reference entities."""
    schema_file = Path(__file__).parent / "schema.sql"
    if not schema_file.exists():
        raise FileNotFoundError(f"Schema file not found at {schema_file}")

    schema_sql = schema_file.read_text(encoding="utf-8")

    conn = get_connection(db_path)
    try:
        conn.executescript(schema_sql)

        # Ensure default organization exists
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM organizations WHERE id = ?", (DEFAULT_ORG_ID,))
        if not cursor.fetchone():
            now = datetime.now(UTC).isoformat()
            cursor.execute(
                "INSERT INTO organizations (id, name, created_at) VALUES (?, ?, ?);",
                (DEFAULT_ORG_ID, DEFAULT_ORG_NAME, now),
            )
            for store_id, name, loc in DEFAULT_STORES:
                cursor.execute(
                    """INSERT OR IGNORE INTO stores (
                        id, organization_id, name, location, created_at
                    ) VALUES (?, ?, ?, ?, ?);""",
                    (store_id, DEFAULT_ORG_ID, name, loc, now),
                )
            for acc_alias, acc_name in DEFAULT_BANK_ACCOUNTS:
                acc_id = f"acc_{acc_alias}"
                cursor.execute(
                    """INSERT OR IGNORE INTO bank_accounts (
                        id, organization_id, account_alias, account_name, created_at
                    ) VALUES (?, ?, ?, ?, ?);""",
                    (acc_id, DEFAULT_ORG_ID, acc_alias, acc_name, now),
                )
    finally:
        conn.close()
    logger.info("Database initialized successfully at %s", resolve_sqlite_path(db_path))


def reset_db(db_path: str | None = None) -> None:
    """Completely wipe and re-initialize the database for clean testing or resets."""
    resolved_path = resolve_sqlite_path(db_path)
    if resolved_path != ":memory:":
        p = Path(resolved_path)
        if p.exists():
            p.unlink(missing_ok=True)
        # Also clean WAL files
        Path(f"{resolved_path}-wal").unlink(missing_ok=True)
        Path(f"{resolved_path}-shm").unlink(missing_ok=True)
    init_db(db_path)
