"""Repository access layer for domain entities, artifacts, and import records."""

from __future__ import annotations

import sqlite3
from decimal import Decimal
from typing import Any

from app.models.domain import (
    ActionAttemptRecord,
    ApprovalRecord,
    AuditEventRecord,
    BankEntryRecord,
    CaseEventRecord,
    CaseRecord,
    ImportJobRecord,
    MockSupportUpdateRecord,
    ReconciliationResultRecord,
    ReconciliationRunRecord,
    SettlementBatchRecord,
    SettlementLineItemRecord,
    SourceArtifactRecord,
    TransactionRecord,
    format_money,
)


def row_to_case(row: sqlite3.Row) -> CaseRecord:
    return CaseRecord(
        id=row["id"],
        organization_id=row["organization_id"],
        reconciliation_result_id=row["reconciliation_result_id"],
        case_type=row["case_type"],
        status=row["status"],
        priority=row["priority"],
        subject_type=row["subject_type"],
        subject_id=row["subject_id"],
        decision_summary=row["decision_summary"],
        version=int(row["version"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def row_to_case_event(row: sqlite3.Row) -> CaseEventRecord:
    return CaseEventRecord(
        id=row["id"],
        case_id=row["case_id"],
        organization_id=row["organization_id"],
        actor_type=row["actor_type"],
        actor_id=row["actor_id"],
        from_status=row["from_status"],
        to_status=row["to_status"],
        event_type=row["event_type"],
        summary=row["summary"],
        details_json=row["details_json"],
        created_at=row["created_at"],
    )


def row_to_approval(row: sqlite3.Row) -> ApprovalRecord:
    return ApprovalRecord(
        id=row["id"],
        case_id=row["case_id"],
        organization_id=row["organization_id"],
        action_type=row["action_type"],
        action_class=row["action_class"],
        payload_hash=row["payload_hash"],
        payload_json=row["payload_json"],
        status=row["status"],
        requested_by_type=row["requested_by_type"],
        requested_by_id=row["requested_by_id"],
        approved_by=row["approved_by"],
        approved_at=row["approved_at"],
        expires_at=row["expires_at"],
        rejection_reason=row["rejection_reason"],
        created_at=row["created_at"],
    )


def row_to_action_attempt(row: sqlite3.Row) -> ActionAttemptRecord:
    return ActionAttemptRecord(
        id=row["id"],
        organization_id=row["organization_id"],
        case_id=row["case_id"],
        approval_id=row["approval_id"],
        idempotency_key=row["idempotency_key"],
        action_type=row["action_type"],
        status=row["status"],
        payload_hash=row["payload_hash"],
        payload_json=row["payload_json"],
        response_json=row["response_json"],
        error_message=row["error_message"],
        executed_at=row["executed_at"],
        created_at=row["created_at"],
    )


def row_to_audit_event(row: sqlite3.Row) -> AuditEventRecord:
    cols = row.keys()
    return AuditEventRecord(
        id=row["id"],
        organization_id=row["organization_id"],
        actor_type=row["actor_type"] if "actor_type" in cols else "system",
        actor_id=row["actor_id"] if "actor_id" in cols else "system",
        correlation_id=row["correlation_id"] if "correlation_id" in cols else None,
        entity_type=row["entity_type"],
        entity_id=row["entity_id"],
        event_type=row["event_type"],
        payload_hash=row["payload_hash"] if "payload_hash" in cols else None,
        details_json=row["details_json"],
        created_at=row["created_at"],
    )


def row_to_artifact(row: sqlite3.Row) -> SourceArtifactRecord:
    return SourceArtifactRecord(
        id=row["id"],
        organization_id=row["organization_id"],
        source_type=row["source_type"],
        file_name=row["file_name"],
        schema_version=row["schema_version"],
        dataset_version=row["dataset_version"],
        sha256=row["sha256"],
        size_bytes=row["size_bytes"],
        storage_path=row["storage_path"],
        record_count=row["record_count"],
        ingested_at=row["ingested_at"],
    )


def row_to_job(row: sqlite3.Row) -> ImportJobRecord:
    return ImportJobRecord(
        id=row["id"],
        organization_id=row["organization_id"],
        artifact_id=row["artifact_id"],
        source_type=row["source_type"],
        status=row["status"],
        total_records=row["total_records"],
        processed_records=row["processed_records"],
        error_count=row["error_count"],
        errors_json=row["errors_json"],
        idempotent_replay=bool(row["idempotent_replay"]),
        started_at=row["started_at"],
        completed_at=row["completed_at"],
    )


def find_artifact_by_digest(
    conn: sqlite3.Connection,
    organization_id: str,
    source_type: str,
    schema_version: str,
    sha256: str,
) -> SourceArtifactRecord | None:
    cur = conn.cursor()
    cur.execute(
        """SELECT * FROM source_artifacts
           WHERE organization_id = ? AND source_type = ? AND schema_version = ? AND sha256 = ?""",
        (organization_id, source_type, schema_version, sha256),
    )
    row = cur.fetchone()
    return row_to_artifact(row) if row else None


def find_completed_job_by_artifact(
    conn: sqlite3.Connection, organization_id: str, artifact_id: str
) -> ImportJobRecord | None:
    cur = conn.cursor()
    cur.execute(
        """SELECT * FROM import_jobs
           WHERE organization_id = ? AND artifact_id = ? AND status = 'COMPLETED'
           ORDER BY started_at DESC LIMIT 1""",
        (organization_id, artifact_id),
    )
    row = cur.fetchone()
    return row_to_job(row) if row else None


def find_job_by_id(conn: sqlite3.Connection, job_id: str) -> ImportJobRecord | None:
    cur = conn.cursor()
    cur.execute("SELECT * FROM import_jobs WHERE id = ?", (job_id,))
    row = cur.fetchone()
    return row_to_job(row) if row else None


def insert_source_artifact(conn: sqlite3.Connection, artifact: SourceArtifactRecord) -> None:
    conn.execute(
        """INSERT INTO source_artifacts (
            id, organization_id, source_type, file_name, schema_version,
            dataset_version, sha256, size_bytes, storage_path, record_count, ingested_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            artifact.id,
            artifact.organization_id,
            artifact.source_type,
            artifact.file_name,
            artifact.schema_version,
            artifact.dataset_version,
            artifact.sha256,
            artifact.size_bytes,
            artifact.storage_path,
            artifact.record_count,
            artifact.ingested_at,
        ),
    )


def insert_import_job(conn: sqlite3.Connection, job: ImportJobRecord) -> None:
    conn.execute(
        """INSERT INTO import_jobs (
            id, organization_id, artifact_id, source_type, status,
            total_records, processed_records, error_count, errors_json,
            idempotent_replay, started_at, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            job.id,
            job.organization_id,
            job.artifact_id,
            job.source_type,
            job.status,
            job.total_records,
            job.processed_records,
            job.error_count,
            job.errors_json,
            1 if job.idempotent_replay else 0,
            job.started_at,
            job.completed_at,
        ),
    )


def update_import_job(conn: sqlite3.Connection, job: ImportJobRecord) -> None:
    conn.execute(
        """UPDATE import_jobs SET
            artifact_id = ?,
            status = ?,
            total_records = ?,
            processed_records = ?,
            error_count = ?,
            errors_json = ?,
            idempotent_replay = ?,
            completed_at = ?
           WHERE id = ?""",
        (
            job.artifact_id,
            job.status,
            job.total_records,
            job.processed_records,
            job.error_count,
            job.errors_json,
            1 if job.idempotent_replay else 0,
            job.completed_at,
            job.id,
        ),
    )


def check_conflicting_transactions(
    conn: sqlite3.Connection, organization_id: str, provider: str, txn_ids: list[str]
) -> list[str]:
    if not txn_ids:
        return []
    cur = conn.cursor()
    placeholders = ",".join("?" for _ in txn_ids)
    sql = (
        "SELECT provider_transaction_id FROM transactions "
        "WHERE organization_id = ? AND provider = ? "
        f"AND provider_transaction_id IN ({placeholders})"
    )
    cur.execute(sql, [organization_id, provider, *txn_ids])
    return [row[0] for row in cur.fetchall()]


def check_conflicting_settlements(
    conn: sqlite3.Connection, organization_id: str, provider: str, settle_ids: list[str]
) -> list[str]:
    if not settle_ids:
        return []
    cur = conn.cursor()
    placeholders = ",".join("?" for _ in settle_ids)
    sql = (
        "SELECT provider_settlement_id FROM settlement_batches "
        "WHERE organization_id = ? AND provider = ? "
        f"AND provider_settlement_id IN ({placeholders})"
    )
    cur.execute(sql, [organization_id, provider, *settle_ids])
    return [row[0] for row in cur.fetchall()]


def check_conflicting_line_items(
    conn: sqlite3.Connection, organization_id: str, line_item_ids: list[str]
) -> list[str]:
    if not line_item_ids:
        return []
    cur = conn.cursor()
    placeholders = ",".join("?" for _ in line_item_ids)
    cur.execute(
        f"""SELECT line_item_id FROM settlement_line_items
           WHERE organization_id = ? AND line_item_id IN ({placeholders})""",
        [organization_id, *line_item_ids],
    )
    return [row[0] for row in cur.fetchall()]


def check_conflicting_bank_entries(
    conn: sqlite3.Connection, organization_id: str, entry_ids: list[str]
) -> list[str]:
    if not entry_ids:
        return []
    cur = conn.cursor()
    placeholders = ",".join("?" for _ in entry_ids)
    cur.execute(
        f"""SELECT statement_entry_id FROM bank_entries
           WHERE organization_id = ? AND statement_entry_id IN ({placeholders})""",
        [organization_id, *entry_ids],
    )
    return [row[0] for row in cur.fetchall()]


def check_conflicting_support_updates(
    conn: sqlite3.Connection, organization_id: str, updates: list[MockSupportUpdateRecord]
) -> list[MockSupportUpdateRecord]:
    if not updates:
        return []
    cur = conn.cursor()
    conflicts: list[MockSupportUpdateRecord] = []
    for u in updates:
        cur.execute(
            """SELECT 1 FROM mock_support_updates
               WHERE organization_id = ? AND case_reference = ? AND event_at = ?""",
            (organization_id, u.case_reference, u.event_at),
        )
        if cur.fetchone():
            conflicts.append(u)
    return conflicts


def check_stores_exist(
    conn: sqlite3.Connection, organization_id: str, store_ids: set[str]
) -> set[str]:
    if not store_ids:
        return set()
    cur = conn.cursor()
    placeholders = ",".join("?" for _ in store_ids)
    cur.execute(
        f"""SELECT id FROM stores
           WHERE organization_id = ? AND id IN ({placeholders})""",
        [organization_id, *store_ids],
    )
    return {row[0] for row in cur.fetchall()}


def check_bank_accounts_exist(
    conn: sqlite3.Connection, organization_id: str, account_aliases: set[str]
) -> set[str]:
    if not account_aliases:
        return set()
    cur = conn.cursor()
    placeholders = ",".join("?" for _ in account_aliases)
    cur.execute(
        f"""SELECT account_alias FROM bank_accounts
           WHERE organization_id = ? AND account_alias IN ({placeholders})""",
        [organization_id, *account_aliases],
    )
    return {row[0] for row in cur.fetchall()}


def check_settlements_exist(
    conn: sqlite3.Connection, organization_id: str, settle_ids: set[str]
) -> set[str]:
    if not settle_ids:
        return set()
    cur = conn.cursor()
    placeholders = ",".join("?" for _ in settle_ids)
    cur.execute(
        f"""SELECT provider_settlement_id FROM settlement_batches
           WHERE organization_id = ? AND provider_settlement_id IN ({placeholders})""",
        [organization_id, *settle_ids],
    )
    return {row[0] for row in cur.fetchall()}


def insert_transactions(conn: sqlite3.Connection, txns: list[TransactionRecord]) -> None:
    conn.executemany(
        """INSERT INTO transactions (
            id, organization_id, store_id, provider, provider_transaction_id,
            merchant_reference, occurred_at, status, payment_method, gross_amount,
            currency, source_artifact_id, source_row_number, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                t.id,
                t.organization_id,
                t.store_id,
                t.provider,
                t.provider_transaction_id,
                t.merchant_reference,
                t.occurred_at,
                t.status,
                t.payment_method,
                format_money(t.gross_amount),
                t.currency,
                t.source_artifact_id,
                t.source_row_number,
                t.created_at,
            )
            for t in txns
        ],
    )


def insert_settlements(conn: sqlite3.Connection, settlements: list[SettlementBatchRecord]) -> None:
    conn.executemany(
        """INSERT INTO settlement_batches (
            id, organization_id, provider, provider_settlement_id, payout_reference,
            settlement_date, reported_status, gross_amount, fee_amount, tax_amount,
            adjustment_amount, net_amount, currency, source_artifact_id,
            source_row_number, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                s.id,
                s.organization_id,
                s.provider,
                s.provider_settlement_id,
                s.payout_reference,
                s.settlement_date,
                s.reported_status,
                format_money(s.gross_amount),
                format_money(s.fee_amount),
                format_money(s.tax_amount),
                format_money(s.adjustment_amount),
                format_money(s.net_amount),
                s.currency,
                s.source_artifact_id,
                s.source_row_number,
                s.created_at,
            )
            for s in settlements
        ],
    )


def insert_settlement_line_items(
    conn: sqlite3.Connection, items: list[SettlementLineItemRecord]
) -> None:
    conn.executemany(
        """INSERT INTO settlement_line_items (
            id, organization_id, provider_settlement_id, line_item_id,
            source_reference, line_type, amount, currency,
            source_artifact_id, source_row_number, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                item.id,
                item.organization_id,
                item.provider_settlement_id,
                item.line_item_id,
                item.source_reference,
                item.line_type,
                format_money(item.amount),
                item.currency,
                item.source_artifact_id,
                item.source_row_number,
                item.created_at,
            )
            for item in items
        ],
    )


def insert_bank_entries(conn: sqlite3.Connection, entries: list[BankEntryRecord]) -> None:
    conn.executemany(
        """INSERT INTO bank_entries (
            id, organization_id, statement_entry_id, bank_account_alias,
            booking_date, direction, amount, currency, narration, utr_reference,
            source_artifact_id, source_row_number, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                b.id,
                b.organization_id,
                b.statement_entry_id,
                b.bank_account_alias,
                b.booking_date,
                b.direction,
                format_money(b.amount),
                b.currency,
                b.narration,
                b.utr_reference,
                b.source_artifact_id,
                b.source_row_number,
                b.created_at,
            )
            for b in entries
        ],
    )


def insert_mock_support_updates(
    conn: sqlite3.Connection, updates: list[MockSupportUpdateRecord]
) -> None:
    conn.executemany(
        """INSERT INTO mock_support_updates (
            id, organization_id, case_reference, event_at, status,
            summary, terminal_outcome, evidence_reference, source_artifact_id,
            source_row_number, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                u.id,
                u.organization_id,
                u.case_reference,
                u.event_at,
                u.status,
                u.summary,
                1 if u.terminal_outcome else 0,
                u.evidence_reference,
                u.source_artifact_id,
                u.source_row_number,
                u.created_at,
            )
            for u in updates
        ],
    )


def insert_audit_event(conn: sqlite3.Connection, event: AuditEventRecord) -> None:
    conn.execute(
        """INSERT INTO audit_events (
            id, organization_id, actor_type, actor_id, correlation_id,
            entity_type, entity_id, event_type, payload_hash, details_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            event.id,
            event.organization_id,
            getattr(event, "actor_type", "system"),
            getattr(event, "actor_id", "system"),
            getattr(event, "correlation_id", None),
            event.entity_type,
            event.entity_id,
            event.event_type,
            getattr(event, "payload_hash", None),
            event.details_json,
            event.created_at,
        ),
    )


def list_audit_events(
    conn: sqlite3.Connection,
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
    cur = conn.cursor()
    query = "SELECT * FROM audit_events WHERE organization_id = ?"
    params: list[Any] = [organization_id]

    if entity_type:
        query += " AND entity_type = ?"
        params.append(entity_type)
    if entity_id:
        query += " AND entity_id = ?"
        params.append(entity_id)
    if event_type:
        query += " AND event_type = ?"
        params.append(event_type)
    if correlation_id:
        query += " AND correlation_id = ?"
        params.append(correlation_id)
    if actor_type:
        query += " AND actor_type = ?"
        params.append(actor_type)
    if actor_id:
        query += " AND actor_id = ?"
        params.append(actor_id)

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    cur.execute(query, params)
    return [row_to_audit_event(r) for r in cur.fetchall()]


def get_financial_counts(
    conn: sqlite3.Connection, organization_id: str = "org_aarav"
) -> dict[str, int]:
    cur = conn.cursor()
    counts = {}
    tables = [
        ("transactions", "transactions"),
        ("settlements", "settlement_batches"),
        ("settlement_line_items", "settlement_line_items"),
        ("bank_entries", "bank_entries"),
        ("mock_support_updates", "mock_support_updates"),
        ("source_artifacts", "source_artifacts"),
        ("import_jobs", "import_jobs"),
    ]
    for key, table in tables:
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE organization_id = ?", (organization_id,))
        counts[key] = cur.fetchone()[0]
    return counts


def list_import_jobs(
    conn: sqlite3.Connection, organization_id: str = "org_aarav", limit: int = 50
) -> list[ImportJobRecord]:
    cur = conn.cursor()
    cur.execute(
        """SELECT * FROM import_jobs
           WHERE organization_id = ?
           ORDER BY started_at DESC LIMIT ?""",
        (organization_id, limit),
    )
    return [row_to_job(r) for r in cur.fetchall()]


def list_source_artifacts(
    conn: sqlite3.Connection, organization_id: str = "org_aarav", limit: int = 50
) -> list[SourceArtifactRecord]:
    cur = conn.cursor()
    cur.execute(
        """SELECT * FROM source_artifacts
           WHERE organization_id = ?
           ORDER BY ingested_at DESC LIMIT ?""",
        (organization_id, limit),
    )
    return [row_to_artifact(r) for r in cur.fetchall()]


def row_to_transaction(row: sqlite3.Row) -> TransactionRecord:
    return TransactionRecord(
        id=row["id"],
        organization_id=row["organization_id"],
        store_id=row["store_id"],
        provider=row["provider"],
        provider_transaction_id=row["provider_transaction_id"],
        merchant_reference=row["merchant_reference"],
        occurred_at=row["occurred_at"],
        status=row["status"],
        payment_method=row["payment_method"],
        gross_amount=Decimal(row["gross_amount"]),
        currency=row["currency"],
        source_artifact_id=row["source_artifact_id"],
        source_row_number=row["source_row_number"],
        created_at=row["created_at"],
    )


def row_to_settlement(row: sqlite3.Row) -> SettlementBatchRecord:
    return SettlementBatchRecord(
        id=row["id"],
        organization_id=row["organization_id"],
        provider=row["provider"],
        provider_settlement_id=row["provider_settlement_id"],
        payout_reference=row["payout_reference"],
        settlement_date=row["settlement_date"],
        reported_status=row["reported_status"],
        gross_amount=Decimal(row["gross_amount"]),
        fee_amount=Decimal(row["fee_amount"]),
        tax_amount=Decimal(row["tax_amount"]),
        adjustment_amount=Decimal(row["adjustment_amount"]),
        net_amount=Decimal(row["net_amount"]),
        currency=row["currency"],
        source_artifact_id=row["source_artifact_id"],
        source_row_number=row["source_row_number"],
        created_at=row["created_at"],
    )


def row_to_line_item(row: sqlite3.Row) -> SettlementLineItemRecord:
    return SettlementLineItemRecord(
        id=row["id"],
        organization_id=row["organization_id"],
        provider_settlement_id=row["provider_settlement_id"],
        line_item_id=row["line_item_id"],
        source_reference=row["source_reference"],
        line_type=row["line_type"],
        amount=Decimal(row["amount"]),
        currency=row["currency"],
        source_artifact_id=row["source_artifact_id"],
        source_row_number=row["source_row_number"],
        created_at=row["created_at"],
    )


def row_to_bank_entry(row: sqlite3.Row) -> BankEntryRecord:
    return BankEntryRecord(
        id=row["id"],
        organization_id=row["organization_id"],
        statement_entry_id=row["statement_entry_id"],
        bank_account_alias=row["bank_account_alias"],
        booking_date=row["booking_date"],
        direction=row["direction"],
        amount=Decimal(row["amount"]),
        currency=row["currency"],
        narration=row["narration"],
        utr_reference=row["utr_reference"],
        source_artifact_id=row["source_artifact_id"],
        source_row_number=row["source_row_number"],
        created_at=row["created_at"],
    )


def row_to_support_update(row: sqlite3.Row) -> MockSupportUpdateRecord:
    return MockSupportUpdateRecord(
        id=row["id"],
        organization_id=row["organization_id"],
        case_reference=row["case_reference"],
        event_at=row["event_at"],
        status=row["status"],
        summary=row["summary"],
        terminal_outcome=bool(row["terminal_outcome"]),
        evidence_reference=row["evidence_reference"],
        source_artifact_id=row["source_artifact_id"],
        source_row_number=row["source_row_number"],
        created_at=row["created_at"],
    )


def row_to_run(row: sqlite3.Row) -> ReconciliationRunRecord:
    return ReconciliationRunRecord(
        id=row["id"],
        organization_id=row["organization_id"],
        rule_version=row["rule_version"],
        status=row["status"],
        as_of_date=row["as_of_date"],
        summary_counts_json=row["summary_counts_json"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
    )


def row_to_result(row: sqlite3.Row) -> ReconciliationResultRecord:
    return ReconciliationResultRecord(
        id=row["id"],
        run_id=row["run_id"],
        organization_id=row["organization_id"],
        scenario_id=row["scenario_id"],
        status=row["status"],
        reason_code=row["reason_code"],
        rule_version=row["rule_version"],
        collected_amount=Decimal(row["collected_amount"]),
        settled_amount=Decimal(row["settled_amount"]),
        bank_credited_amount=Decimal(row["bank_credited_amount"]),
        discrepancy_amount=Decimal(row["discrepancy_amount"]),
        currency=row["currency"],
        input_record_ids_json=row["input_record_ids_json"],
        matched_record_ids_json=row["matched_record_ids_json"],
        evidence_json=row["evidence_json"],
        explanation=row["explanation"],
        case_needed=bool(row["case_needed"]),
        requires_approval=bool(row["requires_approval"]),
        evaluated_at=row["evaluated_at"],
    )


def insert_reconciliation_run(conn: sqlite3.Connection, run: ReconciliationRunRecord) -> None:
    conn.execute(
        """INSERT INTO reconciliation_runs (
            id, organization_id, rule_version, status, as_of_date,
            summary_counts_json, started_at, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            run.id,
            run.organization_id,
            run.rule_version,
            run.status,
            run.as_of_date,
            run.summary_counts_json,
            run.started_at,
            run.completed_at,
        ),
    )


def update_reconciliation_run(conn: sqlite3.Connection, run: ReconciliationRunRecord) -> None:
    conn.execute(
        """UPDATE reconciliation_runs SET
            status = ?,
            summary_counts_json = ?,
            completed_at = ?
           WHERE id = ?""",
        (
            run.status,
            run.summary_counts_json,
            run.completed_at,
            run.id,
        ),
    )


def insert_reconciliation_results(
    conn: sqlite3.Connection, results: list[ReconciliationResultRecord]
) -> None:
    conn.executemany(
        """INSERT INTO reconciliation_results (
            id, run_id, organization_id, scenario_id, status, reason_code,
            rule_version, collected_amount, settled_amount, bank_credited_amount,
            discrepancy_amount, currency, input_record_ids_json, matched_record_ids_json,
            evidence_json, explanation, case_needed, requires_approval, evaluated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                r.id,
                r.run_id,
                r.organization_id,
                r.scenario_id,
                r.status,
                r.reason_code,
                r.rule_version,
                format_money(r.collected_amount),
                format_money(r.settled_amount),
                format_money(r.bank_credited_amount),
                format_money(r.discrepancy_amount),
                r.currency,
                r.input_record_ids_json,
                r.matched_record_ids_json,
                r.evidence_json,
                r.explanation,
                1 if r.case_needed else 0,
                1 if r.requires_approval else 0,
                r.evaluated_at,
            )
            for r in results
        ],
    )


def find_run_by_id(
    conn: sqlite3.Connection, run_id: str, organization_id: str = "org_aarav"
) -> ReconciliationRunRecord | None:
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM reconciliation_runs WHERE id = ? AND organization_id = ?",
        (run_id, organization_id),
    )
    row = cur.fetchone()
    return row_to_run(row) if row else None


def find_latest_run(
    conn: sqlite3.Connection, organization_id: str = "org_aarav"
) -> ReconciliationRunRecord | None:
    cur = conn.cursor()
    cur.execute(
        """SELECT * FROM reconciliation_runs
           WHERE organization_id = ?
           ORDER BY started_at DESC LIMIT 1""",
        (organization_id,),
    )
    row = cur.fetchone()
    return row_to_run(row) if row else None


def list_reconciliation_runs(
    conn: sqlite3.Connection, organization_id: str = "org_aarav", limit: int = 50
) -> list[ReconciliationRunRecord]:
    cur = conn.cursor()
    cur.execute(
        """SELECT * FROM reconciliation_runs
           WHERE organization_id = ?
           ORDER BY started_at DESC LIMIT ?""",
        (organization_id, limit),
    )
    return [row_to_run(r) for r in cur.fetchall()]


def find_result_by_id(
    conn: sqlite3.Connection, result_id: str, organization_id: str = "org_aarav"
) -> ReconciliationResultRecord | None:
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM reconciliation_results WHERE id = ? AND organization_id = ?",
        (result_id, organization_id),
    )
    row = cur.fetchone()
    return row_to_result(row) if row else None


