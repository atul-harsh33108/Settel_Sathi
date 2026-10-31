"""Tests for policy decisions, approval tokens, hash verification, and anti-bypass safeguards."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from app.db.connection import get_connection, init_db
from app.models.domain import (
    ActionClass,
    ActorType,
    ApprovalStatus,
    BankEntryRecord,
    CaseStatus,
    PolicyDecision,
)
from app.services import repository
from app.services.cases import CaseService
from app.services.policy import (
    ApprovalExpiredError,
    ApprovalRequiredError,
    CannotSelfApproveError,
    PayloadHashMismatchError,
    PolicyBlockedError,
    PolicyError,
    PolicyService,
    compute_payload_hash,
)


@pytest.fixture
def test_db(tmp_path: Path) -> str:
    db_file = tmp_path / f"test_policy_{uuid4().hex[:8]}.db"
    db_url = f"sqlite:///{db_file}"
    init_db(db_url)
    return db_url


def test_compute_payload_hash_is_canonical() -> None:
    # Key ordering must not affect the computed hash
    payload_a = {"case_id": "case_1", "amount": "18450.00", "provider": "Paytm"}
    payload_b = {"provider": "Paytm", "amount": "18450.00", "case_id": "case_1"}

    hash_a = compute_payload_hash(payload_a)
    hash_b = compute_payload_hash(payload_b)
    assert hash_a == hash_b
    assert len(hash_a) == 64

    # Minor modification changes the hash
    payload_c = {"provider": "Paytm", "amount": "18450.01", "case_id": "case_1"}
    assert compute_payload_hash(payload_c) != hash_a


def test_policy_action_class_evaluations() -> None:
    service = PolicyService()

    # Read actions -> ALLOWED
    view_res = service.evaluate_action("VIEW_CASE")
    assert view_res.action_class == ActionClass.READ
    assert view_res.decision == PolicyDecision.ALLOWED

    evidence_res = service.evaluate_action("GET_RECONCILIATION_EVIDENCE")
    assert evidence_res.decision == PolicyDecision.ALLOWED

    # Draft actions -> ALLOWED
    draft_res = service.evaluate_action("DRAFT_SUPPORT_CASE")
    assert draft_res.action_class == ActionClass.DRAFT
    assert draft_res.decision == PolicyDecision.ALLOWED

    # Non-sensitive write -> ALLOWED
    notes_res = service.evaluate_action("UPDATE_CASE_NOTES")
    assert notes_res.action_class == ActionClass.EXTERNAL_NON_SENSITIVE_WRITE
    assert notes_res.decision == PolicyDecision.ALLOWED

    # Sensitive writes -> APPROVAL_REQUIRED
    submit_res = service.evaluate_action("SUBMIT_MOCK_SUPPORT_CASE")
    assert submit_res.action_class == ActionClass.SENSITIVE_WRITE
    assert submit_res.decision == PolicyDecision.APPROVAL_REQUIRED

    recredit_res = service.evaluate_action("REQUEST_RECREDIT")
    assert recredit_res.decision == PolicyDecision.APPROVAL_REQUIRED

    # Blocked actions -> BLOCKED
    money_res = service.evaluate_action("MOVE_MONEY")
    assert money_res.action_class == ActionClass.BLOCKED
    assert money_res.decision == PolicyDecision.BLOCKED

    bank_res = service.evaluate_action("MODIFY_BANK_ACCOUNT")
    assert bank_res.decision == PolicyDecision.BLOCKED

    transfer_res = service.evaluate_action("INITIATE_TRANSFER")
    assert transfer_res.decision == PolicyDecision.BLOCKED


def test_blocked_actions_cannot_request_approval(test_db: str) -> None:
    policy_svc = PolicyService(db_path=test_db)
    case_svc = CaseService(db_path=test_db)
    case = case_svc.create_case(organization_id="org_aarav", subject_id="txn_2001")

    # Attempting to request approval for a strictly blocked action raises PolicyBlockedError
    with pytest.raises(PolicyBlockedError) as exc_info:
        policy_svc.request_approval(
            case_id=case.id,
            action_type="MOVE_MONEY",
            payload={"amount": "18450.00", "destination": "acc_external"},
        )
    assert "strictly BLOCKED" in str(exc_info.value)


def test_agent_self_approval_prevention(test_db: str) -> None:
    policy_svc = PolicyService(db_path=test_db)
    case_svc = CaseService(db_path=test_db)
    case = case_svc.create_case(organization_id="org_aarav", subject_id="txn_2002")

    # Agent requests approval
    payload = {"issue": "missing_settlement", "payout_ref": "PO-18450"}
    approval = policy_svc.request_approval(
        case_id=case.id,
        action_type="SUBMIT_MOCK_SUPPORT_CASE",
        payload=payload,
        requested_by_type=ActorType.AGENT,
        requested_by_id="agent_settlesaathi",
    )
    assert approval.status == ApprovalStatus.PENDING

    # Agent actor attempts to approve -> MUST FAIL
    with pytest.raises(CannotSelfApproveError) as exc1:
        policy_svc.approve_action(
            approval_id=approval.id,
            approver_actor_type=ActorType.AGENT,
            approver_actor_id="agent_settlesaathi",
        )
    assert "cannot grant approvals" in str(exc1.value)

    # System actor attempts to approve -> MUST FAIL
    with pytest.raises(CannotSelfApproveError) as exc2:
        policy_svc.approve_action(
            approval_id=approval.id,
            approver_actor_type=ActorType.SYSTEM,
            approver_actor_id="scheduler_system",
        )
    assert "cannot grant approvals" in str(exc2.value)

    # Human user approves -> MUST SUCCEED
    approved = policy_svc.approve_action(
        approval_id=approval.id,
        approver_actor_type=ActorType.USER,
        approver_actor_id="operator_aarav",
        approver_role="finance_ops",
    )
    assert approved.status == ApprovalStatus.APPROVED
    assert approved.approved_by == "operator_aarav"


def test_approval_bypass_prevention(test_db: str) -> None:
    policy_svc = PolicyService(db_path=test_db)
    case_svc = CaseService(db_path=test_db)
    case = case_svc.create_case(organization_id="org_aarav", subject_id="txn_2003")

    payload = {"payout_reference": "PO-9999", "amount": "18450.00"}

    # Attempt 1: Execute sensitive action without any approval_id -> MUST FAIL
    with pytest.raises(ApprovalRequiredError) as exc1:
        policy_svc.execute_action(
            case_id=case.id,
            action_type="SUBMIT_MOCK_SUPPORT_CASE",
            payload=payload,
            approval_id=None,
        )
    assert "requires an approved authorization token" in str(exc1.value)

    # Attempt 2: Request approval but attempt execution while status is still PENDING
    approval = policy_svc.request_approval(
        case_id=case.id,
        action_type="SUBMIT_MOCK_SUPPORT_CASE",
        payload=payload,
    )
    with pytest.raises(ApprovalRequiredError) as exc2:
        policy_svc.execute_action(
            case_id=case.id,
            action_type="SUBMIT_MOCK_SUPPORT_CASE",
            payload=payload,
            approval_id=approval.id,
        )
    assert "expected 'APPROVED'" in str(exc2.value)

    # Attempt 3: Reject approval and attempt execution -> MUST FAIL
    policy_svc.reject_approval(
        approval.id, actor_id="operator_aarav", reason="Discrepancy resolved elsewhere"
    )
    with pytest.raises(ApprovalRequiredError):
        policy_svc.execute_action(
            case_id=case.id,
            action_type="SUBMIT_MOCK_SUPPORT_CASE",
            payload=payload,
            approval_id=approval.id,
        )


def test_payload_tampering_and_hash_mismatch_prevention(test_db: str) -> None:
    policy_svc = PolicyService(db_path=test_db)
    case_svc = CaseService(db_path=test_db)
    case = case_svc.create_case(organization_id="org_aarav", subject_id="txn_2004")

    original_payload = {
        "payout_reference": "PO-ORIG-18450",
        "requested_amount": "18450.00",
        "merchant_claim": "Settlement missing",
    }

    # Request and approve original payload
    approval = policy_svc.request_approval(
        case_id=case.id,
        action_type="SUBMIT_MOCK_SUPPORT_CASE",
        payload=original_payload,
    )
    policy_svc.approve_action(
        approval_id=approval.id,
        approver_actor_type=ActorType.USER,
        approver_actor_id="operator_aarav",
    )

    # Tampered payload: modified amount
    tampered_payload = {
        "payout_reference": "PO-ORIG-18450",
        "requested_amount": "99999.00",  # Changed!
        "merchant_claim": "Settlement missing",
    }

    # Attempt execution with tampered payload -> MUST FAIL with PayloadHashMismatchError
    with pytest.raises(PayloadHashMismatchError) as exc_info:
        policy_svc.execute_action(
            case_id=case.id,
            action_type="SUBMIT_MOCK_SUPPORT_CASE",
            payload=tampered_payload,
            approval_id=approval.id,
        )
    assert "Approval bypass detected" in str(exc_info.value)

    # Verify audit event recorded for blocked tampering attempt
    conn = get_connection(test_db)
    try:
        blocked_events = repository.list_audit_events(
            conn, organization_id="org_aarav", event_type="ACTION_ATTEMPT_BLOCKED"
        )
        assert len(blocked_events) >= 1
        assert "PAYLOAD_HASH_MISMATCH" in (blocked_events[0].details_json or "")
    finally:
        conn.close()


def test_idempotent_action_execution(test_db: str) -> None:
    policy_svc = PolicyService(db_path=test_db)
    case_svc = CaseService(db_path=test_db)
    case = case_svc.create_case(organization_id="org_aarav", subject_id="txn_2005")

    payload = {"payout_reference": "PO-IDEM-18450", "amount": "18450.00"}
    approval = policy_svc.request_approval(
        case_id=case.id,
        action_type="SUBMIT_MOCK_SUPPORT_CASE",
        payload=payload,
    )
    policy_svc.approve_action(
        approval_id=approval.id,
        approver_actor_type=ActorType.USER,
        approver_actor_id="operator_aarav",
    )

    idempotency_key = "idem_support_txn_2005"

    # Execution 1: First execution creates external ticket
    res1 = policy_svc.execute_action(
        case_id=case.id,
        action_type="SUBMIT_MOCK_SUPPORT_CASE",
        payload=payload,
        approval_id=approval.id,
        idempotency_key=idempotency_key,
    )
    assert res1["status"] == "SUCCEEDED"
    assert res1["idempotent_replay"] is False
    ticket_id_1 = res1["external_ticket_id"]

    # Case should now be in MONITORING
    updated_case = case_svc.get_case(case.id, "org_aarav")
    assert updated_case.status == CaseStatus.MONITORING

    # Execution 2: Replay with same idempotency key -> MUST return identical cached response
    res2 = policy_svc.execute_action(
        case_id=case.id,
        action_type="SUBMIT_MOCK_SUPPORT_CASE",
        payload=payload,
        approval_id=approval.id,
        idempotency_key=idempotency_key,
    )
    assert res2["status"] == "SUCCEEDED"
    assert res2["idempotent_replay"] is True
    assert res2["external_ticket_id"] == ticket_id_1


def test_approval_expiry(test_db: str) -> None:
    policy_svc = PolicyService(db_path=test_db)
    case_svc = CaseService(db_path=test_db)
    case = case_svc.create_case(organization_id="org_aarav", subject_id="txn_2006")

    # Request approval with negative expiration (already expired)
    payload = {"payout_reference": "PO-EXP-18450"}
    approval = policy_svc.request_approval(
        case_id=case.id,
        action_type="SUBMIT_MOCK_SUPPORT_CASE",
        payload=payload,
        expires_in_hours=-1,  # Expired in past!
    )

    with pytest.raises(ApprovalExpiredError):
        policy_svc.approve_action(
            approval_id=approval.id,
            approver_actor_type=ActorType.USER,
            approver_actor_id="operator_aarav",
        )


def test_four_eyes_user_self_approval_denied(test_db: str) -> None:
    policy_svc = PolicyService(db_path=test_db)
    case_svc = CaseService(db_path=test_db)
    case = case_svc.create_case(organization_id="org_aarav", subject_id="txn_2007")

    # Human user operator_1 requests approval
    approval = policy_svc.request_approval(
        case_id=case.id,
        action_type="SUBMIT_MOCK_SUPPORT_CASE",
        payload={"reason": "Missing settlement"},
        requested_by_type=ActorType.USER,
        requested_by_id="operator_1",
    )

    # Same user operator_1 attempts to approve own request
    # -> MUST BE DENIED under four-eyes principle
    with pytest.raises(CannotSelfApproveError) as exc:
        policy_svc.approve_action(
            approval_id=approval.id,
            approver_actor_type=ActorType.USER,
            approver_actor_id="operator_1",  # Same user!
        )
    assert "cannot be the same identity" in str(exc.value)

    # Different user operator_2 approves -> MUST SUCCEED
    approved = policy_svc.approve_action(
        approval_id=approval.id,
        approver_actor_type=ActorType.USER,
        approver_actor_id="operator_2",
    )
    assert approved.status == ApprovalStatus.APPROVED


def test_cross_case_approval_rejected(test_db: str) -> None:
    policy_svc = PolicyService(db_path=test_db)
    case_svc = CaseService(db_path=test_db)
    case_a = case_svc.create_case(organization_id="org_aarav", subject_id="txn_2008_a")
    case_b = case_svc.create_case(organization_id="org_aarav", subject_id="txn_2008_b")

    approval_a = policy_svc.request_approval(
        case_id=case_a.id,
        action_type="SUBMIT_MOCK_SUPPORT_CASE",
        payload={"reason": "Case A discrepancy"},
        requested_by_type=ActorType.USER,
        requested_by_id="operator_1",
    )

    from app.services.policy import ApprovalNotFoundError

    # Attempting to approve approval_a under case_b must raise ApprovalNotFoundError
    with pytest.raises(ApprovalNotFoundError):
        policy_svc.approve_action(
            approval_id=approval_a.id,
            case_id=case_b.id,  # Wrong case!
            approver_actor_type=ActorType.USER,
            approver_actor_id="operator_2",
        )


def test_cannot_execute_action_on_resolved_case(test_db: str) -> None:
    policy_svc = PolicyService(db_path=test_db)
    case_svc = CaseService(db_path=test_db)
    case = case_svc.create_case(organization_id="org_aarav", subject_id="txn_2009")

    payload = {"reason": "Test resolved"}
    approval = policy_svc.request_approval(
        case_id=case.id,
        action_type="SUBMIT_MOCK_SUPPORT_CASE",
        payload=payload,
        requested_by_type=ActorType.USER,
        requested_by_id="operator_1",
    )
    policy_svc.approve_action(
        approval_id=approval.id,
        approver_actor_type=ActorType.USER,
        approver_actor_id="operator_2",
    )

    # Manually transition case to VERIFIED_RESOLVED
    conn = get_connection(test_db)
    try:
        art = repository.SourceArtifactRecord(
            id="art_res",
            organization_id="org_aarav",
            source_type="BANK_STATEMENT",
            file_name="bank.csv",
            schema_version="v1.0",
            dataset_version="v1.0",
            sha256="sha_res",
            size_bytes=10,
            storage_path="b.csv",
            record_count=1,
            ingested_at="2026-10-31T00:00:00Z",
        )
        repository.insert_source_artifact(conn, art)
        repository.insert_bank_entries(
            conn,
            [
                BankEntryRecord(
                    id="bank_res_01",
                    organization_id="org_aarav",
                    statement_entry_id="stmt_res_01",
                    bank_account_alias="bank_acc_4092",
                    booking_date="2026-10-31",
                    direction="CREDIT",
                    amount=Decimal("18450.00"),
                    currency="INR",
                    narration="Credit",
                    utr_reference="UTR-RES-01",
                    source_artifact_id=art.id,
                    source_row_number=1,
                    created_at="2026-10-31T00:00:00Z",
                )
            ],
        )
    finally:
        conn.close()

    v1 = case_svc.get_case(case.id).version
    case_svc.transition_case(case.id, CaseStatus.INVESTIGATING, expected_version=v1)
    v2 = case_svc.get_case(case.id).version
    case_svc.transition_case(case.id, CaseStatus.MONITORING, expected_version=v2)
    case_svc.transition_case(
        case.id,
        CaseStatus.VERIFIED_RESOLVED,
        expected_version=case_svc.get_case(case.id).version,
        evidence={"terminal_outcome": True, "bank_statement_entry_id": "bank_res_01"},
    )

    # Executing action on resolved case must fail
    with pytest.raises(PolicyError) as exc:
        policy_svc.execute_action(
            case_id=case.id,
            action_type="SUBMIT_MOCK_SUPPORT_CASE",
            payload=payload,
            approval_id=approval.id,
        )
    assert "already VERIFIED_RESOLVED" in str(exc.value)


def test_unicode_canonical_payload_hashing() -> None:
    payload_unicode_1 = {
        "store": "आरव जनरल स्टोर",
        "currency": "₹",
        "description": "अनसुलझा सेटलमेंट",
        "amount": "18450.00",
    }
    payload_unicode_2 = {
        "amount": "18450.00",
        "description": "अनसुलझा सेटलमेंट",
        "currency": "₹",
        "store": "आरव जनरल स्टोर",
    }

    hash_1 = compute_payload_hash(payload_unicode_1)
    hash_2 = compute_payload_hash(payload_unicode_2)
    assert hash_1 == hash_2
    assert len(hash_1) == 64


def test_blocked_action_variations_always_blocked() -> None:
    svc = PolicyService()
    blocked_actions = [
        "CHANGE_BANK_ACCOUNT",
        "UPDATE_BANK_DETAILS",
        "ALTER_BANK_ACCOUNT",
        "MODIFY_BANK_SETTINGS",
        "UPDATE_PAYOUT_CONFIG",
        "CHANGE_PAYOUT_SETTINGS",
        "PAY_MERCHANT_DIRECT",
        "DISBURSE_FUNDS",
        "DIRECT_DEBIT_ACCOUNT",
        "REFUND_CUSTOMER",
        "ACCESS_CREDENTIALS",
        "GET_DATABASE_PASSWORD",
        "READ_API_KEY",
        "BYPASS_APPROVAL_CHECK",
        "FORCE_CLOSE_UNVERIFIED",
    ]
    for action in blocked_actions:
        res = svc.evaluate_action(action)
        assert res.decision == PolicyDecision.BLOCKED, (
            f"{action} should be BLOCKED but was {res.decision}"
        )
        assert res.action_class == ActionClass.BLOCKED
