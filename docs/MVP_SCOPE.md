# MVP Scope

## Objective

Prove that SettleSaathi can turn a merchant's settlement concern into an evidence-backed, policy-controlled, verified workflow.

## Included

### Data and connectors

- Synthetic payment transaction file.
- Synthetic settlement file, including a settlement/payout reference.
- CSV bank-statement import.
- Mock support-case service.
- Connector status and ingestion history.

### Reconciliation

- Canonical records for transactions, settlement batches, settlement line items, bank entries, and cases.
- Deterministic transaction-to-settlement and settlement-to-bank matching.
- Duplicate detection.
- Clear exception classifications: within expected window, delayed, partially matched, unmatched, and adjustment-explained.
- Evidence links from each result to its source records.

### Merchant workflow

- Dashboard with collections, expected settlement, provider-reported settlement, bank-confirmed credit, and exceptions as distinct values.
- Exception detail view with an evidence-backed explanation.
- Conversational trigger for an investigation.
- Case creation and event timeline.
- Explicit approval gate before simulated support-case submission.
- Recheck and verified closure path.

### Safety and testing

- Role and policy checks around simulated external actions.
- Append-only audit events.
- Automated tests for matching rules, duplicate ingestion, workflow transitions, approval enforcement, and false-closure prevention.

## Explicitly excluded

- Real provider credentials, webhooks, or bank connections.
- Real ticket submission to Paytm or another provider.
- Payment initiation, refunds, or account-detail changes.
- Production authentication, billing, multi-tenant isolation, and full accounting integrations.
- Voice interface and broad multilingual support.

## Definition of done

The MVP is complete when a reviewer can load the synthetic scenario and observe all of the following:

1. A merchant's expected settlement is calculated from source transactions.
2. The provider settlement record is distinct from the bank-credit record.
3. The reconciliation engine detects the absence of a matching bank credit.
4. The agent uses stored evidence to explain the condition without asserting that funds are lost.
5. A case cannot be submitted until a user explicitly approves it.
6. The case timeline records the authorization and simulated external action.
7. Closure occurs only after a terminal outcome is supported by authoritative mock evidence.

## Acceptance scenarios

| Scenario | Expected outcome |
| --- | --- |
| A bank credit matches a settlement reference and amount | Reconciled, with evidence. |
| Provider reports a settlement but bank statement has no match within its imported period | Settlement-to-bank mismatch; investigation or wait state, not a claim of loss. |
| Expected and provider-reported totals differ because of documented adjustments | Adjustment-explained exception. |
| An action needs approval | Workflow remains pending authorization. |
| Case receives verification evidence | Case can move to verified closure. |
