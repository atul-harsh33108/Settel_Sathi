"""Command line interface for local offline seeding, fixture import, and database management."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.db.connection import get_connection, init_db, reset_db
from app.services import repository
from app.services.importer import ImportService
from app.services.reconciliation import ReconciliationService


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


def cmd_reconcile(args: argparse.Namespace) -> None:
    """Execute deterministic reconciliation run."""
    db_url = getattr(args, "db_url", None)
    init_db(db_url)
    service = ReconciliationService(db_path=db_url)

    print(f"Running reconciliation for org={args.org_id} as-of-date={args.as_of_date}...")
    try:
        run_record, results = service.reconcile(
            organization_id=args.org_id,
            as_of_date=args.as_of_date,
        )
    except Exception as e:
        print(f"Reconciliation failed: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\nReconciliation run {run_record.id} completed successfully!")
    summary = json.loads(run_record.summary_counts_json or "{}")
    print(f"  Total clusters: {summary.get('total_clusters')}")
    print(f"  Total collected: {summary.get('total_collected')} INR")
    print(f"  Total settled: {summary.get('total_settled')} INR")
    print(f"  Total bank credit: {summary.get('total_bank_credited')} INR")
    print(f"  Total discrepancy: {summary.get('total_discrepancy')} INR")
    print(f"  Cases needed: {summary.get('cases_needed_count')}")

    print("\nResults by Scenario:")
    print(
        f"{'Scenario':<10} {'Status':<25} {'Collected':<12} "
        f"{'Settled':<12} {'Bank':<12} {'Case Needed'}"
    )
    print("-" * 80)
    for r in results:
        sc_id = r.scenario_id or "-"
        print(
            f"{sc_id:<10} {r.status:<25} {r.collected_amount:>10.2f} "
            f"{r.settled_amount:>10.2f} {r.bank_credited_amount:>10.2f}  "
            f"{'YES (Approval Req)' if r.case_needed else 'No'}"
        )


def cmd_reconciliation_results(args: argparse.Namespace) -> None:
    """View results of a reconciliation run."""
    db_url = getattr(args, "db_url", None)
    init_db(db_url)
    conn = get_connection(db_url)
    try:
        target_run_id = args.run_id
        if not target_run_id:
            latest = repository.find_latest_run(conn, args.org_id)
            if not latest:
                print(f"No reconciliation runs found for {args.org_id}. Run 'reconcile' first.")
                sys.exit(0)
            target_run_id = latest.id

        results = repository.list_reconciliation_results(
            conn,
            organization_id=args.org_id,
            run_id=target_run_id,
            status=args.status,
        )

        print(f"Reconciliation results for run={target_run_id} (count={len(results)}):")
        print(
            f"{'Scenario':<10} {'Status':<25} {'Collected':<12} "
            f"{'Settled':<12} {'Bank':<12} {'Case'}"
        )
        print("-" * 75)
        for r in results:
            sc_id = r.scenario_id or "-"
            print(
                f"{sc_id:<10} {r.status:<25} {r.collected_amount:>10.2f} "
                f"{r.settled_amount:>10.2f} {r.bank_credited_amount:>10.2f}  "
                f"{'YES' if r.case_needed else 'No'}"
            )
    finally:
        conn.close()


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

    # Reconcile
    rec_p = subparsers.add_parser("reconcile", help="Run deterministic reconciliation")
    rec_p.add_argument(
        "--as-of-date",
        default="2026-10-30",
        help="As-of evaluation date (YYYY-MM-DD)",
    )
    rec_p.add_argument("--org-id", default="org_aarav", help="Target organization ID")
    rec_p.add_argument("--db-url", default=None, help="Database URL override")
    rec_p.set_defaults(func=cmd_reconcile)

    # Reconciliation results
    res_p = subparsers.add_parser(
        "reconciliation-results",
        help="List reconciliation results for a run",
    )
    res_p.add_argument("--run-id", default=None, help="Run ID (defaults to latest)")
    res_p.add_argument("--status", default=None, help="Filter by status")
    res_p.add_argument("--org-id", default="org_aarav", help="Target organization ID")
    res_p.add_argument("--db-url", default=None, help="Database URL override")
    res_p.set_defaults(func=cmd_reconciliation_results)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
