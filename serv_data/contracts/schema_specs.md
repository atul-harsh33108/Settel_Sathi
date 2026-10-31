# SettleSaathi Fixture Schema Specifications

**Document Version:** 1.0  
**Status:** Approved Release 0 Contract  
**Target Release:** Release 0  
**Dataset Version:** `v1`

This document defines the strict schema specifications, column orders, types, serialization rules, and compatibility policies for all Release 0 source fixtures.

---

## 1. Schema Specifications

### 1.1 `transactions.csv`
Captures point-of-sale and online customer collections.

**Header Specification:**
```csv
provider,provider_transaction_id,merchant_reference,store_id,occurred_at,status,payment_method,gross_amount,currency
```

| Column | Type | Format / Example | Validation Rule |
| :--- | :--- | :--- | :--- |
| `provider` | `string` | `PAYTM_MOCK` | Matches known provider code. |
| `provider_transaction_id` | `string` | `mock_txn_001` | Non-empty, unique across file. |
| `merchant_reference` | `string` | `mock_ord_001` | Non-empty. |
| `store_id` | `string` | `store_indiranagar` | Matches registered merchant store ID. |
| `occurred_at` | `ISO 8601 UTC` | `2026-10-29T10:15:30Z` | Valid UTC datetime string. |
| `status` | `string` | `SUCCESS` | One of: `SUCCESS`, `FAILED`, `REFUNDED`. |
| `payment_method` | `string` | `UPI` | One of: `UPI`, `CARD`, `NET_BANKING`. |
| `gross_amount` | `Decimal` | `1500.00` | Exactly 2 decimal places, > 0.00. |
| `currency` | `string` | `INR` | ISO 4217 code, exactly `INR`. |

---

### 1.2 `settlements.csv`
Captures provider settlement payouts compiling collections into net bank transfers.

**Header Specification:**
```csv
provider,provider_settlement_id,payout_reference,settlement_date,reported_status,gross_amount,fee_amount,tax_amount,adjustment_amount,net_amount,currency
```

| Column | Type | Format / Example | Validation Rule |
| :--- | :--- | :--- | :--- |
| `provider` | `string` | `PAYTM_MOCK` | Matches known provider code. |
| `provider_settlement_id` | `string` | `mock_settle_001` | Non-empty, unique across file. |
| `payout_reference` | `string` | `mock_utr_001` | Non-empty UTR or payout tracking ref. |
| `settlement_date` | `ISO 8601 Date`| `2026-10-30` | Valid date `YYYY-MM-DD`. |
| `reported_status` | `string` | `PROCESSED` | One of: `PROCESSED`, `PENDING`, `FAILED`. |
| `gross_amount` | `Decimal` | `18450.00` | Exactly 2 decimal places, > 0.00. |
| `fee_amount` | `Decimal` | `0.00` | Exactly 2 decimal places, >= 0.00. |
| `tax_amount` | `Decimal` | `0.00` | Exactly 2 decimal places, >= 0.00. |
| `adjustment_amount` | `Decimal` | `0.00` | Exactly 2 decimal places (+ or -). |
| `net_amount` | `Decimal` | `18450.00` | Must equal `gross - fee - tax + adjustment`. |
| `currency` | `string` | `INR` | Exactly `INR`. |

---

### 1.3 `settlement_line_items.csv`
Line-item reconciliation records linking settlement batches to transactions and adjustments.

**Header Specification:**
```csv
provider_settlement_id,line_item_id,source_reference,line_type,amount,currency
```

| Column | Type | Format / Example | Validation Rule |
| :--- | :--- | :--- | :--- |
| `provider_settlement_id` | `string` | `mock_settle_001` | Must exist in `settlements.csv`. |
| `line_item_id` | `string` | `mock_line_001` | Non-empty, unique across file. |
| `source_reference` | `string` | `mock_txn_001` | Must match transaction ID or adjustment ref. |
| `line_type` | `string` | `PAYMENT` | One of: `PAYMENT`, `REFUND`, `DISPUTE_HOLD`, `ADJUSTMENT`. |
| `amount` | `Decimal` | `1500.00` | Exactly 2 decimal places. |
| `currency` | `string` | `INR` | Exactly `INR`. |

