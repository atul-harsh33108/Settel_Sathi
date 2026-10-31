# SettleSaathi

**An AI-powered merchant operations platform that takes settlement issues from investigation to verified resolution.**

SettleSaathi gives merchants one place to understand collections, expected settlements, provider-reported payouts, bank credits, and exceptions. Its bounded-autonomy AI teammate can investigate evidence, prepare or submit approved workflows, monitor cases, and verify outcomes without inventing financial facts.

## Product goal

Merchants often need to compare payment-provider transactions, settlement reports, bank statements, and support updates before they can answer a simple question: *Where is my money?* SettleSaathi normalizes those sources, reconciles them deterministically, and turns discrepancies into traceable resolution workflows.

## Core principles

- **Evidence before explanation.** Financial status comes from authorized source records and deterministic matching, never a model guess.
- **Bounded autonomy.** The agent may investigate and perform policy-approved actions; sensitive or irreversible actions require explicit authorization.
- **Provider-agnostic foundation.** Integrations are adapters over a canonical financial data model, not provider-specific logic scattered through the product.
- **Verified closure.** A case is closed only after authoritative evidence establishes its terminal outcome.
- **Auditable by default.** Decisions, evidence, tool actions, approvals, and case transitions are retained in an audit trail.

## MVP outcome

The first build will demonstrate one end-to-end, synthetic settlement-to-bank discrepancy:

1. Import payment transactions, settlement data, and a bank statement.
2. Reconcile the records using deterministic rules.
3. Identify a settlement reported as processed but absent from the bank statement.
4. Let the AI teammate explain the evidence and prepare a support case.
5. Require explicit authorization before simulated case submission.
6. Track the case and verify its terminal state.

The initial version uses synthetic data and mock connectors. It is **not** a live Paytm or banking integration.

## Documentation

| Document | Purpose |
| --- | --- |
| [Master PRD](SettleSaathi_PRD_v1.0.md) | Authoritative product requirements and functional specification. |
| [Implementation plan](docs/implementation/IMPLEMENTATION_PLAN.md) | Sequenced delivery plan, gates, and concrete outputs. |
| [Delivery tracker](docs/implementation/TRACKER.md) | The current source of truth for implementation status. |
| [Development guide](docs/DEV_DOC.md) | Engineering conventions, system boundaries, quality gates, and development workflow. |
| [High-level design](docs/HLD.md) | Release 0 data, system, integration, API, and deployment architecture. |
| [Data strategy](docs/DATA_STRATEGY.md) | Deterministic synthetic data design, fixtures, scenarios, and demo-data safeguards. |
| [Agentic architecture](docs/AGENTIC_ARCHITECTURE.md) | Bounded agent workflow, tools, evidence, approvals, verification, and evaluation design. |
| [Documentation management](docs/DOCUMENTATION_MANAGEMENT.md) | Ownership and update rules for product, planning, and engineering documentation. |
| [Architecture](docs/ARCHITECTURE.md) | System boundaries, canonical model, component responsibilities, and data flow. |
| [Security and governance](docs/SECURITY_GOVERNANCE.md) | Bounded-autonomy controls, financial safety rules, and audit requirements. |
| [Demo scenario](docs/DEMO_SCENARIO.md) | The hackathon-ready end-to-end walkthrough. |

## Intended technology direction

The implementation will be selected and documented before coding begins. The initial technical direction is a web dashboard, API service, deterministic reconciliation engine, persistent case workflow, integration adapters, and optional LLM orchestration. An LLM may interpret a merchant request and orchestrate approved tools, but it does not calculate balances or assert settlement facts.

## Status

Documentation baseline established on 31 October 2026. No production integrations or live financial actions are included in the initial scope.
