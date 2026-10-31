# SettleSaathi Product Requirements Document

**Version:** 1.0  
**Date:** 31 October 2026  
**Status:** Product-definition baseline

## 1. Executive summary

SettleSaathi is a provider-agnostic, AI-powered merchant operations platform. It brings payment transactions, settlement records, bank credits, and case workflows into one operational view. It then uses deterministic reconciliation and bounded AI automation to investigate discrepancies, prepare approved actions, monitor progress, and verify closure.

The central promise is simple: **from collected payments to verified bank settlement.**

## 2. Problem statement

Merchants often receive payment events, settlement reports, bank credits, refunds, reversals, and support updates in separate systems. When a settlement appears delayed or incomplete, they must manually find source records, compare references and amounts, understand adjustment entries, and follow up with support.

Existing dashboards show records; they seldom own the resolution workflow. SettleSaathi converts a discrepancy into an evidence-backed, traceable case.

## 3. Users and experiences

| Persona | Primary need | Experience |
| --- | --- | --- |
| Small merchant | Know daily collections, expected payout, and why a credit is pending | Simple Merchant Mode |
| Growing business owner | Consolidate channels and compare stores | Business Operations Mode |
| Finance manager/accountant | Reconcile at transaction level and export audit-ready results | Advanced Finance Console |
| Operations/support manager | Prioritize, investigate, escalate, and track recurring cases | Operations Console |

## 4. Core modules

| ID | Module | Objective |
| --- | --- | --- |
| M01 | Merchant Command Centre | Present the current financial position and exceptions. |
| M02 | Unified Financial Data Hub | Connect, validate, normalize, and monitor source data. |
| M03 | Smart Reconciliation Engine | Match transaction, settlement, adjustment, and bank records. |
| M04 | Autonomous AI Teammate | Investigate and run policy-controlled workflows. |
| M05 | Case and Resolution Management | Own the lifecycle from detection through verified closure. |
| M06 | Monitoring and Alerts | Detect anomalies and missed operational deadlines. |
| M07 | Financial Intelligence | Provide trends, reports, and operational insights. |
| M08 | Multi-Store and Multi-Account Management | Segment data by entity, store, account, and provider. |
| M09 | Conversational Interface | Support plain-language, multilingual merchant questions. |
| M10 | Security and Governance | Enforce access control, authorization, and auditability. |

## 5. Functional requirements

### M01 — Merchant Command Centre

- **FR-001:** Show successful payment collections for a selected period.
- **FR-002:** Show expected settlement value separately from provider-reported settlement value.
- **FR-003:** Show bank credits matched to settlement records.
- **FR-004:** Show pending, partially settled, unmatched, refund, reversal, and chargeback amounts separately.
- **FR-005:** Show open discrepancies, active investigations, and active support cases.
- **FR-006:** Filter by date, provider, bank account, store, and payment method.
- **FR-007:** Offer simplified and advanced presentation modes without changing underlying facts.

### M02 — Unified Financial Data Hub

- **FR-008:** Register multiple provider accounts and multiple merchant bank accounts.
- **FR-009:** Import authorized API, webhook, CSV, XLSX, and supported bank-statement sources.
- **FR-010:** Normalize inputs into a common financial schema while preserving original references and ingestion timestamps.
- **FR-011:** Detect duplicate imports and webhook deliveries.
- **FR-012:** Display connector health, last successful synchronization, and failures.
- **FR-013:** Classify each connector accurately as native, file, partner, or planned.

### M03 — Smart Reconciliation Engine

- **FR-014:** Match payment transactions to settlement line items.
- **FR-015:** Match settlement payouts to bank credits using references, amounts, dates, and defined tolerances.
- **FR-016:** Support one-to-one, many-to-one, and one-to-many matching.
- **FR-017:** Identify missing, duplicate, partial, delayed, unmatched, and adjustment-explained records.
- **FR-018:** Give every match and exception an explainable reason and confidence based on deterministic rules.
- **FR-019:** Preserve source evidence for each reconciliation result.

### M04 and M05 — AI teammate and case management

- **FR-020:** Accept a merchant question or system-detected exception as an investigation trigger.
- **FR-021:** Retrieve scoped evidence only from connected and authorized sources.
- **FR-022:** Produce an explanation that distinguishes observed facts from assumptions.
- **FR-023:** Recommend the correct next workflow: wait, request information, prepare a case, escalate, or close with evidence.
- **FR-024:** Require explicit authorization before policy-designated external or consequential actions.
- **FR-025:** Create a case timeline containing evidence, decision, approval, action, response, and verification events.
- **FR-026:** Recheck authoritative data before closing a case.
- **FR-027:** Escalate unresolved, contradictory, or policy-blocked cases to a human.

### M06 through M10 — operational platform capabilities

- **FR-028:** Alert users to delayed settlements, stale cases, failed connectors, and anomalous reconciliation patterns.
- **FR-029:** Support organization, store, provider, account, and role-based access boundaries.
- **FR-030:** Generate exportable operational and reconciliation reports.
- **FR-031:** Support multilingual text interactions after language capability validation.
- **FR-032:** Retain an immutable audit record for data ingestion, reconciliation, agent reasoning summary, approvals, and tool execution.

## 6. Non-functional requirements

- **Accuracy:** Financial totals and match results must be reproducible from stored source records and rule versions.
- **Security:** Credentials and uploaded data must be protected; least-privilege access applies to every connector.
- **Privacy:** Only data necessary to the requested workflow may be shown to a user or supplied to an AI service.
- **Reliability:** Imports and external workflow actions must be idempotent and retry-safe.
- **Explainability:** A user can inspect why a result occurred and which source evidence supported it.
- **Observability:** The platform records connector health, workflow failures, action attempts, and verification outcomes.

## 7. Success measures

Initial evaluation uses curated synthetic cases. Proposed measures are:

- Reconciliation accuracy and coverage.
- Percentage of exceptions automatically classified with sufficient evidence.
- Time to prepare a support case.
- Duplicate-case rate.
- Time to verified resolution.
- False-closure rate.
- Percentage of agent actions completed within policy.

## 8. Out of scope for the first release

- Initiating payments, changing payout accounts, or moving funds.
- Claiming live support, bank, or payment-provider integrations without approved credentials and a verified contract.
- Replacing a provider's regulated dispute or grievance process.
- Fully autonomous action where approval policy requires a human.
