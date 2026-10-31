# Data Workstream Tracker

**Status values:** `Not started` · `In progress` · `Blocked` · `In review` · `Done`  
**Completion rule:** A task is `Done` only with a concrete artifact/checksum/report link, not when data merely “looks realistic.”

| ID | Milestone | Task | Status | Depends on | Completion evidence | Notes / blocker |
| --- | --- | --- | --- | --- | --- | --- |
| DATA-01 | D0 | Publish canonical data dictionary and entity relationship map | Done | — | [data_dictionary.md](../../serv_data/contracts/data_dictionary.md) | Canonical financial models & ER map published. |
| DATA-02 | D0 | Publish CSV/JSON schema contracts and compatibility/versioning rules | Done | DATA-01 | [schema_specs.md](../../serv_data/contracts/schema_specs.md) | Field-by-field specs and versioning policy approved. |
| DATA-03 | D1 | Create fictional organization, stores, provider, account aliases, and safe ID conventions | Done | DATA-01 | [constants.py](../../serv_data/src/constants.py) | Synthetic entities defined with safe prefixes (`mock_txn_`, etc.). |
| DATA-04 | D1 | Create canonical successful transaction and adjustment records | Done | DATA-03 | [scenarios.py](../../serv_data/src/scenarios.py) | 21 canonical transactions with exact decimal amounts in INR. |
| DATA-05 | D1 | Derive settlement batches, line items, and bank outcomes from canonical records | Done | DATA-04 | [scenarios.py](../../serv_data/src/scenarios.py) | 11 settlements, 21 line items, and 6 bank entries derived and balanced. |
| DATA-06 | D2 | Implement deterministic generator with version, seed, and as-of inputs | Done | DATA-05 | [generator.py](../../serv_data/src/generator.py) | `SyntheticDataGenerator` runs with version `v1`, seed `42`. |
| DATA-07 | D2 | Create manifest and checksum generation | Done | DATA-06 | [manifest.json](../../serv_data/fixtures/v1/manifest.json) | SHA-256 computed for all generated files. |
| DATA-08 | D2 | Prove repeatability with two equal generator runs | Done | DATA-06, DATA-07 | [test_determinism.py](../../serv_data/tests/test_determinism.py) | Unit test & CLI verified identical byte-for-byte SHA-256 hashes across runs. |
| DATA-09 | D3 | Generate valid transaction, settlement, line-item, bank, and support-update fixtures | Done | DATA-06 | [serv_data/fixtures/v1/](../../serv_data/fixtures/v1/) | All core fixtures generated and mirrored to `fixtures/synthetic/v1/`. |
| DATA-10 | D3 | Create separate invalid fixtures for import validation tests | Done | DATA-02, DATA-09 | [serv_data/fixtures/v1/invalid/](../../serv_data/fixtures/v1/invalid/) | 6 negative test fixtures created in isolated `invalid/` directory. |
| DATA-11 | D4 | Implement SCN-01 through SCN-10 fixture narratives and expected outputs | Done | DATA-09 | [scenarios.py](../../serv_data/src/scenarios.py) | Scenarios SCN-01 to SCN-10 implemented; SCN-02 retains ₹18,450. |
| DATA-12 | D4 | Produce and review `expected_results.json` | Done | DATA-11 | [expected_results.json](../../serv_data/fixtures/v1/expected_results.json) | Test oracle covers reconciliation, approval, and closure outcomes. |
| DATA-13 | D5 | Run financial integrity and reference validation | Done | DATA-09, DATA-12 | [test_financial_integrity.py](../../serv_data/tests/test_financial_integrity.py) | Gross = net + deductions balanced; all references valid. |
| DATA-14 | D5 | Run synthetic-data safety scan and labelling check | Done | DATA-09 | [test_safety_and_labels.py](../../serv_data/tests/test_safety_and_labels.py) | Validator scans nested CSV/JSON for phone, PAN, Aadhaar, and live Paytm endpoint patterns. |
| DATA-15 | D5 | Produce validation report and resolve blockers | Done | DATA-13, DATA-14 | [validation_report.md](../../serv_data/fixtures/v1/validation_report.md) | Validator now checks manifest, headers, safety, and oracle alignment: 107 checks passed. |
| DATA-16 | D6 | Create fixture-bundle handoff note, commands, checksums, and limitations | Done | DATA-08, DATA-10, DATA-15 | [HANDOFF.md](../../serv_data/fixtures/v1/HANDOFF.md) | Handoff note and instructions published in fixture bundle. |
| DATA-17 | D6 | Product-workstream import/seed acceptance test | In review | DATA-16 | [HANDOFF.md](../../serv_data/fixtures/v1/HANDOFF.md) | Fixtures delivered and mirrored; awaiting consumer M1 ingestion test. |
| DATA-18 | D5 | Verify manifest checksums/sizes/counts, exact CSV headers, nested safety scan, and oracle amount alignment | Done | DATA-13, DATA-14 | `serv_data/src/validator.py`; 107 checks passed. | Report describes only checks actually performed. |
| DATA-19 | D6 | Correct handoff/report wording for synthetic bank data and fixed scenario seed | Done | DATA-18 | `serv_data/fixtures/v1/HANDOFF.md`, `validation_report.md`, `serv_data/README.md` | |

## Blocker log

| Date | Blocker | Affected IDs | Owner | Next action | Status |
| --- | --- | --- | --- | --- | --- |
| — | No active blockers. | — | — | — | Open |

## Change log

| Date | Change | Updated by | Evidence |
| --- | --- | --- | --- |
| 31 Oct 2026 | Dedicated data-workstream plan and tracker created. | Project team | [Data implementation plan](IMPLEMENTATION_PLAN.md) |
| 31 Oct 2026 | Milestones D0–D6 (DATA-01 to DATA-16) completed; fixtures generated and validated. | Data agent | [manifest.json](../../serv_data/fixtures/v1/manifest.json) |
