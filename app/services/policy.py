"""Policy decisions, approval records, payload hash verification, and action execution."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from app.db.connection import db_session, get_connection
from app.models.domain import (
    ActionAttemptRecord,
    ActionClass,
    ActorType,
    ApprovalRecord,
    ApprovalStatus,
    AuditEventRecord,
    CaseEventRecord,
    CaseStatus,
    PolicyDecision,
)
from app.services import repository
from app.services.cases import CaseNotFoundError, VersionMismatchError

logger = logging.getLogger(__name__)


class PolicyError(Exception):
    """Base exception for policy engine and approval operations."""


class PolicyBlockedError(PolicyError):
    """Raised when an action is strictly blocked by policy."""


class ApprovalRequiredError(PolicyError):
    """Raised when an action requires approval but none (or invalid) was provided."""


class ApprovalNotFoundError(PolicyError):
    """Raised when a referenced approval record is not found."""


class ApprovalExpiredError(PolicyError):
    """Raised when an approval record has expired."""


class PayloadHashMismatchError(PolicyError):
    """Raised when the runtime payload does not match the approved canonical payload hash."""


class CannotSelfApproveError(PolicyError):
    """Raised when an automated agent or unprivileged actor attempts self-approval."""


class InvalidApprovalStateError(PolicyError):
    """Raised when an approval operation is attempted on an invalid approval state."""


# Mapping of action types to their action classes
ACTION_REGISTRY: dict[str, str] = {
    # Read actions
    "VIEW_CASE": ActionClass.READ,
    "VIEW_TIMELINE": ActionClass.READ,
    "GET_CASE": ActionClass.READ,
    "LIST_CASES": ActionClass.READ,
    "GET_RECONCILIATION_EVIDENCE": ActionClass.READ,
    "GET_SETTLEMENT_DETAIL": ActionClass.READ,
    "GET_BANK_MATCH_CANDIDATES": ActionClass.READ,
    # Draft actions
    "DRAFT_SUPPORT_CASE": ActionClass.DRAFT,
    "DRAFT_EXPLANATION": ActionClass.DRAFT,
    "DRAFT_REPLY": ActionClass.DRAFT,
    # External non-sensitive write
    "UPDATE_CASE_NOTES": ActionClass.EXTERNAL_NON_SENSITIVE_WRITE,
    "ADD_CASE_TAG": ActionClass.EXTERNAL_NON_SENSITIVE_WRITE,
    "LOG_INTERNAL_NOTE": ActionClass.EXTERNAL_NON_SENSITIVE_WRITE,
    # Sensitive write (approval required)
    "SUBMIT_MOCK_SUPPORT_CASE": ActionClass.SENSITIVE_WRITE,
    "SUBMIT_SUPPORT_TICKET": ActionClass.SENSITIVE_WRITE,
    "REQUEST_RECREDIT": ActionClass.SENSITIVE_WRITE,
    "ESCALATE_DISPUTE": ActionClass.SENSITIVE_WRITE,
    # Blocked actions (strictly forbidden)
    "MOVE_MONEY": ActionClass.BLOCKED,
    "MODIFY_BANK_ACCOUNT": ActionClass.BLOCKED,
    "DIRECT_DEBIT": ActionClass.BLOCKED,
    "INITIATE_TRANSFER": ActionClass.BLOCKED,
    "CHANGE_PAYOUT_SETTINGS": ActionClass.BLOCKED,
    "BYPASS_APPROVAL": ActionClass.BLOCKED,
    "ISSUE_REFUND": ActionClass.BLOCKED,
}


def compute_payload_hash(payload: Any) -> str:
    """Compute deterministic SHA-256 hash of canonical JSON payload."""
    if isinstance(payload, bytes):
        raw = payload
    elif isinstance(payload, str):
        # If it's already a string, parse and re-serialize to guarantee canonical ordering
        try:
            parsed = json.loads(payload)
            canonical_str = json.dumps(
                parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            )
            raw = canonical_str.encode("utf-8")
        except Exception:
            raw = payload.strip().encode("utf-8")
    elif isinstance(payload, dict | list):
        canonical_str = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        raw = canonical_str.encode("utf-8")
    else:
        raw = str(payload).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class PolicyEvaluationResult:
    """Result of policy evaluation for an action."""

    action_type: str
    action_class: str
    decision: str  # ALLOWED, APPROVAL_REQUIRED, BLOCKED
    reason: str


class PolicyService:
    """Evaluates action safety, manages approval tokens, and enforces bounded autonomy."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path

    def evaluate_action(
        self,
        action_type: str,
        payload: dict[str, Any] | None = None,
    ) -> PolicyEvaluationResult:
        """Evaluate policy decision for a given action."""
        action_upper = action_type.strip().upper()

        # Strict checks for blocked actions by registry or financial safety boundary
        in_registry_blocked = (
            action_upper in ACTION_REGISTRY and ACTION_REGISTRY[action_upper] == ActionClass.BLOCKED
        )
        is_blocked = (
            in_registry_blocked
            or action_upper.startswith("MOVE_")
            or "MONEY" in action_upper
            or "BANK_ACCOUNT" in action_upper
            or "BANK_DETAIL" in action_upper
            or action_upper.startswith("MODIFY_BANK")
            or action_upper.startswith("CHANGE_BANK")
            or action_upper.startswith("UPDATE_BANK")
            or action_upper.startswith("ALTER_BANK")
            or action_upper.startswith("CHANGE_PAYOUT")
            or action_upper.startswith("UPDATE_PAYOUT")
            or "PAYOUT_SETTING" in action_upper
            or "PAYOUT_CONFIG" in action_upper
            or action_upper.startswith("TRANSFER_")
            or action_upper.startswith("INITIATE_TRANSFER")
            or action_upper.startswith("DIRECT_DEBIT")
            or action_upper.startswith("PAY_")
            or "DISBURSE" in action_upper
            or "REFUND" in action_upper
            or "SECRET" in action_upper
            or "PASSWORD" in action_upper
            or "API_KEY" in action_upper
            or "CREDENTIAL" in action_upper
            or "OTP" in action_upper
            or "PIN" in action_upper
            or "CVV" in action_upper
            or "BYPASS" in action_upper
            or "FORCE_CLOSE" in action_upper
        )
        if is_blocked:
            return PolicyEvaluationResult(
                action_type=action_upper,
                action_class=ActionClass.BLOCKED,
                decision=PolicyDecision.BLOCKED,
                reason=f"Action '{action_upper}' is strictly BLOCKED by system policy.",
            )

        action_class = ACTION_REGISTRY.get(action_upper)

        if action_class == ActionClass.READ:
            return PolicyEvaluationResult(
                action_type=action_upper,
                action_class=ActionClass.READ,
                decision=PolicyDecision.ALLOWED,
                reason="Read operations are unconditionally permitted within tenant scope.",
            )

        if action_class == ActionClass.DRAFT:
            return PolicyEvaluationResult(
                action_type=action_upper,
                action_class=ActionClass.DRAFT,
                decision=PolicyDecision.ALLOWED,
                reason="Drafting operations produce unexecuted payloads and are permitted.",
            )

        if action_class == ActionClass.EXTERNAL_NON_SENSITIVE_WRITE:
            return PolicyEvaluationResult(
                action_type=action_upper,
                action_class=ActionClass.EXTERNAL_NON_SENSITIVE_WRITE,
                decision=PolicyDecision.ALLOWED,
                reason="Non-sensitive write is permitted.",
            )

        if action_class == ActionClass.SENSITIVE_WRITE:
            return PolicyEvaluationResult(
                action_type=action_upper,
                action_class=ActionClass.SENSITIVE_WRITE,
                decision=PolicyDecision.APPROVAL_REQUIRED,
                reason=(
                    f"Action '{action_upper}' creates external commitments "
                    "and requires explicit human approval."
                ),
            )

        # Unregistered/unknown action default to approval required for defense-in-depth
        return PolicyEvaluationResult(
            action_type=action_upper,
            action_class=ActionClass.SENSITIVE_WRITE,
            decision=PolicyDecision.APPROVAL_REQUIRED,
            reason=(
                f"Unregistered action '{action_upper}' defaults to APPROVAL_REQUIRED for security."
            ),
        )

    def request_approval(
        self,
        case_id: str,
        action_type: str,
        payload: dict[str, Any],
        requested_by_type: str = ActorType.AGENT,
        requested_by_id: str = "agent_settlesaathi",
        expires_in_hours: int = 24,
        correlation_id: str | None = None,
        organization_id: str = "org_aarav",
    ) -> ApprovalRecord:
        """Create a pending approval record with canonical payload hash."""
        evaluation = self.evaluate_action(action_type, payload)
        if evaluation.decision == PolicyDecision.BLOCKED:
            raise PolicyBlockedError(evaluation.reason)

        now_utc = datetime.now(UTC)
        now_iso = now_utc.isoformat()
        expires_iso = (now_utc + timedelta(hours=expires_in_hours)).isoformat()
        approval_id = f"appr_{uuid4().hex[:12]}"
        payload_hash = compute_payload_hash(payload)
        payload_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)

        approval = ApprovalRecord(
            id=approval_id,
            case_id=case_id,
            organization_id=organization_id,
            action_type=evaluation.action_type,
            action_class=evaluation.action_class,
            payload_hash=payload_hash,
            payload_json=payload_json,
            status=ApprovalStatus.PENDING,
            requested_by_type=requested_by_type,
            requested_by_id=requested_by_id,
            approved_by=None,
            approved_at=None,
            expires_at=expires_iso,
            rejection_reason=None,
            created_at=now_iso,
        )

        with db_session(self.db_path) as s_conn:
            # Verify case exists
            case = repository.find_case_by_id(s_conn, case_id, organization_id)
            if not case:
                raise CaseNotFoundError(
                    f"Case '{case_id}' not found for organization '{organization_id}'"
                )

            if case.status == CaseStatus.VERIFIED_RESOLVED:
                raise PolicyError(
                    f"Cannot request approval for case '{case_id}' "
                    "because it is already VERIFIED_RESOLVED."
                )

            repository.insert_approval(s_conn, approval)

            # Update case status if in DETECTED or INVESTIGATING
            if case.status in (CaseStatus.DETECTED, CaseStatus.INVESTIGATING):
                repository.update_case_with_version(
                    s_conn,
                    case_id=case_id,
                    new_status=CaseStatus.AWAITING_APPROVAL,
                    expected_version=case.version,
                    updated_at=now_iso,
                )

            # Record timeline event on case
            event = CaseEventRecord(
                id=f"evt_{uuid4().hex[:16]}",
                case_id=case_id,
                organization_id=organization_id,
                actor_type=requested_by_type,
                actor_id=requested_by_id,
                from_status=case.status,
                to_status=CaseStatus.AWAITING_APPROVAL,
                event_type="APPROVAL_REQUESTED",
                summary=f"Approval requested for action {evaluation.action_type}",
                details_json=json.dumps(
                    {
                        "approval_id": approval_id,
                        "payload_hash": payload_hash,
                        "action_type": evaluation.action_type,
                    }
                ),
                created_at=now_iso,
            )
            repository.insert_case_event(s_conn, event)

            # Record audit event
            audit_event = AuditEventRecord(
                id=f"aud_{uuid4().hex[:16]}",
                organization_id=organization_id,
                actor_type=requested_by_type,
                actor_id=requested_by_id,
                correlation_id=correlation_id,
                entity_type="APPROVAL",
                entity_id=approval_id,
                event_type="APPROVAL_REQUESTED",
                payload_hash=payload_hash,
                details_json=json.dumps(
                    {
                        "case_id": case_id,
                        "action_type": evaluation.action_type,
                        "expires_at": expires_iso,
                    }
                ),
                created_at=now_iso,
            )
            repository.insert_audit_event(s_conn, audit_event)

        logger.info(
            "Approval %s created for case %s (hash: %s)", approval_id, case_id, payload_hash
        )
        return approval

    def approve_action(
        self,
        approval_id: str,
        approver_actor_type: str = ActorType.USER,
        approver_actor_id: str = "operator_1",
        approver_role: str = "operator",
        case_id: str | None = None,
        correlation_id: str | None = None,
        organization_id: str = "org_aarav",
    ) -> ApprovalRecord:
        """Approve a pending approval token with four-eyes and case scoping checks."""
        # Hard check: Automated agents or system actors cannot grant approvals
        if approver_actor_type in (ActorType.AGENT, ActorType.SYSTEM):
            raise CannotSelfApproveError(
                f"Actor type '{approver_actor_type}' cannot grant approvals. "
                "Explicit human authorization is required."
            )

        now_utc = datetime.now(UTC)
        now_iso = now_utc.isoformat()

        with db_session(self.db_path) as s_conn:
            approval = repository.find_approval_by_id(s_conn, approval_id, organization_id)
            if not approval:
                raise ApprovalNotFoundError(
                    f"Approval '{approval_id}' not found for organization '{organization_id}'"
                )

            if case_id and approval.case_id != case_id:
                raise ApprovalNotFoundError(
                    f"Approval '{approval_id}' belongs to case "
                    f"'{approval.case_id}', not '{case_id}'"
                )

            # Four-eyes governance: Requester and approver cannot be the same identity
            if approver_actor_id == approval.requested_by_id:
                raise CannotSelfApproveError(
                    f"Requester '{approval.requested_by_id}' and approver '{approver_actor_id}' "
                    "cannot be the same identity under four-eyes financial governance."
                )

            if approval.status != ApprovalStatus.PENDING:
                raise InvalidApprovalStateError(
                    f"Cannot approve approval '{approval_id}' in status '{approval.status}'. "
                    "Must be PENDING."
                )

            # Expiration check
            expires_at = datetime.fromisoformat(approval.expires_at)
            if now_utc > expires_at:
                repository.update_approval_status(
                    s_conn,
                    approval_id,
                    ApprovalStatus.EXPIRED,
                    rejection_reason="Approval expired before decision",
                )
                raise ApprovalExpiredError(
                    f"Approval '{approval_id}' expired at {approval.expires_at}."
                )

            repository.update_approval_status(
                s_conn,
                approval_id=approval_id,
                status=ApprovalStatus.APPROVED,
                approved_by=approver_actor_id,
                approved_at=now_iso,
            )

            # Timeline event on case
            event = CaseEventRecord(
                id=f"evt_{uuid4().hex[:16]}",
                case_id=approval.case_id,
                organization_id=organization_id,
                actor_type=approver_actor_type,
                actor_id=approver_actor_id,
                from_status=None,
                to_status=CaseStatus.AWAITING_APPROVAL,
                event_type="APPROVAL_GRANTED",
                summary=f"Approval {approval_id} granted by {approver_actor_id} ({approver_role})",
                details_json=json.dumps(
                    {"approval_id": approval_id, "payload_hash": approval.payload_hash}
                ),
                created_at=now_iso,
            )
            repository.insert_case_event(s_conn, event)

            # Audit event
            audit_event = AuditEventRecord(
                id=f"aud_{uuid4().hex[:16]}",
                organization_id=organization_id,
                actor_type=approver_actor_type,
                actor_id=approver_actor_id,
                correlation_id=correlation_id,
                entity_type="APPROVAL",
                entity_id=approval_id,
                event_type="APPROVAL_GRANTED",
                payload_hash=approval.payload_hash,
                details_json=json.dumps({"approver_role": approver_role, "approved_at": now_iso}),
                created_at=now_iso,
            )
            repository.insert_audit_event(s_conn, audit_event)

            updated = repository.find_approval_by_id(s_conn, approval_id, organization_id)
            assert updated is not None
            return updated

    def reject_approval(
        self,
        approval_id: str,
        actor_id: str = "operator_1",
        reason: str = "Rejected by operator",
        actor_type: str = ActorType.USER,
        case_id: str | None = None,
        correlation_id: str | None = None,
        organization_id: str = "org_aarav",
    ) -> ApprovalRecord:
        """Reject a pending approval."""
        now_iso = datetime.now(UTC).isoformat()
        with db_session(self.db_path) as s_conn:
            approval = repository.find_approval_by_id(s_conn, approval_id, organization_id)
            if not approval:
                raise ApprovalNotFoundError(f"Approval '{approval_id}' not found")

            if case_id and approval.case_id != case_id:
                raise ApprovalNotFoundError(
                    f"Approval '{approval_id}' belongs to case "
                    f"'{approval.case_id}', not '{case_id}'"
                )

            if approval.status != ApprovalStatus.PENDING:
                raise InvalidApprovalStateError(
                    f"Cannot reject approval '{approval_id}' in status '{approval.status}'"
                )

            repository.update_approval_status(
                s_conn,
                approval_id=approval_id,
                status=ApprovalStatus.REJECTED,
                rejection_reason=reason,
            )

            # Case timeline event
            event = CaseEventRecord(
                id=f"evt_{uuid4().hex[:16]}",
                case_id=approval.case_id,
                organization_id=organization_id,
                actor_type=actor_type,
                actor_id=actor_id,
                from_status=None,
                to_status=CaseStatus.INVESTIGATING,
                event_type="APPROVAL_REJECTED",
                summary=f"Approval {approval_id} rejected: {reason}",
                details_json=json.dumps({"reason": reason}),
                created_at=now_iso,
            )
            repository.insert_case_event(s_conn, event)

            # Audit event
            audit_event = AuditEventRecord(
                id=f"aud_{uuid4().hex[:16]}",
                organization_id=organization_id,
                actor_type=actor_type,
                actor_id=actor_id,
                correlation_id=correlation_id,
                entity_type="APPROVAL",
                entity_id=approval_id,
                event_type="APPROVAL_REJECTED",
                payload_hash=approval.payload_hash,
                details_json=json.dumps({"rejection_reason": reason}),
                created_at=now_iso,
            )
            repository.insert_audit_event(s_conn, audit_event)

            updated = repository.find_approval_by_id(s_conn, approval_id, organization_id)
            assert updated is not None
            return updated

    def _record_audit_event_direct(
        self,
        event: AuditEventRecord,
    ) -> None:
        conn = get_connection(self.db_path)
        try:
            repository.insert_audit_event(conn, event)
        finally:
            conn.close()

    def execute_action(
        self,
        case_id: str,
        action_type: str,
        payload: dict[str, Any],
        approval_id: str | None = None,
        idempotency_key: str | None = None,
        actor_type: str = ActorType.USER,
        actor_id: str = "operator_1",
        correlation_id: str | None = None,
        organization_id: str = "org_aarav",
    ) -> dict[str, Any]:
        """Execute a sensitive action with strict policy, approval, and idempotency checks."""
        now_utc = datetime.now(UTC)
        now_iso = now_utc.isoformat()
        norm_action = action_type.strip().upper()
        payload_hash = compute_payload_hash(payload)

        # 1. Idempotency replay check FIRST (return cached response without re-verifying approval)
        if idempotency_key:
            read_conn = get_connection(self.db_path)
            try:
                prior_attempt = repository.find_action_attempt_by_idempotency(
                    read_conn, organization_id, idempotency_key
                )
                if prior_attempt:
                    logger.info("Replaying idempotent action attempt with key %s", idempotency_key)
                    resp_dict = json.loads(prior_attempt.response_json or "{}")
                    resp_dict["idempotent_replay"] = True
                    return resp_dict
            finally:
                read_conn.close()

        # 2. Evaluate policy
        evaluation = self.evaluate_action(norm_action, payload)
        if evaluation.decision == PolicyDecision.BLOCKED:
            self._record_audit_event_direct(
                AuditEventRecord(
                    id=f"aud_{uuid4().hex[:16]}",
                    organization_id=organization_id,
                    actor_type=actor_type,
                    actor_id=actor_id,
                    correlation_id=correlation_id,
                    entity_type="ACTION_ATTEMPT",
                    entity_id=f"attempt_{uuid4().hex[:8]}",
                    event_type="ACTION_ATTEMPT_BLOCKED",
                    payload_hash=payload_hash,
                    details_json=json.dumps({"reason": evaluation.reason, "action": norm_action}),
                    created_at=now_iso,
                )
            )
            raise PolicyBlockedError(evaluation.reason)

        # Pre-check approval requirement outside transaction to safely audit blocks
        if evaluation.decision == PolicyDecision.APPROVAL_REQUIRED and not approval_id:
            self._record_audit_event_direct(
                AuditEventRecord(
                    id=f"aud_{uuid4().hex[:16]}",
                    organization_id=organization_id,
                    actor_type=actor_type,
                    actor_id=actor_id,
                    correlation_id=correlation_id,
                    entity_type="ACTION_ATTEMPT",
                    entity_id=f"attempt_{uuid4().hex[:8]}",
                    event_type="ACTION_ATTEMPT_BLOCKED",
                    payload_hash=payload_hash,
                    details_json=json.dumps(
                        {
                            "reason": "APPROVAL_REQUIRED_BUT_MISSING",
                            "action": norm_action,
                        }
                    ),
                    created_at=now_iso,
                )
            )
            raise ApprovalRequiredError(
                f"Action '{norm_action}' requires an approved authorization token."
            )

        # Pre-check case exists and is not closed
        read_conn = get_connection(self.db_path)
        try:
            case = repository.find_case_by_id(read_conn, case_id, organization_id)
            if not case:
                raise CaseNotFoundError(f"Case '{case_id}' not found")
            if case.status == CaseStatus.VERIFIED_RESOLVED:
                raise PolicyError(
                    f"Cannot execute action on case '{case_id}' "
                    "because it is already VERIFIED_RESOLVED."
                )

            # Check approval pre-conditions
            approval = None
            if evaluation.decision == PolicyDecision.APPROVAL_REQUIRED and approval_id:
                approval = repository.find_approval_by_id(read_conn, approval_id, organization_id)
                if not approval or approval.case_id != case_id:
                    raise ApprovalNotFoundError(
                        f"Approval '{approval_id}' not found for case '{case_id}'"
                    )

                if approval.status != ApprovalStatus.APPROVED:
                    raise ApprovalRequiredError(
                        f"Approval '{approval_id}' is in status '{approval.status}', "
                        "expected 'APPROVED'."
                    )

                if now_utc > datetime.fromisoformat(approval.expires_at):
                    repository.update_approval_status(
                        read_conn,
                        approval_id,
                        ApprovalStatus.EXPIRED,
                        rejection_reason="Expired at execution time",
                    )
                    raise ApprovalExpiredError(
                        f"Approval '{approval_id}' has expired and cannot be used."
                    )

                if payload_hash != approval.payload_hash:
                    repository.insert_audit_event(
                        read_conn,
                        AuditEventRecord(
                            id=f"aud_{uuid4().hex[:16]}",
                            organization_id=organization_id,
                            actor_type=actor_type,
                            actor_id=actor_id,
                            correlation_id=correlation_id,
                            entity_type="ACTION_ATTEMPT",
                            entity_id=f"attempt_{uuid4().hex[:8]}",
                            event_type="ACTION_ATTEMPT_BLOCKED",
                            payload_hash=payload_hash,
                            details_json=json.dumps(
                                {
                                    "reason": "PAYLOAD_HASH_MISMATCH",
                                    "expected_hash": approval.payload_hash,
                                    "computed_hash": payload_hash,
                                }
                            ),
                            created_at=now_iso,
                        ),
                    )
                    raise PayloadHashMismatchError(
                        "Executed payload hash does not match approved payload hash. "
                        "Approval bypass detected."
                    )
        finally:
            read_conn.close()

        # Atomic execution transaction
        with db_session(self.db_path) as s_conn:
            # 2. Idempotency replay check
            if idempotency_key:
                prior_attempt = repository.find_action_attempt_by_idempotency(
                    s_conn, organization_id, idempotency_key
                )
                if prior_attempt:
                    logger.info("Replaying idempotent action attempt with key %s", idempotency_key)
                    resp_dict = json.loads(prior_attempt.response_json or "{}")
                    resp_dict["idempotent_replay"] = True
                    return resp_dict

            # Fetch fresh case state within transaction
            case = repository.find_case_by_id(s_conn, case_id, organization_id)
            if not case:
                raise CaseNotFoundError(f"Case '{case_id}' not found")

            # 3. Execute simulated provider action
            ticket_id = f"TICK-{uuid4().hex[:8].upper()}"
            response_payload = {
                "status": "SUCCEEDED",
                "action_type": norm_action,
                "case_id": case_id,
                "external_ticket_id": ticket_id,
                "idempotency_key": idempotency_key or f"idem_{uuid4().hex[:12]}",
                "idempotent_replay": False,
                "executed_at": now_iso,
            }

            attempt_record = ActionAttemptRecord(
                id=f"att_{uuid4().hex[:16]}",
                organization_id=organization_id,
                case_id=case_id,
                approval_id=approval_id,
                idempotency_key=response_payload["idempotency_key"],
                action_type=norm_action,
                status="SUCCEEDED",
                payload_hash=payload_hash,
                payload_json=json.dumps(payload, sort_keys=True, ensure_ascii=False),
                response_json=json.dumps(response_payload),
                error_message=None,
                executed_at=now_iso,
                created_at=now_iso,
            )
            repository.insert_action_attempt(s_conn, attempt_record)

            if approval_id:
                repository.update_approval_status(s_conn, approval_id, ApprovalStatus.EXECUTED)

            # Update case status if submitting support ticket
            target_status = (
                CaseStatus.MONITORING
                if norm_action
                in (
                    "SUBMIT_MOCK_SUPPORT_CASE",
                    "SUBMIT_SUPPORT_TICKET",
                    "REQUEST_RECREDIT",
                    "ESCALATE_DISPUTE",
                )
                else case.status
            )

            if target_status != case.status:
                updated = repository.update_case_with_version(
                    s_conn,
                    case_id=case_id,
                    new_status=target_status,
                    expected_version=case.version,
                    updated_at=now_iso,
                    decision_summary=f"Submitted mock support ticket {ticket_id}",
                )
                if not updated:
                    raise VersionMismatchError(
                        f"Case '{case_id}' version mismatch during action execution: "
                        f"expected version {case.version}."
                    )

            # Add timeline event
            event = CaseEventRecord(
                id=f"evt_{uuid4().hex[:16]}",
                case_id=case_id,
                organization_id=organization_id,
                actor_type=actor_type,
                actor_id=actor_id,
                from_status=case.status,
                to_status=target_status,
                event_type="ACTION_SUBMITTED",
                summary=f"Support case {ticket_id} submitted and transitioned to {target_status}",
                details_json=json.dumps(response_payload),
                created_at=now_iso,
            )
            repository.insert_case_event(s_conn, event)

            # Audit event
            audit_event = AuditEventRecord(
                id=f"aud_{uuid4().hex[:16]}",
                organization_id=organization_id,
                actor_type=actor_type,
                actor_id=actor_id,
                correlation_id=correlation_id,
                entity_type="ACTION_ATTEMPT",
                entity_id=attempt_record.id,
                event_type="ACTION_ATTEMPT_SUBMITTED",
                payload_hash=payload_hash,
                details_json=json.dumps(
                    {
                        "case_id": case_id,
                        "action": norm_action,
                        "ticket_id": ticket_id,
                        "approval_id": approval_id,
                    }
                ),
                created_at=now_iso,
            )
            repository.insert_audit_event(s_conn, audit_event)

        logger.info(
            "Action %s executed successfully for case %s (ticket: %s)",
            norm_action,
            case_id,
            ticket_id,
        )
        return response_payload