def list_reconciliation_results(
    conn: sqlite3.Connection,
    organization_id: str = "org_aarav",
    run_id: str | None = None,
    status: str | None = None,
    scenario_id: str | None = None,
    case_needed: bool | None = None,
) -> list[ReconciliationResultRecord]:
    cur = conn.cursor()
    query = "SELECT * FROM reconciliation_results WHERE organization_id = ?"
    params: list[Any] = [organization_id]

    if run_id:
        query += " AND run_id = ?"
        params.append(run_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    if scenario_id:
        query += " AND scenario_id = ?"
        params.append(scenario_id)
    if case_needed is not None:
        query += " AND case_needed = ?"
        params.append(1 if case_needed else 0)

    query += " ORDER BY scenario_id ASC, evaluated_at DESC"
    cur.execute(query, params)
    return [row_to_result(r) for r in cur.fetchall()]


def fetch_duplicate_transaction_ids(
    conn: sqlite3.Connection, organization_id: str = "org_aarav"
) -> set[str]:
    cur = conn.cursor()
    cur.execute(
        """SELECT entity_id FROM audit_events
           WHERE organization_id = ? AND entity_type = 'TRANSACTION'
           AND event_type = 'DUPLICATE_SOURCE_RECORD_DETECTED'""",
        (organization_id,),
    )
    return {row[0] for row in cur.fetchall()}


def fetch_reconciliation_inputs(
    conn: sqlite3.Connection, organization_id: str = "org_aarav"
) -> dict[str, Any]:
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM transactions WHERE organization_id = ? ORDER BY occurred_at ASC",
        (organization_id,),
    )
    txns = [row_to_transaction(r) for r in cur.fetchall()]

    cur.execute(
        "SELECT * FROM settlement_batches WHERE organization_id = ? ORDER BY settlement_date ASC",
        (organization_id,),
    )
    settlements = [row_to_settlement(r) for r in cur.fetchall()]

    cur.execute(
        "SELECT * FROM settlement_line_items WHERE organization_id = ? ORDER BY line_item_id ASC",
        (organization_id,),
    )
    line_items = [row_to_line_item(r) for r in cur.fetchall()]

    cur.execute(
        "SELECT * FROM bank_entries WHERE organization_id = ? ORDER BY booking_date ASC",
        (organization_id,),
    )
    bank_entries = [row_to_bank_entry(r) for r in cur.fetchall()]

    cur.execute(
        "SELECT * FROM mock_support_updates WHERE organization_id = ? ORDER BY event_at ASC",
        (organization_id,),
    )
    support_updates = [row_to_support_update(r) for r in cur.fetchall()]

    duplicate_txn_ids = fetch_duplicate_transaction_ids(conn, organization_id)

    return {
        "transactions": txns,
        "settlements": settlements,
        "line_items": line_items,
        "bank_entries": bank_entries,
        "support_updates": support_updates,
        "duplicate_txn_ids": duplicate_txn_ids,
    }


