# Data Workstream Tracker

**Status values:** `Not started` · `In progress` · `Blocked` · `In review` · `Done`  
**Completion rule:** A task is `Done` only with a concrete artifact/checksum/report link, not when data merely “looks realistic.”

| ID | Milestone | Task | Status | Depends on | Completion evidence | Notes / blocker |
| --- | --- | --- | --- | --- | --- | --- |
| DATA-01 | D0 | Publish canonical data dictionary and entity relationship map | Not started | — | — | Align to HLD and data strategy. |
| DATA-02 | D0 | Publish CSV/JSON schema contracts and compatibility/versioning rules | Not started | DATA-01 | — | |
| DATA-03 | D1 | Create fictional organization, stores, provider, account aliases, and safe ID conventions | Not started | DATA-01 | — | No real identity data. |
| DATA-04 | D1 | Create canonical successful transaction and adjustment records | Not started | DATA-03 | — | Fixed as-of date and currency precision. |
| DATA-05 | D1 | Derive settlement batches, line items, and bank outcomes from canonical records | Not started | DATA-04 | — | Must balance except intentional scenarios. |
| DATA-06 | D2 | Implement deterministic generator with version, seed, and as-of inputs | Not started | DATA-05 | — | |
| DATA-07 | D2 | Create manifest and checksum generation | Not started | DATA-06 | — | |
| DATA-08 | D2 | Prove repeatability with two equal generator runs | Not started | DATA-06, DATA-07 | — | Artifact hashes must match. |
| DATA-09 | D3 | Generate valid transaction, settlement, line-item, bank, and support-update fixtures | Not started | DATA-06 | — | |
| DATA-10 | D3 | Create separate invalid fixtures for import validation tests | Not started | DATA-02, DATA-09 | — | Never mix invalid rows into demo fixture. |
| DATA-11 | D4 | Implement SCN-01 through SCN-10 fixture narratives and expected outputs | Not started | DATA-09 | — | SCN-02 must retain ₹18,450. |
| DATA-12 | D4 | Produce and review `expected_results.json` | Not started | DATA-11 | — | Covers reconciliation, approval, and closure outcomes. |
| DATA-13 | D5 | Run financial integrity and reference validation | Not started | DATA-09, DATA-12 | — | |
| DATA-14 | D5 | Run synthetic-data safety scan and labelling check | Not started | DATA-09 | — | No real/sensitive/copy-pasted data. |
| DATA-15 | D5 | Produce validation report and resolve blockers | Not started | DATA-13, DATA-14 | — | |
| DATA-16 | D6 | Create fixture-bundle handoff note, commands, checksums, and limitations | Not started | DATA-08, DATA-10, DATA-15 | — | |
| DATA-17 | D6 | Product-workstream import/seed acceptance test | Not started | DATA-16 | — | Requires implementation team evidence. |

## Blocker log

| Date | Blocker | Affected IDs | Owner | Next action | Status |
| --- | --- | --- | --- | --- | --- |
| — | No active blockers. | — | — | — | Open |

## Change log

| Date | Change | Updated by | Evidence |
| --- | --- | --- | --- |
| 31 Oct 2026 | Dedicated data-workstream plan and tracker created. | Project team | [Data implementation plan](IMPLEMENTATION_PLAN.md) |
