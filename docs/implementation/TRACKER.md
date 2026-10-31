# Release 0 Delivery Tracker

**How to use this tracker:** This is the live implementation status record. Update it in the same change set as completed work. Link evidence to code, tests, issue IDs, or demo output. Do not mark a row complete based only on a plan or an AI-generated claim.

**Status vocabulary:** `Not started` · `In progress` · `Blocked` · `In review` · `Done`

## Current delivery status

| ID | Milestone | Task | Status | Depends on | Completion evidence | Notes / blocker |
| --- | --- | --- | --- | --- | --- | --- |
| FND-01 | M0 | Select repository structure and package management | Not started | — | — | |
| FND-02 | M0 | Add local setup, environment template, linting, tests, and CI baseline | Not started | FND-01 | — | |
| FND-03 | M0 | Add app configuration, structured logging, correlation IDs, and health check | Not started | FND-01 | — | |
| DAT-01 | M1 | Define canonical financial entities and migrations/schema | Not started | FND-01 | — | |
| DAT-02 | M1 | Create versioned synthetic transaction, settlement, and bank fixtures | Not started | DAT-01 | — | Must be clearly labelled synthetic. |
| DAT-03 | M1 | Implement validation, normalization, provenance, and idempotent import jobs | Not started | DAT-01, DAT-02 | — | |
| DAT-04 | M1 | Test invalid and duplicate imports | Not started | DAT-03 | — | |
| REC-01 | M2 | Implement money arithmetic and reconciliation rule framework | Not started | DAT-01 | — | |
| REC-02 | M2 | Match transactions to settlement line items | Not started | REC-01, DAT-03 | — | |
| REC-03 | M2 | Match settlement payouts to bank credits | Not started | REC-01, DAT-03 | — | |
| REC-04 | M2 | Classify and explain expected-window, partial, unmatched, duplicate, and adjustment cases | Not started | REC-02, REC-03 | — | |
| REC-05 | M2 | Add reconciliation regression suite | Not started | REC-04 | — | |
| CAS-01 | M3 | Implement case state machine and timeline | Not started | REC-04 | — | |
| CAS-02 | M3 | Implement policy decisions and approval records | Not started | CAS-01 | — | |
| CAS-03 | M3 | Implement append-only audit events | Not started | CAS-01 | — | |
| CAS-04 | M3 | Test approval bypass and false-closure prevention | Not started | CAS-02, CAS-03 | — | |
| EXP-01 | M4 | Implement dashboard metrics and exception list APIs | Not started | REC-04 | — | |
| EXP-02 | M4 | Implement import, dashboard, evidence, case, and approval UI | Not started | EXP-01, CAS-02 | — | |
| EXP-03 | M4 | Add empty, error, loading, and synthetic-data states | Not started | EXP-02 | — | |
| AGT-01 | M5 | Define agent read-tool and action-tool contracts | Not started | REC-04, CAS-02 | — | |
| AGT-02 | M5 | Implement evidence-grounded investigation workflow | Not started | AGT-01 | — | Must work with deterministic fallback. |
| AGT-03 | M5 | Add agent safety and groundedness evaluations | Not started | AGT-02 | — | |
| WRK-01 | M6 | Implement mock support connector and idempotent submit action | Not started | CAS-02 | — | |
| WRK-02 | M6 | Implement monitoring, verification, and escalation routes | Not started | WRK-01, AGT-02 | — | |
| WRK-03 | M6 | Run full missing-settlement scenario | Not started | EXP-02, WRK-02 | — | |
| REL-01 | M7 | Add one-command synthetic demo seed/reset workflow | Not started | DAT-02, WRK-03 | — | |
| REL-02 | M7 | Document setup, demo, and troubleshooting | Not started | REL-01 | — | |
| REL-03 | M7 | Execute full release checklist and record results | Not started | REL-02 | — | |

## Blocker log

| Date | Blocker | Affected IDs | Owner | Next action | Status |
| --- | --- | --- | --- | --- | --- |
| — | No active blockers. | — | — | — | Open |

## Change log

| Date | Change | Updated by | Evidence |
| --- | --- | --- | --- |
| 31 Oct 2026 | Tracker created from the approved Release 0 scope. | Project team | [Implementation plan](IMPLEMENTATION_PLAN.md) |
