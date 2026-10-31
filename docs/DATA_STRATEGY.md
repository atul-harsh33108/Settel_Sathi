# Data Strategy and Simulation Specification

**Status:** Approved for Release 0  
**Principle:** The prototype uses deterministic, internally consistent synthetic data. It must never present mock records as real Paytm, bank, merchant, or customer data.

**Execution workstream:** [Data implementation plan](data/IMPLEMENTATION_PLAN.md) and [data tracker](data/TRACKER.md). Until that workstream provides validated fixtures, product development uses only its versioned mock-data contract.

## 1. Decision

Release 0 has no authorized payment-provider API, bank API, or merchant CSV source. The product will therefore use three related data forms:

| Form | Purpose | Created how |
| --- | --- | --- |
| Seeded demo database | Makes the first-run demo immediate and reliable | Deterministic generator with a fixed dataset version and random seed. |
| Synthetic CSV fixtures | Exercises the actual CSV-import and validation path | Generated from the same canonical scenario records. |
| Mock adapter responses | Exercises asynchronous provider/support behavior | Versioned JSON fixtures returned by local mock adapters. |

The system must never depend on a live external API to demonstrate its core workflow.

## 2. Data design goals

The dataset must be financially consistent, explainable, deterministic, representative, safe, transparent, and portable:

- Transaction totals, settlement line items, fees, adjustments, net payouts, and bank entries reconcile according to the scenario.
- Every exception has an authored cause and expected explanation.
- The same dataset version and seed always create the same records, IDs, timestamps, and totals.
- It includes ordinary records and realistic exceptions—not only one hard-coded failure.
- Names, bank accounts, UTRs, phone numbers, QR IDs, and provider IDs are invented and non-routable.
- Every demo surface displays `Synthetic demo data — not a live provider or bank connection`.
- The generator creates canonical records first, then provider-report and bank-statement-shaped CSV exports from them.

## 3. Release 0 dataset identity

| Item | Synthetic value | Constraint |
| --- | --- | --- |
| Merchant | `Aarav Stores Demo Pvt. Ltd.` | Clearly fictional. |
| Stores | `Indiranagar Demo Store`, `Koramangala Demo Store` | Demonstrates multi-location filtering without personal data. |
| Payment provider | `Paytm Mock Connector` | Never claim this is an actual Paytm export or API response. |
| Bank account | `Demo Business Account •••• 4092` | No actual account number. |
| Currency | `INR` | Use exact decimal/money representation. |
| Dataset version | `v1` | Stored in a seed manifest and visible in diagnostics. |
| Demo as-of timestamp | Fixed UTC timestamp in manifest | Avoid dependence on the computer clock. |

Generated IDs use safe prefixes: `mock_txn_`, `mock_settle_`, `mock_bank_`, `mock_case_`, and `mock_utr_`. Never use copied real identifiers.

## 4. Required scenarios

| Scenario ID | Condition | Expected result | Agent behavior |
| --- | --- | --- | --- |
| `SCN-01` | Completed transactions, reported settlement, matching bank credit | `RECONCILED` | Explain that payout is verified. |
| `SCN-02` | ₹18,450 transactions and provider-reported payout, no matching bank credit in imported statement period | `UNMATCHED` or `DELAYED`, based on fixed as-of date | Explain evidence and uncertainty; draft an approval-gated mock support case. |
| `SCN-03` | Settlement remains within its defined expected credit window | `WITHIN_EXPECTED_WINDOW` | Recommend waiting/rechecking; do not open an unnecessary case. |
| `SCN-04` | Provider payout partially matches expected transaction value | `PARTIALLY_MATCHED` | Identify residual amount and contributing records. |
| `SCN-05` | Fee/tax/adjustment accounts for gross-to-net difference | `ADJUSTMENT_EXPLAINED` | Explain adjustment rather than flag missing money. |
| `SCN-06` | Duplicate transaction or duplicate imported row | `DUPLICATE` | Exclude duplicate from totals and retain evidence. |
| `SCN-07` | Refund/reversal appears after original transaction | Correctly linked reversal/refund | Keep refund distinct from settlement discrepancy. |
| `SCN-08` | One bank credit represents multiple payout batches | Valid many-to-one match | Show all contributing payouts and match evidence. |
| `SCN-09` | Mock support update confirms a terminal outcome | Eligible for verified closure | Close only after verification rule passes. |
| `SCN-10` | Mock support update is ambiguous or missing | `ESCALATED` / remains active | Do not close case. |

`SCN-02` is the primary hackathon walkthrough. The other scenarios prove the prototype is not a single-path mock.

## 5. Source-fixture contracts

The importer consumes generated CSV fixtures rather than bypassing the real import path.

### `transactions.csv`

```text
provider,provider_transaction_id,merchant_reference,store_id,occurred_at,status,payment_method,gross_amount,currency
```

### `settlements.csv`

```text
provider,provider_settlement_id,payout_reference,settlement_date,reported_status,gross_amount,fee_amount,tax_amount,adjustment_amount,net_amount,currency
```

### `settlement_line_items.csv`

```text
provider_settlement_id,line_item_id,source_reference,line_type,amount,currency
```

### `bank_statement.csv`

```text
statement_entry_id,bank_account_alias,booking_date,direction,amount,currency,narration,utr_reference
```

### `mock_support_updates.json`

```text
case_reference,event_at,status,summary,terminal_outcome,evidence_reference
```

Every fixture set includes a manifest with dataset/schema version, seed, fixed as-of timestamp, scenario IDs, and checksums. The parser validates its schema version before importing records.

## 6. Fixture layout and generation rules

```text
fixtures/
  synthetic/
    v1/
      manifest.json
      transactions.csv
      settlements.csv
      settlement_line_items.csv
      bank_statement.csv
      mock_support_updates.json
      expected_results.json
```

`expected_results.json` is the test oracle: expected statuses, key amounts, and case outcome—not implementation details.

Generation rules:

1. Generate canonical transactions and adjustments first.
2. Generate settlement line items and batches with exact decimal arithmetic.
3. Generate bank entries by scenario—intentionally omit, delay, combine, or alter only as specified.
4. Generate mock support updates from the case lifecycle.
5. Assert unique IDs (except the explicit duplicate scenario), valid currencies, eligible references, expected totals, and no real/personal data patterns.
6. Write fixture artifacts, checksums, and manifest atomically.

## 7. Product behavior around demo data

- First run offers **Load synthetic demo data** and shows covered scenarios.
- Imported records carry `data_origin = SYNTHETIC`.
- Dashboard, case detail, exports, and agent responses display the synthetic-data badge.
- The agent says “the imported demo statement,” never “your bank statement.”
- A reset action removes only the app-generated local demo database/storage and reseeds `v1`; it never targets arbitrary user directories.
- A future user-uploaded CSV is a separate import source and is never silently blended into seeded data.

## 8. Explicit exclusions

- No real Paytm API schema, merchant credentials, bank authentication, UPI PIN, OTP, CVV, or real customer identity.
- No claim about actual bank processing times, dispute outcomes, or provider support SLAs.
- No successful resolution without a mock authoritative evidence record.

## 9. Acceptance criteria

- [ ] A fresh install can seed the full dataset without network access.
- [ ] Generated CSVs use the same validation path as a user upload.
- [ ] `SCN-02` always yields the same ₹18,450 evidence trail and approval-gated case draft.
- [ ] At least one valid reconciliation, adjustment explanation, duplicate, partial match, and unresolved case are visible.
- [ ] Demo labels appear in every financial and agent-facing view.
- [ ] No fixture contains real personal, account, merchant, or credential data.
