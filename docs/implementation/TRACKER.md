# Release 0 Delivery Tracker

**How to use this tracker:** This is the live implementation status record. Update it in the same change set as completed work. Link evidence to code, tests, issue IDs, or demo output. Do not mark a row complete based only on a plan or an AI-generated claim.

**Status vocabulary:** `Not started` · `In progress` · `Blocked` · `In review` · `Done`

## Current delivery status

M1 implementation is tracked in the [M1 plan](M1_PLAN.md) and [M1 tracker](M1_TRACKER.md). Update both this release summary and the detailed M1 tracker as work completes.
M2 reconciliation work is tracked in the [M2 plan](M2_PLAN.md) and [M2 tracker](M2_TRACKER.md).

| ID | Milestone | Task | Status | Depends on | Completion evidence | Notes / blocker |
| --- | --- | --- | --- | --- | --- | --- |
| FND-01 | M0 | Select repository structure and package management | Done | — | `pyproject.toml`, `uv.lock`, `web/package.json`, `web/package-lock.json`; `serv_data/` preserved for data workstream. | Python 3.14.2 resolved by uv in this environment; metadata supports Python >=3.12. |
| FND-02 | M0 | Add local setup, environment template, linting, tests, and CI baseline | Done | FND-01 | `.env.example`, `docs/LOCAL_DEVELOPMENT.md`, `.github/workflows/ci.yml`, `uv.lock`, `web/package-lock.json`; backend Ruff clean + pytest 2 passed; frontend ESLint clean + Vite production build passed. | |
| FND-03 | M0 | Add app configuration, structured logging, correlation IDs, and health check | Done | FND-01 | `app/core/config.py`, `app/core/logging.py`, `app/main.py`, `app/api/routes.py`; health and readiness tests pass. | |
| DAT-01 | M1 | Define canonical financial entities and migrations/schema | Done | FND-01 | `app/db/schema.sql`, `app/db/connection.py`, `app/models/domain.py`, `tests/test_db.py`; SQLite tables, WAL, FK enforcement, fixed-precision Decimal models. | Exact Decimal representation; distinct models for collections, settlements, and bank credits. |
| DAT-02 | M1 | Implement deterministic `v1` synthetic fixtures, manifest, mock responses, and expected-result oracle | Done | DAT-01 | [manifest.json](../../serv_data/fixtures/v1/manifest.json), [HANDOFF.md](../../serv_data/fixtures/v1/HANDOFF.md) | Certified v1 bundle delivered in `serv_data/fixtures/v1/` and mirrored to `fixtures/synthetic/v1/`. |
| DAT-03 | M1 | Implement validation, normalization, provenance, and idempotent import jobs | Done | DAT-01, DAT-02 | `app/services/importer.py`, `app/services/repository.py`, `app/cli.py`, `app/api/routes_import.py`, `tests/test_importer.py`, `tests/test_api_imports.py`; SHA-256 provenance and idempotent re-import. | Ingests transactions, settlements, settlement line items, bank statements, and mock support updates. |
| DAT-04 | M1 | Test invalid and duplicate imports | Done | DAT-03 | `tests/test_importer.py` covers 6 negative fixtures in `fixtures/synthetic/v1/invalid/`, conflict detection, and atomic rollback without partial persistence. | SCN-06 transaction row deduplication and bank duplicate error handled. |
| REC-01 | M2 | Implement money arithmetic and reconciliation rule framework | Done | DAT-01 | `app/db/schema.sql`, `app/models/domain.py`, `app/services/repository.py`; `reconciliation_runs` & `reconciliation_results` schema with exact Decimal representation and status/reason constants. | |
| REC-02 | M2 | Match transactions to settlement line items | Done | REC-01, DAT-03 | `app/services/reconciliation.py`; Stage 1 matching transactions against line items, duplicate source handling, and refund tracking. | |
| REC-03 | M2 | Match settlement payouts to bank credits | Done | REC-01, DAT-03 | `app/services/reconciliation.py`; Stage 2 matching payouts to bank statement credits by UTR, net amount, and multi-batch aggregation (SCN-08). | |
| REC-04 | M2 | Classify and explain expected-window, partial, unmatched, duplicate, and adjustment cases | Done | REC-02, REC-03 | `app/services/reconciliation.py`, `app/api/routes_reconciliation.py`, `app/cli.py`; Stage 3 classification across all 10 scenarios with comprehensive evidence package compilation and audit events. | SCN-02 hero missing settlement flagged as UNMATCHED with approval required. |
| REC-05 | M2 | Add reconciliation regression suite | Done | REC-04 | `tests/test_reconciliation.py`, `tests/test_api_reconciliation.py`, `tests/test_cli.py`; 100% exact match across all 10 scenarios verified against `fixtures/synthetic/v1/expected_results.json`, generic non-synthetic matching, empty database handling, date boundary validation, and CLI commands (51 passed). | |
| CAS-01 | M3 | Implement case state machine and timeline | Not started | REC-04 | — | |
| CAS-02 | M3 | Implement policy decisions and approval records | Not started | CAS-01 | — | |
| CAS-03 | M3 | Implement append-only audit events | Not started | CAS-01 | — | |
| CAS-04 | M3 | Test approval bypass and false-closure prevention | Not started | CAS-02, CAS-03 | — | |
| EXP-01 | M4 | Implement dashboard metrics and exception list APIs | Not started | REC-04 | — | |
| EXP-02 | M4 | Implement import, dashboard, evidence, case, and approval UI | Not started | EXP-01, CAS-02 | — | |
| EXP-03 | M4 | Add empty, error, loading, and synthetic-data states | Not started | EXP-02 | — | |
| AGT-01 | M5 | Implement persisted agent-run state, typed tool contracts, and evidence bundles | Not started | REC-04, CAS-02 | — | Follow [agentic architecture](../AGENTIC_ARCHITECTURE.md). |
| AGT-02 | M5 | Implement evidence-grounded investigation and approval-gated workflow | Not started | AGT-01 | — | Must work with deterministic fallback. |
| AGT-03 | M5 | Add agent safety, groundedness, tenant-scope, and false-closure evaluations | Not started | AGT-02 | — | |
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
| 31 Oct 2026 | Milestone M1 completed and hardened: canonical entities, SQLite WAL/FK schema, Windows path safety, store/bank FK validation, SHA-256 provenance, idempotent import pipeline, CLI, and comprehensive test suite (33 passed). | Antigravity | `tests/test_importer.py`, `tests/test_db.py`, `tests/test_api_imports.py`, `tests/test_cli.py` (33 passed) |
| 31 Oct 2026 | Milestone M2 completed and hardened: deterministic two-stage matching, generic reference-based clustering, elimination of hardcoded scenario ID checks, deduplication audit trail, reconciliation runs/results schema, exact Decimal arithmetic, 10 scenario classifications matching oracle, REST API endpoints, CLI reconcile commands, and regression tests (51 passed). | Antigravity | `tests/test_reconciliation.py`, `tests/test_api_reconciliation.py`, `tests/test_cli.py` (51 passed) |
