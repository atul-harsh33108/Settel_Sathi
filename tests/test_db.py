"""Tests for database initialization, foreign key enforcement, and connection lifecycle."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.db.connection import db_session, get_connection, init_db, reset_db


def test_init_db_creates_tables_and_demo_seed(tmp_path: Path) -> None:
    db_file = tmp_path / "test_init.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    conn = get_connection(db_url)
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row[0] for row in cur.fetchall()}
        required = {
            "organizations",
            "stores",
            "bank_accounts",
            "source_artifacts",
            "import_jobs",
            "transactions",
            "settlement_batches",
            "settlement_line_items",
            "bank_entries",
            "mock_support_updates",
            "audit_events",
        }
        assert required.issubset(tables)

        # Check default organization
        cur.execute("SELECT name FROM organizations WHERE id = 'org_aarav';")
        org = cur.fetchone()
        assert org is not None
        assert org[0] == "Aarav Stores Demo Pvt. Ltd."

        # Check default stores
        cur.execute("SELECT id FROM stores;")
        store_ids = {row[0] for row in cur.fetchall()}
        assert "store_indiranagar" in store_ids
        assert "store_koramangala" in store_ids

        # Check default bank account
        cur.execute(
            "SELECT account_alias FROM bank_accounts WHERE account_alias = 'bank_acc_4092';"
        )
        bank = cur.fetchone()
        assert bank is not None
    finally:
        conn.close()


def test_foreign_keys_are_enforced(tmp_path: Path) -> None:
    db_file = tmp_path / "test_fk.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    conn = get_connection(db_url)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """INSERT INTO stores (id, organization_id, name, location, created_at)
                   VALUES (
                       'store_ghost', 'org_ghost', 'Ghost Store', 'Nowhere', '2026-10-31T00:00:00Z'
                   );"""
            )
    finally:
        conn.close()


def test_db_session_rolls_back_on_error(tmp_path: Path) -> None:
    db_file = tmp_path / "test_rollback.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    with pytest.raises(RuntimeError):
        with db_session(db_url) as conn:
            conn.execute(
                """INSERT INTO organizations (id, name, created_at)
                   VALUES ('org_tmp', 'Temporary Org', '2026-10-31T00:00:00Z');"""
            )
            raise RuntimeError("Forced error for rollback test")

    conn = get_connection(db_url)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM organizations WHERE id = 'org_tmp';")
        assert cur.fetchone() is None
    finally:
        conn.close()


def test_reset_db_recreates_clean_schema(tmp_path: Path) -> None:
    db_file = tmp_path / "test_reset.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    conn = get_connection(db_url)
    conn.execute(
        """INSERT INTO organizations (id, name, created_at)
           VALUES ('org_extra', 'Extra Org', '2026-10-31T00:00:00Z');"""
    )
    conn.close()

    reset_db(db_url)

    conn2 = get_connection(db_url)
    try:
        cur = conn2.cursor()
        cur.execute("SELECT id FROM organizations WHERE id = 'org_extra';")
        assert cur.fetchone() is None
    finally:
        conn2.close()


def test_resolve_sqlite_path_preserves_windows_drive() -> None:
    from app.db.connection import resolve_sqlite_path

    # Windows drive path with sqlite:///
    resolved = resolve_sqlite_path("sqlite:///C:/test_storage/data.db?cache=shared")
    assert "C:" in resolved
    assert "test_storage" in resolved
    assert "?" not in resolved
