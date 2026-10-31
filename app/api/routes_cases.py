"""REST API endpoints for cases, state transitions, timeline, approvals, and actions."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.models.domain import ActorType, CasePriority
from app.services.audit import AuditService
from app.services.cases import (
    CaseNotFoundError,
    CaseService,
    FalseClosureError,
    InvalidStateTransitionError,
    VersionMismatchError,
)
from app.services.policy import (
    ApprovalExpiredError,
    ApprovalNotFoundError,
    ApprovalRequiredError,
    CannotSelfApproveError,
    InvalidApprovalStateError,
    PayloadHashMismatchError,
    PolicyBlockedError,
    PolicyService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cases", tags=["cases"])
audit_router = APIRouter(prefix="/audit-events", tags=["audit"])


# Request and response models
class CreateCaseRequest(BaseModel):
    organization_id: str = Field(default="org_aarav")
    reconciliation_result_id: str | None = None
    case_type: str = Field(default="MISSING_SETTLEMENT")
    priority: str = Field(default=CasePriority.MEDIUM)
    subject_type: str = Field(default="TRANSACTION")
    subject_id: str | None = None
    decision_summary: str | None = None
    actor_type: str = Field(default=ActorType.USER)
    actor_id: str = Field(default="operator_1")
    initial_details: dict[str, Any] | None = None


class TransitionCaseRequest(BaseModel):
    to_status: str
    expected_version: int
    actor_type: str = Field(default=ActorType.USER)
    actor_id: str = Field(default="operator_1")
    summary: str = ""
    details: dict[str, Any] | None = None
    evidence: dict[str, Any] | None = None
    decision_summary: str | None = None
    priority: str | None = None


class UpdateCaseRequest(BaseModel):
    expected_version: int
    priority: str | None = None
    decision_summary: str | None = None
    actor_type: str = Field(default=ActorType.USER)
    actor_id: str = Field(default="operator_1")
    summary: str = ""
    details: dict[str, Any] | None = None


class AddCaseNoteRequest(BaseModel):
    summary: str
    event_type: str = Field(default="NOTE_ADDED")
    actor_type: str = Field(default=ActorType.USER)
    actor_id: str = Field(default="operator_1")
    details: dict[str, Any] | None = None


class RequestApprovalRequest(BaseModel):
    action_type: str
    payload: dict[str, Any]
    requested_by_type: str = Field(default=ActorType.AGENT)
    requested_by_id: str = Field(default="agent_settlesaathi")
    expires_in_hours: int = Field(default=24)


class ApproveActionRequest(BaseModel):
    approver_actor_type: str = Field(default=ActorType.USER)
    approver_actor_id: str = Field(default="operator_1")
    approver_role: str = Field(default="operator")


class RejectActionRequest(BaseModel):
    actor_id: str = Field(default="operator_1")
    reason: str = Field(default="Rejected by operator")
    actor_type: str = Field(default=ActorType.USER)


class SubmitSupportCaseRequest(BaseModel):
    approval_id: str | None = None
    payload: dict[str, Any]
    idempotency_key: str | None = None
    actor_type: str = Field(default=ActorType.USER)
    actor_id: str = Field(default="operator_1")


@router.get("")
@router.get("/")
def list_cases(
    organization_id: str = Query(default="org_aarav"),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    case_type: str | None = Query(default=None),
    subject_type: str | None = Query(default=None),
    subject_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """List cases filtered by criteria."""
    service = CaseService()
    cases = service.list_cases(
        organization_id=organization_id,
        status=status,
        priority=priority,
        case_type=case_type,
        subject_type=subject_type,
        subject_id=subject_id,
        limit=limit,
        offset=offset,
    )
    return {"cases": [c.to_dict() for c in cases], "total": len(cases)}


@router.post("", status_code=201)
@router.post("/", status_code=201)
def create_case(
    request: Request,
    payload: CreateCaseRequest,
) -> dict[str, Any]:
    """Create a new case."""
    service = CaseService()
    correlation_id = getattr(request.state, "correlation_id", None)
    case = service.create_case(
        organization_id=payload.organization_id,
        reconciliation_result_id=payload.reconciliation_result_id,
        case_type=payload.case_type,
        priority=payload.priority,
        subject_type=payload.subject_type,
        subject_id=payload.subject_id,
        decision_summary=payload.decision_summary,
        actor_type=payload.actor_type,
        actor_id=payload.actor_id,
        correlation_id=correlation_id,
        initial_details=payload.initial_details,
    )
    return case.to_dict()


@router.get("/{case_id}")
def get_case(
    case_id: str,
    organization_id: str = Query(default="org_aarav"),
) -> dict[str, Any]:
    """Get case details."""
    service = CaseService()
    try:
        case = service.get_case(case_id, organization_id)
        return case.to_dict()
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{case_id}/transition")
def transition_case(
    case_id: str,
    payload: TransitionCaseRequest,
    request: Request,
    organization_id: str = Query(default="org_aarav"),
) -> dict[str, Any]:
    """Execute a case state machine transition."""
    service = CaseService()
    correlation_id = getattr(request.state, "correlation_id", None)
    try:
        updated = service.transition_case(
            case_id=case_id,
            to_status=payload.to_status,
            expected_version=payload.expected_version,
            actor_type=payload.actor_type,
            actor_id=payload.actor_id,
            summary=payload.summary,
            details=payload.details,
            evidence=payload.evidence,
            decision_summary=payload.decision_summary,
            priority=payload.priority,
            correlation_id=correlation_id,
            organization_id=organization_id,
        )
        return updated.to_dict()
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except VersionMismatchError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FalseClosureError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except InvalidStateTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/{case_id}")
@router.put("/{case_id}")
def update_case(
    case_id: str,
    payload: UpdateCaseRequest,
    request: Request,
    organization_id: str = Query(default="org_aarav"),
) -> dict[str, Any]:
    """Update case priority or decision summary with optimistic concurrency locking."""
    service = CaseService()
    correlation_id = getattr(request.state, "correlation_id", None)
    try:
        updated = service.update_case(
            case_id=case_id,
            expected_version=payload.expected_version,
            priority=payload.priority,
            decision_summary=payload.decision_summary,
            actor_type=payload.actor_type,
            actor_id=payload.actor_id,
            summary=payload.summary,
            details=payload.details,
            correlation_id=correlation_id,
            organization_id=organization_id,
        )
        return updated.to_dict()
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except VersionMismatchError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{case_id}/timeline")
def get_case_timeline(
    case_id: str,
    organization_id: str = Query(default="org_aarav"),
) -> dict[str, Any]:
    """Retrieve chronological event timeline for a case."""
    service = CaseService()
    try:
        events = service.get_timeline(case_id, organization_id)
        return {"case_id": case_id, "events": [e.to_dict() for e in events]}
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{case_id}/events", status_code=201)
def add_case_event(
    case_id: str,
    payload: AddCaseNoteRequest,
    request: Request,
    organization_id: str = Query(default="org_aarav"),
) -> dict[str, Any]:
    """Add a note or diagnostic event to the case timeline."""
    service = CaseService()
    correlation_id = getattr(request.state, "correlation_id", None)
    try:
        event = service.add_timeline_event(
            case_id=case_id,
            event_type=payload.event_type,
            summary=payload.summary,
            actor_type=payload.actor_type,
            actor_id=payload.actor_id,
            details=payload.details,
            correlation_id=correlation_id,
            organization_id=organization_id,
        )
        return event.to_dict()
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{case_id}/approvals")
def list_case_approvals(
    case_id: str,
    organization_id: str = Query(default="org_aarav"),
) -> dict[str, Any]:
    """List approvals created for a case."""
    service = CaseService()
    try:
        service.get_case(case_id, organization_id)
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    from app.db.connection import get_connection
    from app.services import repository

    conn = get_connection()
    try:
        approvals = repository.list_approvals_for_case(conn, case_id, organization_id)
        return {"case_id": case_id, "approvals": [a.to_dict() for a in approvals]}
    finally:
        conn.close()


@router.post("/{case_id}/approvals", status_code=201)
def request_approval(
    case_id: str,
    payload: RequestApprovalRequest,
    request: Request,
    organization_id: str = Query(default="org_aarav"),
) -> dict[str, Any]:
    """Request authorization for a sensitive action."""
    service = PolicyService()
    correlation_id = getattr(request.state, "correlation_id", None)
    try:
        approval = service.request_approval(
            case_id=case_id,
            action_type=payload.action_type,
            payload=payload.payload,
            requested_by_type=payload.requested_by_type,
            requested_by_id=payload.requested_by_id,
            expires_in_hours=payload.expires_in_hours,
            correlation_id=correlation_id,
            organization_id=organization_id,
        )
        return approval.to_dict()
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PolicyBlockedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{case_id}/approvals/{approval_id}/approve")
def approve_action(
    case_id: str,
    approval_id: str,
    payload: ApproveActionRequest,
    request: Request,
    organization_id: str = Query(default="org_aarav"),
) -> dict[str, Any]:
    """Approve a pending action authorization."""
    service = PolicyService()
    correlation_id = getattr(request.state, "correlation_id", None)
    try:
        approval = service.approve_action(
            approval_id=approval_id,
            approver_actor_type=payload.approver_actor_type,
            approver_actor_id=payload.approver_actor_id,
            approver_role=payload.approver_role,
            case_id=case_id,
            correlation_id=correlation_id,
            organization_id=organization_id,
        )
        return approval.to_dict()
    except CannotSelfApproveError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ApprovalNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ApprovalExpiredError as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc
    except InvalidApprovalStateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{case_id}/approvals/{approval_id}/reject")
def reject_action(
    case_id: str,
    approval_id: str,
    payload: RejectActionRequest,
    request: Request,
    organization_id: str = Query(default="org_aarav"),
) -> dict[str, Any]:
    """Reject a pending action authorization."""
    service = PolicyService()
    correlation_id = getattr(request.state, "correlation_id", None)
    try:
        approval = service.reject_approval(
            approval_id=approval_id,
            actor_id=payload.actor_id,
            reason=payload.reason,
            actor_type=payload.actor_type,
            case_id=case_id,
            correlation_id=correlation_id,
            organization_id=organization_id,
        )
        return approval.to_dict()
    except ApprovalNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidApprovalStateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{case_id}/actions/submit-support-case")
def submit_support_case(
    case_id: str,
    payload: SubmitSupportCaseRequest,
    request: Request,
    organization_id: str = Query(default="org_aarav"),
) -> dict[str, Any]:
    """Submit a simulated support ticket gated by policy and approval."""
    service = PolicyService()
    correlation_id = getattr(request.state, "correlation_id", None)
    idempotency_key = (
        payload.idempotency_key
        or request.headers.get("Idempotency-Key")
        or request.headers.get("idempotency-key")
    )
    try:
        result = service.execute_action(
            case_id=case_id,
            action_type="SUBMIT_MOCK_SUPPORT_CASE",
            payload=payload.payload,
            approval_id=payload.approval_id,
            idempotency_key=idempotency_key,
            actor_type=payload.actor_type,
            actor_id=payload.actor_id,
            correlation_id=correlation_id,
            organization_id=organization_id,
        )
        return result
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except VersionMismatchError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PolicyBlockedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (ApprovalRequiredError, PayloadHashMismatchError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ApprovalNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ApprovalExpiredError as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@audit_router.get("")
@audit_router.get("/")
def list_audit_events(
    organization_id: str = Query(default="org_aarav"),
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    correlation_id: str | None = Query(default=None),
    actor_type: str | None = Query(default=None),
    actor_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """Query immutable audit events for audit and compliance inspection."""
    service = AuditService()
    events = service.list_events(
        organization_id=organization_id,
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        correlation_id=correlation_id,
        actor_type=actor_type,
        actor_id=actor_id,
        limit=limit,
        offset=offset,
    )
    return {"events": [e.to_dict() for e in events], "total": len(events)}
