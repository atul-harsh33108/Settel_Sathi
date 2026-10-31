# Product Decisions

This document records the decisions already made for SettleSaathi. New implementation choices must preserve these constraints unless this document is intentionally revised.

| Area | Decision | Implication |
| --- | --- | --- |
| Product identity | AI-powered merchant operations platform | Build a workflow platform, not a Paytm-only dashboard or generic support chatbot. |
| Primary users | Small merchants, growing businesses, multi-location businesses, finance and operations teams | Support a simple merchant experience and an advanced operations experience over the same underlying data. |
| Data integration | Multi-provider | Use a canonical financial model and connector adapters; add providers incrementally. |
| Agent autonomy | Bounded | Separate observation, recommendation, authorized action, and verification. |
| Financial logic | Deterministic | Reconciliation, amount calculations, matching, and permissions must be executable code with evidence. |
| Product scope | Platform foundation, focused MVP | Start with one high-confidence settlement-discrepancy flow rather than many incomplete features. |
| Launch data | Synthetic and mock connectors | Do not imply live Paytm, bank, or support-system access in the MVP. |
| Hackathon runtime | Self-contained modular monolith | Use SQLite, local private artifact storage, FastAPI/Uvicorn, `uv`, and a project-local `.venv`; no Postgres, Redis, or queue infrastructure. |
| Documentation diagrams | Mermaid | Use Mermaid for all new architecture, sequence, state, and entity-relationship diagrams. |

## Non-negotiable product truths

1. Successful collection, provider-reported settlement, and bank-confirmed credit are different financial states and must remain separately visible.
2. An absence in an imported bank statement is not proof that money is missing. The product must consider the statement period, expected settlement window, and available source records.
3. The agent must not transfer funds, change bank details, submit a sensitive request, or claim resolution without an applicable policy and, where required, user approval.
4. A planned connector must never be displayed as an active integration.
5. Every generated explanation must be traceable to its evidence and clearly distinguish facts, assumptions, and requested information.

## Initial connector sequence

1. Synthetic Paytm-style transaction and settlement files.
2. Generic CSV/XLSX bank-statement import.
3. Mock support-case connector.
4. Authorized provider or sandbox connector only after a verified data contract is available.

## Deferred decisions

- Exact live-provider access method and merchant onboarding requirements.
- Accounting, POS, e-commerce, and ERP connector priorities.
- Identity provider, production database, hosting, and data-retention periods.
- Commercial packaging and pricing.
- Final language/voice-model provider.
