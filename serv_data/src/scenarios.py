"""Scenario definitions (SCN-01 to SCN-10) for SettleSaathi synthetic generation."""

from decimal import Decimal
from typing import List, Tuple, Dict
from serv_data.src.constants import (
    PROVIDER_CODE,
    STORE_INDIRANAGAR,
    STORE_KORAMANGALA,
    BANK_ACCOUNT_ALIAS,
    CURRENCY_INR,
)
from serv_data.src.models import (
    CanonicalTransaction,
    CanonicalSettlement,
    CanonicalSettlementLineItem,
    CanonicalBankEntry,
    CanonicalSupportUpdate,
    ScenarioOracle,
)


def build_scenarios() -> Tuple[
    List[CanonicalTransaction],
    List[CanonicalSettlement],
    List[CanonicalSettlementLineItem],
    List[CanonicalBankEntry],
    List[CanonicalSupportUpdate],
    Dict[str, ScenarioOracle],
]:
    """Build all synthetic records and the test oracle for SCN-01 through SCN-10."""
    transactions: List[CanonicalTransaction] = []
    settlements: List[CanonicalSettlement] = []
    line_items: List[CanonicalSettlementLineItem] = []
    bank_entries: List[CanonicalBankEntry] = []
    support_updates: List[CanonicalSupportUpdate] = []
    oracle: Dict[str, ScenarioOracle] = {}

    # =========================================================================
    # SCN-01: Standard Reconciliation (Happy Path)
    # Total: ₹12,500.00 fully matched from Txn -> Settlement -> Bank Credit
    # =========================================================================
    t1 = CanonicalTransaction(
        provider=PROVIDER_CODE,
        provider_transaction_id="mock_txn_scn01_001",
        merchant_reference="mock_ord_scn01_001",
        store_id=STORE_INDIRANAGAR,
        occurred_at="2026-10-28T09:30:00Z",
        status="SUCCESS",
        payment_method="UPI",
        gross_amount=Decimal("5000.00"),
    )
    t2 = CanonicalTransaction(
        provider=PROVIDER_CODE,
        provider_transaction_id="mock_txn_scn01_002",
        merchant_reference="mock_ord_scn01_002",
        store_id=STORE_INDIRANAGAR,
        occurred_at="2026-10-28T11:45:00Z",
        status="SUCCESS",
        payment_method="UPI",
        gross_amount=Decimal("4500.00"),
    )
    t3 = CanonicalTransaction(
        provider=PROVIDER_CODE,
        provider_transaction_id="mock_txn_scn01_003",
        merchant_reference="mock_ord_scn01_003",
        store_id=STORE_INDIRANAGAR,
        occurred_at="2026-10-28T14:15:00Z",
        status="SUCCESS",
        payment_method="CARD",
        gross_amount=Decimal("3000.00"),
    )
    transactions.extend([t1, t2, t3])

    s1 = CanonicalSettlement(
        provider=PROVIDER_CODE,
        provider_settlement_id="mock_settle_scn01_001",
        payout_reference="mock_utr_scn01_001",
        settlement_date="2026-10-28",
        reported_status="PROCESSED",
        gross_amount=Decimal("12500.00"),
        fee_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        adjustment_amount=Decimal("0.00"),
        net_amount=Decimal("12500.00"),
    )
    settlements.append(s1)

    line_items.extend([
        CanonicalSettlementLineItem(
            provider_settlement_id="mock_settle_scn01_001",
            line_item_id="mock_line_scn01_001",
            source_reference="mock_txn_scn01_001",
            line_type="PAYMENT",
            amount=Decimal("5000.00"),
        ),
        CanonicalSettlementLineItem(
            provider_settlement_id="mock_settle_scn01_001",
            line_item_id="mock_line_scn01_002",
            source_reference="mock_txn_scn01_002",
            line_type="PAYMENT",
            amount=Decimal("4500.00"),
        ),
        CanonicalSettlementLineItem(
            provider_settlement_id="mock_settle_scn01_001",
            line_item_id="mock_line_scn01_003",
            source_reference="mock_txn_scn01_003",
            line_type="PAYMENT",
            amount=Decimal("3000.00"),
        ),
    ])

    b1 = CanonicalBankEntry(
        statement_entry_id="mock_bank_scn01_001",
        bank_account_alias=BANK_ACCOUNT_ALIAS,
        booking_date="2026-10-29",
        direction="CREDIT",
        amount=Decimal("12500.00"),
        currency=CURRENCY_INR,
        narration="NEFT-PAYTM-mock_utr_scn01_001",
        utr_reference="mock_utr_scn01_001",
    )
    bank_entries.append(b1)

    oracle["SCN-01"] = ScenarioOracle(
        scenario_id="SCN-01",
        name="Standard Reconciliation",
        description="Transactions fully settled by provider and confirmed credited in bank statement.",
        expected_status="RECONCILED",
        reason_code="MATCHED_PAYOUT_TO_BANK",
        expected_collected_amount=Decimal("12500.00"),
        expected_settled_amount=Decimal("12500.00"),
        expected_bank_credit=Decimal("12500.00"),
        expected_case_needed=False,
        requires_approval=False,
        terminal_outcome=True,
        contributing_transaction_ids=[t1.provider_transaction_id, t2.provider_transaction_id, t3.provider_transaction_id],
        contributing_settlement_ids=[s1.provider_settlement_id],
        contributing_bank_entry_ids=[b1.statement_entry_id],
    )

    # =========================================================================
    # SCN-02: Missing Settlement (Hero Hackathon Demo)
    # Total: ₹18,450.00 collected & reported settled, but absent from bank!
    # =========================================================================
    t2_1 = CanonicalTransaction(
        provider=PROVIDER_CODE,
        provider_transaction_id="mock_txn_scn02_001",
        merchant_reference="mock_ord_scn02_001",
        store_id=STORE_KORAMANGALA,
        occurred_at="2026-10-29T10:00:00Z",
        status="SUCCESS",
        payment_method="UPI",
        gross_amount=Decimal("6000.00"),
    )
    t2_2 = CanonicalTransaction(
        provider=PROVIDER_CODE,
        provider_transaction_id="mock_txn_scn02_002",
        merchant_reference="mock_ord_scn02_002",
        store_id=STORE_KORAMANGALA,
        occurred_at="2026-10-29T13:20:00Z",
        status="SUCCESS",
        payment_method="UPI",
        gross_amount=Decimal("4450.00"),
    )
    t2_3 = CanonicalTransaction(
        provider=PROVIDER_CODE,
        provider_transaction_id="mock_txn_scn02_003",
        merchant_reference="mock_ord_scn02_003",
        store_id=STORE_KORAMANGALA,
        occurred_at="2026-10-29T15:40:00Z",
        status="SUCCESS",
        payment_method="CARD",
        gross_amount=Decimal("5000.00"),
    )
    t2_4 = CanonicalTransaction(
        provider=PROVIDER_CODE,
        provider_transaction_id="mock_txn_scn02_004",
        merchant_reference="mock_ord_scn02_004",
        store_id=STORE_KORAMANGALA,
        occurred_at="2026-10-29T18:10:00Z",
        status="SUCCESS",
        payment_method="UPI",
        gross_amount=Decimal("3000.00"),
    )
    transactions.extend([t2_1, t2_2, t2_3, t2_4])

    s2 = CanonicalSettlement(
        provider=PROVIDER_CODE,
        provider_settlement_id="mock_settle_scn02_001",
        payout_reference="mock_utr_scn02_999",
        settlement_date="2026-10-30",
        reported_status="PROCESSED",
        gross_amount=Decimal("18450.00"),
        fee_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        adjustment_amount=Decimal("0.00"),
        net_amount=Decimal("18450.00"),
    )
    settlements.append(s2)

    line_items.extend([
        CanonicalSettlementLineItem(
            provider_settlement_id="mock_settle_scn02_001",
            line_item_id="mock_line_scn02_001",
            source_reference="mock_txn_scn02_001",
            line_type="PAYMENT",
            amount=Decimal("6000.00"),
        ),
        CanonicalSettlementLineItem(
            provider_settlement_id="mock_settle_scn02_001",
            line_item_id="mock_line_scn02_002",
            source_reference="mock_txn_scn02_002",
            line_type="PAYMENT",
            amount=Decimal("4450.00"),
        ),
        CanonicalSettlementLineItem(
            provider_settlement_id="mock_settle_scn02_001",
            line_item_id="mock_line_scn02_003",
            source_reference="mock_txn_scn02_003",
            line_type="PAYMENT",
            amount=Decimal("5000.00"),
        ),
        CanonicalSettlementLineItem(
            provider_settlement_id="mock_settle_scn02_001",
            line_item_id="mock_line_scn02_004",
            source_reference="mock_txn_scn02_004",
            line_type="PAYMENT",
            amount=Decimal("3000.00"),
        ),
    ])

    # NOTE: In SCN-02, bank entry is deliberately absent!
    oracle["SCN-02"] = ScenarioOracle(
        scenario_id="SCN-02",
        name="Missing Settlement (Hero Demo)",
        description="Transactions totalling ₹18,450 reported settled by provider under UTR mock_utr_scn02_999, but no credit appears in bank statement.",
        expected_status="UNMATCHED",
        reason_code="SETTLEMENT_ABSENT_FROM_BANK",
        expected_collected_amount=Decimal("18450.00"),
        expected_settled_amount=Decimal("18450.00"),
        expected_bank_credit=Decimal("0.00"),
        expected_case_needed=True,
        requires_approval=True,
        terminal_outcome=None,
        contributing_transaction_ids=[t2_1.provider_transaction_id, t2_2.provider_transaction_id, t2_3.provider_transaction_id, t2_4.provider_transaction_id],
        contributing_settlement_ids=[s2.provider_settlement_id],
        contributing_bank_entry_ids=[],
    )

    # =========================================================================
    # SCN-03: Within Expected Window (In-Flight Settlement)
    # Total: ₹8,200.00 settled on as-of date (T+0), bank credit expected T+1
    # =========================================================================
    t3_1 = CanonicalTransaction(
        provider=PROVIDER_CODE,
        provider_transaction_id="mock_txn_scn03_001",
        merchant_reference="mock_ord_scn03_001",
        store_id=STORE_INDIRANAGAR,
        occurred_at="2026-10-30T10:00:00Z",
        status="SUCCESS",
        payment_method="UPI",
        gross_amount=Decimal("5200.00"),
    )
    t3_2 = CanonicalTransaction(
        provider=PROVIDER_CODE,
        provider_transaction_id="mock_txn_scn03_002",
        merchant_reference="mock_ord_scn03_002",
        store_id=STORE_INDIRANAGAR,
        occurred_at="2026-10-30T14:00:00Z",
        status="SUCCESS",
        payment_method="NET_BANKING",
        gross_amount=Decimal("3000.00"),
    )
    transactions.extend([t3_1, t3_2])

    s3 = CanonicalSettlement(
        provider=PROVIDER_CODE,
        provider_settlement_id="mock_settle_scn03_001",
        payout_reference="mock_utr_scn03_001",
        settlement_date="2026-10-30",
        reported_status="PROCESSED",
        gross_amount=Decimal("8200.00"),
        fee_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        adjustment_amount=Decimal("0.00"),
        net_amount=Decimal("8200.00"),
    )
    settlements.append(s3)

    line_items.extend([
        CanonicalSettlementLineItem(
            provider_settlement_id="mock_settle_scn03_001",
            line_item_id="mock_line_scn03_001",
            source_reference="mock_txn_scn03_001",
            line_type="PAYMENT",
            amount=Decimal("5200.00"),
        ),
        CanonicalSettlementLineItem(
            provider_settlement_id="mock_settle_scn03_001",
            line_item_id="mock_line_scn03_002",
            source_reference="mock_txn_scn03_002",
            line_type="PAYMENT",
            amount=Decimal("3000.00"),
        ),
    ])

    oracle["SCN-03"] = ScenarioOracle(
        scenario_id="SCN-03",
        name="Within Expected Window",
        description="Settlement initiated recently; within allowed banking window (T+1). Do not open case.",
        expected_status="WITHIN_EXPECTED_WINDOW",
        reason_code="SETTLEMENT_IN_FLIGHT_WINDOW",
        expected_collected_amount=Decimal("8200.00"),
        expected_settled_amount=Decimal("8200.00"),
        expected_bank_credit=Decimal("0.00"),
        expected_case_needed=False,
        requires_approval=False,
        terminal_outcome=None,
        contributing_transaction_ids=[t3_1.provider_transaction_id, t3_2.provider_transaction_id],
        contributing_settlement_ids=[s3.provider_settlement_id],
        contributing_bank_entry_ids=[],
    )

    # =========================================================================
    # SCN-04: Partial Match
    # Total expected: ₹5,000.00; Settlement batch only includes ₹3,500.00 (residual ₹1,500.00)
    # =========================================================================
    t4_1 = CanonicalTransaction(
        provider=PROVIDER_CODE,
        provider_transaction_id="mock_txn_scn04_001",
        merchant_reference="mock_ord_scn04_001",
        store_id=STORE_KORAMANGALA,
        occurred_at="2026-10-27T08:00:00Z",
        status="SUCCESS",
        payment_method="UPI",
        gross_amount=Decimal("3500.00"),
    )
    t4_2 = CanonicalTransaction(
        provider=PROVIDER_CODE,
        provider_transaction_id="mock_txn_scn04_002",
        merchant_reference="mock_ord_scn04_002",
        store_id=STORE_KORAMANGALA,
        occurred_at="2026-10-27T09:30:00Z",
        status="SUCCESS",
        payment_method="UPI",
        gross_amount=Decimal("1500.00"),
    )
    transactions.extend([t4_1, t4_2])

    s4 = CanonicalSettlement(
        provider=PROVIDER_CODE,
        provider_settlement_id="mock_settle_scn04_001",
        payout_reference="mock_utr_scn04_001",
        settlement_date="2026-10-28",
        reported_status="PROCESSED",
        gross_amount=Decimal("3500.00"),
        fee_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        adjustment_amount=Decimal("0.00"),
        net_amount=Decimal("3500.00"),
    )
    settlements.append(s4)

    line_items.append(
        CanonicalSettlementLineItem(
            provider_settlement_id="mock_settle_scn04_001",
            line_item_id="mock_line_scn04_001",
            source_reference="mock_txn_scn04_001",
            line_type="PAYMENT",
            amount=Decimal("3500.00"),
        )
    )

    b4 = CanonicalBankEntry(
        statement_entry_id="mock_bank_scn04_001",
        bank_account_alias=BANK_ACCOUNT_ALIAS,
        booking_date="2026-10-28",
        direction="CREDIT",
        amount=Decimal("3500.00"),
        currency=CURRENCY_INR,
        narration="NEFT-PAYTM-mock_utr_scn04_001",
        utr_reference="mock_utr_scn04_001",
    )
    bank_entries.append(b4)

    oracle["SCN-04"] = ScenarioOracle(
        scenario_id="SCN-04",
        name="Partial Match",
        description="Transactions total ₹5,000, but settlement batch only included ₹3,500; ₹1,500 residual pending.",
        expected_status="PARTIALLY_MATCHED",
        reason_code="PARTIAL_SETTLEMENT_BATCH",
        expected_collected_amount=Decimal("5000.00"),
        expected_settled_amount=Decimal("3500.00"),
        expected_bank_credit=Decimal("3500.00"),
        expected_case_needed=True,
        requires_approval=True,
        terminal_outcome=None,
        contributing_transaction_ids=[t4_1.provider_transaction_id, t4_2.provider_transaction_id],
        contributing_settlement_ids=[s4.provider_settlement_id],
        contributing_bank_entry_ids=[b4.statement_entry_id],
    )

    # =========================================================================
    # SCN-05: Adjustment / Fee Explained
    # Gross: ₹10,000.00, Fee: ₹150.00, Tax: ₹27.00, Adj: -₹200.00 -> Net: ₹9,623.00
    # =========================================================================
    t5_1 = CanonicalTransaction(
        provider=PROVIDER_CODE,
        provider_transaction_id="mock_txn_scn05_001",
        merchant_reference="mock_ord_scn05_001",
        store_id=STORE_INDIRANAGAR,
        occurred_at="2026-10-28T16:00:00Z",
        status="SUCCESS",
        payment_method="CARD",
        gross_amount=Decimal("6000.00"),
    )
    t5_2 = CanonicalTransaction(
        provider=PROVIDER_CODE,
        provider_transaction_id="mock_txn_scn05_002",
        merchant_reference="mock_ord_scn05_002",
        store_id=STORE_INDIRANAGAR,
        occurred_at="2026-10-28T17:30:00Z",
        status="SUCCESS",
        payment_method="UPI",
        gross_amount=Decimal("4000.00"),
    )
    transactions.extend([t5_1, t5_2])

    s5 = CanonicalSettlement(
        provider=PROVIDER_CODE,
        provider_settlement_id="mock_settle_scn05_001",
        payout_reference="mock_utr_scn05_001",
        settlement_date="2026-10-29",
        reported_status="PROCESSED",
        gross_amount=Decimal("10000.00"),
        fee_amount=Decimal("150.00"),
        tax_amount=Decimal("27.00"),
        adjustment_amount=Decimal("-200.00"),
        net_amount=Decimal("9623.00"),
    )
    settlements.append(s5)

    line_items.extend([
        CanonicalSettlementLineItem(
            provider_settlement_id="mock_settle_scn05_001",
            line_item_id="mock_line_scn05_001",
            source_reference="mock_txn_scn05_001",
            line_type="PAYMENT",
            amount=Decimal("6000.00"),
        ),
        CanonicalSettlementLineItem(
            provider_settlement_id="mock_settle_scn05_001",
            line_item_id="mock_line_scn05_002",
            source_reference="mock_txn_scn05_002",
            line_type="PAYMENT",
            amount=Decimal("4000.00"),
        ),
        CanonicalSettlementLineItem(
            provider_settlement_id="mock_settle_scn05_001",
            line_item_id="mock_line_scn05_adj",
            source_reference="mock_adj_dispute_001",
            line_type="ADJUSTMENT",
            amount=Decimal("-200.00"),
        ),
    ])

    b5 = CanonicalBankEntry(
        statement_entry_id="mock_bank_scn05_001",
        bank_account_alias=BANK_ACCOUNT_ALIAS,
        booking_date="2026-10-29",
        direction="CREDIT",
        amount=Decimal("9623.00"),
        currency=CURRENCY_INR,
        narration="NEFT-PAYTM-mock_utr_scn05_001",
        utr_reference="mock_utr_scn05_001",
    )
    bank_entries.append(b5)

    oracle["SCN-05"] = ScenarioOracle(
        scenario_id="SCN-05",
        name="Adjustment Explained",
        description="Gross collections ₹10,000 reduced by fees (₹150), taxes (₹27), and chargeback adjustment (-₹200) yielding exact ₹9,623 bank credit.",
        expected_status="ADJUSTMENT_EXPLAINED",
        reason_code="DEDUCTIONS_MATCH_POLICY",
        expected_collected_amount=Decimal("10000.00"),
        expected_settled_amount=Decimal("9623.00"),
        expected_bank_credit=Decimal("9623.00"),
        expected_case_needed=False,
        requires_approval=False,
        terminal_outcome=True,
        contributing_transaction_ids=[t5_1.provider_transaction_id, t5_2.provider_transaction_id],
        contributing_settlement_ids=[s5.provider_settlement_id],
        contributing_bank_entry_ids=[b5.statement_entry_id],
    )

    # =========================================================================
    # SCN-06: Duplicate Transaction Row
    # Duplicate transaction row imported with identical ID; deduplication test
    # =========================================================================
    t6_1 = CanonicalTransaction(
        provider=PROVIDER_CODE,
        provider_transaction_id="mock_txn_scn06_001",
        merchant_reference="mock_ord_scn06_001",
        store_id=STORE_KORAMANGALA,
        occurred_at="2026-10-28T12:00:00Z",
        status="SUCCESS",
        payment_method="UPI",
        gross_amount=Decimal("2500.00"),
    )
    # The duplicate record has same transaction ID
    t6_dup = CanonicalTransaction(
        provider=PROVIDER_CODE,
        provider_transaction_id="mock_txn_scn06_001",
        merchant_reference="mock_ord_scn06_001",
        store_id=STORE_KORAMANGALA,
        occurred_at="2026-10-28T12:00:00Z",
        status="SUCCESS",
        payment_method="UPI",
        gross_amount=Decimal("2500.00"),
    )
    transactions.extend([t6_1, t6_dup])

    s6 = CanonicalSettlement(
        provider=PROVIDER_CODE,
        provider_settlement_id="mock_settle_scn06_001",
        payout_reference="mock_utr_scn06_001",
        settlement_date="2026-10-29",
        reported_status="PROCESSED",
        gross_amount=Decimal("2500.00"),
        fee_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        adjustment_amount=Decimal("0.00"),
        net_amount=Decimal("2500.00"),
    )
    settlements.append(s6)

    line_items.append(
        CanonicalSettlementLineItem(
            provider_settlement_id="mock_settle_scn06_001",
            line_item_id="mock_line_scn06_001",
            source_reference="mock_txn_scn06_001",
            line_type="PAYMENT",
            amount=Decimal("2500.00"),
        )
    )

    b6 = CanonicalBankEntry(
        statement_entry_id="mock_bank_scn06_001",
        bank_account_alias=BANK_ACCOUNT_ALIAS,
        booking_date="2026-10-29",
        direction="CREDIT",
        amount=Decimal("2500.00"),
        currency=CURRENCY_INR,
        narration="NEFT-PAYTM-mock_utr_scn06_001",
        utr_reference="mock_utr_scn06_001",
    )
    bank_entries.append(b6)

    oracle["SCN-06"] = ScenarioOracle(
        scenario_id="SCN-06",
        name="Duplicate Transaction",
        description="Duplicate transaction row detected and safely excluded from net settlement totals.",
        expected_status="DUPLICATE",
        reason_code="DUPLICATE_SOURCE_RECORD_DETECTED",
        expected_collected_amount=Decimal("2500.00"),
        expected_settled_amount=Decimal("2500.00"),
        expected_bank_credit=Decimal("2500.00"),
        expected_case_needed=False,
        requires_approval=False,
        terminal_outcome=True,
        contributing_transaction_ids=[t6_1.provider_transaction_id],
        contributing_settlement_ids=[s6.provider_settlement_id],
        contributing_bank_entry_ids=[b6.statement_entry_id],
    )

    # =========================================================================
    # SCN-07: Refund / Reversal Linked
    # Customer paid ₹2,100, then refunded ₹2,100; net settlement ₹0.00
    # =========================================================================
    t7_1 = CanonicalTransaction(
        provider=PROVIDER_CODE,
        provider_transaction_id="mock_txn_scn07_001",
        merchant_reference="mock_ord_scn07_001",
        store_id=STORE_INDIRANAGAR,
        occurred_at="2026-10-27T10:00:00Z",
        status="REFUNDED",
        payment_method="UPI",
        gross_amount=Decimal("2100.00"),
    )
    transactions.append(t7_1)

    s7 = CanonicalSettlement(
        provider=PROVIDER_CODE,
        provider_settlement_id="mock_settle_scn07_001",
        payout_reference="mock_utr_scn07_001",
        settlement_date="2026-10-28",
        reported_status="PROCESSED",
        gross_amount=Decimal("2100.00"),
        fee_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        adjustment_amount=Decimal("-2100.00"),
        net_amount=Decimal("0.00"),
    )
    settlements.append(s7)

    line_items.extend([
        CanonicalSettlementLineItem(
            provider_settlement_id="mock_settle_scn07_001",
            line_item_id="mock_line_scn07_001",
            source_reference="mock_txn_scn07_001",
            line_type="PAYMENT",
            amount=Decimal("2100.00"),
        ),
        CanonicalSettlementLineItem(
            provider_settlement_id="mock_settle_scn07_001",
            line_item_id="mock_line_scn07_002",
            source_reference="mock_txn_scn07_001",
            line_type="REFUND",
            amount=Decimal("-2100.00"),
        ),
    ])

    oracle["SCN-07"] = ScenarioOracle(
        scenario_id="SCN-07",
        name="Refund / Reversal Linked",
        description="Sale refunded before settlement; net payout ₹0.00 accurately reconciled.",
        expected_status="RECONCILED",
        reason_code="REFUND_BALANCED",
        expected_collected_amount=Decimal("2100.00"),
        expected_settled_amount=Decimal("0.00"),
        expected_bank_credit=Decimal("0.00"),
        expected_case_needed=False,
        requires_approval=False,
        terminal_outcome=True,
        contributing_transaction_ids=[t7_1.provider_transaction_id],
        contributing_settlement_ids=[s7.provider_settlement_id],
        contributing_bank_entry_ids=[],
    )

    # =========================================================================
    # SCN-08: Batching / Many-to-One Bank Credit Match
    # Morning batch (₹6,200.00) + Evening batch (₹4,800.00) = Combined Bank Credit ₹11,000.00
    # =========================================================================
    t8_1 = CanonicalTransaction(
        provider=PROVIDER_CODE,
        provider_transaction_id="mock_txn_scn08_001",
        merchant_reference="mock_ord_scn08_001",
        store_id=STORE_KORAMANGALA,
        occurred_at="2026-10-28T09:00:00Z",
        status="SUCCESS",
        payment_method="UPI",
        gross_amount=Decimal("3200.00"),
    )
    t8_2 = CanonicalTransaction(
        provider=PROVIDER_CODE,
        provider_transaction_id="mock_txn_scn08_002",
        merchant_reference="mock_ord_scn08_002",
        store_id=STORE_KORAMANGALA,
        occurred_at="2026-10-28T11:00:00Z",
        status="SUCCESS",
        payment_method="UPI",
        gross_amount=Decimal("3000.00"),
    )
    t8_3 = CanonicalTransaction(
        provider=PROVIDER_CODE,
        provider_transaction_id="mock_txn_scn08_003",
        merchant_reference="mock_ord_scn08_003",
        store_id=STORE_KORAMANGALA,
        occurred_at="2026-10-28T17:00:00Z",
        status="SUCCESS",
        payment_method="CARD",
        gross_amount=Decimal("4800.00"),
    )
    transactions.extend([t8_1, t8_2, t8_3])

    s8_1 = CanonicalSettlement(
        provider=PROVIDER_CODE,
        provider_settlement_id="mock_settle_scn08_001",
        payout_reference="mock_utr_scn08_comb",
        settlement_date="2026-10-29",
        reported_status="PROCESSED",
        gross_amount=Decimal("6200.00"),
        fee_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        adjustment_amount=Decimal("0.00"),
        net_amount=Decimal("6200.00"),
    )
    s8_2 = CanonicalSettlement(
        provider=PROVIDER_CODE,
        provider_settlement_id="mock_settle_scn08_002",
        payout_reference="mock_utr_scn08_comb",
        settlement_date="2026-10-29",
        reported_status="PROCESSED",
        gross_amount=Decimal("4800.00"),
        fee_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        adjustment_amount=Decimal("0.00"),
        net_amount=Decimal("4800.00"),
    )
    settlements.extend([s8_1, s8_2])

    line_items.extend([
        CanonicalSettlementLineItem(
            provider_settlement_id="mock_settle_scn08_001",
            line_item_id="mock_line_scn08_001",
            source_reference="mock_txn_scn08_001",
            line_type="PAYMENT",
            amount=Decimal("3200.00"),
        ),
        CanonicalSettlementLineItem(
            provider_settlement_id="mock_settle_scn08_001",
            line_item_id="mock_line_scn08_002",
            source_reference="mock_txn_scn08_002",
            line_type="PAYMENT",
            amount=Decimal("3000.00"),
        ),
        CanonicalSettlementLineItem(
            provider_settlement_id="mock_settle_scn08_002",
            line_item_id="mock_line_scn08_003",
            source_reference="mock_txn_scn08_003",
            line_type="PAYMENT",
            amount=Decimal("4800.00"),
        ),
    ])

    b8 = CanonicalBankEntry(
        statement_entry_id="mock_bank_scn08_001",
        bank_account_alias=BANK_ACCOUNT_ALIAS,
        booking_date="2026-10-29",
        direction="CREDIT",
        amount=Decimal("11000.00"),
        currency=CURRENCY_INR,
        narration="NEFT-PAYTM-mock_utr_scn08_comb",
        utr_reference="mock_utr_scn08_comb",
    )
    bank_entries.append(b8)

    oracle["SCN-08"] = ScenarioOracle(
        scenario_id="SCN-08",
        name="Multi-Batch Settlement",
        description="Two settlement batches (₹6,200 and ₹4,800) merged into one combined bank credit of ₹11,000.",
        expected_status="RECONCILED",
        reason_code="MANY_TO_ONE_BATCH_MATCH",
        expected_collected_amount=Decimal("11000.00"),
        expected_settled_amount=Decimal("11000.00"),
        expected_bank_credit=Decimal("11000.00"),
        expected_case_needed=False,
        requires_approval=False,
        terminal_outcome=True,
        contributing_transaction_ids=[t8_1.provider_transaction_id, t8_2.provider_transaction_id, t8_3.provider_transaction_id],
        contributing_settlement_ids=[s8_1.provider_settlement_id, s8_2.provider_settlement_id],
        contributing_bank_entry_ids=[b8.statement_entry_id],
    )

    # =========================================================================
    # SCN-09: Support Terminal Resolution (Authoritative Verification)
    # Support update confirms credit was executed with new UTR; case eligible for verified closure
    # =========================================================================
    t9 = CanonicalTransaction(
        provider=PROVIDER_CODE,
        provider_transaction_id="mock_txn_scn09_001",
        merchant_reference="mock_ord_scn09_001",
        store_id=STORE_INDIRANAGAR,
        occurred_at="2026-10-26T15:00:00Z",
        status="SUCCESS",
        payment_method="UPI",
        gross_amount=Decimal("7500.00"),
    )
    transactions.append(t9)

    s9 = CanonicalSettlement(
        provider=PROVIDER_CODE,
        provider_settlement_id="mock_settle_scn09_001",
        payout_reference="mock_utr_scn09_fail",
        settlement_date="2026-10-27",
        reported_status="PROCESSED",
        gross_amount=Decimal("7500.00"),
        fee_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        adjustment_amount=Decimal("0.00"),
        net_amount=Decimal("7500.00"),
    )
    settlements.append(s9)

    line_items.append(
        CanonicalSettlementLineItem(
            provider_settlement_id="mock_settle_scn09_001",
            line_item_id="mock_line_scn09_001",
            source_reference="mock_txn_scn09_001",
            line_type="PAYMENT",
            amount=Decimal("7500.00"),
        )
    )

    # Bank entry has the re-credited UTR
    b9 = CanonicalBankEntry(
        statement_entry_id="mock_bank_scn09_001",
        bank_account_alias=BANK_ACCOUNT_ALIAS,
        booking_date="2026-10-29",
        direction="CREDIT",
        amount=Decimal("7500.00"),
        currency=CURRENCY_INR,
        narration="NEFT-PAYTM-mock_utr_scn09_recredit",
        utr_reference="mock_utr_scn09_recredit",
    )
    bank_entries.append(b9)

    sup9 = CanonicalSupportUpdate(
        case_reference="mock_case_scn09_001",
        event_at="2026-10-29T16:00:00Z",
        status="RESOLVED",
        summary="Provider confirmed bank re-processed payout under UTR mock_utr_scn09_recredit.",
        terminal_outcome=True,
        evidence_reference="mock_ticket_ack_90412",
    )
    support_updates.append(sup9)

    oracle["SCN-09"] = ScenarioOracle(
        scenario_id="SCN-09",
        name="Support Terminal Resolution",
        description="Provider confirmed payout re-processed; verified by authoritative bank credit under re-credit UTR.",
        expected_status="VERIFIED_RESOLVED",
        reason_code="TERMINAL_RESOLUTION_EVIDENCE_MATCHED",
        expected_collected_amount=Decimal("7500.00"),
        expected_settled_amount=Decimal("7500.00"),
        expected_bank_credit=Decimal("7500.00"),
        expected_case_needed=True,
        requires_approval=True,
        terminal_outcome=True,
        contributing_transaction_ids=[t9.provider_transaction_id],
        contributing_settlement_ids=[s9.provider_settlement_id],
        contributing_bank_entry_ids=[b9.statement_entry_id],
    )

    # =========================================================================
    # SCN-10: Ambiguous / Active Mock Support State
    # Support update is non-terminal / under investigation; cannot be closed!
    # =========================================================================
    t10 = CanonicalTransaction(
        provider=PROVIDER_CODE,
        provider_transaction_id="mock_txn_scn10_001",
        merchant_reference="mock_ord_scn10_001",
        store_id=STORE_KORAMANGALA,
        occurred_at="2026-10-27T11:00:00Z",
        status="SUCCESS",
        payment_method="UPI",
        gross_amount=Decimal("4200.00"),
    )
    transactions.append(t10)

    s10 = CanonicalSettlement(
        provider=PROVIDER_CODE,
        provider_settlement_id="mock_settle_scn10_001",
        payout_reference="mock_utr_scn10_001",
        settlement_date="2026-10-28",
        reported_status="PROCESSED",
        gross_amount=Decimal("4200.00"),
        fee_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        adjustment_amount=Decimal("0.00"),
        net_amount=Decimal("4200.00"),
    )
    settlements.append(s10)

    line_items.append(
        CanonicalSettlementLineItem(
            provider_settlement_id="mock_settle_scn10_001",
            line_item_id="mock_line_scn10_001",
            source_reference="mock_txn_scn10_001",
            line_type="PAYMENT",
            amount=Decimal("4200.00"),
        )
    )

    sup10 = CanonicalSupportUpdate(
        case_reference="mock_case_scn10_001",
        event_at="2026-10-29T14:30:00Z",
        status="IN_REVIEW",
        summary="Provider support ticket active; awaiting nodal bank inquiry response.",
        terminal_outcome=False,
        evidence_reference="mock_ticket_ack_pending",
    )
    support_updates.append(sup10)

    oracle["SCN-10"] = ScenarioOracle(
        scenario_id="SCN-10",
        name="Ambiguous Support State",
        description="Support response is pending and non-terminal; system blocks false closure and keeps case active.",
        expected_status="ESCALATED",
        reason_code="AWAITING_TERMINAL_OUTCOME",
        expected_collected_amount=Decimal("4200.00"),
        expected_settled_amount=Decimal("4200.00"),
        expected_bank_credit=Decimal("0.00"),
        expected_case_needed=True,
        requires_approval=True,
        terminal_outcome=False,
        contributing_transaction_ids=[t10.provider_transaction_id],
        contributing_settlement_ids=[s10.provider_settlement_id],
        contributing_bank_entry_ids=[],
    )

    return transactions, settlements, line_items, bank_entries, support_updates, oracle