def insert_case(conn: sqlite3.Connection, case: CaseRecord) -> None:
    conn.execute(
        """INSERT INTO cases (
            id, organization_id, reconciliation_result_id, case_type,
            status, priority, subject_type, subject_id, decision_summary,
            version, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            case.id,
            case.organization_id,
            case.reconciliation_result_id,
            case.case_type,
            case.status,
            case.priority,
            case.subject_type,
            case.subject_id,
            case.decision_summary,
            case.version,
            case.created_at,
            case.updated_at,
        ),
    )


def find_case_by_id(
    conn: sqlite3.Connection, case_id: str, organization_id: str | None = None
) -> CaseRecord | None:
    cur = conn.cursor()
    if organization_id:
        cur.execute(
            "SELECT * FROM cases WHERE id = ? AND organization_id = ?",
            (case_id, organization_id),
        )
    else:
        cur.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
    row = cur.fetchone()
    return row_to_case(row) if row else None


def update_case_with_version(
    conn: sqlite3.Connection,
    case_id: str,
    new_status: str,
    expected_version: int,
    updated_at: str,
    decision_summary: str | None = None,
    priority: str | None = None,
) -> bool:
    cur = conn.cursor()
    query = """UPDATE cases
               SET status = ?,
                   version = version + 1,
                   updated_at = ?,
                   decision_summary = COALESCE(?, decision_summary),
                   priority = COALESCE(?, priority)
               WHERE id = ? AND version = ?"""
    cur.execute(
        query, (new_status, updated_at, decision_summary, priority, case_id, expected_version)
    )
    return cur.rowcount > 0


def list_cases(
    conn: sqlite3.Connection,
    organization_id: str = "org_aarav",
    status: str | None = None,
    priority: str | None = None,
    case_type: str | None = None,
    subject_type: str | None = None,
    subject_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[CaseRecord]:
    cur = conn.cursor()
    query = "SELECT * FROM cases WHERE organization_id = ?"
    params: list[Any] = [organization_id]

    if status:
        query += " AND status = ?"
        params.append(status)
    if priority:
        query += " AND priority = ?"
        params.append(priority)
    if case_type:
        query += " AND case_type = ?"
        params.append(case_type)
    if subject_type:
        query += " AND subject_type = ?"
        params.append(subject_type)
    if subject_id:
        query += " AND subject_id = ?"
        params.append(subject_id)

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    cur.execute(query, params)
    return [row_to_case(r) for r in cur.fetchall()]


def insert_case_event(conn: sqlite3.Connection, event: CaseEventRecord) -> None:
    conn.execute(
        """INSERT INTO case_events (
            id, case_id, organization_id, actor_type, actor_id,
            from_status, to_status, event_type, summary, details_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            event.id,
            event.case_id,
            event.organization_id,
            event.actor_type,
            event.actor_id,
            event.from_status,
            event.to_status,
            event.event_type,
            event.summary,
            event.details_json,
            event.created_at,
        ),
    )


