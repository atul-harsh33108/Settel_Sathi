# Data Workstream Implementation Plan

**Owner:** Data-workstream agent/team  
**Consumer:** SettleSaathi product implementation  
**Product contract:** [Data strategy](../DATA_STRATEGY.md)  
**Goal:** Deliver safe, deterministic, internally consistent Release 0 test data and its validation evidence—without live APIs or real merchant/bank data.

## 1. Scope and handoff rule

The data workstream creates the fixtures, manifest, generator, validation checks, and expected-result oracle. The product workstream builds import, reconciliation, case, and agent behavior against those versioned artifacts.

Until the data workstream marks a fixture version accepted, the product workstream must use only clearly labelled temporary mock data that follows the same schema contract. It must not invent a different CSV shape or silently change expected outcomes.

## 2. Deliverables

| ID | Deliverable | Consumer use |
| --- | --- | --- |
| D-01 | Canonical data dictionary | Defines fields, types, enumerations, and cross-record relationships. |
| D-02 | Fixture schema specification | Defines CSV/JSON columns, required/optional fields, dates, decimals, and validation rules. |
| D-03 | Deterministic synthetic-data generator | Recreates a dataset from fixed version, seed, and as-of timestamp. |
| D-04 | `v1` import fixtures | Exercises actual transaction, settlement, line-item, bank-statement, and mock-support import paths. |
| D-05 | Scenario catalogue | Documents narrative, expected status, and expected agent outcome for each scenario. |
| D-06 | Expected-result oracle | Supplies assertions for reconciliation, case state, approval, and verification tests. |
| D-07 | Quality-validation report | Proves integrity checks and synthetic-data safety checks passed. |
| D-08 | Handoff note | Records fixture version, checksums, setup command, known limitations, and acceptance evidence. |

## 3. Milestones

```mermaid
flowchart LR
    A[D0: Contract] --> B[D1: Canonical data]
    B --> C[D2: Generator]
    C --> D[D3: Fixtures]
    D --> E[D4: Scenario oracle]
    E --> F[D5: Validation]
    F --> G[D6: Handoff]
```

| Milestone | Outcome | Exit gate |
| --- | --- | --- |
| D0 — Contract alignment | Product and data teams agree one field/schema contract | Signed-off data dictionary and fixture schemas. |
| D1 — Canonical records | Base transactions, adjustments, settlements, and bank outcomes modelled | Every source relationship can be traced by stable mock IDs. |
| D2 — Generator | Same inputs yield same complete dataset | Generator passes deterministic repeatability test. |
| D3 — Import fixtures | Files exercise each product import path | Schema validator and import dry run pass. |
| D4 — Scenario oracle | Expected outputs are explicit, testable, and scenario-specific | Every required scenario has expected reconciliation and case outcome. |
| D5 — Quality validation | Integrity and safety checks prove fixture quality | Validation report has no blocking failures. |
| D6 — Handoff | Product team can consume the data unaided | Versioned bundle, checksums, setup instructions, and acceptance sign-off delivered. |

## 4. Task breakdown

### D0 — Contract alignment

1. Derive the canonical entities from the HLD: transactions, settlement batches, settlement line items, bank entries, cases, mock support updates, and provenance.
2. Define types, nullable fields, enumerations, money precision, date/time format, primary keys, and foreign-key-like references.
3. Freeze Release 0 source-file contracts: `transactions.csv`, `settlements.csv`, `settlement_line_items.csv`, `bank_statement.csv`, `mock_support_updates.json`, `manifest.json`, and `expected_results.json`.
4. Publish fixture-versioning rules and a compatibility policy.

**Exit evidence:** Data dictionary and schema documents reviewed with product implementation owner.

### D1 — Canonical records

1. Create fictional organization, stores, payment-provider identity, and bank-account aliases.
2. Create base successful transactions over a fixed time window and distribute them over stores/payment methods.
3. Create settlement batches and line items from those transactions using exact decimal arithmetic.
4. Create bank entries and mock support updates only from defined scenario outcomes.
5. Apply unique, safe mock ID prefixes and source provenance fields.

