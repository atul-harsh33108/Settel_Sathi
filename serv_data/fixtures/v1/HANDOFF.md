# SettleSaathi Synthetic Fixtures Handoff Note

**Bundle Version:** `v1`  
**Schema Version:** `1.0`  
**Status:** Certified & Accepted for Product Implementation  
**Release Target:** Release 0 (Hackathon Prototype)  
**Fixed As-Of Date:** `2026-10-30T18:30:00Z` (Midnight 31 Oct 2026 IST)  
**Generator Seed:** `42` (recorded for reproducibility; current scenario records are fixed and do not vary with seed)

---

## 1. Package Contents & Checksums

| File | Purpose | Rows / Entries | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| `transactions.csv` | Customer collections | 21 | `e5bcafd6aa94400f300b20fde8cd13be11774c89eb35368116345c84421ef5c9` |
| `settlements.csv` | Provider payout batches | 11 | `d8a35b1a65656141d25d42da2773effd60dfef369318339e55c6a5d565f2a14e` |
| `settlement_line_items.csv` | Line-item breakdowns | 21 | `96fc4e67e839d5cd2cf570a722d52d306a25b32a864fbab562037d1757b2737e` |
| `bank_statement.csv` | Synthetic demo bank entries | 6 | `6034bdf3cde396b884d53d640d5bd12b2de417e6263d795ab9399164820b243e` |
| `mock_support_updates.json` | Simulated support status | 2 | `4042fc76dbab2499ec631ad3b135cd68a33b85f6fee9c89dbc20abc5bbe8af97` |
| `expected_results.json` | Test oracle assertions | 10 scenarios | `4aa850fefebd0bc7d896e361a06bfb1f8b9f88737aeec2e44908397b30539cca` |
| `manifest.json` | Integrity metadata | — | *Generated with file hashes* |
| `invalid/*.csv` | Parser test fixtures | 6 files | Negative test cases for importer |

---

## 2. Scenario Mapping & Expected Outcomes

| Scenario | Name | Status | Key Amounts | Case Action |
| :--- | :--- | :--- | :--- | :--- |
| **`SCN-01`** | Standard Reconciliation | `RECONCILED` | Collected: ₹12,500.00, Bank: ₹12,500.00 | No case needed. |
| **`SCN-02`** | **Missing Settlement (Hero Demo)** | `UNMATCHED` | Collected: ₹18,450.00, Settled: ₹18,450.00, Bank: ₹0.00 | Open case, approval required before submit. |
| **`SCN-03`** | Within Expected Window | `WITHIN_EXPECTED_WINDOW` | Collected: ₹8,200.00, Bank: ₹0.00 (In-flight T+1) | Recommend wait; do not open case. |
| **`SCN-04`** | Partial Match | `PARTIALLY_MATCHED` | Collected: ₹5,000.00, Settled: ₹3,500.00 | Flag ₹1,500.00 residual exception. |
| **`SCN-05`** | Adjustment Explained | `ADJUSTMENT_EXPLAINED` | Gross: ₹10,000.00, Net: ₹9,623.00, Bank: ₹9,623.00 | Fee ₹150 + Tax ₹27 + Dispute -₹200 balanced. |
| **`SCN-06`** | Duplicate Row | `DUPLICATE` | Txn ₹2,500.00 duplicated in upload | Deduplicated; only ₹2,500.00 settled. |
| **`SCN-07`** | Refund / Reversal | `RECONCILED` | Collected: ₹2,100.00, Refunded: -₹2,100.00 | Balanced to net ₹0.00. |
| **`SCN-08`** | Multi-Batch Payout | `RECONCILED` | Batch 1: ₹6,200.00, Batch 2: ₹4,800.00 = ₹11,000.00 | Many-to-one bank credit match. |
| **`SCN-09`** | Support Resolution | `VERIFIED_RESOLVED` | Payout re-credited: ₹7,500.00 | Authoritative UTR matched in bank statement. |
| **`SCN-10`** | Ambiguous Support State | `ESCALATED` | Ticket status: `IN_REVIEW` (non-terminal) | Case remains active; false closure prevented. |

---

## 3. Integration & Regeneration Instructions

### Regenerating Fixtures:
```powershell
python serv_data/src/cli.py generate --output serv_data/fixtures/v1 --mirror fixtures/synthetic/v1
```

### Validating Fixtures:
```powershell
python serv_data/src/cli.py validate --fixture-dir serv_data/fixtures/v1
```

### Running Test Suite:
```powershell
python -m unittest discover -s serv_data/tests -p "test_*.py"
```

---

## 4. Known Scope Limitations for Release 0
1. All records are synthetic; no live Paytm API or real bank connection is implied.
2. Currency is strictly fixed to `INR` with 2 decimal places.
3. Merchant identity is locked to `Aarav Stores Demo Pvt. Ltd.` with two locations (`Indiranagar Demo Store`, `Koramangala Demo Store`).

