"""Canonical data models and serialization for SettleSaathi synthetic fixtures."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Dict, Any


def format_money(val: Decimal) -> str:
    """Format decimal money to exact two decimal places."""
    return f"{val:.2f}"


@dataclass(frozen=True)
class CanonicalTransaction:
    """Represents a collected payment transaction."""
    provider: str
    provider_transaction_id: str
    merchant_reference: str
    store_id: str
    occurred_at: str
    status: str
    payment_method: str
    gross_amount: Decimal
    currency: str = "INR"

    def to_csv_row(self) -> Dict[str, str]:
        return {
            "provider": self.provider,
            "provider_transaction_id": self.provider_transaction_id,
            "merchant_reference": self.merchant_reference,
            "store_id": self.store_id,
            "occurred_at": self.occurred_at,
            "status": self.status,
            "payment_method": self.payment_method,
            "gross_amount": format_money(self.gross_amount),
            "currency": self.currency,
        }


@dataclass(frozen=True)
class CanonicalSettlement:
    """Represents a provider settlement payout batch."""
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
    currency: str = "INR"

    def to_csv_row(self) -> Dict[str, str]:
        return {
            "provider": self.provider,
            "provider_settlement_id": self.provider_settlement_id,
            "payout_reference": self.payout_reference,
            "settlement_date": self.settlement_date,
            "reported_status": self.reported_status,
            "gross_amount": format_money(self.gross_amount),
            "fee_amount": format_money(self.fee_amount),
            "tax_amount": format_money(self.tax_amount),
            "adjustment_amount": format_money(self.adjustment_amount),
            "net_amount": format_money(self.net_amount),
            "currency": self.currency,
        }


@dataclass(frozen=True)
class CanonicalSettlementLineItem:
    """Represents an itemized line entry within a settlement payout batch."""
    provider_settlement_id: str
    line_item_id: str
    source_reference: str
    line_type: str
    amount: Decimal
    currency: str = "INR"

    def to_csv_row(self) -> Dict[str, str]:
        return {
            "provider_settlement_id": self.provider_settlement_id,
            "line_item_id": self.line_item_id,
            "source_reference": self.source_reference,
            "line_type": self.line_type,
            "amount": format_money(self.amount),
            "currency": self.currency,
        }


@dataclass(frozen=True)
class CanonicalBankEntry:
    """Represents an entry on the merchant's official bank statement."""
    statement_entry_id: str
    bank_account_alias: str
    booking_date: str
    direction: str
    amount: Decimal
    currency: str
    narration: str
    utr_reference: str

    def to_csv_row(self) -> Dict[str, str]:
        return {
            "statement_entry_id": self.statement_entry_id,
            "bank_account_alias": self.bank_account_alias,
            "booking_date": self.booking_date,
            "direction": self.direction,
            "amount": format_money(self.amount),
            "currency": self.currency,
            "narration": self.narration,
            "utr_reference": self.utr_reference,
        }


@dataclass(frozen=True)
class CanonicalSupportUpdate:
    """Represents an update or terminal outcome from the mock support connector."""
    case_reference: str
    event_at: str
    status: str
    summary: str
    terminal_outcome: bool
    evidence_reference: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_reference": self.case_reference,
            "event_at": self.event_at,
            "status": self.status,
            "summary": self.summary,
            "terminal_outcome": self.terminal_outcome,
            "evidence_reference": self.evidence_reference,
        }


@dataclass(frozen=True)
class ScenarioOracle:
    """Test oracle assertion for a specific scenario."""
    scenario_id: str
    name: str
    description: str
    expected_status: str
    reason_code: str
    expected_collected_amount: Decimal
    expected_settled_amount: Decimal
    expected_bank_credit: Decimal
    expected_case_needed: bool
    requires_approval: bool
    terminal_outcome: Optional[bool]
    contributing_transaction_ids: list
    contributing_settlement_ids: list
    contributing_bank_entry_ids: list

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "expected_status": self.expected_status,
            "reason_code": self.reason_code,
            "expected_collected_amount": format_money(self.expected_collected_amount),
            "expected_settled_amount": format_money(self.expected_settled_amount),
            "expected_bank_credit": format_money(self.expected_bank_credit),
            "expected_case_needed": self.expected_case_needed,
            "requires_approval": self.requires_approval,
            "terminal_outcome": self.terminal_outcome,
            "contributing_transaction_ids": self.contributing_transaction_ids,
            "contributing_settlement_ids": self.contributing_settlement_ids,
            "contributing_bank_entry_ids": self.contributing_bank_entry_ids,
        }