**Exit evidence:** Canonical-record export has referential-integrity and amount-balance checks.

### D2 — Deterministic generator

1. Accept `dataset_version`, `seed`, and `as_of_timestamp` as explicit inputs.
2. Generate canonical records first; derive every CSV/JSON artifact from them.
3. Enforce stable ordering and deterministic IDs/timestamps.
4. Produce a manifest with schema version, scenario list, record counts, and SHA-256 checksums.
5. Run generator twice and compare artifact hashes.

**Exit evidence:** Repeatability report with identical hashes for two runs.

### D3 — Import fixtures

1. Create valid fixtures for all required source types.
2. Create invalid fixtures separately for parser/error-path tests: malformed decimal, invalid date, unsupported currency, missing required field, duplicate upload, and unmatched reference.
3. Ensure valid fixtures are compact enough for fast local demo startup while covering all required scenarios.
4. Validate each file against its documented column order, types, encoding, and schema version.

**Exit evidence:** Fixture validator results and a successful product-import dry run when available.

### D4 — Scenario catalogue and oracle

1. Implement all `SCN-01` through `SCN-10` from the data strategy.
2. Specify expected input records, reconciliation status, reason code, amount(s), case transition, required approval behavior, and final outcome for every scenario.
3. Confirm the ₹18,450 `SCN-02` values and source links are fixed and reproducible.
4. Define expected negative outcomes: no closure for absent/ambiguous terminal evidence; no action for missing approval.

**Exit evidence:** Versioned `expected_results.json` independently reviewed against generated data.

### D5 — Quality and safety validation

1. Check referential integrity, monetary balance, fixed precision, uniqueness, valid status values, and time ordering.
2. Check that expected-result assertions match the source fixture values.
3. Scan for forbidden real data: credentials, full account numbers, actual UTRs, phone/email/address patterns, or copied provider payloads.
4. Confirm every artifact is labelled synthetic and no live endpoint/configuration is needed.

**Exit evidence:** Validation report with no blocker and a list of any accepted limitations.

### D6 — Handoff and version control

1. Place the complete versioned fixture bundle under `fixtures/synthetic/v1/`.
2. Provide generator command, seed, as-of timestamp, checksums, and reset instructions.
3. Deliver a short handoff note for product implementation: schema changes, known gaps, and test commands.
4. Update the data tracker with evidence links and mark the version accepted.

**Exit evidence:** Product implementation can seed/import the bundle without data-team assistance.

## 5. Mandatory validation rules

| Area | Rule |
| --- | --- |
| Money | All values use INR and two decimal places; no binary float serialization. |
| Gross/net | Settlement net equals gross minus fees, taxes, and adjustments as defined by the scenario. |
| References | Settlement line items reference valid canonical records unless a scenario deliberately tests invalid input. |
| Bank matching | Bank entries match only the intended settlement references/amounts/date windows. |
| Determinism | Same version, seed, and as-of timestamp produce byte-identical artifacts or documented canonical equivalent. |
| Safety | No real people, merchants, account data, credentials, or copied external payloads. |
| Labelling | Every source artifact and UI-import description identifies synthetic origin. |
| Compatibility | A fixture schema change requires a new schema/dataset version and product-team review. |

## 6. Handoff package

```text
fixtures/synthetic/v1/
  manifest.json
  transactions.csv
  settlements.csv
  settlement_line_items.csv
  bank_statement.csv
  mock_support_updates.json
  expected_results.json
  invalid/
  validation_report.md
  HANDOFF.md
```

The product workstream treats the manifest and expected-results oracle as the contract. It may add application seed adapters, but it must not edit fixture meaning without returning the change to this data workstream.

## 7. Out of scope

- Live Paytm/bank/provider access or real merchant exports.
- Simulated payment movement, regulated dispute adjudication, or real support SLA claims.
- Random ad-hoc records that cannot be reproduced or tested.
