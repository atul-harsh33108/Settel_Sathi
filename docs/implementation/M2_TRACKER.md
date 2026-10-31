# M2 Deterministic Reconciliation Tracker

**Status values:** `Not started` · `In progress` · `Blocked` · `In review` · `Done`  
**Rule:** Each implementation task maps to the [M2 plan](M2_PLAN.md); update with test or demo evidence.

| ID | Task | Status | Depends on | Evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| M2-01 | Map SCN-01–SCN-10 oracle IDs to imported M1 record IDs | Done | M1 complete | `serv_data/fixtures/v1/expected_results.json`; validator cross-checks oracle amounts against referenced records. | |
| M2-02 | Document edge semantics: signed adjustments, refunds, duplicates, T+1, group matching | Done | M2-01 | `serv_data/src/scenarios.py`, `app/services/reconciliation.py` | Signed deductions, refund balancing, duplicate upload exclusion, and T+1 window semantics documented and codified. |
| M2-03 | Define rule version, evaluation timestamp, and exact money comparison policy | Done | M2-02 | `app/models/domain.py` (`DEFAULT_RULE_VERSION = "v1.0.0"`, `ReconciliationStatus`, `ReconciliationReasonCode`) | Exact Decimal comparison with zero tolerance. |
| M2-04 | Implement transaction-to-line-item matching | Done | M2-03 | `app/services/reconciliation.py` (Stage 1 matching) | Line items link transactions to settlement batches. |
| M2-05 | Implement settlement gross/fees/tax/adjustment/net validation | Done | M2-03 | `app/services/reconciliation.py` (Rule 5 SCN-05) | Verifies gross - fee - tax + adj == net against bank statement. |
| M2-06 | Implement payout-to-bank UTR/reference matching | Done | M2-04, M2-05 | `app/services/reconciliation.py` (Stage 2 matching) | Direct UTR lookup and re-credit support update matching. |
| M2-07 | Implement partial and many-to-one/one-to-many grouping | Done | M2-06 | `app/services/reconciliation.py` (Rule 4 SCN-08 & Rule 6 SCN-04) | Residual amount calculation for partials; multi-batch aggregation. |
| M2-08 | Implement statement-coverage and expected-window classification | Done | M2-06 | `app/services/reconciliation.py` (Rule 7 SCN-03) | T+1 in-flight window check prevents false case creation. |
| M2-09 | Persist reconciliation runs/results and evidence links | Done | M2-04, M2-05, M2-06 | `app/db/schema.sql`, `app/services/repository.py` | `reconciliation_runs` and `reconciliation_results` tables with audit trail. |
| M2-10 | Implement all required statuses/reason codes | Done | M2-07, M2-08, M2-09 | `app/services/reconciliation.py`, `app/models/domain.py` | All 8 statuses and 10 reason codes implemented. |
| M2-11 | Add oracle-driven tests for all 10 scenarios | Done | M2-10 | `tests/test_reconciliation.py` (14 passed) | 100% exact match on statuses, reason codes, amounts, and IDs against oracle, plus generic records and boundary tests. |
| M2-12 | Add run/results/evidence API endpoints | Done | M2-09, M2-10 | `app/api/routes_reconciliation.py`, `tests/test_api_reconciliation.py` (3 passed) | REST endpoints for runs, results, filtering, evidence packages, and input validation. |
| M2-13 | Add dashboard metrics and exception detail view | In progress | M2-12 | APIs complete (`/api/v1/reconciliation/runs`, `/results`); UI view in M4 | Master plan tracks UI in Milestone M4. |
| M2-14 | Run M2 acceptance gates and record results | Done | M2-11, M2-12, M2-13 | `tests/test_reconciliation.py`, `tests/test_api_reconciliation.py`, `tests/test_cli.py` (51 passed) | All Release 0 M2 acceptance gates verified offline. |

## Blocker log

| Date | Blocker | Tasks | Next action | Status |
| --- | --- | --- | --- | --- |
| — | No active blockers recorded. | — | — | Open |

## Change log

| Date | Change | Evidence |
| --- | --- | --- |
| 31 Oct 2026 | M2 reconciliation plan and tracker prepared after M1 import completion. | [M2 plan](M2_PLAN.md), [M1 tracker](M1_TRACKER.md) |
| 31 Oct 2026 | M2 deterministic reconciliation engine, repository layer, REST API, CLI commands, and oracle regression suite delivered and hardened. | `app/services/reconciliation.py`, `tests/test_reconciliation.py`, `tests/test_api_reconciliation.py`, `tests/test_cli.py` (51 passed) |
