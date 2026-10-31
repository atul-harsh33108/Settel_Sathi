"""Tests for case state machine, event timeline, concurrency, and false-closure prevention."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from app.db.connection import get_connection, init_db
from app.models.domain import (
    ActorType,
    BankEntryRecord,
    CasePriority,
    CaseStatus,
    MockSupportUpdateRecord,
)
from app.services import repository
from app.services.cases import (
    CaseNotFoundError,
    CaseService,
    FalseClosureError,
    InvalidStateTransitionError,
    VersionMismatchError,
)


@pytest.fixture
def test_db(tmp_path: Path) -> str:
    db_file = tmp_path / f"test_cases_{uuid4().hex[:8]}.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)
    return db_url


def test_create_case_initializes_detected_status_and_version(test_db: str) -> None:
    service = CaseService(db_path=test_db)
    case = service.create_case(
        organization_id="org_aarav",
        case_type="MISSING_SETTLEMENT",
        priority=CasePriority.HIGH,
        subject_type="TRANSACTION",
        subject_id="txn_1001",
        decision_summary="₹18,450.00 payout missing from bank statement",
        actor_type=ActorType.USER,
        actor_id="operator_aarav",
    )

    assert case.id.startswith("case_")
    assert case.status == CaseStatus.DETECTED
    assert case.version == 1
    assert case.priority == CasePriority.HIGH
    assert case.subject_type == "TRANSACTION"
    assert case.subject_id == "txn_1001"

    # Verify timeline event
    timeline = service.get_timeline(case.id, organization_id="org_aarav")
    assert len(timeline) == 1
    assert timeline[0].event_type == "CASE_CREATED"
    assert timeline[0].from_status is None
    assert timeline[0].to_status == CaseStatus.DETECTED

    # Verify audit event
    conn = get_connection(test_db)
    try:
        audit_events = repository.list_audit_events(
            conn, organization_id="org_aarav", entity_type="CASE", entity_id=case.id
        )
        assert len(audit_events) == 1
        assert audit_events[0].event_type == "CASE_CREATED"
        assert audit_events[0].actor_id == "operator_aarav"
    finally:
        conn.close()


def test_case_lifecycle_state_transitions(test_db: str) -> None:
    service = CaseService(db_path=test_db)
    case = service.create_case(
        organization_id="org_aarav",
        case_type="MISSING_SETTLEMENT",
        priority=CasePriority.HIGH,
        subject_type="TRANSACTION",
        subject_id="txn_1002",
    )
    assert case.status == CaseStatus.DETECTED
    assert case.version == 1

    # Transition 1: DETECTED -> INVESTIGATING
    case = service.transition_case(
        case_id=case.id,
        to_status=CaseStatus.INVESTIGATING,
        expected_version=1,
        actor_type=ActorType.AGENT,
        actor_id="agent_settlesaathi",
        summary="Agent started autonomous investigation",
    )
    assert case.status == CaseStatus.INVESTIGATING
    assert case.version == 2

    # Transition 2: INVESTIGATING -> AWAITING_APPROVAL
    case = service.transition_case(
        case_id=case.id,
        to_status=CaseStatus.AWAITING_APPROVAL,
        expected_version=2,
        actor_type=ActorType.AGENT,
        actor_id="agent_settlesaathi",
        summary="Drafted support ticket payload and awaiting operator approval",
    )
    assert case.status == CaseStatus.AWAITING_APPROVAL
    assert case.version == 3

    # Transition 3: AWAITING_APPROVAL -> SUBMITTED
    case = service.transition_case(
        case_id=case.id,
        to_status=CaseStatus.SUBMITTED,
        expected_version=3,
        actor_type=ActorType.USER,
        actor_id="operator_aarav",
        summary="Operator approved ticket submission",
    )
    assert case.status == CaseStatus.SUBMITTED
    assert case.version == 4

    # Transition 4: SUBMITTED -> MONITORING
    case = service.transition_case(
        case_id=case.id,
        to_status=CaseStatus.MONITORING,
        expected_version=4,
        actor_type=ActorType.SYSTEM,
        actor_id="connector_service",
        summary="Ticket accepted by provider mock; polling for updates",
    )
    assert case.status == CaseStatus.MONITORING
    assert case.version == 5

    # Insert authoritative mock resolution record in DB
    conn = get_connection(test_db)
    update_id = f"sup_{uuid4().hex[:12]}"
    try:
        # Create dummy artifact for foreign key
        artifact = repository.SourceArtifactRecord(
            id=f"art_{uuid4().hex[:12]}",
            organization_id="org_aarav",
            source_type="MOCK_SUPPORT_UPDATES",
            file_name="support.csv",
            schema_version="v1.0",
            dataset_version="v1.0",
            sha256="dummy_sha256",
            size_bytes=100,
            storage_path="dummy.csv",
            record_count=1,
            ingested_at="2026-10-31T00:00:00Z",
        )
        repository.insert_source_artifact(conn, artifact)
        repository.insert_mock_support_updates(
            conn,
            [
                MockSupportUpdateRecord(
                    id=update_id,
                    organization_id="org_aarav",
                    case_reference="SCN-02",
                    event_at="2026-10-31T05:00:00Z",
                    status="REFUND_PROCESSED",
                    summary="Settlement payout re-credited to merchant account",
                    terminal_outcome=True,
                    evidence_reference="UTR-REF-18450",
                    source_artifact_id=artifact.id,
                    source_row_number=1,
                    created_at="2026-10-31T05:00:00Z",
                )
            ],
        )
    finally:
        conn.close()

    # Transition 5: MONITORING -> VERIFIED_RESOLVED with authoritative evidence
    case = service.transition_case(
        case_id=case.id,
        to_status=CaseStatus.VERIFIED_RESOLVED,
        expected_version=5,
        actor_type=ActorType.SYSTEM,
        actor_id="verification_engine",
        summary="Verified terminal outcome via mock support update",
        evidence={
            "terminal_outcome": True,
            "mock_support_update_id": update_id,
            "evidence_reference": "UTR-REF-18450",
        },
    )
    assert case.status == CaseStatus.VERIFIED_RESOLVED
    assert case.version == 6

    # Verify timeline reflects all 6 events chronologically
    timeline = service.get_timeline(case.id, organization_id="org_aarav")
    assert len(timeline) == 6
    statuses = [(e.from_status, e.to_status) for e in timeline]
    assert statuses == [
        (None, CaseStatus.DETECTED),
        (CaseStatus.DETECTED, CaseStatus.INVESTIGATING),
        (CaseStatus.INVESTIGATING, CaseStatus.AWAITING_APPROVAL),
        (CaseStatus.AWAITING_APPROVAL, CaseStatus.SUBMITTED),
        (CaseStatus.SUBMITTED, CaseStatus.MONITORING),
        (CaseStatus.MONITORING, CaseStatus.VERIFIED_RESOLVED),
    ]


def test_invalid_state_transitions_are_rejected(test_db: str) -> None:
    service = CaseService(db_path=test_db)
    case = service.create_case(
        organization_id="org_aarav",
        subject_id="txn_1003",
    )
    assert case.status == CaseStatus.DETECTED

    # Cannot jump directly from DETECTED to VERIFIED_RESOLVED
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        service.transition_case(
            case_id=case.id,
            to_status=CaseStatus.VERIFIED_RESOLVED,
            expected_version=1,
        )
    assert "Invalid state transition" in str(exc_info.value)

    # Cannot jump from DETECTED to SUBMITTED
    with pytest.raises(InvalidStateTransitionError):
        service.transition_case(
            case_id=case.id,
            to_status=CaseStatus.SUBMITTED,
            expected_version=1,
        )

    # Move to ESCALATED
    case = service.transition_case(
        case_id=case.id,
        to_status=CaseStatus.ESCALATED,
        expected_version=1,
    )
    assert case.status == CaseStatus.ESCALATED

    # From ESCALATED, cannot jump directly to SUBMITTED
    with pytest.raises(InvalidStateTransitionError):
        service.transition_case(
            case_id=case.id,
            to_status=CaseStatus.SUBMITTED,
            expected_version=2,
        )


def test_false_closure_prevention(test_db: str) -> None:
    service = CaseService(db_path=test_db)
    case = service.create_case(
        organization_id="org_aarav",
        subject_id="txn_1004",
    )
    # Move to MONITORING
    case = service.transition_case(case.id, CaseStatus.INVESTIGATING, expected_version=1)
    case = service.transition_case(case.id, CaseStatus.MONITORING, expected_version=2)
    assert case.status == CaseStatus.MONITORING

    # Attempt 1: Transition with no evidence -> Must fail
    with pytest.raises(FalseClosureError) as exc1:
        service.transition_case(
            case.id,
            to_status=CaseStatus.VERIFIED_RESOLVED,
            expected_version=3,
            evidence=None,
        )
    assert "False-closure rejected" in str(exc1.value)

    # Attempt 2: Empty evidence dict -> Must fail
    with pytest.raises(FalseClosureError):
        service.transition_case(
            case.id,
            to_status=CaseStatus.VERIFIED_RESOLVED,
            expected_version=3,
            evidence={},
        )

    # Attempt 3: Subjective agent narration with terminal_outcome=False -> Must fail
    with pytest.raises(FalseClosureError):
        service.transition_case(
            case.id,
            to_status=CaseStatus.VERIFIED_RESOLVED,
            expected_version=3,
            evidence={
                "note": "Agent thinks ticket was probably solved",
                "terminal_outcome": False,
            },
        )

    # Attempt 4: terminal_outcome=True but missing reference -> Must fail
    with pytest.raises(FalseClosureError):
        service.transition_case(
            case.id,
            to_status=CaseStatus.VERIFIED_RESOLVED,
            expected_version=3,
            evidence={"terminal_outcome": True},
        )

    # Attempt 5: Non-existent update reference in database -> Must fail
    with pytest.raises(FalseClosureError):
        service.transition_case(
            case.id,
            to_status=CaseStatus.VERIFIED_RESOLVED,
            expected_version=3,
            evidence={
                "terminal_outcome": True,
                "mock_support_update_id": "nonexistent_update_id",
                "evidence_reference": "UTR-GHOST",
            },
        )

    # Attempt 6: Unverified evidence_reference alone without DB record -> MUST FAIL
    with pytest.raises(FalseClosureError):
        service.transition_case(
            case.id,
            to_status=CaseStatus.VERIFIED_RESOLVED,
            expected_version=3,
            evidence={
                "terminal_outcome": True,
                "evidence_reference": "UTR-UNVERIFIED-STRING",
            },
        )

    # Attempt 7: Unverified case_reference alone without DB record -> MUST FAIL
    with pytest.raises(FalseClosureError):
        service.transition_case(
            case.id,
            to_status=CaseStatus.VERIFIED_RESOLVED,
            expected_version=3,
            evidence={
                "terminal_outcome": True,
                "case_reference": "SCN-GHOST",
            },
        )

    # Attempt 8: Unverified utr_reference alone without DB record -> MUST FAIL
    with pytest.raises(FalseClosureError):
        service.transition_case(
            case.id,
            to_status=CaseStatus.VERIFIED_RESOLVED,
            expected_version=3,
            evidence={
                "terminal_outcome": True,
                "utr_reference": "UTR-GHOST-12345",
            },
        )

    # Attempt 9: Bank entry reference exists but direction is DEBIT (money out) -> MUST FAIL
    conn = get_connection(test_db)
    debit_entry_id = f"bank_deb_{uuid4().hex[:8]}"
    credit_entry_id = f"bank_cred_{uuid4().hex[:8]}"
    try:
        artifact = repository.SourceArtifactRecord(
            id=f"art_b_{uuid4().hex[:8]}",
            organization_id="org_aarav",
            source_type="BANK_STATEMENT",
            file_name="bank.csv",
            schema_version="v1.0",
            dataset_version="v1.0",
            sha256="dummy_sha256_bank",
            size_bytes=100,
            storage_path="bank.csv",
            record_count=2,
            ingested_at="2026-10-31T00:00:00Z",
        )
        repository.insert_source_artifact(conn, artifact)
        repository.insert_bank_entries(
            conn,
            [
                BankEntryRecord(
                    id=debit_entry_id,
                    organization_id="org_aarav",
                    statement_entry_id="stmt_deb_01",
                    bank_account_alias="bank_acc_4092",
                    booking_date="2026-10-31",
                    direction="DEBIT",
                    amount=Decimal("18450.00"),
                    currency="INR",
                    narration="Debit withdrawal",
                    utr_reference="UTR-DEB-01",
                    source_artifact_id=artifact.id,
                    source_row_number=1,
                    created_at="2026-10-31T00:00:00Z",
                ),
                BankEntryRecord(
                    id=credit_entry_id,
                    organization_id="org_aarav",
                    statement_entry_id="stmt_cred_01",
                    bank_account_alias="bank_acc_4092",
                    booking_date="2026-10-31",
                    direction="CREDIT",
                    amount=Decimal("18450.00"),
                    currency="INR",
                    narration="Credit settlement",
                    utr_reference="UTR-CRED-01",
                    source_artifact_id=artifact.id,
                    source_row_number=2,
                    created_at="2026-10-31T00:00:00Z",
                ),
            ],
        )
    finally:
        conn.close()

    with pytest.raises(FalseClosureError):
        service.transition_case(
            case.id,
            to_status=CaseStatus.VERIFIED_RESOLVED,
            expected_version=3,
            evidence={
                "terminal_outcome": True,
                "bank_statement_entry_id": debit_entry_id,
            },
        )

    # Attempt 10: Valid verified bank credit -> MUST SUCCEED
    resolved_case = service.transition_case(
        case.id,
        to_status=CaseStatus.VERIFIED_RESOLVED,
        expected_version=3,
        evidence={
            "terminal_outcome": True,
            "bank_statement_entry_id": credit_entry_id,
            "utr_reference": "UTR-CRED-01",
        },
    )
    assert resolved_case.status == CaseStatus.VERIFIED_RESOLVED
    assert resolved_case.version == 4


def test_optimistic_concurrency_version_checks(test_db: str) -> None:
    service = CaseService(db_path=test_db)
    case = service.create_case(
        organization_id="org_aarav",
        subject_id="txn_1005",
    )
    assert case.version == 1

    # First valid update: expected_version=1 -> version becomes 2
    case = service.transition_case(
        case.id,
        to_status=CaseStatus.INVESTIGATING,
        expected_version=1,
    )
    assert case.version == 2

    # Concurrent stale update with expected_version=1 -> MUST FAIL with VersionMismatchError
    with pytest.raises(VersionMismatchError) as exc_info:
        service.transition_case(
            case.id,
            to_status=CaseStatus.AWAITING_APPROVAL,
            expected_version=1,  # Stale version!
        )
    assert "version mismatch" in str(exc_info.value).lower()

    # Retry with correct expected_version=2 -> MUST SUCCEED
    case = service.transition_case(
        case.id,
        to_status=CaseStatus.AWAITING_APPROVAL,
        expected_version=2,
    )
    assert case.version == 3


def test_case_timeline_notes_and_events(test_db: str) -> None:
    service = CaseService(db_path=test_db)
    case = service.create_case(
        organization_id="org_aarav",
        subject_id="txn_1006",
    )

    # Add a custom note
    note_event = service.add_timeline_event(
        case_id=case.id,
        event_type="OPERATOR_NOTE",
        summary="Contacted merchant via phone; confirmed no payout received.",
        actor_type=ActorType.USER,
        actor_id="operator_aarav",
        details={"phone": "+91-9876543210", "merchant_confirmed": True},
    )
    assert note_event.event_type == "OPERATOR_NOTE"
    assert note_event.from_status == CaseStatus.DETECTED
    assert note_event.to_status == CaseStatus.DETECTED

    timeline = service.get_timeline(case.id, "org_aarav")
    assert len(timeline) == 2
    assert timeline[1].summary == "Contacted merchant via phone; confirmed no payout received."


def test_case_scoping_and_not_found(test_db: str) -> None:
    service = CaseService(db_path=test_db)
    with pytest.raises(CaseNotFoundError):
        service.get_case("case_nonexistent", "org_aarav")

    case = service.create_case(organization_id="org_aarav", subject_id="txn_1007")

    # Accessing with wrong org fails with CaseNotFoundError
    with pytest.raises(CaseNotFoundError):
        service.get_case(case.id, "org_other")


def test_update_case_metadata_and_concurrency(test_db: str) -> None:
    service = CaseService(db_path=test_db)
    case = service.create_case(
        organization_id="org_aarav",
        subject_id="txn_1008",
        priority=CasePriority.LOW,
        decision_summary="Initial triage",
    )
    assert case.version == 1
    assert case.priority == CasePriority.LOW

    # Valid update
    updated = service.update_case(
        case_id=case.id,
        expected_version=1,
        priority=CasePriority.HIGH,
        decision_summary="Upgraded priority after merchant call",
        actor_id="lead_operator",
        summary="Priority bumped to HIGH",
    )
    assert updated.version == 2
    assert updated.priority == CasePriority.HIGH
    assert updated.decision_summary == "Upgraded priority after merchant call"

    # Concurrency conflict on stale version
    with pytest.raises(VersionMismatchError):
        service.update_case(
            case_id=case.id,
            expected_version=1,  # Stale version!
            priority=CasePriority.CRITICAL,
        )

    # Verify timeline recorded CASE_UPDATED
    timeline = service.get_timeline(case.id, "org_aarav")
    assert any(e.event_type == "CASE_UPDATED" for e in timeline)
