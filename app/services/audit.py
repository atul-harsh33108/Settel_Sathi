"""Append-only audit trail service capturing actors, state transitions, and action attempts."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.db.connection import db_session, get_connection
from app.models.domain import AuditEventRecord
from app.services import repository


class AuditService:
    """Service providing append-only audit trail operations."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path

    def record_event(
        self,
        organization_id: str,
        entity_type: str,
        entity_id: str,
        event_type: str,
        actor_type: str = "system",
        actor_id: str = "system",
        correlation_id: str | None = None,
        payload_hash: str | None = None,
        details: dict[str, Any] | None = None,
        conn: sqlite3.Connection | None = None,
    ) -> AuditEventRecord:
        """Record an immutable append-only audit event."""
        now_utc = datetime.now(UTC).isoformat()
        event_id = f"aud_{uuid4().hex[:16]}"
        details_json = json.dumps(details) if details is not None else None

        record = AuditEventRecord(
            id=event_id,
            organization_id=organization_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            correlation_id=correlation_id,
            payload_hash=payload_hash,
            details_json=details_json,
            created_at=now_utc,
        )

        if conn is not None:
            repository.insert_audit_event(conn, record)
        else:
            with db_session(self.db_path) as s_conn:
                repository.insert_audit_event(s_conn, record)

        return record

    def list_events(
        self,
        organization_id: str = "org_aarav",
        entity_type: str | None = None,
        entity_id: str | None = None,
        event_type: str | None = None,
        correlation_id: str | None = None,
        actor_type: str | None = None,
        actor_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEventRecord]:
        """Query immutable audit events with scoping and filtering."""
        conn = get_connection(self.db_path)
        try:
            return repository.list_audit_events(
                conn,
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
        finally:
            conn.close()
