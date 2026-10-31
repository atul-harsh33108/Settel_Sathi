# Development Guide

**Purpose:** This document tells the engineering team how to turn the PRD into a safe, testable SettleSaathi prototype. It is implementation-oriented; product scope belongs in the PRD and sequencing belongs in the implementation plan.

## 1. Development target

Build a **modular monolith** for Release 0. Keep domain boundaries explicit so later provider integrations and background workers can be introduced without rewriting financial logic.

Recommended starting direction:

| Area | Release 0 choice | Notes |
| --- | --- | --- |
| Frontend | React + Vite | Matches the configured frontend environment and keeps the UI fast to run locally. |
| API | Python + FastAPI served by Uvicorn | Typed request/response contracts; one local backend process. |
| Python tooling | `uv` with a project-local `.venv` | Always create/run through the virtual environment; do not use global packages. |
| Persistence | SQLite with foreign keys and WAL enabled | Self-contained, reliable prototype store; repository boundaries preserve future portability. |
| Reconciliation | Python services with `Decimal` or integer minor units | Do not use binary floating point for money. |
| Background work | Synchronous application services or FastAPI background tasks | Persist task state in SQLite; no Redis or external queue. |
| AI | Optional tool-calling provider plus deterministic fallback | The app must function safely without an API key. |
| File storage | Private local `storage/` directory | Store CSV source artifacts and evidence packs outside SQLite blobs. |

## 2. Project structure

Use a structure equivalent to the following; exact names may adapt to the chosen framework.

```text
app/
  api/                 # HTTP routes, request validation, response schemas
  domain/              # entities, enums, value objects, domain rules
  services/            # reconciliation, case workflow, policy services
  adapters/            # files, mock providers, mock support, model providers
  persistence/         # repositories, migrations, transactions
  workflows/           # agent and case orchestration state machines
  security/            # authorization, approvals, secret/config access
  observability/       # structured logging, metrics, tracing helpers
  web/                 # UI, if kept in the same repository
tests/
  unit/
  integration/
  e2e/
fixtures/
  synthetic/
docs/
```

Dependencies point inward: API/UI and adapters may call services; services may call domain interfaces; domain code cannot import API, UI, database, or LLM code.

## 3. Required developer commands

Every Python command runs through the project-local virtual environment created by `uv`:

```powershell
uv venv .venv
.\.venv\Scripts\Activate.ps1
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Never run project `python` or `pip` commands from the global interpreter; use `uv run ...` inside the project-local `.venv`. The repository will provide the exact `uv` commands for tests, linting, seed data, and demo startup once the application scaffold exists.

Use Mermaid for all new architecture, sequence, state, and entity-relationship diagrams in Markdown. Do not add hand-drawn ASCII diagrams to documentation.

## 4. Dependency policy

Use the latest **stable, compatible** package releases when a dependency is first added. Use `uv add <package>` without an arbitrary old pin, review its release compatibility with the selected Python/runtime version, and commit the resulting lockfile.

Do not use a prerelease, major-version upgrade, or newly released package blindly when it could jeopardize the hackathon demo. Prefer the latest stable version that passes the project’s tests and works with the existing dependency graph. Any exception—such as a package held back for compatibility—must be recorded in the implementation tracker with its reason.

## 5. Engineering invariants

1. **Money is exact.** Persist currency and decimal precision (or minor units); format only at the UI boundary.
2. **Financial states stay separate.** Payment collection, provider settlement, and bank credit are not interchangeable fields.
3. **Evidence is persisted.** Each reconciliation outcome points to source record IDs and a rule version.
4. **Every write is scoped.** Organization and actor authorization are checked server-side.
5. **Consequential writes are idempotent.** Import and external-action endpoints accept or derive an idempotency key.
6. **The agent is not an authority.** Its tool calls and outputs are validated by application code.
7. **Closure is verified.** No agent message, successful API request, or elapsed timer can close a case alone.
8. **Synthetic data is labeled.** Fixtures and UI must never imply real merchant or provider information.

## 6. Core contracts

### Import contract

An import must record source type, source file identity, importer, timestamp, schema version, validation result, and normalized-record count. Reprocessing an identical source must return the existing result or a safe no-op.

### Reconciliation contract

Every result includes:

```text
status, reason_code, rule_version, input_record_ids,
matched_record_ids, monetary_values, evaluated_at, evidence_references
```

Suggested initial status values:

```text
RECONCILED
WITHIN_EXPECTED_WINDOW
DELAYED
PARTIALLY_MATCHED
UNMATCHED
DUPLICATE
ADJUSTMENT_EXPLAINED
REQUIRES_REVIEW
```

### Case and approval contract

Cases transition only through an explicit state machine. An approval record binds an actor, a case, an action type, a reviewed payload/version, timestamp, and expiry. A new or modified payload invalidates an earlier approval.

### Agent tool contract

Define narrow typed tools such as:

- `get_case(case_id)`
- `get_reconciliation_evidence(exception_id)`
- `list_case_events(case_id)`
- `draft_support_case(case_id)`
- `request_action_approval(case_id, action_type, payload_version)`
- `submit_mock_support_case(case_id, approval_id)`

The last tool must independently verify approval and policy; it must never rely on the model saying it has permission.

## 7. API conventions

- Version endpoints, for example `/api/v1/...`.
- Validate all inputs and return a consistent error envelope with a correlation ID.
- Paginate collections and specify stable sort order.
- Derive organization scope and permissions from authenticated identity, not client-provided identifiers alone.
- Redact secrets and sensitive raw data from errors and logs.
- Use optimistic concurrency or version checks for case transitions and approval payloads.

## 8. Testing strategy

| Test layer | Focus | Required Release 0 examples |
| --- | --- | --- |
| Unit | Pure domain rules | Decimal arithmetic, match rules, status classification, state transitions. |
| Integration | Persistence and adapters | Duplicate import, CSV validation, audit persistence, mock-support idempotency. |
| API | Auth, validation, and policy boundaries | Denied cross-organization access, invalid payload, action without approval. |
| End-to-end | Visible product outcome | The missing ₹18,450 synthetic settlement case. |
| AI evaluation | Safe orchestration | Grounded explanation, ambiguity disclosure, blocked unsafe action, no false closure. |

For every defect, add or strengthen the smallest test that would have caught it.

## 9. Local development workflow

1. Read the PRD requirement and linked tracker task before coding.
2. Record any material design decision in `docs/DECISIONS.md` or an ADR before implementing it.
3. Implement domain tests before or alongside service code.
4. Run formatter, linter/type checks, unit tests, and affected integration tests locally.
5. Update the tracker with direct evidence in the same change set.
6. Keep changes small: one coherent tracker task or a tightly coupled group.

## 10. Configuration and secrets

- Put only non-secret defaults in version control.
- Supply local secrets through an ignored `.env` file based on `.env.example`.
- Do not log provider credentials, uploaded full statement contents, access tokens, or API keys.
- Do not commit `.env`, tokens, actual merchant data, or unredacted screenshots.
- Keep the application usable with no LLM key by using a deterministic explanation mode.

## 11. Definition of done for a tracker task

A task is `Done` only when its acceptance condition is met, relevant automated tests pass, error behavior is considered, security/policy implications are covered, documentation is updated, and the tracker contains a concrete evidence link. Code that exists but cannot be demonstrated or verified remains `In progress`.
