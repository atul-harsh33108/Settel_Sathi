"""Canonical domain models, exact money helpers, and validation schemas."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

MONEY_REGEX = re.compile(r"^-?\d+\.\d{2}$")


def format_money(val: Decimal) -> str:
    """Format decimal money to exact canonical two decimal places."""
    return f"{val:.2f}"


def parse_money(val: Any, field_name: str = "amount") -> Decimal:
    """Parse exact fixed-precision money string. Reject floats and invalid precision."""
    if isinstance(val, (int | float)):
        # Binary floats or raw ints without explicit minor/canonical format are rejected
        raise ValueError(
            f"{field_name} must be an exact two-decimal string (e.g. '1500.00'), not float/int"
        )
    val_str = str(val).strip()
    if not MONEY_REGEX.match(val_str):
        msg = f"{field_name} '{val_str}' is malformed; must be exact 2-decimal format"
        raise ValueError(msg)
    try:
        return Decimal(val_str)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid decimal value '{val_str}' for {field_name}") from exc


@dataclass(frozen=True)
class RowValidationError:
    """Structured row-level validation error."""

    row_number: int
    field: str
    code: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_number": self.row_number,
            "field": self.field,
            "code": self.code,
            "message": self.message,
        }


@dataclass(frozen=True)
class SourceArtifactRecord:
    """Persisted source file artifact metadata and provenance digest."""

    id: str
    organization_id: str
    source_type: str
    file_name: str
    schema_version: str
    dataset_version: str
    sha256: str
    size_bytes: int
    storage_path: str
    record_count: int
    ingested_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ImportJobRecord:
    """Execution record for an idempotent import job."""

    id: str
    organization_id: str
    artifact_id: str | None
    source_type: str
    status: str  # PENDING, PROCESSING, COMPLETED, FAILED
    total_records: int
    processed_records: int
    error_count: int
    errors_json: str | None
    idempotent_replay: bool
    started_at: str
    completed_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TransactionRecord:
    """Customer payment collection record."""

    id: str
    organization_id: str
    store_id: str
    provider: str
    provider_transaction_id: str
    merchant_reference: str
    occurred_at: str
    status: str
    payment_method: str
    gross_amount: Decimal
    currency: str
    source_artifact_id: str
    source_row_number: int
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["gross_amount"] = format_money(self.gross_amount)
        return d


@dataclass(frozen=True)
class SettlementBatchRecord:
    """Provider payout batch compiling customer collections."""

    id: str
    organization_id: str
    provider: str
    provider_settlement_id: str
    payout_reference: str
    settlement_date: str
    reported_status: str
    gross_amount: Decimal
    fee_amount: Decimal
    tax_amount: Decimal
    adjustment_amount: Decimal
    net_amount: Decimal
    currency: str
    source_artifact_id: str
    source_row_number: int
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["gross_amount"] = format_money(self.gross_amount)
        d["fee_amount"] = format_money(self.fee_amount)
        d["tax_amount"] = format_money(self.tax_amount)
        d["adjustment_amount"] = format_money(self.adjustment_amount)
        d["net_amount"] = format_money(self.net_amount)
        return d


@dataclass(frozen=True)
class SettlementLineItemRecord:
    """Itemized transaction or deduction linking to a settlement batch."""

    id: str
    organization_id: str
    provider_settlement_id: str
    line_item_id: str
    source_reference: str
    line_type: str
    amount: Decimal
    currency: str
    source_artifact_id: str
    source_row_number: int
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["amount"] = format_money(self.amount)
        return d


@dataclass(frozen=True)
class BankEntryRecord:
    """Authoritative credit or debit record from official bank statement."""

    id: str
    organization_id: str
    statement_entry_id: str
    bank_account_alias: str
    booking_date: str
    direction: str
    amount: Decimal
    currency: str
    narration: str
    utr_reference: str | None
    source_artifact_id: str
    source_row_number: int
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["amount"] = format_money(self.amount)
        return d


@dataclass(frozen=True)
class MockSupportUpdateRecord:
    """Simulated provider support resolution status update."""

    id: str
    organization_id: str
    case_reference: str
    event_at: str
    status: str
    summary: str
    terminal_outcome: bool
    evidence_reference: str
    source_artifact_id: str
    source_row_number: int
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AuditEventRecord:
    """Immutable audit trail event."""

    id: str
    organization_id: str
    entity_type: str
    entity_id: str
    event_type: str
    details_json: str | None
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReconciliationStatus:
    RECONCILED = "RECONCILED"
    UNMATCHED = "UNMATCHED"
    WITHIN_EXPECTED_WINDOW = "WITHIN_EXPECTED_WINDOW"
    PARTIALLY_MATCHED = "PARTIALLY_MATCHED"
    ADJUSTMENT_EXPLAINED = "ADJUSTMENT_EXPLAINED"
    DUPLICATE = "DUPLICATE"
    VERIFIED_RESOLVED = "VERIFIED_RESOLVED"
    ESCALATED = "ESCALATED"


class ReconciliationReasonCode:
    MATCHED_PAYOUT_TO_BANK = "MATCHED_PAYOUT_TO_BANK"
    SETTLEMENT_ABSENT_FROM_BANK = "SETTLEMENT_ABSENT_FROM_BANK"
    SETTLEMENT_IN_FLIGHT_WINDOW = "SETTLEMENT_IN_FLIGHT_WINDOW"
    PARTIAL_SETTLEMENT_BATCH = "PARTIAL_SETTLEMENT_BATCH"
    DEDUCTIONS_MATCH_POLICY = "DEDUCTIONS_MATCH_POLICY"
    DUPLICATE_SOURCE_RECORD_DETECTED = "DUPLICATE_SOURCE_RECORD_DETECTED"
    REFUND_BALANCED = "REFUND_BALANCED"
    MANY_TO_ONE_BATCH_MATCH = "MANY_TO_ONE_BATCH_MATCH"
    TERMINAL_RESOLUTION_EVIDENCE_MATCHED = "TERMINAL_RESOLUTION_EVIDENCE_MATCHED"
    AWAITING_TERMINAL_OUTCOME = "AWAITING_TERMINAL_OUTCOME"


DEFAULT_RULE_VERSION = "v1.0.0"


@dataclass(frozen=True)
class ReconciliationRunRecord:
    """Execution record for a deterministic reconciliation run."""

    id: str
    organization_id: str
    rule_version: str
    status: str  # PENDING, COMPLETED, FAILED
    as_of_date: str
    summary_counts_json: str | None
    started_at: str
    completed_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReconciliationResultRecord:
    """Detailed reconciliation result and evidence for a transaction cluster or scenario."""

    id: str
    run_id: str
    organization_id: str
    scenario_id: str | None
    status: str
    reason_code: str
    rule_version: str
    collected_amount: Decimal
    settled_amount: Decimal
    bank_credited_amount: Decimal
    discrepancy_amount: Decimal
    currency: str
    input_record_ids_json: str
    matched_record_ids_json: str
    evidence_json: str
    explanation: str
    case_needed: bool
    requires_approval: bool
    evaluated_at: str

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["collected_amount"] = format_money(self.collected_amount)
        d["settled_amount"] = format_money(self.settled_amount)
        d["bank_credited_amount"] = format_money(self.bank_credited_amount)
        d["discrepancy_amount"] = format_money(self.discrepancy_amount)
        return d
