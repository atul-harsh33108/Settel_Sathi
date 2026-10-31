"""Tests for offline CLI commands."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.cli import (
    cmd_approve_case,
    cmd_case_detail,
    cmd_cases,
    cmd_import_file,
    cmd_reconcile,
    cmd_reconciliation_results,
    cmd_reset,
    cmd_seed,
    cmd_status,
)
from app.db.connection import get_connection, init_db
from app.services import repository
from app.services.cases import CaseService
from app.services.policy import PolicyService


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


def test_cli_reconcile_and_results(tmp_path: Path, capsys) -> None:
    db_file = tmp_path / "cli_rec_test.db"
    db_url = f"sqlite:///{db_file}"

    # 1. Seed database first
    seed_args = DummyArgs(
        fixture_dir="fixtures/synthetic/v1",
        org_id="org_aarav",
        db_url=db_url,
    )
    cmd_seed(seed_args)
    capsys.readouterr()

    # 2. Run reconcile command
    rec_args = DummyArgs(
        org_id="org_aarav",
        as_of_date="2026-10-30",
        db_url=db_url,
    )
    cmd_reconcile(rec_args)
    rec_captured = capsys.readouterr()
    assert "completed successfully" in rec_captured.out
    assert "Total clusters: 10" in rec_captured.out
    assert "Total collected: 81450.00 INR" in rec_captured.out
    assert "SCN-02" in rec_captured.out
    assert "YES (Approval Req)" in rec_captured.out

    # 3. Run reconciliation-results command for latest run
    res_args = DummyArgs(
        org_id="org_aarav",
        run_id=None,
        status="UNMATCHED",
        db_url=db_url,
    )
    cmd_reconciliation_results(res_args)
    res_captured = capsys.readouterr()
    assert "Reconciliation results for run=" in res_captured.out
    assert "count=1" in res_captured.out
    assert "SCN-02" in res_captured.out


def test_cli_cases_and_detail(tmp_path: Path, capsys) -> None:
    db_file = tmp_path / "cli_cases.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    case_svc = CaseService(db_path=db_url)
    case = case_svc.create_case(
        organization_id="org_aarav",
        case_type="MISSING_SETTLEMENT",
        subject_id="txn_cli_01",
        decision_summary="Missing payout for SCN-02",
    )

    # Test cases list CLI
    cases_args = DummyArgs(org_id="org_aarav", status=None, db_url=db_url)
    cmd_cases(cases_args)
    captured = capsys.readouterr()
    assert case.id in captured.out
    assert "MISSING_SETTLEMENT" in captured.out
    assert "DETECTED" in captured.out

    # Test case detail CLI
    detail_args = DummyArgs(case_id=case.id, org_id="org_aarav", db_url=db_url)
    cmd_case_detail(detail_args)
    det_captured = capsys.readouterr()
    assert f"Case ID:        {case.id}" in det_captured.out
    assert "CASE_CREATED" in det_captured.out
    assert "Timeline Events (1)" in det_captured.out


def test_cli_approve_case(tmp_path: Path, capsys) -> None:
    db_file = tmp_path / "cli_appr.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    case_svc = CaseService(db_path=db_url)
    case = case_svc.create_case(organization_id="org_aarav", subject_id="txn_cli_02")

    policy_svc = PolicyService(db_path=db_url)
    appr = policy_svc.request_approval(
        case_id=case.id,
        action_type="SUBMIT_MOCK_SUPPORT_CASE",
        payload={"reason": "Missing payout"},
        organization_id="org_aarav",
    )

    # Approve via CLI
    appr_args = DummyArgs(
        case_id=case.id,
        approval_id=appr.id,
        actor_id="operator_cli",
        reject=False,
        reason=None,
        org_id="org_aarav",
        db_url=db_url,
    )
    cmd_approve_case(appr_args)
    captured = capsys.readouterr()
    assert "approved by 'operator_cli'" in captured.out

    # Test rejection via CLI on a fresh approval
    appr2 = policy_svc.request_approval(
        case_id=case.id,
        action_type="SUBMIT_MOCK_SUPPORT_CASE",
        payload={"reason": "Second ticket"},
        organization_id="org_aarav",
    )
    reject_args = DummyArgs(
        case_id=case.id,
        approval_id=appr2.id,
        actor_id="operator_cli",
        reject=True,
        reason="Not needed",
        org_id="org_aarav",
        db_url=db_url,
    )
    cmd_approve_case(reject_args)
    rej_captured = capsys.readouterr()
    assert "rejected by 'operator_cli'" in rej_captured.out