---

### 1.4 `bank_statement.csv`
Authoritative credit/debit records from the merchant's business bank account.

**Header Specification:**
```csv
statement_entry_id,bank_account_alias,booking_date,direction,amount,currency,narration,utr_reference
```

| Column | Type | Format / Example | Validation Rule |
| :--- | :--- | :--- | :--- |
| `statement_entry_id` | `string` | `mock_bank_001` | Non-empty, unique across file. |
| `bank_account_alias` | `string` | `bank_acc_4092` | Registered demo bank account alias. |
| `booking_date` | `ISO 8601 Date`| `2026-10-30` | Valid date `YYYY-MM-DD`. |
| `direction` | `string` | `CREDIT` | One of: `CREDIT`, `DEBIT`. |
| `amount` | `Decimal` | `12500.00` | Exactly 2 decimal places, > 0.00. |
| `currency` | `string` | `INR` | Exactly `INR`. |
| `narration` | `string` | `NEFT-PAYTM-mock_utr_001` | Standard bank narration line. |
| `utr_reference` | `string` | `mock_utr_001` | Matched payout reference or UTR. |

---

### 1.5 `mock_support_updates.json`
Array of JSON objects simulating asynchronous support desk updates:

```json
[
  {
    "case_reference": "mock_case_scn02_001",
    "event_at": "2026-10-31T04:30:00Z",
    "status": "IN_REVIEW",
    "summary": "Paytm mock support acknowledged ticket; banking partner tracing UTR.",
    "terminal_outcome": false,
    "evidence_reference": "mock_ticket_ack_88421"
  }
]
```

---

### 1.6 `expected_results.json`
The deterministic test oracle defining expected outcomes per scenario:

```json
{
  "dataset_version": "v1",
  "as_of_timestamp": "2026-10-30T18:30:00Z",
  "scenarios": {
    "SCN-01": {
      "name": "Standard Reconciliation",
      "expected_status": "RECONCILED",
      "reason_code": "MATCHED_PAYOUT_TO_BANK",
      "expected_collected_amount": "12500.00",
      "expected_settled_amount": "12500.00",
      "expected_bank_credit": "12500.00",
      "expected_case_needed": false
    },
    "SCN-02": {
      "name": "Missing Settlement (Hero Demo)",
      "expected_status": "UNMATCHED",
      "reason_code": "SETTLEMENT_ABSENT_FROM_BANK",
      "expected_collected_amount": "18450.00",
      "expected_settled_amount": "18450.00",
      "expected_bank_credit": "0.00",
      "expected_case_needed": true,
      "requires_approval": true,
      "case_status": "AWAITING_APPROVAL"
    }
  }
}
```

---

### 1.7 `manifest.json`
Package manifest with integrity verification checksums:

```json
{
  "dataset_version": "v1",
  "schema_version": "1.0",
  "seed": 42,
  "as_of_timestamp": "2026-10-30T18:30:00Z",
  "generated_at": "2026-10-31T12:00:00Z",
  "scenarios": ["SCN-01", "SCN-02", "SCN-03", "SCN-04", "SCN-05", "SCN-06", "SCN-07", "SCN-08", "SCN-09", "SCN-10"],
  "record_counts": {
    "transactions": 25,
    "settlements": 9,
    "settlement_line_items": 26,
    "bank_entries": 8,
    "mock_support_updates": 3
  },
  "files": {
    "transactions.csv": {
      "sha256": "...",
      "size_bytes": 1420
    }
  }
}
```

---

## 2. Compatibility & Versioning Policy

1. **Semantic Versioning:** Dataset schemas follow `v<Major>` versioning. Breaking column additions, removals, or type changes require incrementing to `v2`.
2. **Backward Compatibility:** Parsers must reject unknown schemas and validate the `schema_version` in `manifest.json`.
3. **Immutability of Released Versions:** Once a version (e.g. `v1`) is marked `Done` in `docs/data/TRACKER.md`, its contents cannot be altered without bumping the version or publishing a documented revision.

