# M3 Delivery Tracker — Cases, Policy, and Audit

**Status values:** `Not started` · `In progress` · `Blocked` · `In review` · `Done`  
**Rule:** Each task links directly to the [M3 plan](M3_PLAN.md); update with code, tests, and evidence.

| ID | Task | Status | Depends on | Evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| M3-01 | Define canonical SQLite schema for cases, case events, approvals, action attempts, and upgraded audit events | Done | M2 complete | `app/db/schema.sql`, `tests/test_db.py` | Optimistic locking `version` on cases; exact payload hashes on approvals. |
| M3-02 | Define canonical domain models and dataclasses | Done | M3-01 | `app/models/domain.py` | `CaseRecord`, `CaseEventRecord`, `ApprovalRecord`, `ActionAttemptRecord`, `AuditEventRecord`, `CaseStatus`, `ActionClass`, `PolicyDecision`. |
| M3-03 | Implement repository access methods | Done | M3-02 | `app/services/repository.py` | CRUD and query filters for cases, timeline events, approvals, attempts, and audit events. |
| M3-04 | Implement case state machine and optimistic concurrency control (CAS-01) | Done | M3-03 | `app/services/cases.py`, `tests/test_cases.py` | Valid transitions enforced; version increment and conflict detection on update. |
| M3-05 | Implement false-closure prevention guard (CAS-01) | Done | M3-04 | `app/services/cases.py`, `tests/test_cases.py` | Rejects transition to `VERIFIED_RESOLVED` unless verified terminal evidence exists. |
| M3-06 | Implement policy engine with action classes and payload hashing (CAS-02) | Done | M3-02 | `app/services/policy.py`, `tests/test_policy.py` | `READ`, `DRAFT`, `EXTERNAL_NON_SENSITIVE_WRITE`, `SENSITIVE_WRITE`, `BLOCKED`; canonical SHA-256 hash. |
| M3-07 | Implement approval lifecycle and anti-bypass checks (CAS-02) | Done | M3-06 | `app/services/policy.py`, `tests/test_policy.py` | Prevents agent self-approval; enforces expiration; validates exact payload hash match. |
| M3-08 | Implement idempotent action execution adapter (CAS-02) | Done | M3-07 | `app/services/policy.py`, `app/services/cases.py` | `SUBMIT_MOCK_SUPPORT_CASE` checks approval and case state; caches results by idempotency key. |
| M3-09 | Implement append-only audit trail service (CAS-03) | Done | M3-03 | `app/services/audit.py`, `app/services/repository.py` | Append-only logging of actors, correlation IDs, entity types, transitions, approvals, and action attempts. |
| M3-10 | Implement REST API routes under `/api/v1/cases` | Done | M3-04, M3-07, M3-08 | `app/api/routes_cases.py`, `app/main.py`, `tests/test_api_cases.py` | Case listing, creation, detail, transition, timeline, approvals, and action execution endpoints. |
| M3-11 | Implement CLI commands (`cases`, `case-detail`, `approve-case`) | Done | M3-04, M3-07 | `app/cli.py`, `tests/test_cli.py` | CLI commands for operator case inspection, timeline viewing, and approval granting. |
| M3-12 | Comprehensive unit & regression test suite (CAS-04) | Done | M3-04, M3-07, M3-10 | `tests/test_cases.py`, `tests/test_policy.py`, `tests/test_api_cases.py` | Testing approval bypass prevention, false-closure prevention, and optimistic concurrency. |
| M3-13 | Update master tracker and verify zero lint errors | Done | M3-12 | `docs/implementation/TRACKER.md`, `uv run pytest`, `uv run ruff check` | Mark CAS-01 through CAS-04 Done; 80 tests passing, ruff clean. |

## Blocker log

| Date | Blocker | Tasks | Next action | Status |
| --- | --- | --- | --- | --- |
| — | No active blockers recorded. | — | — | Resolved |

## Change log

| Date | Change | Evidence |
| --- | --- | --- |
| 31 Oct 2026 | Milestone M3 plan and tracker initialized following M2 verification. | [M3 plan](M3_PLAN.md), [Release tracker](TRACKER.md) |
| 31 Oct 2026 | Completed Milestone M3 implementation (CAS-01 through CAS-04) including state machine, false-closure prevention, policy engine, approval lifecycle, audit trail, API routes, CLI, and test suite. 80 tests passing, 0 ruff lint errors. | `tests/test_cases.py`, `tests/test_policy.py`, `tests/test_api_cases.py`, `docs/implementation/TRACKER.md` |
