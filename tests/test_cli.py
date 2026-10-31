"""Tests for offline CLI commands."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.cli import cmd_import_file, cmd_reset, cmd_seed, cmd_status
from app.db.connection import get_connection, init_db
from app.services import repository


class DummyArgs:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_cli_seed_and_status(tmp_path: Path, capsys) -> None:
    db_file = tmp_path / "cli_test.db"
    db_url = f"sqlite:///{db_file}"

    # Run seed
    seed_args = DummyArgs(
        fixture_dir="fixtures/synthetic/v1",
        org_id="org_aarav",
        db_url=db_url,
    )
    cmd_seed(seed_args)
    captured = capsys.readouterr()
    assert "Seed completed successfully!" in captured.out
    assert "transactions: 20" in captured.out

    # Run status
    status_args = DummyArgs(org_id="org_aarav", db_url=db_url)
    cmd_status(status_args)
    status_captured = capsys.readouterr()
    assert "transactions: 20" in status_captured.out

    # Run reset
    reset_args = DummyArgs(db_url=db_url)
    cmd_reset(reset_args)
    reset_captured = capsys.readouterr()
    assert "Database reset and re-initialized successfully." in reset_captured.out

    # Verify counts after reset are 0
    conn = get_connection(db_url)
    counts = repository.get_financial_counts(conn, "org_aarav")
    conn.close()
    assert counts["transactions"] == 0


def test_cli_import_file(tmp_path: Path, capsys) -> None:
    db_file = tmp_path / "cli_file.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    file_path = Path("fixtures/synthetic/v1/bank_statement.csv")
    args = DummyArgs(
        file=str(file_path),
        type="BANK_STATEMENT",
        org_id="org_aarav",
        db_url=db_url,
    )
    cmd_import_file(args)
    captured = capsys.readouterr()
    assert "status=COMPLETED" in captured.out
    assert "processed=6" in captured.out


def test_cli_import_file_failure_exits(tmp_path: Path, capsys) -> None:
    db_file = tmp_path / "cli_file_err.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    file_path = Path("fixtures/synthetic/v1/invalid/malformed_decimal.csv")
    args = DummyArgs(
        file=str(file_path),
        type="TRANSACTIONS",
        org_id="org_aarav",
        db_url=db_url,
    )
    with pytest.raises(SystemExit):
        cmd_import_file(args)
    captured = capsys.readouterr()
    assert "status=FAILED" in captured.out
