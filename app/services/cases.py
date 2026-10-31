"""Case management service: state machine, event timeline, and false-closure prevention."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.db.connection import db_session, get_connection
from app.models.domain import (
    ActorType,
    AuditEventRecord,
    CaseEventRecord,
    CasePriority,
    CaseRecord,
    CaseStatus,
    normalize_case_status,
)
from app.services import repository

logger = logging.getLogger(__name__)


class CaseError(Exception):
    """Base exception for case operations."""


class CaseNotFoundError(CaseError):
    """Raised when a requested case is not found."""


class VersionMismatchError(CaseError):
    """Raised when an optimistic concurrency check fails due to stale case version."""


class InvalidStateTransitionError(CaseError):
    """Raised when an invalid state machine transition is attempted."""


class FalseClosureError(CaseError):
    """Raised when attempting to close a case without authoritative verification evidence."""


VALID_TRANSITIONS: dict[str, set[str]] = {
    CaseStatus.DETECTED: {CaseStatus.INVESTIGATING, CaseStatus.ESCALATED},
    CaseStatus.INVESTIGATING: {
        CaseStatus.AWAITING_INFORMATION,
        CaseStatus.AWAITING_APPROVAL,
        CaseStatus.MONITORING,
        CaseStatus.ESCALATED,
    },
    CaseStatus.AWAITING_INFORMATION: {
        CaseStatus.INVESTIGATING,
        CaseStatus.ESCALATED,
    },
    CaseStatus.AWAITING_APPROVAL: {
        CaseStatus.SUBMITTED,
        CaseStatus.INVESTIGATING,
        CaseStatus.ESCALATED,
    },
    CaseStatus.SUBMITTED: {
        CaseStatus.MONITORING,
        CaseStatus.ESCALATED,
    },
    CaseStatus.MONITORING: {
        CaseStatus.VERIFIED_RESOLVED,
        CaseStatus.ESCALATED,
        CaseStatus.INVESTIGATING,
    },
    CaseStatus.VERIFIED_RESOLVED: set(),
    CaseStatus.ESCALATED: {
        CaseStatus.INVESTIGATING,
        CaseStatus.VERIFIED_RESOLVED,
    },
}


def is_authoritative_resolution_evidence(
    conn: sqlite3.Connection,
    case: CaseRecord,
    evidence: dict[str, Any] | None,
) -> bool:
    """Validate whether provided evidence constitutes authoritative proof of resolution.

    Foundational Safety Invariant:
    A case CANNOT transition to VERIFIED_RESOLVED based on model/user claims or unverified strings.
    Evidence must be verified against actual records in SQLite (mock_support_updates, bank_entries,
    or reconciliation_results).
    """
    if not evidence or not isinstance(evidence, dict):
        return False

    # Check 1: Explicit terminal_outcome flag must be strictly True (boolean True or integer 1)
    terminal_outcome = evidence.get("terminal_outcome")
    if terminal_outcome not in (True, 1) or terminal_outcome is False:
        return False

    cur = conn.cursor()
    verified_authoritative_source = False

    # Check 2: Verify against mock_support_updates
    update_id = evidence.get("mock_support_update_id")
    if update_id:
        cur.execute(
            """SELECT terminal_outcome FROM mock_support_updates
               WHERE id = ? AND organization_id = ?""",
            (update_id, case.organization_id),
        )
        row = cur.fetchone()
        if not row or not row[0]:
            return False
        verified_authoritative_source = True

    case_ref = evidence.get("case_reference")
    if case_ref:
        cur.execute(
            """SELECT terminal_outcome FROM mock_support_updates
               WHERE case_reference = ? AND organization_id = ? AND terminal_outcome = 1""",
            (case_ref, case.organization_id),
        )
        if not cur.fetchone():
            return False
        verified_authoritative_source = True

    # Check 3: Verify against bank_entries (Must be CREDIT direction)
    bank_entry_id = evidence.get("bank_statement_entry_id")
    if bank_entry_id:
        cur.execute(
            "SELECT id, direction FROM bank_entries WHERE id = ? AND organization_id = ?",
            (bank_entry_id, case.organization_id),
        )
        row = cur.fetchone()
        if not row or str(row[1]).upper() != "CREDIT":
            return False
        verified_authoritative_source = True

    utr_ref = evidence.get("utr_reference")
    if utr_ref:
        cur.execute(
            """SELECT id FROM bank_entries
               WHERE utr_reference = ? AND organization_id = ? AND direction = 'CREDIT'""",
            (utr_ref, case.organization_id),
        )
        in_bank = cur.fetchone()
        cur.execute(
            """SELECT id FROM mock_support_updates
               WHERE evidence_reference = ? AND organization_id = ? AND terminal_outcome = 1""",
            (utr_ref, case.organization_id),
        )
        in_support = cur.fetchone()
        if not in_bank and not in_support:
            return False
        verified_authoritative_source = True

    # Check 4: Verify against reconciliation_results
    if evidence.get("reconciliation_result_id"):
        cur.execute(
            """SELECT id, status FROM reconciliation_results
               WHERE id = ? AND organization_id = ?""",
            (evidence.get("reconciliation_result_id"), case.organization_id),
        )
        row = cur.fetchone()
        if not row or row[1] not in ("RECONCILED", "VERIFIED_RESOLVED"):
            return False
        verified_authoritative_source = True

    # Check 5: If generic evidence_reference is provided, it must match an authoritative record
    evidence_ref = evidence.get("evidence_reference")
    if evidence_ref:
        cur.execute(
            """SELECT id FROM mock_support_updates
               WHERE evidence_reference = ? AND organization_id = ? AND terminal_outcome = 1""",
            (evidence_ref, case.organization_id),
        )
        in_support = cur.fetchone()
        cur.execute(
            """SELECT id FROM bank_entries
               WHERE utr_reference = ? AND organization_id = ? AND direction = 'CREDIT'""",
            (evidence_ref, case.organization_id),
        )
        in_bank = cur.fetchone()
        if in_support or in_bank:
            verified_authoritative_source = True
        elif not (update_id or case_ref or bank_entry_id or utr_ref):
            return False

    return verified_authoritative_source


class CaseService:
    """Service orchestrating operational case lifecycles, state transitions, and audit records."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path

    def create_case(
        self,
        organization_id: str = "org_aarav",
        reconciliation_result_id: str | None = None,
        case_type: str = "MISSING_SETTLEMENT",
        priority: str = CasePriority.MEDIUM,
        subject_type: str = "TRANSACTION",
        subject_id: str | None = None,
        decision_summary: str | None = None,
        actor_type: str = ActorType.SYSTEM,
        actor_id: str = "reconciliation_service",
        correlation_id: str | None = None,
        initial_details: dict[str, Any] | None = None,
    ) -> CaseRecord:
        """Create a new case in DETECTED status and emit timeline and audit records."""
        now_utc = datetime.now(UTC).isoformat()
        case_id = f"case_{uuid4().hex[:12]}"

        # If created from a reconciliation result, populate context
        conn = get_connection(self.db_path)
        try:
            if reconciliation_result_id:
                rec_res = repository.find_result_by_id(conn, reconciliation_result_id)
                if rec_res:
                    if not subject_id or subject_id == "unknown":
                        subject_type = "RECONCILIATION_RESULT"
                        subject_id = rec_res.id
                    if not decision_summary:
                        decision_summary = f"{rec_res.reason_code}: {rec_res.explanation}"
                    if rec_res.requires_approval or rec_res.status in ("UNMATCHED", "ESCALATED"):
                        priority = CasePriority.HIGH
        finally:
            conn.close()

        resolved_subject_id = subject_id or f"subj_{uuid4().hex[:8]}"

        case = CaseRecord(
            id=case_id,
            organization_id=organization_id,
            reconciliation_result_id=reconciliation_result_id,
            case_type=case_type,
            status=CaseStatus.DETECTED,
            priority=priority,
            subject_type=subject_type,
            subject_id=resolved_subject_id,
            decision_summary=decision_summary,
            version=1,
            created_at=now_utc,
            updated_at=now_utc,
        )

        event = CaseEventRecord(
            id=f"evt_{uuid4().hex[:16]}",
            case_id=case_id,
            organization_id=organization_id,
            actor_type=actor_type,
            actor_id=actor_id,
            from_status=None,
            to_status=CaseStatus.DETECTED,
            event_type="CASE_CREATED",
            summary=f"Case detected: {decision_summary or case_type}",
            details_json=json.dumps(initial_details or {}),
            created_at=now_utc,
        )

        audit_event = AuditEventRecord(
            id=f"aud_{uuid4().hex[:16]}",
            organization_id=organization_id,
            actor_type=actor_type,
            actor_id=actor_id,
            correlation_id=correlation_id,
            entity_type="CASE",
            entity_id=case_id,
            event_type="CASE_CREATED",
            details_json=json.dumps(
                {
                    "case_type": case_type,
                    "priority": priority,
                    "reconciliation_result_id": reconciliation_result_id,
                }
            ),
            created_at=now_utc,
        )

        with db_session(self.db_path) as s_conn:
            repository.insert_case(s_conn, case)
            repository.insert_case_event(s_conn, event)
            repository.insert_audit_event(s_conn, audit_event)

        logger.info("Case %s created in status DETECTED for org %s", case_id, organization_id)
        return case

    def get_case(self, case_id: str, organization_id: str = "org_aarav") -> CaseRecord:
        """Fetch a case by ID and organization scope."""
        conn = get_connection(self.db_path)
        try:
            case = repository.find_case_by_id(conn, case_id, organization_id)
            if not case:
                raise CaseNotFoundError(
                    f"Case '{case_id}' not found for organization '{organization_id}'"
                )
            return case
        finally:
            conn.close()

    def list_cases(
        self,
        organization_id: str = "org_aarav",
        status: str | None = None,
        priority: str | None = None,
        case_type: str | None = None,
        subject_type: str | None = None,
        subject_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CaseRecord]:
        """List cases matching search and status criteria."""
        conn = get_connection(self.db_path)
        try:
            norm_status = normalize_case_status(status) if status else None
            return repository.list_cases(
                conn,
                organization_id=organization_id,
                status=norm_status,
                priority=priority,
                case_type=case_type,
                subject_type=subject_type,
                subject_id=subject_id,
                limit=limit,
                offset=offset,
            )
        finally:
            conn.close()

    def transition_case(
        self,
        case_id: str,
        to_status: str,
        expected_version: int,
        actor_type: str = ActorType.USER,
        actor_id: str = "operator_1",
        summary: str = "",
        details: dict[str, Any] | None = None,
        evidence: dict[str, Any] | None = None,
        decision_summary: str | None = None,
        priority: str | None = None,
        correlation_id: str | None = None,
        organization_id: str = "org_aarav",
    ) -> CaseRecord:
        """Execute a state transition with optimistic concurrency and false-closure verification."""
        norm_to_status = normalize_case_status(to_status)
        now_utc = datetime.now(UTC).isoformat()

        with db_session(self.db_path) as s_conn:
            case = repository.find_case_by_id(s_conn, case_id, organization_id)
            if not case:
                raise CaseNotFoundError(
                    f"Case '{case_id}' not found for organization '{organization_id}'"
                )

            # 1. Check state machine validity
            allowed = VALID_TRANSITIONS.get(case.status, set())
            if norm_to_status not in allowed:
                raise InvalidStateTransitionError(
                    f"Invalid state transition: Cannot transition case '{case_id}' "
                    f"from '{case.status}' to '{norm_to_status}'."
                )

            # 2. Check false-closure prevention invariant
            if norm_to_status == CaseStatus.VERIFIED_RESOLVED:
                if not is_authoritative_resolution_evidence(s_conn, case, evidence):
                    raise FalseClosureError(
                        f"False-closure rejected for case '{case_id}': Cannot transition "
                        "to VERIFIED_RESOLVED without authoritative terminal verification evidence."
                    )

            # 3. Optimistic concurrency check and atomic update
            updated = repository.update_case_with_version(
                s_conn,
                case_id=case_id,
                new_status=norm_to_status,
                expected_version=expected_version,
                updated_at=now_utc,
                decision_summary=decision_summary,
                priority=priority,
            )
            if not updated:
                current_case = repository.find_case_by_id(s_conn, case_id, organization_id)
                current_version = current_case.version if current_case else "unknown"
                raise VersionMismatchError(
                    f"Case '{case_id}' version mismatch: expected version {expected_version}, "
                    f"but current version is {current_version}."
                )

            # 4. Record event timeline entry
            event_id = f"evt_{uuid4().hex[:16]}"
            event_type = "STATUS_CHANGED"
            if norm_to_status == CaseStatus.VERIFIED_RESOLVED:
                event_type = "RESOLUTION_VERIFIED"
            elif norm_to_status == CaseStatus.ESCALATED:
                event_type = "CASE_ESCALATED"
            elif norm_to_status == CaseStatus.AWAITING_APPROVAL:
                event_type = "APPROVAL_REQUESTED"
            elif norm_to_status == CaseStatus.SUBMITTED:
                event_type = "ACTION_SUBMITTED"

            merged_details = dict(details or {})
            if evidence:
                merged_details["verification_evidence"] = evidence

            event = CaseEventRecord(
                id=event_id,
                case_id=case_id,
                organization_id=organization_id,
                actor_type=actor_type,
                actor_id=actor_id,
                from_status=case.status,
                to_status=norm_to_status,
                event_type=event_type,
                summary=summary or f"Status transitioned from {case.status} to {norm_to_status}",
                details_json=json.dumps(merged_details),
                created_at=now_utc,
            )
            repository.insert_case_event(s_conn, event)

            # 5. Record append-only audit event
            audit_event = AuditEventRecord(
                id=f"aud_{uuid4().hex[:16]}",
                organization_id=organization_id,
                actor_type=actor_type,
                actor_id=actor_id,
                correlation_id=correlation_id,
                entity_type="CASE",
                entity_id=case_id,
                event_type="CASE_TRANSITION",
                details_json=json.dumps(
                    {
                        "from_status": case.status,
                        "to_status": norm_to_status,
                        "expected_version": expected_version,
                        "new_version": case.version + 1,
                    }
                ),
                created_at=now_utc,
            )
            repository.insert_audit_event(s_conn, audit_event)

            # Fetch fresh state
            updated_case = repository.find_case_by_id(s_conn, case_id, organization_id)
            assert updated_case is not None
            return updated_case

    def get_timeline(
        self, case_id: str, organization_id: str = "org_aarav"
    ) -> list[CaseEventRecord]:
        """Retrieve chronological event history for a case."""
        conn = get_connection(self.db_path)
        try:
            # Verify case exists
            self.get_case(case_id, organization_id)
            return repository.list_case_events(conn, case_id, organization_id)
        finally:
            conn.close()

    def add_timeline_event(
        self,
        case_id: str,
        event_type: str,
        summary: str,
        actor_type: str = ActorType.USER,
        actor_id: str = "operator_1",
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        organization_id: str = "org_aarav",
    ) -> CaseEventRecord:
        """Add an informational event or note to the case timeline without status change."""
        now_utc = datetime.now(UTC).isoformat()
        with db_session(self.db_path) as s_conn:
            case = repository.find_case_by_id(s_conn, case_id, organization_id)
            if not case:
                raise CaseNotFoundError(
                    f"Case '{case_id}' not found for organization '{organization_id}'"
                )

            event = CaseEventRecord(
                id=f"evt_{uuid4().hex[:16]}",
                case_id=case_id,
                organization_id=organization_id,
                actor_type=actor_type,
                actor_id=actor_id,
                from_status=case.status,
                to_status=case.status,
                event_type=event_type,
                summary=summary,
                details_json=json.dumps(details or {}),
                created_at=now_utc,
            )
            repository.insert_case_event(s_conn, event)

            audit_event = AuditEventRecord(
                id=f"aud_{uuid4().hex[:16]}",
                organization_id=organization_id,
                actor_type=actor_type,
                actor_id=actor_id,
                correlation_id=correlation_id,
                entity_type="CASE",
                entity_id=case_id,
                event_type=f"CASE_EVENT_{event_type}",
                details_json=json.dumps(details or {}),
                created_at=now_utc,
            )
            repository.insert_audit_event(s_conn, audit_event)

            return event

    def update_case(
        self,
        case_id: str,
        expected_version: int,
        priority: str | None = None,
        decision_summary: str | None = None,
        actor_type: str = ActorType.USER,
        actor_id: str = "operator_1",
        summary: str = "",
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
        organization_id: str = "org_aarav",
    ) -> CaseRecord:
        """Update case priority or decision summary with optimistic concurrency locking."""
        now_utc = datetime.now(UTC).isoformat()
        with db_session(self.db_path) as s_conn:
            case = repository.find_case_by_id(s_conn, case_id, organization_id)
            if not case:
                raise CaseNotFoundError(
                    f"Case '{case_id}' not found for organization '{organization_id}'"
                )

            updated = repository.update_case_with_version(
                s_conn,
                case_id=case_id,
                new_status=case.status,
                expected_version=expected_version,
                updated_at=now_utc,
                decision_summary=decision_summary,
                priority=priority,
            )
            if not updated:
                current_case = repository.find_case_by_id(s_conn, case_id, organization_id)
                current_version = current_case.version if current_case else "unknown"
                raise VersionMismatchError(
                    f"Case '{case_id}' version mismatch: expected version {expected_version}, "
                    f"but current version is {current_version}."
                )

            # Record timeline event
            event = CaseEventRecord(
                id=f"evt_{uuid4().hex[:16]}",
                case_id=case_id,
                organization_id=organization_id,
                actor_type=actor_type,
                actor_id=actor_id,
                from_status=case.status,
                to_status=case.status,
                event_type="CASE_UPDATED",
                summary=summary or f"Case updated (version {case.version} -> {case.version + 1})",
                details_json=json.dumps(
                    {
                        "priority": priority or case.priority,
                        "decision_summary": decision_summary or case.decision_summary,
                        **(details or {}),
                    }
                ),
                created_at=now_utc,
            )
            repository.insert_case_event(s_conn, event)

            # Record audit event
            audit_event = AuditEventRecord(
                id=f"aud_{uuid4().hex[:16]}",
                organization_id=organization_id,
                actor_type=actor_type,
                actor_id=actor_id,
                correlation_id=correlation_id,
                entity_type="CASE",
                entity_id=case_id,
                event_type="CASE_UPDATED",
                details_json=json.dumps(
                    {
                        "expected_version": expected_version,
                        "new_version": case.version + 1,
                        "priority": priority,
                        "decision_summary": decision_summary,
                    }
                ),
                created_at=now_utc,
            )
            repository.insert_audit_event(s_conn, audit_event)

            updated_case = repository.find_case_by_id(s_conn, case_id, organization_id)
            assert updated_case is not None
            return updated_case
