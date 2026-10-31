# M1 Domain Model and Data Ingestion Tracker

**Status vocabulary:** `Not started` · `In progress` · `Blocked` · `In review` · `Done`  
**Rule:** Update a row only with implementation evidence; all work follows plan → tracker → implement → verify → tracker.

| ID | Phase | Task | Status | Depends on | Evidence | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| M1-01 | Contract | Review actual v1 headers, manifest, data dictionary, schema spec, handoff, and oracle together | Done | M0 complete, data bundle delivered | `serv_data/fixtures/v1/HANDOFF.md`, `serv_data/contracts/schema_specs.md` | v1 header contracts confirmed; 21 raw rows in transactions.csv with SCN-06 deduplication. |
| M1-02 | Contract | Record accepted field mapping and money storage representation | Done | M1-01 | `app/models/domain.py`, `format_money()`, `parse_money()` | Exact Decimal representation; canonical 2-decimal string in SQLite TEXT; distinct collections, settlements, bank models. |
| M1-03 | SQLite | Implement connection lifecycle, safe path handling, FK enforcement, and WAL | Done | M1-02 | `app/db/connection.py`, `tests/test_db.py` | `PRAGMA foreign_keys = ON;`, `PRAGMA journal_mode = WAL;`, busy timeout 5000ms. |
| M1-04 | SQLite | Create schema for org/store/account, artifacts/import jobs, transactions, settlements/items, bank entries, provenance/audit | Done | M1-03 | `app/db/schema.sql`, `tests/test_db.py` | 11 tables with foreign keys, unique constraints, and lookup indexes. |
| M1-05 | Persistence | Add repository/service interfaces and transaction boundaries | Done | M1-04 | `app/services/repository.py`, `app/db/connection.py` | Isolated SQL repositories and `db_session` context manager. |
| M1-06 | Import | Implement artifact hashing, private storage, manifest/version validation | Done | M1-05 | `app/services/importer.py` (`_save_artifact_content`, version check) | SHA-256 storage beneath `storage/artifacts/<prefix>/<hash>/`. |
| M1-07 | Import | Implement transaction CSV parser and row-level validation | Done | M1-06 | `app/services/importer.py` (`_parse_transactions`) | SCN-06 duplicate row deduplicated; exact money, enum, and date checks. |
| M1-08 | Import | Implement settlement and line-item parsers and balance/reference checks | Done | M1-06 | `app/services/importer.py` (`_parse_settlements`, `_parse_settlement_line_items`) | `net == gross - fee - tax + adj` balance invariant and settlement existence enforced. |
| M1-09 | Import | Implement bank statement parser and reference/date validation | Done | M1-06 | `app/services/importer.py` (`_parse_bank_statement`) | Bank account alias, ISO date, direction, amount, and duplicate entry checks. |
| M1-10 | Import | Implement mock support JSON validation/import | Done | M1-06 | `app/services/importer.py` (`_parse_mock_support_updates`) | Status enum, ISO 8601 UTC timestamp, and terminal outcome boolean validation. |
| M1-11 | Persistence | Normalize and atomically persist valid bundle with source row provenance | Done | M1-07, M1-08, M1-09, M1-10 | `app/services/importer.py`, `tests/test_importer.py` | Atomic rollback on row error; provenance links (`source_artifact_id`, `source_row_number`). |
| M1-12 | Idempotency | Define digest key, repeat-import behavior, and conflicting source-ID behavior | Done | M1-11 | `app/services/importer.py`, `tests/test_importer.py` | `(org, source_type, version, sha256)` digest key; safe no-op on replay; explicit `CONFLICT` error on conflicting source IDs. |
| M1-13 | CLI | Implement offline seed/import command through the shared import service | Done | M1-12 | `app/cli.py`, `tests/test_cli.py` | CLI commands `seed`, `status`, `reset`, `import-file`. |
| M1-14 | API | Add upload, job status, and row-error endpoints with correlation IDs | Done | M1-12 | `app/api/routes_import.py`, `tests/test_api_imports.py` | Endpoints `/api/v1/imports/seed`, `/upload`, `/jobs/{job_id}`, `/summary`, `/artifacts`. |
| M1-15 | UI | Add fixture load/import affordance and visible synthetic source/version | Done | M1-13 | `web/src/App.jsx`, `web/src/index.css` | Provenance badge, load fixtures button, and live record counts grid; ESLint and Vite build pass. |
| M1-16 | Tests | Cover success, invalid rows, refs/balance, atomic rollback, provenance, idempotent re-import | Done | M1-11, M1-12 | `tests/test_importer.py`, `tests/test_db.py`, `tests/test_api_imports.py`, `tests/test_cli.py` | 33 pytest tests passed covering all 6 negative fixtures in `fixtures/synthetic/v1/invalid/`, balance invariants, FK validation, and Windows drive path resolution. |
| M1-17 | Acceptance | Run offline seed/import and record counts against manifest | Done | M1-13, M1-14, M1-16 | `python -m app.cli seed --fixture-dir serv_data/fixtures/v1` executed successfully | Output: 20 unique txns (from 21 rows), 11 settlements, 21 lines, 6 bank entries, 2 support updates, 5 artifacts. |

## Blocker log

| Date | Blocker | Tasks | Next action | Status |
| --- | --- | --- | --- | --- |
| — | No active blockers recorded. | — | — | Open |

## Change log

| Date | Change | Evidence |
| --- | --- | --- |
| 31 Oct 2026 | M1 plan and task tracker created from delivered v1 data contract. | [M1 plan](M1_PLAN.md), [v1 handoff](../../serv_data/fixtures/v1/HANDOFF.md) |
| 31 Oct 2026 | Milestone M1 completed and hardened: 17 sub-tasks verified with 33 unit/integration tests, offline CLI, and web UI affordance. | `tests/test_importer.py`, `tests/test_db.py`, `tests/test_api_imports.py`, `tests/test_cli.py` (33 passed) |
