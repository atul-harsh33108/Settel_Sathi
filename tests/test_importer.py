"""Unit and integration tests for the import pipeline, idempotency, and negative fixtures."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from app.db.connection import get_connection, init_db
from app.models.domain import parse_money
from app.services import repository
from app.services.importer import ImportService

FIXTURES_DIR = Path("fixtures/synthetic/v1")
INVALID_DIR = FIXTURES_DIR / "invalid"


def test_money_parsing_strictness() -> None:
    # Valid exact money
    assert parse_money("1500.00") == Decimal("1500.00")
    assert parse_money("-200.00") == Decimal("-200.00")
    assert parse_money("0.00") == Decimal("0.00")

    # Invalid formats rejected
    invalid_cases = ["18.45.00", "1500", "1500.5", "1500.000", "abc", 1500.0, 1500]
    for case in invalid_cases:
        try:
            parse_money(case)
            raise AssertionError(f"Expected ValueError for '{case}'")
        except ValueError:
            pass


def test_import_v1_bundle_and_verify_counts(tmp_path: Path) -> None:
    db_file = tmp_path / "test_bundle.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    service = ImportService(db_path=db_url, storage_dir=tmp_path / "storage")
    jobs = service.import_bundle(FIXTURES_DIR, organization_id="org_aarav")

    assert len(jobs) == 5
    for j in jobs:
        assert j.status == "COMPLETED", f"Job for {j.source_type} failed: {j.errors_json}"
        assert j.error_count == 0
        assert j.idempotent_replay is False

    conn = get_connection(db_url)
    try:
        counts = repository.get_financial_counts(conn, "org_aarav")
        assert counts["transactions"] == 20
        assert counts["settlements"] == 11
        assert counts["settlement_line_items"] == 21
        assert counts["bank_entries"] == 6
        assert counts["mock_support_updates"] == 2
        assert counts["source_artifacts"] == 5

        # Invariant check: net_amount == gross - fee - tax + adj for all settlements
        cur = conn.cursor()
        cur.execute(
            """SELECT gross_amount, fee_amount, tax_amount, adjustment_amount, net_amount
               FROM settlement_batches WHERE organization_id = 'org_aarav'"""
        )
        for g_str, f_str, t_str, a_str, n_str in cur.fetchall():
            gross = Decimal(g_str)
            fee = Decimal(f_str)
            tax = Decimal(t_str)
            adj = Decimal(a_str)
            net = Decimal(n_str)
            diff = gross - fee - tax + adj
            assert net == diff, f"Invariant failed: {net} != {diff}"

        # Provenance check: every transaction must link to an artifact and have a source row number
        cur.execute(
            """SELECT t.id, t.source_artifact_id, t.source_row_number, a.sha256
               FROM transactions t
               JOIN source_artifacts a ON t.source_artifact_id = a.id
               WHERE t.organization_id = 'org_aarav'"""
        )
        txns = cur.fetchall()
        assert len(txns) == 20
        for _, art_id, row_num, sha in txns:
            assert art_id
            assert row_num >= 2
            assert len(sha) == 64
    finally:
        conn.close()


def test_idempotent_reimport_returns_existing_job(tmp_path: Path) -> None:
    db_file = tmp_path / "test_idempotency.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    service = ImportService(db_path=db_url, storage_dir=tmp_path / "storage")

    # Initial import
    jobs_1 = service.import_bundle(FIXTURES_DIR, organization_id="org_aarav")
    for j in jobs_1:
        assert j.status == "COMPLETED"
        assert j.idempotent_replay is False

    conn = get_connection(db_url)
    counts_before = repository.get_financial_counts(conn, "org_aarav")
    conn.close()

    # Re-import identical bundle
    jobs_2 = service.import_bundle(FIXTURES_DIR, organization_id="org_aarav")
    for j in jobs_2:
        assert j.status == "COMPLETED"
        assert j.idempotent_replay is True

    conn2 = get_connection(db_url)
    counts_after = repository.get_financial_counts(conn2, "org_aarav")
    conn2.close()

    # Counts must remain completely unchanged
    assert counts_before == counts_after


def test_conflict_detection_prevents_silent_overwrite(tmp_path: Path) -> None:
    db_file = tmp_path / "test_conflict.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    service = ImportService(db_path=db_url, storage_dir=tmp_path / "storage")

    # 1. Import valid transactions
    txn_file = FIXTURES_DIR / "transactions.csv"
    job_1 = service.import_file(
        content=txn_file.read_bytes(),
        file_name="transactions.csv",
        source_type="TRANSACTIONS",
        organization_id="org_aarav",
    )
    assert job_1.status == "COMPLETED"

    # 2. Modify one line to create a different hash, retaining existing provider_transaction_id
    hdr = (
        "provider,provider_transaction_id,merchant_reference,store_id,"
        "occurred_at,status,payment_method,gross_amount,currency\n"
    )
    row = (
        "PAYTM_MOCK,mock_txn_scn01_001,mock_ord_new,store_indiranagar,"
        "2026-10-28T09:30:00Z,SUCCESS,UPI,9999.00,INR\n"
    )
    modified_csv = hdr + row

    job_2 = service.import_file(
        content=modified_csv.encode("utf-8"),
        file_name="conflicting_transactions.csv",
        source_type="TRANSACTIONS",
        organization_id="org_aarav",
    )
    assert job_2.status == "FAILED"
    assert job_2.error_count > 0
    assert "CONFLICT" in job_2.errors_json


def test_negative_fixture_duplicate_rows(tmp_path: Path) -> None:
    db_file = tmp_path / "test_neg_dup.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    service = ImportService(db_path=db_url, storage_dir=tmp_path / "storage")
    path = INVALID_DIR / "duplicate_rows.csv"
    job = service.import_file(
        content=path.read_bytes(),
        file_name="duplicate_rows.csv",
        source_type="BANK_STATEMENT",
        organization_id="org_aarav",
    )
    assert job.status == "FAILED"
    errors = json.loads(job.errors_json)
    codes = [e["code"] for e in errors]
    assert "DUPLICATE_IDENTIFIER" in codes

    conn = get_connection(db_url)
    counts = repository.get_financial_counts(conn, "org_aarav")
    conn.close()
    assert counts["bank_entries"] == 0


def test_negative_fixture_invalid_date(tmp_path: Path) -> None:
    db_file = tmp_path / "test_neg_date.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    service = ImportService(db_path=db_url, storage_dir=tmp_path / "storage")
    path = INVALID_DIR / "invalid_date.csv"
    job = service.import_file(
        content=path.read_bytes(),
        file_name="invalid_date.csv",
        source_type="SETTLEMENTS",
        organization_id="org_aarav",
    )
    assert job.status == "FAILED"
    errors = json.loads(job.errors_json)
    codes = [e["code"] for e in errors]
    assert "INVALID_DATE" in codes

    conn = get_connection(db_url)
    counts = repository.get_financial_counts(conn, "org_aarav")
    conn.close()
    assert counts["settlements"] == 0


def test_negative_fixture_malformed_decimal(tmp_path: Path) -> None:
    db_file = tmp_path / "test_neg_dec.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    service = ImportService(db_path=db_url, storage_dir=tmp_path / "storage")
    path = INVALID_DIR / "malformed_decimal.csv"
    job = service.import_file(
        content=path.read_bytes(),
        file_name="malformed_decimal.csv",
        source_type="TRANSACTIONS",
        organization_id="org_aarav",
    )
    assert job.status == "FAILED"
    errors = json.loads(job.errors_json)
    codes = [e["code"] for e in errors]
    assert "INVALID_AMOUNT" in codes

    conn = get_connection(db_url)
    counts = repository.get_financial_counts(conn, "org_aarav")
    conn.close()
    assert counts["transactions"] == 0


def test_negative_fixture_missing_required_field(tmp_path: Path) -> None:
    db_file = tmp_path / "test_neg_req.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    service = ImportService(db_path=db_url, storage_dir=tmp_path / "storage")
    path = INVALID_DIR / "missing_required_field.csv"
    job = service.import_file(
        content=path.read_bytes(),
        file_name="missing_required_field.csv",
        source_type="TRANSACTIONS",
        organization_id="org_aarav",
    )
    assert job.status == "FAILED"
    errors = json.loads(job.errors_json)
    codes = [e["code"] for e in errors]
    assert "MISSING_FIELD" in codes

    conn = get_connection(db_url)
    counts = repository.get_financial_counts(conn, "org_aarav")
    conn.close()
    assert counts["transactions"] == 0


def test_negative_fixture_unmatched_reference(tmp_path: Path) -> None:
    db_file = tmp_path / "test_neg_ref.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    service = ImportService(db_path=db_url, storage_dir=tmp_path / "storage")
    path = INVALID_DIR / "unmatched_reference.csv"
    job = service.import_file(
        content=path.read_bytes(),
        file_name="unmatched_reference.csv",
        source_type="SETTLEMENT_LINE_ITEMS",
        organization_id="org_aarav",
    )
    assert job.status == "FAILED"
    errors = json.loads(job.errors_json)
    codes = [e["code"] for e in errors]
    assert "UNMATCHED_REFERENCE" in codes

    conn = get_connection(db_url)
    counts = repository.get_financial_counts(conn, "org_aarav")
    conn.close()
    assert counts["settlement_line_items"] == 0


def test_negative_fixture_unsupported_currency(tmp_path: Path) -> None:
    db_file = tmp_path / "test_neg_curr.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    service = ImportService(db_path=db_url, storage_dir=tmp_path / "storage")
    path = INVALID_DIR / "unsupported_currency.csv"
    job = service.import_file(
        content=path.read_bytes(),
        file_name="unsupported_currency.csv",
        source_type="TRANSACTIONS",
        organization_id="org_aarav",
    )
    assert job.status == "FAILED"
    errors = json.loads(job.errors_json)
    codes = [e["code"] for e in errors]
    assert "UNSUPPORTED_CURRENCY" in codes

    conn = get_connection(db_url)
    counts = repository.get_financial_counts(conn, "org_aarav")
    conn.close()
    assert counts["transactions"] == 0


def test_settlement_balance_invariant_violation(tmp_path: Path) -> None:
    db_file = tmp_path / "test_balance_err.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    service = ImportService(db_path=db_url, storage_dir=tmp_path / "storage")
    hdr = (
        "provider,provider_settlement_id,payout_reference,settlement_date,"
        "reported_status,gross_amount,fee_amount,tax_amount,adjustment_amount,net_amount,currency\n"
    )
    # Net should be 10000 - 100 - 18 = 9882.00, but is set to 9500.00
    bad_row = (
        "PAYTM_MOCK,mock_settle_bad_inv,mock_utr_001,2026-10-29,"
        "PROCESSED,10000.00,100.00,18.00,0.00,9500.00,INR\n"
    )
    content = (hdr + bad_row).encode("utf-8")

    job = service.import_file(
        content=content,
        file_name="bad_settlement.csv",
        source_type="SETTLEMENTS",
        organization_id="org_aarav",
    )
    assert job.status == "FAILED"
    assert job.total_records == 1
    assert job.processed_records == 0
    assert job.error_count == 1
    errors = json.loads(job.errors_json)
    assert errors[0]["code"] == "BALANCE_INVARIANT_VIOLATION"

    conn = get_connection(db_url)
    counts = repository.get_financial_counts(conn, "org_aarav")
    conn.close()
    assert counts["settlements"] == 0


def test_unsupported_schema_version_rejected(tmp_path: Path) -> None:
    db_file = tmp_path / "test_ver_err.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    service = ImportService(db_path=db_url, storage_dir=tmp_path / "storage")
    txn_file = FIXTURES_DIR / "transactions.csv"
    job = service.import_file(
        content=txn_file.read_bytes(),
        file_name="transactions.csv",
        source_type="TRANSACTIONS",
        organization_id="org_aarav",
        schema_version="99.0",
    )
    assert job.status == "FAILED"
    assert "UNSUPPORTED_SCHEMA_VERSION" in job.errors_json


def test_unknown_store_rejected(tmp_path: Path) -> None:
    db_file = tmp_path / "test_store_err.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    service = ImportService(db_path=db_url, storage_dir=tmp_path / "storage")
    hdr = (
        "provider,provider_transaction_id,merchant_reference,store_id,"
        "occurred_at,status,payment_method,gross_amount,currency\n"
    )
    row = (
        "PAYTM_MOCK,mock_txn_store_err,mock_ord_001,store_ghost,"
        "2026-10-29T10:00:00Z,SUCCESS,UPI,1000.00,INR\n"
    )
    content = (hdr + row).encode("utf-8")

    job = service.import_file(
        content=content,
        file_name="transactions.csv",
        source_type="TRANSACTIONS",
        organization_id="org_aarav",
    )
    assert job.status == "FAILED"
    assert job.total_records == 1
    assert job.processed_records == 0
    errors = json.loads(job.errors_json)
    assert any(e["code"] == "UNKNOWN_STORE" for e in errors)

    conn = get_connection(db_url)
    counts = repository.get_financial_counts(conn, "org_aarav")
    conn.close()
    assert counts["transactions"] == 0


def test_unknown_bank_account_rejected(tmp_path: Path) -> None:
    db_file = tmp_path / "test_bank_alias_err.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    service = ImportService(db_path=db_url, storage_dir=tmp_path / "storage")
    hdr = (
        "statement_entry_id,bank_account_alias,booking_date,direction,"
        "amount,currency,narration,utr_reference\n"
    )
    row = "mock_bank_acc_err,bank_acc_ghost,2026-10-29,CREDIT,5000.00,INR,NEFT-PAYTM,mock_utr_001\n"
    content = (hdr + row).encode("utf-8")

    job = service.import_file(
        content=content,
        file_name="bank_statement.csv",
        source_type="BANK_STATEMENT",
        organization_id="org_aarav",
    )
    assert job.status == "FAILED"
    assert job.total_records == 1
    assert job.processed_records == 0
    errors = json.loads(job.errors_json)
    assert any(e["code"] == "UNKNOWN_BANK_ACCOUNT" for e in errors)

    conn = get_connection(db_url)
    counts = repository.get_financial_counts(conn, "org_aarav")
    conn.close()
    assert counts["bank_entries"] == 0


def test_conflict_detection_support_updates(tmp_path: Path) -> None:
    db_file = tmp_path / "test_sup_conflict.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    service = ImportService(db_path=db_url, storage_dir=tmp_path / "storage")
    sup_file = FIXTURES_DIR / "mock_support_updates.json"
    job_1 = service.import_file(
        content=sup_file.read_bytes(),
        file_name="mock_support_updates.json",
        source_type="MOCK_SUPPORT_UPDATES",
        organization_id="org_aarav",
    )
    assert job_1.status == "COMPLETED"

    # Ingest modified json with different hash but conflicting (case_reference, event_at)
    conflicting_json = json.dumps(
        [
            {
                "case_reference": "mock_case_scn09_001",
                "event_at": "2026-10-29T16:00:00Z",
                "status": "REJECTED",
                "summary": "Different summary causing conflict",
                "terminal_outcome": True,
                "evidence_reference": "mock_ticket_ack_conflict",
            }
        ]
    ).encode("utf-8")

    job_2 = service.import_file(
        content=conflicting_json,
        file_name="conflicting_updates.json",
        source_type="MOCK_SUPPORT_UPDATES",
        organization_id="org_aarav",
    )
    assert job_2.status == "FAILED"
    assert "CONFLICT" in job_2.errors_json


def test_negative_fixture_exact_counts(tmp_path: Path) -> None:
    db_file = tmp_path / "test_exact_counts.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    service = ImportService(db_path=db_url, storage_dir=tmp_path / "storage")

    # duplicate_rows.csv has 2 data rows, 1 duplicate error
    job_dup = service.import_file(
        content=(INVALID_DIR / "duplicate_rows.csv").read_bytes(),
        file_name="duplicate_rows.csv",
        source_type="BANK_STATEMENT",
        organization_id="org_aarav",
    )
    assert job_dup.total_records == 2
    assert job_dup.processed_records == 0
    assert job_dup.error_count == 1

    # invalid_date.csv has 1 data row, 1 date error
    job_date = service.import_file(
        content=(INVALID_DIR / "invalid_date.csv").read_bytes(),
        file_name="invalid_date.csv",
        source_type="SETTLEMENTS",
        organization_id="org_aarav",
    )
    assert job_date.total_records == 1
    assert job_date.processed_records == 0
    assert job_date.error_count == 1

    # malformed_decimal.csv has 1 data row, 1 decimal error
    job_dec = service.import_file(
        content=(INVALID_DIR / "malformed_decimal.csv").read_bytes(),
        file_name="malformed_decimal.csv",
        source_type="TRANSACTIONS",
        organization_id="org_aarav",
    )
    assert job_dec.total_records == 1
    assert job_dec.processed_records == 0
    assert job_dec.error_count == 1


def test_unsupported_provider_rejected(tmp_path: Path) -> None:
    db_file = tmp_path / "test_prov_err.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    service = ImportService(db_path=db_url, storage_dir=tmp_path / "storage")
    hdr = (
        "provider,provider_transaction_id,merchant_reference,store_id,"
        "occurred_at,status,payment_method,gross_amount,currency\n"
    )
    row = (
        "STRIPE,mock_txn_prov_err,mock_ord_001,store_indiranagar,"
        "2026-10-29T10:00:00Z,SUCCESS,UPI,1000.00,INR\n"
    )
    content = (hdr + row).encode("utf-8")

    job = service.import_file(
        content=content,
        file_name="transactions.csv",
        source_type="TRANSACTIONS",
        organization_id="org_aarav",
    )
    assert job.status == "FAILED"
    errors = json.loads(job.errors_json)
    assert any(e["code"] == "UNSUPPORTED_PROVIDER" for e in errors)


def test_artifact_storage_path_traversal_prevention(tmp_path: Path) -> None:
    service = ImportService(storage_dir=tmp_path / "storage")
    saved_path = Path(service._save_artifact_content(b"test data", "a" * 64, "../../evil.csv"))
    assert saved_path.name == "evil.csv"
    assert str(tmp_path) in str(saved_path)
    assert ".." not in str(saved_path)


def test_manifest_checksum_mismatch_raises_error(tmp_path: Path) -> None:
    import shutil

    bundle_copy = tmp_path / "tampered_bundle"
    shutil.copytree(FIXTURES_DIR, bundle_copy)

    # Tamper with transactions.csv
    txn_file = bundle_copy / "transactions.csv"
    txn_file.write_text("tampered content", encoding="utf-8")

    db_url = f"sqlite:///{tmp_path / 'test_tamper.db'}"
    init_db(db_url)
    service = ImportService(db_path=db_url, storage_dir=tmp_path / "storage")

    try:
        service.import_bundle(bundle_copy)
        raise AssertionError("Expected ValueError on checksum mismatch")
    except ValueError as e:
        assert "Checksum mismatch" in str(e)