def list_case_events(
    conn: sqlite3.Connection, case_id: str, organization_id: str | None = None
) -> list[CaseEventRecord]:
    cur = conn.cursor()
    if organization_id:
        cur.execute(
            """SELECT * FROM case_events
               WHERE case_id = ? AND organization_id = ?
               ORDER BY created_at ASC""",
            (case_id, organization_id),
        )
    else:
        cur.execute(
            "SELECT * FROM case_events WHERE case_id = ? ORDER BY created_at ASC",
            (case_id,),
        )
    return [row_to_case_event(r) for r in cur.fetchall()]


def insert_approval(conn: sqlite3.Connection, approval: ApprovalRecord) -> None:
    conn.execute(
        """INSERT INTO approvals (
            id, case_id, organization_id, action_type, action_class,
            payload_hash, payload_json, status, requested_by_type,
            requested_by_id, approved_by, approved_at, expires_at,
            rejection_reason, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            approval.id,
            approval.case_id,
            approval.organization_id,
            approval.action_type,
            approval.action_class,
            approval.payload_hash,
            approval.payload_json,
            approval.status,
            approval.requested_by_type,
            approval.requested_by_id,
            approval.approved_by,
            approval.approved_at,
            approval.expires_at,
            approval.rejection_reason,
            approval.created_at,
        ),
    )


def find_approval_by_id(
    conn: sqlite3.Connection, approval_id: str, organization_id: str | None = None
) -> ApprovalRecord | None:
    cur = conn.cursor()
    if organization_id:
        cur.execute(
            "SELECT * FROM approvals WHERE id = ? AND organization_id = ?",
            (approval_id, organization_id),
        )
    else:
        cur.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,))
    row = cur.fetchone()
    return row_to_approval(row) if row else None


def list_approvals_for_case(
    conn: sqlite3.Connection,
    case_id: str,
    organization_id: str | None = None,
    status: str | None = None,
) -> list[ApprovalRecord]:
    cur = conn.cursor()
    query = "SELECT * FROM approvals WHERE case_id = ?"
    params: list[Any] = [case_id]
    if organization_id:
        query += " AND organization_id = ?"
        params.append(organization_id)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC"
    cur.execute(query, params)
    return [row_to_approval(r) for r in cur.fetchall()]


def update_approval_status(
    conn: sqlite3.Connection,
    approval_id: str,
    status: str,
    approved_by: str | None = None,
    approved_at: str | None = None,
    rejection_reason: str | None = None,
) -> bool:
    cur = conn.cursor()
    cur.execute(
        """UPDATE approvals
           SET status = ?,
               approved_by = COALESCE(?, approved_by),
               approved_at = COALESCE(?, approved_at),
               rejection_reason = COALESCE(?, rejection_reason)
           WHERE id = ?""",
        (status, approved_by, approved_at, rejection_reason, approval_id),
    )
    return cur.rowcount > 0


def insert_action_attempt(conn: sqlite3.Connection, attempt: ActionAttemptRecord) -> None:
    conn.execute(
        """INSERT INTO external_action_attempts (
            id, organization_id, case_id, approval_id, idempotency_key,
            action_type, status, payload_hash, payload_json, response_json,
            error_message, executed_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            attempt.id,
            attempt.organization_id,
            attempt.case_id,
            attempt.approval_id,
            attempt.idempotency_key,
            attempt.action_type,
            attempt.status,
            attempt.payload_hash,
            attempt.payload_json,
            attempt.response_json,
            attempt.error_message,
            attempt.executed_at,
            attempt.created_at,
        ),
    )


def find_action_attempt_by_idempotency(
    conn: sqlite3.Connection, organization_id: str, idempotency_key: str
) -> ActionAttemptRecord | None:
    cur = conn.cursor()
    cur.execute(
        """SELECT * FROM external_action_attempts
           WHERE organization_id = ? AND idempotency_key = ?""",
        (organization_id, idempotency_key),
    )
    row = cur.fetchone()
    return row_to_action_attempt(row) if row else None
