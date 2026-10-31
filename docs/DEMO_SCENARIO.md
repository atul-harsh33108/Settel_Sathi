# Demo Scenario: Missing Settlement Investigation

## Purpose

This synthetic scenario demonstrates SettleSaathi's central difference: it owns a settlement issue from evidence collection through verified outcome instead of behaving like a generic support chatbot.

## Scenario setup

All names, amounts, records, and outcomes are illustrative synthetic data.

The merchant asks:

> My records show ₹18,450 expected from yesterday's sales, but I cannot match it to my bank credit. Please investigate.

The imported dataset contains:

- completed payment transactions totaling ₹18,450;
- a provider settlement batch reporting a net payout of ₹18,450 with a payout reference;
- a bank statement that has no matching credit for that reference or amount during the imported period.

## Walkthrough

1. **Command Centre** — The dashboard displays collections, expected settlement, provider-reported payout, and bank-confirmed credit as distinct values. The provider payout is not treated as proof of bank credit.
2. **Reconciliation** — Deterministic matching links the transactions to the settlement batch. A settlement-to-bank exception is generated because the imported statement contains no qualified matching credit.
3. **Evidence-backed explanation** — The agent shows the contributing transactions, settlement ID, payout reference, and searched statement period. It says that the payout is provider-reported but has not been matched in the available bank data; it does not say the bank lost the funds.
4. **Next step** — The agent recommends checking the expected settlement window and, if the condition requires it, prepares a support-case draft containing the evidence pack.
5. **Approval gate** — The user reviews the payload and explicitly authorizes the simulated submission. Without approval, the case remains `Awaiting approval`.
6. **Monitoring** — The mock support connector posts an update. The case timeline records each event.
7. **Verification** — A synthetic updated bank record or an authoritative mock terminal response is ingested. The system verifies it against the original case and only then reaches a verified terminal outcome.

## What this proves

- Cross-source financial reconciliation.
- Clear distinction between facts and uncertainty.
- Bounded agent behavior with a human approval gate.
- Persistent, auditable case ownership.
- Verified closure rather than a conversational claim of success.

## Judge-facing narrative

“A merchant should not need to become a reconciliation expert to know what happened to a settlement. SettleSaathi connects the evidence, determines the right next step, carries the case forward with permission, and closes it only when the outcome is verified.”
