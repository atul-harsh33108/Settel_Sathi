# Managing the Three Documentation Types

SettleSaathi uses three complementary documentation types. They have different jobs and must not be merged into one ever-growing file.

| Type | Canonical location | Answers | Update trigger | Owner |
| --- | --- | --- | --- | --- |
| Product documentation | [Master PRD](../SettleSaathi_PRD_v1.0.md) | What are we building, for whom, why, and under what product/safety requirements? | Product decision, scope change, acceptance-criteria change, or new user need. | Product owner, reviewed by engineering. |
| Planning and tracking | [Implementation plan](implementation/IMPLEMENTATION_PLAN.md) and [tracker](implementation/TRACKER.md) | In what order will we build it, what is happening now, and what blocks delivery? | Milestone/task change, status change, dependency, risk, or evidence of completion. | Delivery lead / active implementer. |
| Development documentation | [Development guide](DEV_DOC.md), architecture, security, and decision records | How is it built, tested, secured, and operated? | Material technical decision, interface/schema change, development convention, or operational learning. | Engineering owner, reviewed by affected developers. |

## The source-of-truth rule

- The **PRD** is authoritative for product intent, requirements, scope, user outcomes, and product acceptance.
- The **implementation plan** is authoritative for sequence, deliverables, dependencies, and release gates.
- The **tracker** is authoritative for current execution status.
- The **development documentation** is authoritative for engineering method and technical constraints.

If two documents disagree, do not silently update only one. Resolve the decision with the document owner and update every affected source in the same change set.

## Change flow

```text
New information or request
        |
        +--> Changes what/why? ------> Update PRD
        |
        +--> Changes order/scope of work? -> Update plan + tracker
        |
        +--> Changes how we build safely? -> Update DEV_DOC / architecture / decision record
        |
        +--> Changes more than one? -----> Update each affected document together
```

## Working rules

1. **Plan before implementation.** Each coding change maps to a tracker ID and a PRD requirement or acceptance criterion.
2. **Track facts, not aspirations.** Mark `Done` only with verifiable evidence: tests, a code path, a demo, or a reviewed artifact.
3. **Keep the PRD stable.** Routine implementation progress belongs in the tracker, not in product requirements.
4. **Keep technical detail out of the tracker.** Link to the DEV document, an architecture section, a decision record, code, or test instead of duplicating design prose.
5. **Record decisions promptly.** A decision that affects code structure, a data contract, policy, or future cost must be recorded before it becomes accidental architecture.
6. **Review at milestones.** Before moving a milestone to `Done`, review PRD acceptance, plan exit gate, tests, and documentation together.

## Suggested cadence

| Moment | Required update |
| --- | --- |
| Before beginning a milestone | Confirm PRD scope; decompose the plan into tracker rows; identify technical decisions. |
| During implementation | Update task status and blockers; add development notes when the design changes. |
| On completing a task | Add evidence to tracker; update DEV documentation if behavior or contracts changed. |
| On changing product scope | Update PRD first, then assess plan, tracker, architecture, tests, and demo impact. |
| Before a demo/release | Reconcile tracker evidence against the PRD acceptance criteria and release gate. |

## Change-control examples

| Change | Documents to update |
| --- | --- |
| Add a new payment-provider adapter | PRD integration scope, plan, tracker, architecture, connector/development contract. |
| Change the CSV schema | DEV document and architecture; tracker if planned work changes; PRD only if user capability changes. |
| Add approval before a support-case submission | PRD governance requirement, plan/tracker, DEV contract, security documentation, and tests. |
| Fix a reconciliation bug without changing behavior | Tracker evidence and tests; DEV docs only if it exposes a missing rule or convention. |

## Document hygiene

- Use Markdown and relative links.
- Date and summarize material changes in the tracker or a decision record.
- Keep secrets, personal data, and real merchant financial records out of documentation.
- Label all sample data as synthetic.
- Prefer a link to the canonical source over copying the same requirement into several documents.
