"""Comprehensive deterministic reconciliation tests against the v1 test oracle."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from app.db.connection import get_connection, init_db
from app.models.domain import (
    BankEntryRecord,
    SettlementBatchRecord,
    SettlementLineItemRecord,
    SourceArtifactRecord,
    TransactionRecord,
    format_money,
)
from app.services import repository
from app.services.importer import ImportService
from app.services.reconciliation import ReconciliationService

FIXTURES_DIR = Path("fixtures/synthetic/v1")
ORACLE_FILE = FIXTURES_DIR / "expected_results.json"


def seed_test_database(tmp_path: Path) -> tuple[str, ImportService]:
    """Helper to initialize and seed a clean database for testing."""
    db_file = tmp_path / "test_reconciliation.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)
    service = ImportService(db_path=db_url, storage_dir=tmp_path / "storage")
    jobs = service.import_bundle(FIXTURES_DIR, organization_id="org_aarav")
    for j in jobs:
        assert j.status == "COMPLETED", f"Seed failed for {j.source_type}: {j.errors_json}"
    return db_url, service


def test_oracle_regression_all_10_scenarios(tmp_path: Path) -> None:
    """Validate 100% exact match against fixtures/synthetic/v1/expected_results.json oracle."""
    db_url, _ = seed_test_database(tmp_path)
    oracle_data = json.loads(ORACLE_FILE.read_text(encoding="utf-8"))
    oracle_scenarios = oracle_data["scenarios"]
    assert len(oracle_scenarios) == 10

    service = ReconciliationService(db_path=db_url)
    run_record, results = service.reconcile(
        organization_id="org_aarav",
        as_of_date="2026-10-30",
    )

    assert run_record.status == "COMPLETED"
    assert len(results) == 10

    results_by_scenario = {r.scenario_id: r for r in results}

    for scenario_id, expected in oracle_scenarios.items():
        assert scenario_id in results_by_scenario, f"Missing result for {scenario_id}"
        actual = results_by_scenario[scenario_id]

        # 1. Status and Reason Code
        assert actual.status == expected["expected_status"], (
            f"Scenario {scenario_id}: status {actual.status} != {expected['expected_status']}"
        )
        assert actual.reason_code == expected["reason_code"], (
            f"Scenario {scenario_id}: reason_code {actual.reason_code} != {expected['reason_code']}"
        )

        # 2. Key Monetary Totals
        assert format_money(actual.collected_amount) == expected["expected_collected_amount"], (
            f"Scenario {scenario_id}: collected {actual.collected_amount} != "
            f"{expected['expected_collected_amount']}"
        )
        assert format_money(actual.settled_amount) == expected["expected_settled_amount"], (
            f"Scenario {scenario_id}: settled {actual.settled_amount} != "
            f"{expected['expected_settled_amount']}"
        )
        assert format_money(actual.bank_credited_amount) == expected["expected_bank_credit"], (
            f"Scenario {scenario_id}: bank credit {actual.bank_credited_amount} != "
            f"{expected['expected_bank_credit']}"
        )

        # 3. Case and Approval Flags
        assert actual.case_needed == expected["expected_case_needed"], (
            f"Scenario {scenario_id}: case_needed {actual.case_needed} != "
            f"{expected['expected_case_needed']}"
        )
        assert actual.requires_approval == expected["requires_approval"], (
            f"Scenario {scenario_id}: requires_approval {actual.requires_approval} != "
            f"{expected['requires_approval']}"
        )

        # 4. Evidence Package & Contributing Records
        evidence = json.loads(actual.evidence_json)
        assert sorted(evidence["contributing_transaction_ids"]) == sorted(
            expected["contributing_transaction_ids"]
        ), f"Scenario {scenario_id}: transaction IDs mismatch"

        assert sorted(evidence["contributing_settlement_ids"]) == sorted(
            expected["contributing_settlement_ids"]
        ), f"Scenario {scenario_id}: settlement IDs mismatch"

        assert sorted(evidence["contributing_bank_entry_ids"]) == sorted(
            expected["contributing_bank_entry_ids"]
        ), f"Scenario {scenario_id}: bank entry IDs mismatch"

        assert evidence["terminal_outcome"] == expected["terminal_outcome"], (
            f"Scenario {scenario_id}: terminal_outcome {evidence['terminal_outcome']} != "
            f"{expected['terminal_outcome']}"
        )


def test_scn02_hero_missing_settlement(tmp_path: Path) -> None:
    """Hero case SCN-02: ₹18,450 missing settlement requires approval-gated case."""
    db_url, _ = seed_test_database(tmp_path)
    service = ReconciliationService(db_path=db_url)
    _, results = service.reconcile(organization_id="org_aarav", as_of_date="2026-10-30")

    scn02 = next(r for r in results if r.scenario_id == "SCN-02")
    assert scn02.status == "UNMATCHED"
    assert scn02.reason_code == "SETTLEMENT_ABSENT_FROM_BANK"
    assert scn02.collected_amount == Decimal("18450.00")
    assert scn02.settled_amount == Decimal("18450.00")
    assert scn02.bank_credited_amount == Decimal("0.00")
    assert scn02.discrepancy_amount == Decimal("18450.00")
    assert scn02.case_needed is True
    assert scn02.requires_approval is True

    evidence = json.loads(scn02.evidence_json)
    assert len(evidence["contributing_transaction_ids"]) == 4
    assert len(evidence["contributing_bank_entry_ids"]) == 0
    assert "mock_utr_scn02_999" in evidence["payout_references"]


def test_scn03_within_expected_window(tmp_path: Path) -> None:
    """SCN-03: In-flight T+1 settlement does not raise a spurious case."""
    db_url, _ = seed_test_database(tmp_path)
    service = ReconciliationService(db_path=db_url)
    _, results = service.reconcile(organization_id="org_aarav", as_of_date="2026-10-30")

    scn03 = next(r for r in results if r.scenario_id == "SCN-03")
    assert scn03.status == "WITHIN_EXPECTED_WINDOW"
    assert scn03.reason_code == "SETTLEMENT_IN_FLIGHT_WINDOW"
    assert scn03.case_needed is False
    assert scn03.requires_approval is False


def test_scn04_partial_settlement_match(tmp_path: Path) -> None:
    """SCN-04: Partial payout identifies residual amount and opens case."""
    db_url, _ = seed_test_database(tmp_path)
    service = ReconciliationService(db_path=db_url)
    _, results = service.reconcile(organization_id="org_aarav", as_of_date="2026-10-30")

    scn04 = next(r for r in results if r.scenario_id == "SCN-04")
    assert scn04.status == "PARTIALLY_MATCHED"
    assert scn04.reason_code == "PARTIAL_SETTLEMENT_BATCH"
    assert scn04.collected_amount == Decimal("5000.00")
    assert scn04.settled_amount == Decimal("3500.00")
    assert scn04.bank_credited_amount == Decimal("3500.00")
    assert scn04.discrepancy_amount == Decimal("1500.00")
    assert scn04.case_needed is True
    assert scn04.requires_approval is True


def test_scn05_adjustment_explained(tmp_path: Path) -> None:
    """SCN-05: Deductions (fees, tax, chargeback) explain gross-to-net difference."""
    db_url, _ = seed_test_database(tmp_path)
    service = ReconciliationService(db_path=db_url)
    _, results = service.reconcile(organization_id="org_aarav", as_of_date="2026-10-30")

    scn05 = next(r for r in results if r.scenario_id == "SCN-05")
    assert scn05.status == "ADJUSTMENT_EXPLAINED"
    assert scn05.reason_code == "DEDUCTIONS_MATCH_POLICY"
    assert scn05.collected_amount == Decimal("10000.00")
    assert scn05.settled_amount == Decimal("9623.00")
    assert scn05.bank_credited_amount == Decimal("9623.00")
    assert scn05.case_needed is False
    assert scn05.requires_approval is False

    evidence = json.loads(scn05.evidence_json)
    deductions = evidence["deduction_breakdown"]
    assert deductions["fee_amount"] == "150.00"
    assert deductions["tax_amount"] == "27.00"
    assert deductions["adjustment_amount"] == "-200.00"


def test_scn06_duplicate_source_detected(tmp_path: Path) -> None:
    """SCN-06: Duplicate row in merchant feed safely excluded from settlement."""
    db_url, _ = seed_test_database(tmp_path)
    service = ReconciliationService(db_path=db_url)
    _, results = service.reconcile(organization_id="org_aarav", as_of_date="2026-10-30")

    scn06 = next(r for r in results if r.scenario_id == "SCN-06")
    assert scn06.status == "DUPLICATE"
    assert scn06.reason_code == "DUPLICATE_SOURCE_RECORD_DETECTED"
    assert scn06.collected_amount == Decimal("2500.00")
    assert scn06.settled_amount == Decimal("2500.00")
    assert scn06.bank_credited_amount == Decimal("2500.00")


def test_scn07_refund_balanced(tmp_path: Path) -> None:
    """SCN-07: Linked refund balances customer payment to net 0.00."""
    db_url, _ = seed_test_database(tmp_path)
    service = ReconciliationService(db_path=db_url)
    _, results = service.reconcile(organization_id="org_aarav", as_of_date="2026-10-30")

    scn07 = next(r for r in results if r.scenario_id == "SCN-07")
    assert scn07.status == "RECONCILED"
    assert scn07.reason_code == "REFUND_BALANCED"
    assert scn07.collected_amount == Decimal("2100.00")
    assert scn07.settled_amount == Decimal("0.00")
    assert scn07.bank_credited_amount == Decimal("0.00")


def test_scn08_multi_batch_consolidation(tmp_path: Path) -> None:
    """SCN-08: Two batches (₹6,200 + ₹4,800) consolidate into one ₹11,000 credit."""
    db_url, _ = seed_test_database(tmp_path)
    service = ReconciliationService(db_path=db_url)
    _, results = service.reconcile(organization_id="org_aarav", as_of_date="2026-10-30")

    scn08 = next(r for r in results if r.scenario_id == "SCN-08")
    assert scn08.status == "RECONCILED"
    assert scn08.reason_code == "MANY_TO_ONE_BATCH_MATCH"
    assert scn08.collected_amount == Decimal("11000.00")
    assert scn08.settled_amount == Decimal("11000.00")
    assert scn08.bank_credited_amount == Decimal("11000.00")

    evidence = json.loads(scn08.evidence_json)
    assert len(evidence["contributing_settlement_ids"]) == 2


def test_scn09_support_terminal_resolution(tmp_path: Path) -> None:
    """SCN-09: Terminal support update confirms re-credit UTR verified against bank."""
    db_url, _ = seed_test_database(tmp_path)
    service = ReconciliationService(db_path=db_url)
    _, results = service.reconcile(organization_id="org_aarav", as_of_date="2026-10-30")

    scn09 = next(r for r in results if r.scenario_id == "SCN-09")
    assert scn09.status == "VERIFIED_RESOLVED"
    assert scn09.reason_code == "TERMINAL_RESOLUTION_EVIDENCE_MATCHED"
    assert scn09.case_needed is True
    assert scn09.requires_approval is True

    evidence = json.loads(scn09.evidence_json)
    assert evidence["terminal_outcome"] is True
    assert "mock_utr_scn09_recredit" in evidence["bank_utrs"]


def test_scn10_ambiguous_support_state(tmp_path: Path) -> None:
    """SCN-10: In-review support update blocks false closure and escalates."""
    db_url, _ = seed_test_database(tmp_path)
    service = ReconciliationService(db_path=db_url)
    _, results = service.reconcile(organization_id="org_aarav", as_of_date="2026-10-30")

    scn10 = next(r for r in results if r.scenario_id == "SCN-10")
    assert scn10.status == "ESCALATED"
    assert scn10.reason_code == "AWAITING_TERMINAL_OUTCOME"
    assert scn10.case_needed is True
    assert scn10.requires_approval is True

    evidence = json.loads(scn10.evidence_json)
    assert evidence["terminal_outcome"] is False


def test_reconciliation_persistence_and_audit(tmp_path: Path) -> None:
    """Ensure runs, results, and audit events are cleanly stored and retrievable."""
    db_url, _ = seed_test_database(tmp_path)
    service = ReconciliationService(db_path=db_url)
    run_record, results = service.reconcile(organization_id="org_aarav", as_of_date="2026-10-30")

    conn = get_connection(db_url)
    try:
        persisted_run = repository.find_run_by_id(conn, run_record.id, "org_aarav")
        assert persisted_run is not None
        assert persisted_run.id == run_record.id
        assert persisted_run.status == "COMPLETED"

        persisted_results = repository.list_reconciliation_results(
            conn, organization_id="org_aarav", run_id=run_record.id
        )
        assert len(persisted_results) == 10

        # Verify audit trail
        cur = conn.cursor()
        cur.execute(
            """SELECT entity_type, entity_id, event_type FROM audit_events
               WHERE organization_id = 'org_aarav' AND entity_id = ?""",
            (run_record.id,),
        )
        audits = cur.fetchall()
        assert len(audits) >= 1
        assert audits[0][0] == "RECONCILIATION_RUN"
        assert audits[0][2] == "RUN_COMPLETED"
    finally:
        conn.close()


def test_reconciliation_empty_database(tmp_path: Path) -> None:
    """Ensure running reconciliation on an empty database completes gracefully with 0 results."""
    db_file = tmp_path / "empty_rec.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    service = ReconciliationService(db_path=db_url)
    run_record, results = service.reconcile(organization_id="org_aarav", as_of_date="2026-10-30")

    assert run_record.status == "COMPLETED"
    assert len(results) == 0
    assert run_record.summary_counts_json is not None
    summary = json.loads(run_record.summary_counts_json)
    assert summary["total_clusters"] == 0
    assert summary["total_collected"] == "0.00"


def test_reconciliation_generic_records_without_scenario_tags(tmp_path: Path) -> None:
    """Verify non-synthetic records without 'scn' tags are clustered and reconciled."""
    db_file = tmp_path / "generic_rec.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    conn = get_connection(db_url)
    try:
        # Create a dummy artifact for foreign key constraints
        art = SourceArtifactRecord(
            id="art_generic_001",
            organization_id="org_aarav",
            source_type="CUSTOM",
            file_name="generic.csv",
            schema_version="1.0",
            dataset_version="v1",
            sha256="0" * 64,
            size_bytes=100,
            storage_path="/tmp/generic.csv",
            record_count=1,
            ingested_at="2026-10-30T10:00:00Z",
        )
        repository.insert_source_artifact(conn, art)

        # 1. Transaction
        txn = TransactionRecord(
            id="tx_rec_001",
            organization_id="org_aarav",
            store_id="store_indiranagar",
            provider="PAYTM_MOCK",
            provider_transaction_id="txn_real_custom_001",
            merchant_reference="ord_real_custom_001",
            occurred_at="2026-10-28T10:00:00Z",
            status="SUCCESS",
            payment_method="UPI",
            gross_amount=Decimal("5000.00"),
            currency="INR",
            source_artifact_id=art.id,
            source_row_number=2,
            created_at="2026-10-30T10:00:00Z",
        )
        repository.insert_transactions(conn, [txn])

        # 2. Settlement batch
        settle = SettlementBatchRecord(
            id="stl_rec_001",
            organization_id="org_aarav",
            provider="PAYTM_MOCK",
            provider_settlement_id="settle_real_custom_001",
            payout_reference="utr_real_custom_001",
            settlement_date="2026-10-29",
            reported_status="PROCESSED",
            gross_amount=Decimal("5000.00"),
            fee_amount=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            adjustment_amount=Decimal("0.00"),
            net_amount=Decimal("5000.00"),
            currency="INR",
            source_artifact_id=art.id,
            source_row_number=2,
            created_at="2026-10-30T10:00:00Z",
        )
        repository.insert_settlements(conn, [settle])

        # 3. Settlement line item
        line_item = SettlementLineItemRecord(
            id="sli_rec_001",
            organization_id="org_aarav",
            provider_settlement_id="settle_real_custom_001",
            line_item_id="line_real_custom_001",
            source_reference="txn_real_custom_001",
            line_type="PAYMENT",
            amount=Decimal("5000.00"),
            currency="INR",
            source_artifact_id=art.id,
            source_row_number=2,
            created_at="2026-10-30T10:00:00Z",
        )
        repository.insert_settlement_line_items(conn, [line_item])

        # 4. Bank statement credit
        bank = BankEntryRecord(
            id="bnk_rec_001",
            organization_id="org_aarav",
            statement_entry_id="bank_real_custom_001",
            bank_account_alias="bank_acc_4092",
            booking_date="2026-10-29",
            direction="CREDIT",
            amount=Decimal("5000.00"),
            currency="INR",
            narration="NEFT-PAYTM-utr_real_custom_001",
            utr_reference="utr_real_custom_001",
            source_artifact_id=art.id,
            source_row_number=2,
            created_at="2026-10-30T10:00:00Z",
        )
        repository.insert_bank_entries(conn, [bank])
    finally:
        conn.close()

    service = ReconciliationService(db_path=db_url)
    run_record, results = service.reconcile(organization_id="org_aarav", as_of_date="2026-10-30")

    assert run_record.status == "COMPLETED"
    assert len(results) == 1

    res = results[0]
    assert res.scenario_id is None  # Generic record has no synthetic scenario ID
    assert res.status == "RECONCILED"
    assert res.reason_code == "MATCHED_PAYOUT_TO_BANK"
    assert res.collected_amount == Decimal("5000.00")
    assert res.settled_amount == Decimal("5000.00")
    assert res.bank_credited_amount == Decimal("5000.00")
    assert res.discrepancy_amount == Decimal("0.00")
    assert res.case_needed is False


def test_reconciliation_generic_in_flight_and_missing(tmp_path: Path) -> None:
    """Verify pure date-based T+1 evaluation works on generic records without scenario tags."""
    db_file = tmp_path / "generic_window.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)

    conn = get_connection(db_url)
    try:
        art = SourceArtifactRecord(
            id="art_window_001",
            organization_id="org_aarav",
            source_type="CUSTOM",
            file_name="window.csv",
            schema_version="1.0",
            dataset_version="v1",
            sha256="1" * 64,
            size_bytes=100,
            storage_path="/tmp/window.csv",
            record_count=2,
            ingested_at="2026-10-30T10:00:00Z",
        )
        repository.insert_source_artifact(conn, art)

        # Batch A: In flight (transaction occurred today 2026-10-30)
        txn_a = TransactionRecord(
            id="tx_inf_001",
            organization_id="org_aarav",
            store_id="store_indiranagar",
            provider="PAYTM_MOCK",
            provider_transaction_id="txn_flight_001",
            merchant_reference="ord_flight_001",
            occurred_at="2026-10-30T14:00:00Z",
            status="SUCCESS",
            payment_method="UPI",
            gross_amount=Decimal("3000.00"),
            currency="INR",
            source_artifact_id=art.id,
            source_row_number=2,
            created_at="2026-10-30T10:00:00Z",
        )
        settle_a = SettlementBatchRecord(
            id="stl_inf_001",
            organization_id="org_aarav",
            provider="PAYTM_MOCK",
            provider_settlement_id="settle_flight_001",
            payout_reference="utr_flight_001",
            settlement_date="2026-10-30",
            reported_status="PROCESSED",
            gross_amount=Decimal("3000.00"),
            fee_amount=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            adjustment_amount=Decimal("0.00"),
            net_amount=Decimal("3000.00"),
            currency="INR",
            source_artifact_id=art.id,
            source_row_number=2,
            created_at="2026-10-30T10:00:00Z",
        )
        line_a = SettlementLineItemRecord(
            id="sli_inf_001",
            organization_id="org_aarav",
            provider_settlement_id="settle_flight_001",
            line_item_id="line_flight_001",
            source_reference="txn_flight_001",
            line_type="PAYMENT",
            amount=Decimal("3000.00"),
            currency="INR",
            source_artifact_id=art.id,
            source_row_number=2,
            created_at="2026-10-30T10:00:00Z",
        )

        # Batch B: Missing (transaction occurred 2026-10-27, 3 days ago)
        txn_b = TransactionRecord(
            id="tx_mis_001",
            organization_id="org_aarav",
            store_id="store_koramangala",
            provider="PAYTM_MOCK",
            provider_transaction_id="txn_missing_001",
            merchant_reference="ord_missing_001",
            occurred_at="2026-10-27T10:00:00Z",
            status="SUCCESS",
            payment_method="UPI",
            gross_amount=Decimal("4000.00"),
            currency="INR",
            source_artifact_id=art.id,
            source_row_number=3,
            created_at="2026-10-30T10:00:00Z",
        )
        settle_b = SettlementBatchRecord(
            id="stl_mis_001",
            organization_id="org_aarav",
            provider="PAYTM_MOCK",
            provider_settlement_id="settle_missing_001",
            payout_reference="utr_missing_001",
            settlement_date="2026-10-28",
            reported_status="PROCESSED",
            gross_amount=Decimal("4000.00"),
            fee_amount=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            adjustment_amount=Decimal("0.00"),
            net_amount=Decimal("4000.00"),
            currency="INR",
            source_artifact_id=art.id,
            source_row_number=3,
            created_at="2026-10-30T10:00:00Z",
        )
        line_b = SettlementLineItemRecord(
            id="sli_mis_001",
            organization_id="org_aarav",
            provider_settlement_id="settle_missing_001",
            line_item_id="line_missing_001",
            source_reference="txn_missing_001",
            line_type="PAYMENT",
            amount=Decimal("4000.00"),
            currency="INR",
            source_artifact_id=art.id,
            source_row_number=3,
            created_at="2026-10-30T10:00:00Z",
        )

        repository.insert_transactions(conn, [txn_a, txn_b])
        repository.insert_settlements(conn, [settle_a, settle_b])
        repository.insert_settlement_line_items(conn, [line_a, line_b])
    finally:
        conn.close()

    service = ReconciliationService(db_path=db_url)
    _, results = service.reconcile(organization_id="org_aarav", as_of_date="2026-10-30")

    assert len(results) == 2
    by_status = {r.status: r for r in results}
    assert "WITHIN_EXPECTED_WINDOW" in by_status
    assert "UNMATCHED" in by_status

    in_flight_res = by_status["WITHIN_EXPECTED_WINDOW"]
    assert in_flight_res.case_needed is False
    assert in_flight_res.reason_code == "SETTLEMENT_IN_FLIGHT_WINDOW"

    missing_res = by_status["UNMATCHED"]
    assert missing_res.case_needed is True
    assert missing_res.requires_approval is True
    assert missing_res.reason_code == "SETTLEMENT_ABSENT_FROM_BANK"
