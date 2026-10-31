"""Command line interface for local offline seeding, fixture import, and database management."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.db.connection import get_connection, init_db, reset_db
from app.services import repository
from app.services.importer import ImportService


def cmd_seed(args: argparse.Namespace) -> None:
    """Seed the database with certified synthetic fixtures."""
    db_url = getattr(args, "db_url", None)
    fixture_dir = Path(args.fixture_dir)
    if not fixture_dir.exists():
        alt_dir = Path("fixtures/synthetic/v1")
        if alt_dir.exists():
            fixture_dir = alt_dir
        else:
            print(f"Error: Fixture directory {fixture_dir} does not exist", file=sys.stderr)
            sys.exit(1)

    print(f"Initializing database and seeding from {fixture_dir}...")
    init_db(db_url)

    service = ImportService(db_path=db_url)
    try:
        jobs = service.import_bundle(fixture_dir, organization_id=args.org_id)
    except Exception as e:
        print(f"Failed to import bundle: {e}", file=sys.stderr)
        sys.exit(1)

    has_failure = False
    for job in jobs:
        status_str = (
            f"status={job.status} total={job.total_records} "
            f"processed={job.processed_records} errors={job.error_count}"
        )
        if job.idempotent_replay:
            status_str += " (idempotent replay)"
        print(f"  [{job.source_type}] {status_str}")
        if job.status == "FAILED":
            has_failure = True
            if job.errors_json:
                print(f"    Errors: {job.errors_json}")

    conn = get_connection(db_url)
    try:
        counts = repository.get_financial_counts(conn, args.org_id)
        print("\nDatabase current record counts:")
        for table, cnt in counts.items():
            print(f"  {table}: {cnt}")
    finally:
        conn.close()

    if has_failure:
        sys.exit(1)
    print("\nSeed completed successfully!")


def cmd_status(args: argparse.Namespace) -> None:
    """Show current record counts and recent jobs."""
    db_url = getattr(args, "db_url", None)
    init_db(db_url)
    conn = get_connection(db_url)
    try:
        counts = repository.get_financial_counts(conn, args.org_id)
        print("Record counts:")
        for table, cnt in counts.items():
            print(f"  {table}: {cnt}")

        print("\nRecent import jobs:")
        jobs = repository.list_import_jobs(conn, args.org_id, limit=5)
        for j in jobs:
            print(
                f"  [{j.id[:12]}] {j.source_type} status={j.status} "
                f"processed={j.processed_records}/{j.total_records} errors={j.error_count} "
                f"started={j.started_at}"
            )
    finally:
        conn.close()


def cmd_reset(args: argparse.Namespace) -> None:
    """Reset the database to clean initialized state."""
    db_url = getattr(args, "db_url", None)
    reset_db(db_url)
    print("Database reset and re-initialized successfully.")


def cmd_import_file(args: argparse.Namespace) -> None:
    """Import a single fixture file."""
    db_url = getattr(args, "db_url", None)
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File {file_path} does not exist", file=sys.stderr)
        sys.exit(1)

    init_db(db_url)
    service = ImportService(db_path=db_url)
    content = file_path.read_bytes()
    job = service.import_file(
        content=content,
        file_name=file_path.name,
        source_type=args.type,
        organization_id=args.org_id,
    )
    print(
        f"Import completed: job_id={job.id} status={job.status} "
        f"processed={job.processed_records} errors={job.error_count} "
        f"replay={job.idempotent_replay}"
    )
    if job.status == "FAILED" and job.errors_json:
        print(f"Errors: {job.errors_json}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="SettleSaathi CLI Operations")
    parser.add_argument("--db-url", default=None, help="Database URL override")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Seed
    seed_p = subparsers.add_parser("seed", help="Seed database with synthetic v1 fixtures")
    seed_p.add_argument(
        "--fixture-dir",
        default="serv_data/fixtures/v1",
        help="Path to fixture directory containing manifest.json",
    )
    seed_p.add_argument("--org-id", default="org_aarav", help="Target organization ID")
    seed_p.add_argument("--db-url", default=None, help="Database URL override")
    seed_p.set_defaults(func=cmd_seed)

    # Status
    status_p = subparsers.add_parser("status", help="Show database record status")
    status_p.add_argument("--org-id", default="org_aarav", help="Target organization ID")
    status_p.add_argument("--db-url", default=None, help="Database URL override")
    status_p.set_defaults(func=cmd_status)

    # Reset
    reset_p = subparsers.add_parser("reset", help="Reset and recreate database schema")
    reset_p.add_argument("--db-url", default=None, help="Database URL override")
    reset_p.set_defaults(func=cmd_reset)

    # Import file
    imp_p = subparsers.add_parser("import-file", help="Import a single file")
    imp_p.add_argument("--file", required=True, help="Path to file to import")
    imp_p.add_argument(
        "--type",
        choices=[
            "TRANSACTIONS",
            "SETTLEMENTS",
            "SETTLEMENT_LINE_ITEMS",
            "BANK_STATEMENT",
            "MOCK_SUPPORT_UPDATES",
        ],
        default=None,
        help="Explicit source type (inferred if omitted)",
    )
    imp_p.add_argument("--org-id", default="org_aarav", help="Target organization ID")
    imp_p.add_argument("--db-url", default=None, help="Database URL override")
    imp_p.set_defaults(func=cmd_import_file)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
