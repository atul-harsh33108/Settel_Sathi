"""Integration tests for cases, approvals, action execution, and audit trail REST APIs."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.connection import init_db
from app.main import app

client = TestClient(app)


def setup_api_test_env(tmp_path: Path, monkeypatch) -> str:
    db_file = tmp_path / f"test_api_cases_{uuid4().hex[:8]}.db"
    db_url = f"sqlite:///{db_file}"
    monkeypatch.setenv("SETTLESAATHI_DATABASE_URL", db_url)
    get_settings.cache_clear()
    init_db(db_url)
    return db_url


def test_api_case_crud_and_timeline(tmp_path: Path, monkeypatch) -> None:
    setup_api_test_env(tmp_path, monkeypatch)

    # 1. List cases initially (empty)
    list_resp = client.get("/api/v1/cases?organization_id=org_aarav")
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 0

    # 2. Create case via POST /api/v1/cases
    create_payload = {
        "organization_id": "org_aarav",
        "case_type": "MISSING_SETTLEMENT",
        "priority": "HIGH",
        "subject_type": "TRANSACTION",
        "subject_id": "txn_api_1",
        "decision_summary": "Missing settlement for hero scenario SCN-02",
        "actor_type": "USER",
        "actor_id": "operator_api",
    }
    create_resp = client.post(
        "/api/v1/cases",
        json=create_payload,
        headers={"X-Correlation-ID": "corr-case-create-001"},
    )
    assert create_resp.status_code == 201
    case_data = create_resp.json()
    case_id = case_data["id"]
    assert case_data["status"] == "DETECTED"
    assert case_data["version"] == 1
    assert case_data["priority"] == "HIGH"

    # 3. Get case detail via GET /api/v1/cases/{id}
    detail_resp = client.get(f"/api/v1/cases/{case_id}?organization_id=org_aarav")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == case_id

    # 4. Get timeline via GET /api/v1/cases/{id}/timeline
    timeline_resp = client.get(f"/api/v1/cases/{case_id}/timeline")
    assert timeline_resp.status_code == 200
    events = timeline_resp.json()["events"]
    assert len(events) == 1
    assert events[0]["event_type"] == "CASE_CREATED"

    # 5. Add custom note via POST /api/v1/cases/{id}/events
    note_resp = client.post(
        f"/api/v1/cases/{case_id}/events",
        json={
            "summary": "Verified bank statement has no credit entry",
            "event_type": "INVESTIGATION_NOTE",
            "actor_id": "operator_api",
        },
    )
    assert note_resp.status_code == 201

    # Check timeline again
    t2_resp = client.get(f"/api/v1/cases/{case_id}/timeline")
    assert len(t2_resp.json()["events"]) == 2


def test_api_case_transitions_and_concurrency(tmp_path: Path, monkeypatch) -> None:
    setup_api_test_env(tmp_path, monkeypatch)

    # Create case
    case_resp = client.post(
        "/api/v1/cases",
        json={"organization_id": "org_aarav", "subject_id": "txn_api_2"},
    )
    case_id = case_resp.json()["id"]

    # Valid transition to INVESTIGATING with version=1
    trans_resp = client.post(
        f"/api/v1/cases/{case_id}/transition",
        json={
            "to_status": "INVESTIGATING",
            "expected_version": 1,
            "summary": "Beginning investigation",
        },
    )
    assert trans_resp.status_code == 200
    assert trans_resp.json()["status"] == "INVESTIGATING"
    assert trans_resp.json()["version"] == 2

    # Stale version update: retry with version=1 -> MUST return 409 Conflict
    stale_resp = client.post(
        f"/api/v1/cases/{case_id}/transition",
        json={
            "to_status": "AWAITING_APPROVAL",
            "expected_version": 1,  # Stale!
        },
    )
    assert stale_resp.status_code == 409
    assert "version mismatch" in stale_resp.json()["detail"].lower()

    # Invalid state transition: from INVESTIGATING directly to DETECTED -> 400 Bad Request
    invalid_resp = client.post(
        f"/api/v1/cases/{case_id}/transition",
        json={
            "to_status": "DETECTED",
            "expected_version": 2,
        },
    )
    assert invalid_resp.status_code == 400

    # False closure attempt without evidence -> 422 Unprocessable Entity
    # First move to MONITORING

    client.post(
        f"/api/v1/cases/{case_id}/transition",
        json={"to_status": "MONITORING", "expected_version": 2},
    )
    closure_resp = client.post(
        f"/api/v1/cases/{case_id}/transition",
        json={
            "to_status": "VERIFIED_RESOLVED",
            "expected_version": 3,
            "evidence": {},  # Empty evidence!
        },
    )
    assert closure_resp.status_code == 422
    assert "False-closure rejected" in closure_resp.json()["detail"]


def test_api_approval_lifecycle_and_execution(tmp_path: Path, monkeypatch) -> None:
    setup_api_test_env(tmp_path, monkeypatch)

    case_resp = client.post(
        "/api/v1/cases",
        json={"organization_id": "org_aarav", "subject_id": "txn_api_3"},
    )
    case_id = case_resp.json()["id"]

    # 1. Blocked action request -> 403 Forbidden
    blocked_resp = client.post(
        f"/api/v1/cases/{case_id}/approvals",
        json={"action_type": "MOVE_MONEY", "payload": {"amount": "100.00"}},
    )
    assert blocked_resp.status_code == 403

    # 2. Request valid approval for sensitive action
    action_payload = {
        "payout_reference": "PO-API-18450",
        "gross_amount": "18450.00",
        "reason": "Missing settlement payout in bank statement",
    }
    appr_req_resp = client.post(
        f"/api/v1/cases/{case_id}/approvals",
        json={
            "action_type": "SUBMIT_MOCK_SUPPORT_CASE",
            "payload": action_payload,
            "requested_by_type": "AGENT",
            "requested_by_id": "agent_aarav",
        },
    )
    assert appr_req_resp.status_code == 201
    approval = appr_req_resp.json()
    approval_id = approval["id"]
    assert approval["status"] == "PENDING"
    assert len(approval["payload_hash"]) == 64

    # 3. Agent self-approval attempt -> 403 Forbidden
    self_appr_resp = client.post(
        f"/api/v1/cases/{case_id}/approvals/{approval_id}/approve",
        json={"approver_actor_type": "AGENT", "approver_actor_id": "agent_aarav"},
    )
    assert self_appr_resp.status_code == 403
    assert "cannot grant approvals" in self_appr_resp.json()["detail"]

    # 4. Attempt action execution before approval -> 422 Unprocessable Entity
    early_exec_resp = client.post(
        f"/api/v1/cases/{case_id}/actions/submit-support-case",
        json={"approval_id": approval_id, "payload": action_payload},
    )
    assert early_exec_resp.status_code == 422
    assert "expected 'APPROVED'" in early_exec_resp.json()["detail"]

    # 5. Human user grants approval -> 200 OK
    approve_resp = client.post(
        f"/api/v1/cases/{case_id}/approvals/{approval_id}/approve",
        json={
            "approver_actor_type": "USER",
            "approver_actor_id": "operator_aarav",
            "approver_role": "operations_lead",
        },
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "APPROVED"

    # 6. Attempt execution with tampered payload -> 422 Unprocessable Entity (anti-tamper)
    tampered_payload = dict(action_payload)
    tampered_payload["gross_amount"] = "99999.00"
    tampered_resp = client.post(
        f"/api/v1/cases/{case_id}/actions/submit-support-case",
        json={"approval_id": approval_id, "payload": tampered_payload},
    )
    assert tampered_resp.status_code == 422
    assert "Approval bypass detected" in tampered_resp.json()["detail"]

    # 7. Valid execution with approved payload -> 200 OK
    idempotency_key = "idem_api_key_001"
    exec_resp = client.post(
        f"/api/v1/cases/{case_id}/actions/submit-support-case",
        json={
            "approval_id": approval_id,
            "payload": action_payload,
            "idempotency_key": idempotency_key,
        },
    )
    assert exec_resp.status_code == 200
    exec_data = exec_resp.json()
    assert exec_data["status"] == "SUCCEEDED"
    assert exec_data["idempotent_replay"] is False
    assert "external_ticket_id" in exec_data

    # 8. Idempotent replay with same idempotency key -> 200 OK with idempotent_replay=true
    replay_resp = client.post(
        f"/api/v1/cases/{case_id}/actions/submit-support-case",
        json={
            "approval_id": approval_id,
            "payload": action_payload,
            "idempotency_key": idempotency_key,
        },
    )
    assert replay_resp.status_code == 200
    assert replay_resp.json()["idempotent_replay"] is True
    assert replay_resp.json()["external_ticket_id"] == exec_data["external_ticket_id"]


def test_api_audit_events_endpoint(tmp_path: Path, monkeypatch) -> None:
    setup_api_test_env(tmp_path, monkeypatch)

    # Perform action that creates audit events
    client.post(
        "/api/v1/cases",
        json={
            "organization_id": "org_aarav",
            "subject_id": "txn_audit_1",
            "actor_type": "USER",
            "actor_id": "auditor_bob",
        },
    )

    # Query audit events endpoint
    audit_resp = client.get("/api/v1/audit-events?organization_id=org_aarav")
    assert audit_resp.status_code == 200
    data = audit_resp.json()
    assert data["total"] >= 1
    events = data["events"]
    assert any(e["event_type"] == "CASE_CREATED" for e in events)

    # Query with actor filter
    actor_resp = client.get("/api/v1/audit-events?organization_id=org_aarav&actor_id=auditor_bob")
    assert actor_resp.status_code == 200
    assert actor_resp.json()["total"] >= 1


def test_api_case_patch_update_and_errors(tmp_path: Path, monkeypatch) -> None:
    setup_api_test_env(tmp_path, monkeypatch)

    # 1. Create a case
    case_resp = client.post(
        "/api/v1/cases",
        json={"organization_id": "org_aarav", "subject_id": "txn_patch_1", "priority": "LOW"},
    )
    case_id = case_resp.json()["id"]

    # 2. Update priority and decision summary via PATCH /api/v1/cases/{id}
    patch_resp = client.patch(
        f"/api/v1/cases/{case_id}",
        json={
            "expected_version": 1,
            "priority": "HIGH",
            "decision_summary": "Priority upgraded via API",
        },
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["priority"] == "HIGH"
    assert updated["decision_summary"] == "Priority upgraded via API"
    assert updated["version"] == 2

    # 3. Concurrency conflict on stale version -> 409 Conflict
    conflict_resp = client.patch(
        f"/api/v1/cases/{case_id}",
        json={
            "expected_version": 1,  # Stale!
            "priority": "CRITICAL",
        },
    )
    assert conflict_resp.status_code == 409

    # 4. Update nonexistent case -> 404 Not Found
    nf_resp = client.patch(
        "/api/v1/cases/case_nonexistent",
        json={"expected_version": 1, "priority": "HIGH"},
    )
    assert nf_resp.status_code == 404


def test_api_idempotency_key_header_and_cross_case_checks(tmp_path: Path, monkeypatch) -> None:
    setup_api_test_env(tmp_path, monkeypatch)

    case_resp = client.post(
        "/api/v1/cases",
        json={"organization_id": "org_aarav", "subject_id": "txn_idem_hdr"},
    )
    case_id = case_resp.json()["id"]

    # Nonexistent case approvals -> 404
    bad_appr_resp = client.get("/api/v1/cases/case_ghost/approvals")
    assert bad_appr_resp.status_code == 404

    bad_req_resp = client.post(
        "/api/v1/cases/case_ghost/approvals",
        json={"action_type": "SUBMIT_MOCK_SUPPORT_CASE", "payload": {"foo": "bar"}},
    )
    assert bad_req_resp.status_code == 404

    # Request valid approval
    action_payload = {"payout_reference": "PO-HDR-01"}
    req_resp = client.post(
        f"/api/v1/cases/{case_id}/approvals",
        json={
            "action_type": "SUBMIT_MOCK_SUPPORT_CASE",
            "payload": action_payload,
            "requested_by_type": "USER",
            "requested_by_id": "requester_alice",
        },
    )
    assert req_resp.status_code == 201
    approval_id = req_resp.json()["id"]

    # Cross-case approval attempt -> 404
    cross_appr_resp = client.post(
        f"/api/v1/cases/case_other/approvals/{approval_id}/approve",
        json={"approver_actor_type": "USER", "approver_actor_id": "approver_bob"},
    )
    assert cross_appr_resp.status_code == 404

    # Valid approval by different user
    ok_appr_resp = client.post(
        f"/api/v1/cases/{case_id}/approvals/{approval_id}/approve",
        json={"approver_actor_type": "USER", "approver_actor_id": "approver_bob"},
    )
    assert ok_appr_resp.status_code == 200

    # Submit action using Idempotency-Key HTTP header
    exec_resp = client.post(
        f"/api/v1/cases/{case_id}/actions/submit-support-case",
        json={"approval_id": approval_id, "payload": action_payload},
        headers={"Idempotency-Key": "idem_hdr_unique_001"},
    )
    assert exec_resp.status_code == 200
    assert exec_resp.json()["idempotency_key"] == "idem_hdr_unique_001"
    assert exec_resp.json()["idempotent_replay"] is False

    # Replay using same Idempotency-Key HTTP header
    replay_resp = client.post(
        f"/api/v1/cases/{case_id}/actions/submit-support-case",
        json={"approval_id": approval_id, "payload": action_payload},
        headers={"Idempotency-Key": "idem_hdr_unique_001"},
    )
    assert replay_resp.status_code == 200
    assert replay_resp.json()["idempotent_replay"] is True
