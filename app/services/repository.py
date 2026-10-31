"""Repository access layer for domain entities, artifacts, and import records."""

from __future__ import annotations

import sqlite3

from app.models.domain import (
    AuditEventRecord,
    BankEntryRecord,
    ImportJobRecord,
    MockSupportUpdateRecord,
    SettlementBatchRecord,
    SettlementLineItemRecord,
    SourceArtifactRecord,
    TransactionRecord,
    format_money,
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
            id, organization_id, entity_type, entity_id, event_type, details_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            event.id,
            event.organization_id,
            event.entity_type,
            event.entity_id,
            event.event_type,
            event.details_json,
            event.created_at,
        ),
    )


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
