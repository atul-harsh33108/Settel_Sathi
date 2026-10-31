# Security and Governance

## Purpose

SettleSaathi handles sensitive merchant-financial information. Its design must ensure that automation is useful without becoming an unaccountable actor.

## Bounded-autonomy model

| Level | Agent capability | Example |
| --- | --- | --- |
| Observe | Read authorized data and identify a condition | Find an unmatched provider payout. |
| Explain | Summarize evidence and uncertainty | Explain that no matching bank entry appears in the imported statement period. |
| Recommend | Propose an allowed next step | Recommend waiting, uploading a later statement, or preparing a case. |
| Draft | Generate an action payload for review | Draft a support-case description and evidence pack. |
| Execute | Perform a policy-approved action | Submit a mock case after explicit authorization. |
| Verify | Re-read authoritative sources before closure | Confirm a bank-credit or terminal support outcome. |

The MVP permits observation, explanation, recommendation, drafting, and approval-gated simulated execution. It does not permit moving money or altering payment/bank-account details.

## Authorization controls

- Enforce role-based and organization-scoped access.
- Treat connector credentials as secrets and grant least privilege.
- Bind every external action to a case, policy decision, actor, and approval when required.
- Use idempotency keys for imports and external action attempts.
- Require a fresh confirmation for actions that could create external commitments.
- Expose clear action previews before approval.

## Financial integrity controls

- Store money as decimal fixed-precision values, never binary floating point.
- Preserve original source data, normalized data, ingestion time, and source identifiers.
- Version matching rules and retain their input evidence.
- Keep collection, provider settlement, and bank credit as separate states.
- Do not infer finality from missing data or a delayed import.
- Block closure without defined verification evidence.

## Audit requirements

Every important event records:

- actor (human, service, or agent);
- timestamp;
- affected organization and data scope;
- action or state transition;
- policy and rule version;
- source evidence references;
- approval reference, where applicable; and
- outcome, error, or retry information.

Audit logs should be append-only at the application boundary. Sensitive raw values must be protected according to production retention and access policies.

## AI-specific safeguards

- Supply the model only the minimally necessary, authorized data.
- Ground explanations in retrieved evidence.
- Label unresolved ambiguity explicitly.
- Treat tool outputs as untrusted until validated by application code.
- Never let generated text directly execute privileged actions.
- Evaluate for false diagnoses, unsafe actions, and false closure before enabling broader autonomy.

## Production readiness prerequisites

Before any live connector is enabled, the team must verify the provider's data contract, authentication method, permissions, rate limits, webhook verification, error semantics, retention obligations, and approved support workflow. A mock API or synthetic schema is never evidence of production compatibility.
