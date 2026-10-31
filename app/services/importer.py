"""Import pipeline: strict validation, provenance hashing, and atomic persistence."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.config import get_settings
from app.db.connection import db_session, get_connection
from app.models.domain import (
    AuditEventRecord,
    BankEntryRecord,
    ImportJobRecord,
    MockSupportUpdateRecord,
    RowValidationError,
    SettlementBatchRecord,
    SettlementLineItemRecord,
    SourceArtifactRecord,
    TransactionRecord,
    parse_money,
)
from app.services import repository

logger = logging.getLogger(__name__)

SUPPORTED_SCHEMA_VERSION = "1.0"
SUPPORTED_DATASET_VERSION = "v1"
ALLOWED_CURRENCY = "INR"
ALLOWED_PROVIDER = "PAYTM_MOCK"

TRANSACTION_HEADERS = [
    "provider",
    "provider_transaction_id",
    "merchant_reference",
    "store_id",
    "occurred_at",
    "status",
    "payment_method",
    "gross_amount",
    "currency",
]

SETTLEMENT_HEADERS = [
    "provider",
    "provider_settlement_id",
    "payout_reference",
    "settlement_date",
    "reported_status",
    "gross_amount",
    "fee_amount",
    "tax_amount",
    "adjustment_amount",
    "net_amount",
    "currency",
]

LINE_ITEM_HEADERS = [
    "provider_settlement_id",
    "line_item_id",
    "source_reference",
    "line_type",
    "amount",
    "currency",
]

BANK_HEADERS = [
    "statement_entry_id",
    "bank_account_alias",
    "booking_date",
    "direction",
    "amount",
    "currency",
    "narration",
    "utr_reference",
]


def validate_iso_utc(val: str) -> bool:
    """Validate ISO 8601 UTC timestamp format (must end with Z)."""
    if not val or not val.endswith("Z"):
        return False
    try:
        dt = datetime.fromisoformat(val[:-1] + "+00:00")
        return dt.tzinfo is not None
    except Exception:
        return False


def validate_iso_date(val: str) -> bool:
    """Validate ISO 8601 date string (YYYY-MM-DD)."""
    if not val or len(val) != 10:
        return False
    try:
        dt = datetime.strptime(val, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d") == val
    except Exception:
        return False


class ImportService:
    """Encapsulates validation, hashing, storage, and persistence for financial imports."""

    def __init__(self, db_path: str | None = None, storage_dir: Path | None = None) -> None:
        self.db_path = db_path
        settings = get_settings()
        if storage_dir is not None:
            self.storage_dir = storage_dir
        else:
            base = settings.storage_dir
            self.storage_dir = Path.cwd() / base if not base.is_absolute() else base
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _save_artifact_content(self, content_bytes: bytes, sha256: str, file_name: str) -> str:
        """Store an artifact copy in the private app storage root."""
        dest_dir = self.storage_dir / "artifacts" / sha256[:2] / sha256
        dest_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(file_name).name or "artifact.dat"
        dest_file = dest_dir / safe_name
        dest_file.write_bytes(content_bytes)
        return str(dest_file)

    def import_file(
        self,
        content: bytes | str,
        file_name: str,
        source_type: str | None = None,
        organization_id: str = "org_aarav",
        schema_version: str = SUPPORTED_SCHEMA_VERSION,
        dataset_version: str = SUPPORTED_DATASET_VERSION,
    ) -> ImportJobRecord:
        """Import a single CSV or JSON file atomically with validation and idempotency."""
        content_bytes = content.encode("utf-8") if isinstance(content, str) else content
        sha256 = hashlib.sha256(content_bytes).hexdigest()
        now_utc = datetime.now(UTC).isoformat()
        job_id = f"job_{uuid4().hex[:16]}"
        artifact_id = f"art_{uuid4().hex[:16]}"

        inferred_type = source_type or self._infer_source_type(file_name)

        # 1. Version enforcement
        if schema_version != SUPPORTED_SCHEMA_VERSION:
            msg = (
                f"Schema version '{schema_version}' unsupported. "
                f"Expected '{SUPPORTED_SCHEMA_VERSION}'"
            )
            error = RowValidationError(
                row_number=1,
                field="schema_version",
                code="UNSUPPORTED_SCHEMA_VERSION",
                message=msg,
            )
            return self._record_failed_job(
                job_id=job_id,
                organization_id=organization_id,
                artifact_id=None,
                source_type=inferred_type,
                errors=[error],
                started_at=now_utc,
            )

        # 2. Check idempotency: identical artifact already ingested?
        conn = get_connection(self.db_path)
        try:
            existing_artifact = repository.find_artifact_by_digest(
                conn, organization_id, inferred_type, schema_version, sha256
            )
            if existing_artifact:
                completed_job = repository.find_completed_job_by_artifact(
                    conn, organization_id, existing_artifact.id
                )
                if completed_job:
                    logger.info(
                        "Idempotent re-import of %s (%s); returning existing job %s",
                        file_name,
                        sha256[:8],
                        completed_job.id,
                    )
                    return ImportJobRecord(
                        id=completed_job.id,
                        organization_id=organization_id,
                        artifact_id=existing_artifact.id,
                        source_type=inferred_type,
                        status="COMPLETED",
                        total_records=completed_job.total_records,
                        processed_records=completed_job.processed_records,
                        error_count=0,
                        errors_json=None,
                        idempotent_replay=True,
                        started_at=completed_job.started_at,
                        completed_at=completed_job.completed_at,
                    )
        finally:
            conn.close()

        # 3. Create initial processing job record
        initial_job = ImportJobRecord(
            id=job_id,
            organization_id=organization_id,
            artifact_id=None,
            source_type=inferred_type,
            status="PROCESSING",
            total_records=0,
            processed_records=0,
            error_count=0,
            errors_json=None,
            idempotent_replay=False,
            started_at=now_utc,
            completed_at=None,
        )

        with db_session(self.db_path) as s_conn:
            repository.insert_import_job(s_conn, initial_job)
            repository.insert_audit_event(
                s_conn,
                AuditEventRecord(
                    id=f"aud_{uuid4().hex[:16]}",
                    organization_id=organization_id,
                    entity_type="IMPORT_JOB",
                    entity_id=job_id,
                    event_type="IMPORT_STARTED",
                    details_json=json.dumps({"file_name": file_name, "sha256": sha256}),
                    created_at=now_utc,
                ),
            )

        total_source_records = 0
        try:
            # 4. Parse and validate based on source type
            errors: list[RowValidationError] = []
            records: list[Any] = []

            try:
                text_content = content_bytes.decode("utf-8")
            except UnicodeDecodeError as exc:
                return self._record_failed_job(
                    job_id=job_id,
                    organization_id=organization_id,
                    artifact_id=None,
                    source_type=inferred_type,
                    errors=[
                        RowValidationError(
                            row_number=1,
                            field="encoding",
                            code="INVALID_ENCODING",
                            message=f"File must be UTF-8 encoded: {exc}",
                        )
                    ],
                    started_at=now_utc,
                )

            if inferred_type == "TRANSACTIONS":
                records, errors, total_source_records = self._parse_transactions(
                    text_content, organization_id, artifact_id, now_utc
                )
            elif inferred_type == "SETTLEMENTS":
                records, errors, total_source_records = self._parse_settlements(
                    text_content, organization_id, artifact_id, now_utc
                )
            elif inferred_type == "SETTLEMENT_LINE_ITEMS":
                records, errors, total_source_records = self._parse_settlement_line_items(
                    text_content, organization_id, artifact_id, now_utc
                )
            elif inferred_type == "BANK_STATEMENT":
                records, errors, total_source_records = self._parse_bank_statement(
                    text_content, organization_id, artifact_id, now_utc
                )
            elif inferred_type == "MOCK_SUPPORT_UPDATES":
                records, errors, total_source_records = self._parse_mock_support_updates(
                    text_content, organization_id, artifact_id, now_utc
                )
            else:
                errors.append(
                    RowValidationError(
                        row_number=1,
                        field="source_type",
                        code="UNKNOWN_SOURCE_TYPE",
                        message=f"Unknown source type '{inferred_type}'",
                    )
                )

            # Abort if validation errors occurred
            if errors:
                return self._record_failed_job(
                    job_id=job_id,
                    organization_id=organization_id,
                    artifact_id=None,
                    source_type=inferred_type,
                    errors=errors,
                    started_at=now_utc,
                    total_records=total_source_records,
                )

            # 5. Check for conflicts against existing records from different artifacts
            conflict_errors = self._check_conflicts(inferred_type, organization_id, records)
            if conflict_errors:
                return self._record_failed_job(
                    job_id=job_id,
                    organization_id=organization_id,
                    artifact_id=None,
                    source_type=inferred_type,
                    errors=conflict_errors,
                    started_at=now_utc,
                    total_records=total_source_records,
                )

            # 6. Atomic persistence of artifact, financial records, and completed job
            storage_path = self._save_artifact_content(content_bytes, sha256, file_name)
            artifact = SourceArtifactRecord(
                id=artifact_id,
                organization_id=organization_id,
                source_type=inferred_type,
                file_name=Path(file_name).name or "artifact.dat",
                schema_version=schema_version,
                dataset_version=dataset_version,
                sha256=sha256,
                size_bytes=len(content_bytes),
                storage_path=storage_path,
                record_count=total_source_records,
                ingested_at=now_utc,
            )

            completed_at = datetime.now(UTC).isoformat()
            completed_job = ImportJobRecord(
                id=job_id,
                organization_id=organization_id,
                artifact_id=artifact_id,
                source_type=inferred_type,
                status="COMPLETED",
                total_records=total_source_records,
                processed_records=len(records),
                error_count=0,
                errors_json=None,
                idempotent_replay=False,
                started_at=now_utc,
                completed_at=completed_at,
            )

            with db_session(self.db_path) as s_conn:
                repository.insert_source_artifact(s_conn, artifact)
                if inferred_type == "TRANSACTIONS":
                    repository.insert_transactions(s_conn, records)
                elif inferred_type == "SETTLEMENTS":
                    repository.insert_settlements(s_conn, records)
                elif inferred_type == "SETTLEMENT_LINE_ITEMS":
                    repository.insert_settlement_line_items(s_conn, records)
                elif inferred_type == "BANK_STATEMENT":
                    repository.insert_bank_entries(s_conn, records)
                elif inferred_type == "MOCK_SUPPORT_UPDATES":
                    repository.insert_mock_support_updates(s_conn, records)

                repository.update_import_job(s_conn, completed_job)
                repository.insert_audit_event(
                    s_conn,
                    AuditEventRecord(
                        id=f"aud_{uuid4().hex[:16]}",
                        organization_id=organization_id,
                        entity_type="IMPORT_JOB",
                        entity_id=job_id,
                        event_type="IMPORT_COMPLETED",
                        details_json=json.dumps(
                            {"record_count": len(records), "artifact_id": artifact_id}
                        ),
                        created_at=completed_at,
                    ),
                )

            logger.info(
                "Successfully imported %d %s records from %s (job %s)",
                len(records),
                inferred_type,
                file_name,
                job_id,
            )
            return completed_job
        except Exception as exc:
            logger.exception("Unexpected error processing import job %s: %s", job_id, exc)
            return self._record_failed_job(
                job_id=job_id,
                organization_id=organization_id,
                artifact_id=None,
                source_type=inferred_type,
                errors=[
                    RowValidationError(
                        row_number=1,
                        field="import",
                        code="INTERNAL_ERROR",
                        message=f"Internal import failure: {exc}",
                    )
                ],
                started_at=now_utc,
                total_records=total_source_records,
            )

    def _infer_source_type(self, file_name: str) -> str:
        name = Path(file_name).name.lower()
        if "transaction" in name:
            return "TRANSACTIONS"
        if "line_item" in name or "settlement_line" in name:
            return "SETTLEMENT_LINE_ITEMS"
        if "settlement" in name:
            return "SETTLEMENTS"
        if "bank" in name:
            return "BANK_STATEMENT"
        if "support" in name:
            return "MOCK_SUPPORT_UPDATES"
        return "UNKNOWN"

    def _record_failed_job(
        self,
        job_id: str,
        organization_id: str,
        artifact_id: str | None,
        source_type: str,
        errors: list[RowValidationError],
        started_at: str,
        total_records: int = 0,
    ) -> ImportJobRecord:
        completed_at = datetime.now(UTC).isoformat()
        errors_json = json.dumps([e.to_dict() for e in errors])
        job = ImportJobRecord(
            id=job_id,
            organization_id=organization_id,
            artifact_id=artifact_id,
            source_type=source_type,
            status="FAILED",
            total_records=total_records,
            processed_records=0,
            error_count=len(errors),
            errors_json=errors_json,
            idempotent_replay=False,
            started_at=started_at,
            completed_at=completed_at,
        )
        with db_session(self.db_path) as conn:
            existing = repository.find_job_by_id(conn, job_id)
            if existing:
                repository.update_import_job(conn, job)
            else:
                repository.insert_import_job(conn, job)
            repository.insert_audit_event(
                conn,
                AuditEventRecord(
                    id=f"aud_{uuid4().hex[:16]}",
                    organization_id=organization_id,
                    entity_type="IMPORT_JOB",
                    entity_id=job_id,
                    event_type="IMPORT_FAILED",
                    details_json=json.dumps({"error_count": len(errors)}),
                    created_at=completed_at,
                ),
            )
        logger.warning("Import job %s failed with %d errors", job_id, len(errors))
        return job

    def _check_conflicts(
        self, source_type: str, organization_id: str, records: list[Any]
    ) -> list[RowValidationError]:
        """Verify that no record in the new artifact conflicts with existing records."""
        conn = get_connection(self.db_path)
        conflicts: list[RowValidationError] = []
        try:
            if source_type == "TRANSACTIONS":
                row_map = {r.provider_transaction_id: r.source_row_number for r in records}
                txn_ids = list(row_map.keys())
                existing = repository.check_conflicting_transactions(
                    conn, organization_id, ALLOWED_PROVIDER, txn_ids
                )
                for eid in existing:
                    conflicts.append(
                        RowValidationError(
                            row_number=row_map.get(eid, 1),
                            field="provider_transaction_id",
                            code="CONFLICT",
                            message=f"Transaction '{eid}' already exists in database",
                        )
                    )
            elif source_type == "SETTLEMENTS":
                row_map = {r.provider_settlement_id: r.source_row_number for r in records}
                settle_ids = list(row_map.keys())
                existing = repository.check_conflicting_settlements(
                    conn, organization_id, ALLOWED_PROVIDER, settle_ids
                )
                for eid in existing:
                    conflicts.append(
                        RowValidationError(
                            row_number=row_map.get(eid, 1),
                            field="provider_settlement_id",
                            code="CONFLICT",
                            message=f"Settlement batch '{eid}' already exists in database",
                        )
                    )
            elif source_type == "SETTLEMENT_LINE_ITEMS":
                row_map = {r.line_item_id: r.source_row_number for r in records}
                line_ids = list(row_map.keys())
                existing = repository.check_conflicting_line_items(conn, organization_id, line_ids)
                for eid in existing:
                    conflicts.append(
                        RowValidationError(
                            row_number=row_map.get(eid, 1),
                            field="line_item_id",
                            code="CONFLICT",
                            message=f"Line item '{eid}' already exists in database",
                        )
                    )
            elif source_type == "BANK_STATEMENT":
                row_map = {r.statement_entry_id: r.source_row_number for r in records}
                entry_ids = list(row_map.keys())
                existing = repository.check_conflicting_bank_entries(
                    conn, organization_id, entry_ids
                )
                for eid in existing:
                    conflicts.append(
                        RowValidationError(
                            row_number=row_map.get(eid, 1),
                            field="statement_entry_id",
                            code="CONFLICT",
                            message=f"Bank entry '{eid}' already exists in database",
                        )
                    )
            elif source_type == "MOCK_SUPPORT_UPDATES":
                conflicting_updates = repository.check_conflicting_support_updates(
                    conn, organization_id, records
                )
                for u in conflicting_updates:
                    conflicts.append(
                        RowValidationError(
                            row_number=u.source_row_number,
                            field="case_reference",
                            code="CONFLICT",
                            message=(
                                f"Support update for case '{u.case_reference}' at "
                                f"'{u.event_at}' already exists in database"
                            ),
                        )
                    )
        finally:
            conn.close()
        return conflicts

    def _parse_transactions(
        self,
        content: str,
        organization_id: str,
        artifact_id: str,
        now_utc: str,
    ) -> tuple[list[TransactionRecord], list[RowValidationError], int]:
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        if not rows:
            return (
                [],
                [
                    RowValidationError(
                        row_number=1,
                        field="file",
                        code="EMPTY_FILE",
                        message="CSV file is empty",
                    )
                ],
                0,
            )

        headers = [h.strip() for h in rows[0]]
        if headers != TRANSACTION_HEADERS:
            return (
                [],
                [
                    RowValidationError(
                        row_number=1,
                        field="headers",
                        code="INVALID_HEADERS",
                        message=f"Expected columns {TRANSACTION_HEADERS}, got {headers}",
                    )
                ],
                0,
            )

        records: list[TransactionRecord] = []
        errors: list[RowValidationError] = []
        seen_ids: set[str] = set()
        store_ids: set[str] = set()
        total_data_rows = 0

        for idx, row in enumerate(rows[1:], start=2):
            if not row or all(c.strip() == "" for c in row):
                continue
            total_data_rows += 1
            if len(row) != len(TRANSACTION_HEADERS):
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="row",
                        code="COLUMN_COUNT_MISMATCH",
                        message=f"Expected {len(TRANSACTION_HEADERS)} columns, got {len(row)}",
                    )
                )
                continue

            (
                provider,
                provider_txn_id,
                merchant_ref,
                store_id,
                occurred_at,
                status,
                payment_method,
                gross_amount_str,
                currency,
            ) = [c.strip() for c in row]

            row_errors_before = len(errors)

            if provider != ALLOWED_PROVIDER:
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="provider",
                        code="UNSUPPORTED_PROVIDER",
                        message=f"provider '{provider}' unsupported; must be '{ALLOWED_PROVIDER}'",
                    )
                )

            if not provider_txn_id:
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="provider_transaction_id",
                        code="MISSING_FIELD",
                        message="provider_transaction_id is required and cannot be empty",
                    )
                )
            elif not provider_txn_id.startswith("mock_txn_"):
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="provider_transaction_id",
                        code="INVALID_PREFIX",
                        message="provider_transaction_id must start with 'mock_txn_'",
                    )
                )
            elif provider_txn_id in seen_ids:
                # SCN-06: Deduplicate duplicate transaction row in merchant feed
                logger.info("Deduplicating transaction %s at row %d", provider_txn_id, idx)
                continue
            else:
                seen_ids.add(provider_txn_id)

            if not merchant_ref:
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="merchant_reference",
                        code="MISSING_FIELD",
                        message="merchant_reference is required",
                    )
                )

            if not store_id:
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="store_id",
                        code="MISSING_FIELD",
                        message="store_id is required",
                    )
                )
            else:
                store_ids.add(store_id)

            if not validate_iso_utc(occurred_at):
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="occurred_at",
                        code="INVALID_DATE",
                        message=(
                            f"occurred_at '{occurred_at}' must be valid ISO 8601 UTC (ending in Z)"
                        ),
                    )
                )

            if status not in ("SUCCESS", "FAILED", "REFUNDED"):
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="status",
                        code="INVALID_ENUM",
                        message=f"status '{status}' must be SUCCESS, FAILED, or REFUNDED",
                    )
                )

            if payment_method not in ("UPI", "CARD", "NET_BANKING"):
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="payment_method",
                        code="INVALID_ENUM",
                        message=(
                            f"payment_method '{payment_method}' must be UPI, CARD, or NET_BANKING"
                        ),
                    )
                )

            if currency != ALLOWED_CURRENCY:
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="currency",
                        code="UNSUPPORTED_CURRENCY",
                        message=f"Unsupported currency '{currency}'; must be '{ALLOWED_CURRENCY}'",
                    )
                )

            try:
                gross_amount = parse_money(gross_amount_str, "gross_amount")
                if gross_amount <= Decimal("0.00"):
                    errors.append(
                        RowValidationError(
                            row_number=idx,
                            field="gross_amount",
                            code="INVALID_AMOUNT",
                            message="gross_amount must be greater than 0.00",
                        )
                    )
            except ValueError as e:
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="gross_amount",
                        code="INVALID_AMOUNT",
                        message=str(e),
                    )
                )
                gross_amount = Decimal("0.00")

            if len(errors) == row_errors_before:
                records.append(
                    TransactionRecord(
                        id=f"txn_{uuid4().hex[:16]}",
                        organization_id=organization_id,
                        store_id=store_id,
                        provider=provider,
                        provider_transaction_id=provider_txn_id,
                        merchant_reference=merchant_ref,
                        occurred_at=occurred_at,
                        status=status,
                        payment_method=payment_method,
                        gross_amount=gross_amount,
                        currency=currency,
                        source_artifact_id=artifact_id,
                        source_row_number=idx,
                        created_at=now_utc,
                    )
                )

        # Referential integrity check on stores
        if store_ids:
            conn = get_connection(self.db_path)
            try:
                existing_stores = repository.check_stores_exist(conn, organization_id, store_ids)
                for rec in list(records):
                    if rec.store_id not in existing_stores:
                        errors.append(
                            RowValidationError(
                                row_number=rec.source_row_number,
                                field="store_id",
                                code="UNKNOWN_STORE",
                                message=(
                                    f"Store '{rec.store_id}' does not exist for "
                                    f"organization '{organization_id}'"
                                ),
                            )
                        )
            finally:
                conn.close()

        return records, errors, total_data_rows

    def _parse_settlements(
        self,
        content: str,
        organization_id: str,
        artifact_id: str,
        now_utc: str,
    ) -> tuple[list[SettlementBatchRecord], list[RowValidationError], int]:
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        if not rows:
            return (
                [],
                [
                    RowValidationError(
                        row_number=1,
                        field="file",
                        code="EMPTY_FILE",
                        message="CSV file is empty",
                    )
                ],
                0,
            )

        headers = [h.strip() for h in rows[0]]
        if headers != SETTLEMENT_HEADERS:
            return (
                [],
                [
                    RowValidationError(
                        row_number=1,
                        field="headers",
                        code="INVALID_HEADERS",
                        message=f"Expected columns {SETTLEMENT_HEADERS}, got {headers}",
                    )
                ],
                0,
            )

        records: list[SettlementBatchRecord] = []
        errors: list[RowValidationError] = []
        seen_ids: set[str] = set()
        total_data_rows = 0

        for idx, row in enumerate(rows[1:], start=2):
            if not row or all(c.strip() == "" for c in row):
                continue
            total_data_rows += 1
            if len(row) != len(SETTLEMENT_HEADERS):
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="row",
                        code="COLUMN_COUNT_MISMATCH",
                        message=f"Expected {len(SETTLEMENT_HEADERS)} columns, got {len(row)}",
                    )
                )
                continue

            (
                provider,
                provider_settle_id,
                payout_ref,
                settle_date,
                reported_status,
                gross_str,
                fee_str,
                tax_str,
                adj_str,
                net_str,
                currency,
            ) = [c.strip() for c in row]

            row_errors_before = len(errors)

            if provider != ALLOWED_PROVIDER:
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="provider",
                        code="UNSUPPORTED_PROVIDER",
                        message=f"provider '{provider}' unsupported; must be '{ALLOWED_PROVIDER}'",
                    )
                )

            if not provider_settle_id:
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="provider_settlement_id",
                        code="MISSING_FIELD",
                        message="provider_settlement_id is required and cannot be empty",
                    )
                )
            elif not provider_settle_id.startswith("mock_settle_"):
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="provider_settlement_id",
                        code="INVALID_PREFIX",
                        message="provider_settlement_id must start with 'mock_settle_'",
                    )
                )
            elif provider_settle_id in seen_ids:
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="provider_settlement_id",
                        code="DUPLICATE_IDENTIFIER",
                        message=f"Duplicate provider_settlement_id '{provider_settle_id}' in file",
                    )
                )
            else:
                seen_ids.add(provider_settle_id)

            if not payout_ref or not payout_ref.startswith("mock_utr_"):
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="payout_reference",
                        code="INVALID_PREFIX",
                        message="payout_reference must start with 'mock_utr_'",
                    )
                )

            if not validate_iso_date(settle_date):
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="settlement_date",
                        code="INVALID_DATE",
                        message=(
                            f"settlement_date '{settle_date}' must be ISO 8601 date (YYYY-MM-DD)"
                        ),
                    )
                )

            if reported_status not in ("PROCESSED", "PENDING", "FAILED"):
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="reported_status",
                        code="INVALID_ENUM",
                        message=(
                            f"reported_status '{reported_status}' "
                            "must be PROCESSED, PENDING, or FAILED"
                        ),
                    )
                )

            if currency != ALLOWED_CURRENCY:
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="currency",
                        code="UNSUPPORTED_CURRENCY",
                        message=f"Unsupported currency '{currency}'; must be '{ALLOWED_CURRENCY}'",
                    )
                )

            gross = Decimal("0.00")
            fee = Decimal("0.00")
            tax = Decimal("0.00")
            adj = Decimal("0.00")
            net = Decimal("0.00")
            money_valid = True

            for field_name, val_str in [
                ("gross_amount", gross_str),
                ("fee_amount", fee_str),
                ("tax_amount", tax_str),
                ("adjustment_amount", adj_str),
                ("net_amount", net_str),
            ]:
                try:
                    parsed = parse_money(val_str, field_name)
                    if field_name == "gross_amount" and parsed <= Decimal("0.00"):
                        errors.append(
                            RowValidationError(
                                row_number=idx,
                                field=field_name,
                                code="INVALID_AMOUNT",
                                message="gross_amount must be greater than 0.00",
                            )
                        )
                        money_valid = False
                    elif field_name in ("fee_amount", "tax_amount") and parsed < Decimal("0.00"):
                        errors.append(
                            RowValidationError(
                                row_number=idx,
                                field=field_name,
                                code="INVALID_AMOUNT",
                                message=f"{field_name} must be >= 0.00",
                            )
                        )
                        money_valid = False

                    if field_name == "gross_amount":
                        gross = parsed
                    elif field_name == "fee_amount":
                        fee = parsed
                    elif field_name == "tax_amount":
                        tax = parsed
                    elif field_name == "adjustment_amount":
                        adj = parsed
                    elif field_name == "net_amount":
                        net = parsed
                except ValueError as e:
                    errors.append(
                        RowValidationError(
                            row_number=idx,
                            field=field_name,
                            code="INVALID_AMOUNT",
                            message=str(e),
                        )
                    )
                    money_valid = False

            if money_valid:
                expected_net = gross - fee - tax + adj
                if net != expected_net:
                    msg = (
                        f"Settlement balance invariant failed: net_amount {net} "
                        f"!= gross {gross} - fee {fee} - tax {tax} + adj {adj} ({expected_net})"
                    )
                    errors.append(
                        RowValidationError(
                            row_number=idx,
                            field="net_amount",
                            code="BALANCE_INVARIANT_VIOLATION",
                            message=msg,
                        )
                    )

            if len(errors) == row_errors_before and money_valid:
                records.append(
                    SettlementBatchRecord(
                        id=f"stl_{uuid4().hex[:16]}",
                        organization_id=organization_id,
                        provider=provider,
                        provider_settlement_id=provider_settle_id,
                        payout_reference=payout_ref,
                        settlement_date=settle_date,
                        reported_status=reported_status,
                        gross_amount=gross,
                        fee_amount=fee,
                        tax_amount=tax,
                        adjustment_amount=adj,
                        net_amount=net,
                        currency=currency,
                        source_artifact_id=artifact_id,
                        source_row_number=idx,
                        created_at=now_utc,
                    )
                )

        return records, errors, total_data_rows

    def _parse_settlement_line_items(
        self,
        content: str,
        organization_id: str,
        artifact_id: str,
        now_utc: str,
    ) -> tuple[list[SettlementLineItemRecord], list[RowValidationError], int]:
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        if not rows:
            return (
                [],
                [
                    RowValidationError(
                        row_number=1,
                        field="file",
                        code="EMPTY_FILE",
                        message="CSV file is empty",
                    )
                ],
                0,
            )

        headers = [h.strip() for h in rows[0]]
        if headers != LINE_ITEM_HEADERS:
            return (
                [],
                [
                    RowValidationError(
                        row_number=1,
                        field="headers",
                        code="INVALID_HEADERS",
                        message=f"Expected columns {LINE_ITEM_HEADERS}, got {headers}",
                    )
                ],
                0,
            )

        records: list[SettlementLineItemRecord] = []
        errors: list[RowValidationError] = []
        seen_line_ids: set[str] = set()
        settlement_refs: set[str] = set()
        total_data_rows = 0

        for idx, row in enumerate(rows[1:], start=2):
            if not row or all(c.strip() == "" for c in row):
                continue
            total_data_rows += 1
            if len(row) != len(LINE_ITEM_HEADERS):
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="row",
                        code="COLUMN_COUNT_MISMATCH",
                        message=f"Expected {len(LINE_ITEM_HEADERS)} columns, got {len(row)}",
                    )
                )
                continue

            (
                provider_settle_id,
                line_item_id,
                source_ref,
                line_type,
                amount_str,
                currency,
            ) = [c.strip() for c in row]

            row_errors_before = len(errors)

            if not provider_settle_id or not provider_settle_id.startswith("mock_settle_"):
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="provider_settlement_id",
                        code="INVALID_PREFIX",
                        message="provider_settlement_id must start with 'mock_settle_'",
                    )
                )
            else:
                settlement_refs.add(provider_settle_id)

            if not line_item_id or not line_item_id.startswith("mock_line_"):
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="line_item_id",
                        code="INVALID_PREFIX",
                        message="line_item_id must start with 'mock_line_'",
                    )
                )
            elif line_item_id in seen_line_ids:
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="line_item_id",
                        code="DUPLICATE_IDENTIFIER",
                        message=f"Duplicate line_item_id '{line_item_id}' in file",
                    )
                )
            else:
                seen_line_ids.add(line_item_id)

            if not source_ref:
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="source_reference",
                        code="MISSING_FIELD",
                        message="source_reference is required",
                    )
                )
            elif not source_ref.startswith(("mock_txn_", "mock_adj_")):
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="source_reference",
                        code="INVALID_PREFIX",
                        message="source_reference must start with 'mock_txn_' or 'mock_adj_'",
                    )
                )

            if line_type not in ("PAYMENT", "REFUND", "DISPUTE_HOLD", "ADJUSTMENT"):
                msg = (
                    f"line_type '{line_type}' must be PAYMENT, REFUND, DISPUTE_HOLD, or ADJUSTMENT"
                )
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="line_type",
                        code="INVALID_ENUM",
                        message=msg,
                    )
                )

            if currency != ALLOWED_CURRENCY:
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="currency",
                        code="UNSUPPORTED_CURRENCY",
                        message=f"Unsupported currency '{currency}'; must be '{ALLOWED_CURRENCY}'",
                    )
                )

            try:
                amount = parse_money(amount_str, "amount")
                if line_type == "PAYMENT" and amount <= Decimal("0.00"):
                    errors.append(
                        RowValidationError(
                            row_number=idx,
                            field="amount",
                            code="INVALID_AMOUNT",
                            message="PAYMENT amount must be greater than 0.00",
                        )
                    )
            except ValueError as e:
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="amount",
                        code="INVALID_AMOUNT",
                        message=str(e),
                    )
                )
                amount = Decimal("0.00")

            if len(errors) == row_errors_before:
                records.append(
                    SettlementLineItemRecord(
                        id=f"sli_{uuid4().hex[:16]}",
                        organization_id=organization_id,
                        provider_settlement_id=provider_settle_id,
                        line_item_id=line_item_id,
                        source_reference=source_ref,
                        line_type=line_type,
                        amount=amount,
                        currency=currency,
                        source_artifact_id=artifact_id,
                        source_row_number=idx,
                        created_at=now_utc,
                    )
                )

        # Referential integrity check
        if settlement_refs:
            conn = get_connection(self.db_path)
            try:
                existing = repository.check_settlements_exist(
                    conn, organization_id, settlement_refs
                )
                for rec in list(records):
                    if rec.provider_settlement_id not in existing:
                        msg = (
                            f"Referenced settlement '{rec.provider_settlement_id}' "
                            f"does not exist in settlement batches"
                        )
                        errors.append(
                            RowValidationError(
                                row_number=rec.source_row_number,
                                field="provider_settlement_id",
                                code="UNMATCHED_REFERENCE",
                                message=msg,
                            )
                        )
            finally:
                conn.close()

        return records, errors, total_data_rows

    def _parse_bank_statement(
        self,
        content: str,
        organization_id: str,
        artifact_id: str,
        now_utc: str,
    ) -> tuple[list[BankEntryRecord], list[RowValidationError], int]:
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        if not rows:
            return (
                [],
                [
                    RowValidationError(
                        row_number=1,
                        field="file",
                        code="EMPTY_FILE",
                        message="CSV file is empty",
                    )
                ],
                0,
            )

        headers = [h.strip() for h in rows[0]]
        if headers != BANK_HEADERS:
            return (
                [],
                [
                    RowValidationError(
                        row_number=1,
                        field="headers",
                        code="INVALID_HEADERS",
                        message=f"Expected columns {BANK_HEADERS}, got {headers}",
                    )
                ],
                0,
            )

        records: list[BankEntryRecord] = []
        errors: list[RowValidationError] = []
        seen_entry_ids: set[str] = set()
        bank_account_aliases: set[str] = set()
        total_data_rows = 0

        for idx, row in enumerate(rows[1:], start=2):
            if not row or all(c.strip() == "" for c in row):
                continue
            total_data_rows += 1
            if len(row) != len(BANK_HEADERS):
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="row",
                        code="COLUMN_COUNT_MISMATCH",
                        message=f"Expected {len(BANK_HEADERS)} columns, got {len(row)}",
                    )
                )
                continue

            (
                entry_id,
                acc_alias,
                booking_date,
                direction,
                amount_str,
                currency,
                narration,
                utr_ref,
            ) = [c.strip() for c in row]

            row_errors_before = len(errors)

            if not entry_id:
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="statement_entry_id",
                        code="MISSING_FIELD",
                        message="statement_entry_id is required",
                    )
                )
            elif not entry_id.startswith("mock_bank_"):
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="statement_entry_id",
                        code="INVALID_PREFIX",
                        message="statement_entry_id must start with 'mock_bank_'",
                    )
                )
            elif entry_id in seen_entry_ids:
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="statement_entry_id",
                        code="DUPLICATE_IDENTIFIER",
                        message=f"Duplicate statement_entry_id '{entry_id}' in file",
                    )
                )
            else:
                seen_entry_ids.add(entry_id)

            if not acc_alias:
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="bank_account_alias",
                        code="MISSING_FIELD",
                        message="bank_account_alias is required",
                    )
                )
            else:
                bank_account_aliases.add(acc_alias)

            if not validate_iso_date(booking_date):
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="booking_date",
                        code="INVALID_DATE",
                        message=f"booking_date '{booking_date}' must be ISO 8601 date (YYYY-MM-DD)",
                    )
                )

            if direction not in ("CREDIT", "DEBIT"):
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="direction",
                        code="INVALID_ENUM",
                        message=f"direction '{direction}' must be CREDIT or DEBIT",
                    )
                )

            if currency != ALLOWED_CURRENCY:
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="currency",
                        code="UNSUPPORTED_CURRENCY",
                        message=f"Unsupported currency '{currency}'; must be '{ALLOWED_CURRENCY}'",
                    )
                )

            if not narration:
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="narration",
                        code="MISSING_FIELD",
                        message="narration is required",
                    )
                )

            if utr_ref and not utr_ref.startswith("mock_utr_"):
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="utr_reference",
                        code="INVALID_PREFIX",
                        message="utr_reference must start with 'mock_utr_'",
                    )
                )

            try:
                amount = parse_money(amount_str, "amount")
                if amount <= Decimal("0.00"):
                    errors.append(
                        RowValidationError(
                            row_number=idx,
                            field="amount",
                            code="INVALID_AMOUNT",
                            message="amount must be greater than 0.00",
                        )
                    )
            except ValueError as e:
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="amount",
                        code="INVALID_AMOUNT",
                        message=str(e),
                    )
                )
                amount = Decimal("0.00")

            if len(errors) == row_errors_before:
                records.append(
                    BankEntryRecord(
                        id=f"bnk_{uuid4().hex[:16]}",
                        organization_id=organization_id,
                        statement_entry_id=entry_id,
                        bank_account_alias=acc_alias,
                        booking_date=booking_date,
                        direction=direction,
                        amount=amount,
                        currency=currency,
                        narration=narration,
                        utr_reference=utr_ref if utr_ref else None,
                        source_artifact_id=artifact_id,
                        source_row_number=idx,
                        created_at=now_utc,
                    )
                )

        # Referential integrity check on bank accounts
        if bank_account_aliases:
            conn = get_connection(self.db_path)
            try:
                existing_aliases = repository.check_bank_accounts_exist(
                    conn, organization_id, bank_account_aliases
                )
                for rec in list(records):
                    if rec.bank_account_alias not in existing_aliases:
                        errors.append(
                            RowValidationError(
                                row_number=rec.source_row_number,
                                field="bank_account_alias",
                                code="UNKNOWN_BANK_ACCOUNT",
                                message=(
                                    f"Bank account alias '{rec.bank_account_alias}' "
                                    f"does not exist for organization '{organization_id}'"
                                ),
                            )
                        )
            finally:
                conn.close()

        return records, errors, total_data_rows

    def _parse_mock_support_updates(
        self,
        content: str,
        organization_id: str,
        artifact_id: str,
        now_utc: str,
    ) -> tuple[list[MockSupportUpdateRecord], list[RowValidationError], int]:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            return (
                [],
                [
                    RowValidationError(
                        row_number=1,
                        field="json",
                        code="INVALID_JSON",
                        message=f"Malformed JSON: {exc}",
                    )
                ],
                0,
            )

        if not isinstance(data, list):
            return (
                [],
                [
                    RowValidationError(
                        row_number=1,
                        field="json",
                        code="INVALID_STRUCTURE",
                        message="Expected top-level JSON array of support update objects",
                    )
                ],
                0,
            )

        records: list[MockSupportUpdateRecord] = []
        errors: list[RowValidationError] = []
        total_data_rows = len(data)

        for idx, item in enumerate(data, start=1):
            if not isinstance(item, dict):
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="item",
                        code="INVALID_ROW_TYPE",
                        message="Expected object in array",
                    )
                )
                continue

            row_errors_before = len(errors)

            case_ref = item.get("case_reference", "")
            event_at = item.get("event_at", "")
            status = item.get("status", "")
            summary = item.get("summary", "")
            terminal = item.get("terminal_outcome")
            evidence = item.get("evidence_reference", "")

            if not case_ref or not str(case_ref).startswith("mock_case_"):
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="case_reference",
                        code="INVALID_PREFIX",
                        message="case_reference must start with 'mock_case_'",
                    )
                )

            if not validate_iso_utc(str(event_at)):
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="event_at",
                        code="INVALID_DATE",
                        message=f"event_at '{event_at}' must be ISO 8601 UTC (ending in Z)",
                    )
                )

            if status not in ("SUBMITTED", "IN_REVIEW", "RESOLVED", "REJECTED"):
                msg = f"status '{status}' must be SUBMITTED, IN_REVIEW, RESOLVED, or REJECTED"
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="status",
                        code="INVALID_ENUM",
                        message=msg,
                    )
                )

            if not summary:
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="summary",
                        code="MISSING_FIELD",
                        message="summary is required",
                    )
                )

            if not isinstance(terminal, bool):
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="terminal_outcome",
                        code="INVALID_BOOLEAN",
                        message="terminal_outcome must be true or false",
                    )
                )

            if not evidence:
                errors.append(
                    RowValidationError(
                        row_number=idx,
                        field="evidence_reference",
                        code="MISSING_FIELD",
                        message="evidence_reference is required",
                    )
                )

            if len(errors) == row_errors_before:
                records.append(
                    MockSupportUpdateRecord(
                        id=f"sup_{uuid4().hex[:16]}",
                        organization_id=organization_id,
                        case_reference=str(case_ref),
                        event_at=str(event_at),
                        status=str(status),
                        summary=str(summary),
                        terminal_outcome=bool(terminal),
                        evidence_reference=str(evidence),
                        source_artifact_id=artifact_id,
                        source_row_number=idx,
                        created_at=now_utc,
                    )
                )

        return records, errors, total_data_rows

    def import_bundle(
        self,
        bundle_dir: Path,
        organization_id: str = "org_aarav",
    ) -> list[ImportJobRecord]:
        """Import a full synthetic fixture bundle in canonical order with manifest verification."""
        manifest_path = bundle_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found at {manifest_path}")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        schema_version = manifest.get("schema_version", SUPPORTED_SCHEMA_VERSION)
        dataset_version = manifest.get("dataset_version", SUPPORTED_DATASET_VERSION)

        if schema_version != SUPPORTED_SCHEMA_VERSION:
            msg = (
                f"Unsupported manifest schema_version '{schema_version}'. "
                f"Expected '{SUPPORTED_SCHEMA_VERSION}'"
            )
            raise ValueError(msg)

        sequence = [
            ("transactions.csv", "TRANSACTIONS"),
            ("settlements.csv", "SETTLEMENTS"),
            ("settlement_line_items.csv", "SETTLEMENT_LINE_ITEMS"),
            ("bank_statement.csv", "BANK_STATEMENT"),
            ("mock_support_updates.json", "MOCK_SUPPORT_UPDATES"),
        ]

        jobs: list[ImportJobRecord] = []
        for file_name, s_type in sequence:
            file_path = bundle_dir / file_name
            if not file_path.exists():
                logger.warning("Bundle file %s missing in %s; skipping", file_name, bundle_dir)
                continue

            content_bytes = file_path.read_bytes()

            if "files" in manifest and file_name in manifest["files"]:
                expected_hash = manifest["files"][file_name]["sha256"]
                actual_hash = hashlib.sha256(content_bytes).hexdigest()
                if actual_hash != expected_hash:
                    msg = (
                        f"Checksum mismatch for {file_name}: "
                        f"expected {expected_hash}, got {actual_hash}"
                    )
                    raise ValueError(msg)

            job = self.import_file(
                content=content_bytes,
                file_name=file_name,
                source_type=s_type,
                organization_id=organization_id,
                schema_version=schema_version,
                dataset_version=dataset_version,
            )
            jobs.append(job)
            if job.status == "FAILED":
                logger.error("Bundle import halted at %s due to failures", file_name)
                break

        return jobs
