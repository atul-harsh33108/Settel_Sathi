# SettleSaathi
## Product Requirements Document (PRD) and Functional Specification

| Document metadata | Value |
|---|---|
| Product | SettleSaathi |
| Document type | Product Requirements Document + Functional Specification |
| Version | 1.0 |
| Status | Product baseline for discovery, design and engineering planning |
| Date | 31 October 2026 |
| Product category | AI-powered Merchant Financial Operations Platform |
| Primary users | Small merchants, growing businesses, multi-location businesses, finance and operations teams |
| Integration strategy | Multi-provider, adapter-based; APIs, webhooks, reports and bank-statement imports |
| Agent autonomy | Bounded autonomy, with policy-controlled execution and human approval for restricted actions |
| Product positioning | **Your autonomous financial operations teammate** |

> **Purpose of this document**  
> This PRD defines what SettleSaathi is, who it serves, what users should be able to do, how the autonomous teammate is allowed to operate, which systems it must integrate with, and how the product will be evaluated. It is the product baseline for subsequent UX design, system architecture, implementation planning and testing. It is not a claim that every described integration is already available or approved.

---

# 1. Executive Summary

SettleSaathi is a multi-provider, AI-powered merchant operations platform that helps businesses understand, monitor, reconcile and resolve financial operations across payment providers, bank accounts and business systems.

Merchants commonly work across multiple payment provider dashboards, transaction reports, settlement files, bank statements, accounting tools and support channels. When records do not line up, a merchant or finance employee may have to manually identify the affected transactions, determine what happened, gather evidence, contact a provider and follow up until the issue is resolved.

SettleSaathi brings these activities into one operational workspace. It normalizes financial records from supported sources, reconciles payment transactions with settlement records and bank credits, identifies exceptions, and provides an AI teammate that can investigate issues and carry out permitted workflow actions.

The AI teammate is not the financial system of record. Authoritative payment facts, monetary calculations, reconciliation matches, permissions and case-closure conditions are handled by deterministic services and verified source records. The AI interprets requests, coordinates tools, explains evidence and recommends or executes workflows within explicit policies.

## 1.1 Product vision

Become the intelligent operations layer between merchants and their financial infrastructure.

## 1.2 Product mission

Reduce the manual work required to understand, monitor, reconcile and resolve merchant financial operations.

## 1.3 Core value proposition

- **Visibility:** Give merchants one view of collections, settlements, bank credits, refunds, exceptions and active cases.
- **Intelligence:** Explain financial discrepancies using records and traceable evidence.
- **Autonomy:** Investigate issues, execute permitted workflow actions, monitor progress and verify outcomes.
- **Interoperability:** Work across multiple payment providers and supported banking-data sources instead of assuming one provider's data model.
- **Control:** Keep merchants and authorized employees in control of consequential actions.

## 1.4 Product principles

1. **Evidence before explanation.** Every financial statement must be traceable to source records.
2. **Deterministic money, AI-assisted operations.** Monetary arithmetic and financial status validation must not depend on LLM output.
3. **Bounded autonomy.** An agent may only act inside permissions, policy and authorization constraints.
4. **Provider neutrality.** Provider-specific formats are contained in adapters; domain logic uses a canonical data model.
5. **No false completion.** A case is not resolved merely because a tool call succeeded or an agent said so.
6. **Human escalation is a feature.** Ambiguous, high-risk or unsupported situations must be handed to an authorized human.
7. **Progressive delivery.** Start with a complete, reliable workflow and expand providers and capabilities incrementally.
8. **Privacy by design.** Collect, process and retain only the information needed for an explicit product purpose.

---

# 2. Product Definition and Scope

## 2.1 What SettleSaathi is

SettleSaathi is a merchant financial operations platform with the following capabilities:

- Consolidate financial records from connected payment providers and supported bank-data sources.
- Reconcile payment transactions, settlement entries, adjustments and bank credits.
- Identify missing, partial, delayed, duplicate, reversed or unmatched records.
- Investigate exceptions using source-backed evidence.
- Create and manage investigation cases.
- Execute authorized internal and external workflow actions.
- Monitor provider events and case updates.
- Generate operational reports and business insights.
- Support single-store and multi-location organizations.
- Offer a conversational interface for natural-language financial operations requests.

## 2.2 What SettleSaathi is not

The initial product is not intended to:

- Operate as a payment gateway, payment aggregator, bank or wallet.
- Hold, move, route or settle customer or merchant funds.
- Replace payment providers' authoritative transaction or settlement records.
- Guarantee recovery of missing funds or guarantee provider response times.
- Make autonomous lending, underwriting or credit decisions.
- Adjudicate fraud as a legal or definitive fact based solely on anomaly detection.
- Perform unauthorized scraping of provider dashboards.
- Collect UPI PINs, OTPs, CVVs, bank passwords or other authentication secrets.
- Execute unrestricted financial transactions through an LLM.

## 2.3 Product boundaries

SettleSaathi is an orchestration, reconciliation and operational intelligence layer. Payment acceptance, settlement execution, bank account servicing and provider-side complaint resolution remain responsibilities of the relevant authorized institutions and systems.

## 2.4 Product modes

The application should adapt to user needs without splitting into unrelated products.

| Mode | Intended user | Experience |
|---|---|---|
| Simple Merchant Mode | Shopkeeper or small business owner | Clear summaries, conversational questions, alerts and guided case resolution |
| Business Operations Mode | Growing business owner or multi-location manager | Store comparisons, provider breakdowns, operational trends and case assignments |
| Finance Console | Accountant or finance manager | Detailed records, reconciliation queues, exports, adjustments and audit trails |
| Operations Console | Support or operations manager | Case queues, prioritization, assignment, approvals, escalations and performance measures |
| Auditor / Read-only Mode | Internal or external reviewer | Read-only access to records, match evidence and action history according to permission |

---

# 3. Goals, Non-Goals and Success Criteria

## 3.1 Product goals

**G-01 — Unified financial visibility:** Provide a consolidated view of authorized payment and bank records across supported sources.

**G-02 — Reliable reconciliation:** Identify and explain matches and exceptions between transactions, settlements and bank credits.

**G-03 — Autonomous investigation:** Allow the AI teammate to investigate a well-scoped issue using approved tools and verified records.

**G-04 — Controlled workflow execution:** Execute permitted actions while enforcing approval and authorization requirements outside the LLM.

**G-05 — Verified resolution:** Track cases until they reach a supported terminal state, with evidence for closure or escalation.

**G-06 — Multi-provider extensibility:** Add providers through independent adapters without rewriting core financial logic.

**G-07 — Merchant accessibility:** Make complex financial operations understandable to users with different levels of technical and financial expertise.

## 3.2 Non-goals for the first release

- Supporting every payment provider at launch.
- Real-time access to every bank account.
- Performing direct fund transfers or refunds.
- Replacing full accounting, ERP or enterprise resource planning products.
- Building a general-purpose autonomous agent platform.
- Building predictive financial forecasting before reliable historical data is available.
- Claiming fraud detection or fraud prevention without validated models and operational processes.
- Launching all Indian languages simultaneously.

## 3.3 North Star metric

**Verified Settlement Reconciliation Rate**

The share of eligible settlement value that is matched to authoritative provider and bank records within the applicable expected settlement window.

The metric must distinguish confirmed matches from candidate matches, pending amounts, estimated values and unresolved exceptions. The denominator and exclusions must be defined consistently for every report.

## 3.4 Supporting KPIs

| KPI | Definition | Measurement considerations |
|---|---|---|
| Automatic Match Rate | Eligible records matched without manual intervention | Report by provider and match method |
| Reconciliation Accuracy | Audited automatic matches that are correct | Use sampled manual audits and known test fixtures |
| False Match Rate | Incorrect matches divided by confirmed automatic matches | Critical trust metric; monitor separately |
| Exception Precision | Detected exceptions confirmed as genuine | Label outcomes using review data |
| Mean Time to Detect | Time from source-data availability to exception creation | Exclude periods where source data was unavailable, but report them separately |
| Mean Time to Resolve | Time from case creation to verified terminal outcome | Segment by issue type and external dependency |
| Evidence Completeness | Cases containing all required evidence for their type | Define required evidence per case category |
| Agent Tool Success Rate | Successful tool executions divided by attempted executions | Distinguish tool success from business outcome success |
| Human Escalation Rate | Eligible cases escalated to a human | A lower rate is not always better; safe escalation is desirable |
| False Closure Rate | Cases closed without satisfying closure conditions | Zero-tolerance target for production workflows |
| Unauthorized Action Rate | Restricted actions executed without required authorization | Zero-tolerance target |
| Merchant Time Saved | Self-reported or measured reduction in manual effort | Establish a baseline before reporting improvement |
| Active Merchant Rate | Merchants actively using core workflows in a defined period | Define active use beyond login activity |

Targets must be set after baseline measurement and pilot validation. Do not present unmeasured improvements as achieved results.

---

# 4. Users, Personas and Jobs-to-be-Done

## 4.1 Persona A — Small merchant / shopkeeper

**Profile:** One or a few outlets; accepts UPI, QR and other digital payments; may not have dedicated finance staff; may prefer simple language or voice interaction.

**Jobs-to-be-done:**
- Understand how much was collected today or yesterday.
- Understand how much is expected to reach the bank.
- Know whether a settlement is still within its expected processing window.
- Get a simple explanation when records do not match.
- Raise and track a support issue without learning provider-specific terminology.

**Pain points:** Multiple dashboards, unclear settlement terminology, limited time, difficulty preparing evidence and repeated follow-up.

**Product experience:** Simple Merchant Mode, prominent status explanations and a task-oriented assistant.

## 4.2 Persona B — Growing business owner

**Profile:** Several payment channels, multiple employees, one or more locations, increased transaction volume and some accounting processes.

**Jobs-to-be-done:**
- Compare collections and settlement performance across locations.
- Monitor payment providers and bank accounts.
- Identify operational patterns and repeated issues.
- Delegate case follow-up.
- Understand the business-wide financial operations position.

**Product experience:** Business Operations Mode with consolidated and location-level views.

## 4.3 Persona C — Finance manager / accountant

**Profile:** Responsible for reconciling transactions, settlements, bank statements, fees, refunds and reporting.

**Jobs-to-be-done:**
- Import and validate financial files.
- Match transactions to settlement entries and bank credits.
- Review unmatched records and low-confidence candidates.
- Explain differences and adjustments.
- Export data for accounting and audit workflows.

**Product experience:** Finance Console with detailed tables, filters, review queues, exports and traceable match evidence.

## 4.4 Persona D — Operations / support manager

**Profile:** Manages unresolved merchant issues and coordinates with providers or internal finance teams.

**Jobs-to-be-done:**
- See all open cases and their age, severity and owner.
- Prioritize and assign cases.
- Review agent investigation evidence.
- Approve restricted actions.
- Monitor provider responses and escalation deadlines.

**Product experience:** Operations Console with case queues, approvals, assignments and workflow timelines.

## 4.5 Persona E — Auditor / read-only reviewer

**Profile:** Needs to inspect financial provenance, reconciliation methods and system actions without modifying records.

**Jobs-to-be-done:**
- Trace a summary number to underlying source records.
- Inspect match decisions and manual overrides.
- Review agent actions and approvals.
- Export authorized evidence.

**Product experience:** Read-only access, audit views and immutable event history where technically appropriate.

---

# 5. Information Architecture and Application Navigation

The application should have a consistent navigation structure with role-based visibility and authorization.

## 5.1 Proposed primary navigation

1. **Overview** — Merchant command centre.
2. **Transactions** — Payment records, refunds, reversals and status history.
3. **Settlements** — Batches, settlement entries, expected dates and payout references.
4. **Reconciliation** — Matching workspace, review queue and exceptions.
5. **Cases** — Investigations, support requests, approvals and escalations.
6. **AI Teammate** — Conversational assistant and active agent tasks.
7. **Insights** — Business analytics and operational reports.
8. **Locations** — Store and entity management.
9. **Connections** — Payment providers, bank-data sources and business integrations.
10. **Team & Permissions** — Users, roles, policies and approvals.
11. **Audit & Activity** — Record provenance and consequential action history.
12. **Settings** — Organization settings, notifications, language and security.

## 5.2 Global interface elements

- Organization and location selector.
- Date-range selector.
- Provider/account filter.
- Global search across permitted records and cases.
- Notifications and action-required indicator.
- AI teammate entry point.
- User profile and organization context.
- Data synchronization health indicator.

## 5.3 Dashboard requirements

The overview should display distinct financial concepts rather than combine them into one ambiguous balance:

- Gross successful collections.
- Refunds and reversals.
- Provider-reported settlement amount.
- Expected settlement amount, with schedule and assumptions.
- Bank credits matched to settlements.
- Pending or unmatched settlement value.
- Open discrepancies and their age.
- Active support cases.
- Last successful data synchronization for each source.

Every KPI must show its date range, currency, source coverage and, where relevant, whether it is actual, expected, estimated or pending.

---

# 6. Functional Requirements

Requirements use stable identifiers so they can be mapped to design tickets, API specifications and acceptance tests.

Priority definitions:

- **P0 — Release-critical:** Required for the first end-to-end merchant workflow.
- **P1 — Important:** Required for a credible pilot or early expansion.
- **P2 — Later:** Valuable capability that should not delay the core workflow.

## 6.1 M01 — Merchant Command Centre

**Objective:** Provide a unified view of financial operations for the selected organization, location, provider and time range.

| ID | Requirement | Priority |
|---|---|---|
| FR-001 | Display successful payment collections for a selected period. | P0 |
| FR-002 | Display provider-reported settlements separately from expected settlements. | P0 |
| FR-003 | Display bank credits matched to settlement records. | P0 |
| FR-004 | Display pending, partial, unmatched and delayed amounts distinctly. | P0 |
| FR-005 | Display refunds, reversals, chargebacks and adjustments where source data supports them. | P1 |
| FR-006 | Display discrepancy count, amount and aging. | P0 |
| FR-007 | Display active investigations and action-required cases. | P0 |
| FR-008 | Filter views by date, provider, account, location and payment method. | P1 |
| FR-009 | Provide simplified and advanced dashboard modes. | P1 |
| FR-010 | Show source coverage and last synchronization time for displayed data. | P0 |
| FR-011 | Allow authorized users to drill from an aggregate to underlying records. | P0 |
| FR-012 | Export authorized dashboard data to supported formats. | P1 |

**Acceptance criteria:**
- Every financial aggregate is reproducible from the displayed underlying records and calculation definition.
- Pending and unmatched values are not presented as confirmed losses.
- Provider-reported settlement is not presented as bank-confirmed credit.
- Stale or unavailable data is clearly labelled.
- A user cannot drill into a record outside their organization or permitted location scope.

## 6.2 M02 — Unified Financial Data Hub

**Objective:** Connect financial data from multiple payment providers, banking-data sources and business systems through an adapter-based integration layer.

### Integration categories

**Payment providers:** Paytm, Razorpay, Cashfree, PhonePe Payment Gateway and additional providers selected through customer demand and technical validation.

**Banking data:** CSV/XLSX statements, supported PDF statements and approved banking-data integrations.

**Business systems:** POS, accounting, ERP, billing and e-commerce systems where an authorized interface exists.

| ID | Requirement | Priority |
|---|---|---|
| FR-013 | Allow an authorized organization administrator to register provider accounts. | P0 |
| FR-014 | Support multiple provider accounts per organization. | P1 |
| FR-015 | Support multiple bank accounts per authorized business entity. | P1 |
| FR-016 | Support authorized API-based, read-only integrations. | P0 |
| FR-017 | Support webhook ingestion where the provider offers it. | P1 |
| FR-018 | Support scheduled synchronization and manual refresh. | P0 |
| FR-019 | Support CSV and XLSX uploads using validated mapping templates. | P0 |
| FR-020 | Support selected bank-statement PDF formats with extraction review. | P1 |
| FR-021 | Normalize provider data into canonical internal records. | P0 |
| FR-022 | Preserve provider-specific fields and original source references. | P0 |
| FR-023 | Detect duplicate file imports and duplicate webhook deliveries. | P0 |
| FR-024 | Display connector status, last synchronization and failure reason. | P0 |
| FR-025 | Support credential rotation, revocation and reauthorization. | P1 |
| FR-026 | Prevent a connector from reading data outside its granted scopes. | P0 |

**Provider integration classification:**

- **Native connector:** Implemented and tested with authorized API access.
- **File connector:** Supported import of provider-generated reports.
- **Partner connector:** Implemented through an authorized partner service.
- **Planned connector:** Not yet available; must not be represented as connected.

**Acceptance criteria:**
- A provider connector translates data into the canonical model without leaking provider-specific assumptions into reconciliation logic.
- Every ingested record retains its source provider, account, external reference and ingestion timestamp.
- Reprocessing the same file or webhook does not create duplicate financial records.
- Connector failure does not corrupt previously ingested records.
- The user can see whether displayed data is current, delayed, incomplete or unavailable.

## 6.3 M03 — Smart Reconciliation Engine

**Objective:** Reconcile payment transactions, settlement entries, adjustments and bank credits using explainable, deterministic logic.

### Record classes

1. Payment transaction.
2. Refund and reversal.
3. Settlement batch.
4. Settlement line item.
5. Fee, tax and adjustment.
6. Provider payout.
7. Bank statement entry.
8. Reconciliation match and exception.

| ID | Requirement | Priority |
|---|---|---|
| FR-027 | Match payment transactions to settlement line items. | P0 |
| FR-028 | Match settlement payouts to bank statement credits. | P0 |
| FR-029 | Support one-to-one, one-to-many and many-to-one matching. | P0 |
| FR-030 | Identify partial settlements. | P0 |
| FR-031 | Identify missing, duplicate and unmatched transactions. | P0 |
| FR-032 | Identify unmatched bank credits. | P0 |
| FR-033 | Account for supported fees, taxes, refunds, reversals and adjustments. | P0 |
| FR-034 | Support provider- and product-specific settlement schedules. | P0 |
| FR-035 | Produce an explanation and provenance for each match or exception. | P0 |
| FR-036 | Provide candidate matches when exact references are unavailable. | P1 |
| FR-037 | Require review for ambiguous or low-confidence matches. | P0 |
| FR-038 | Allow authorized manual review and correction. | P1 |
| FR-039 | Preserve a history of match creation, changes and overrides. | P0 |
| FR-040 | Re-run reconciliation safely when new source data arrives. | P0 |
| FR-041 | Provide reconciliation reports and exception exports. | P1 |

### Matching approach

**Level 1 — Exact identifiers:** UTR, payout ID, settlement reference, provider transaction ID or another provider-authoritative reference.

**Level 2 — Composite matching:** Merchant account, amount, currency, date/time window, settlement batch and transaction type.

**Level 3 — Candidate matching:** Generate possible matches where exact references are absent. Candidate matching must include a confidence value and the evidence used. It must not silently become a confirmed match.

### Reconciliation statuses

- Matched
- Partially matched
- Unmatched
- Pending
- Delayed
- Failed
- Reversed
- Under investigation
- Manually verified
- Excluded with reason

### Financial correctness rules

- Use integer minor units (for INR, paise) or exact decimal arithmetic for monetary calculations.
- Never use binary floating-point arithmetic for authoritative monetary calculations.
- Preserve gross collection, refund/reversal, fee/tax/adjustment, net settlement and bank credit as distinct fields or linked records.
- Calculate expected settlement dates using provider-, product- and merchant-specific rules.
- Do not classify a missing bank entry as lost funds without authoritative evidence.
- Do not infer a fee or adjustment solely to make amounts balance.
- Keep original and normalized statuses separately.

**Acceptance criteria:**
- The same source data produces the same deterministic match output under the same rules version.
- Every match identifies the records, method, rule version and evidence used.
- A candidate match is not represented as a confirmed match.
- Partial settlement and consolidated bank payout scenarios are tested.
- Refunds, reversals, fees and adjustments are not double-counted.
- Reconciliation can be safely repeated without duplicate matches or duplicate exceptions.

## 6.4 M04 — Autonomous AI Teammate

**Objective:** Understand merchant requests, investigate financial issues, select appropriate workflows and execute actions within explicit authorization policies.

### Example requests

- "Why is yesterday's settlement pending?"
- "Find all transactions collected but not settled."
- "Investigate the ₹5,000 difference in my bank statement."
- "Which store has the highest number of failed settlements?"
- "Prepare a support request for the missing payout."
- "What happened to this refund?"

| ID | Requirement | Priority |
|---|---|---|
| FR-042 | Understand natural-language financial operations requests. | P0 |
| FR-043 | Resolve the relevant organization, location, account and time range. | P0 |
| FR-044 | Retrieve records through authorized tools only. | P0 |
| FR-045 | Invoke deterministic reconciliation and validation services. | P0 |
| FR-046 | Diagnose an issue using verified records and explicit evidence. | P0 |
| FR-047 | Select an appropriate workflow based on issue type and policy. | P0 |
| FR-048 | Execute permitted low-risk actions. | P0 |
| FR-049 | Request approval for restricted actions. | P0 |
| FR-050 | Persist investigation state and resume eligible workflows. | P0 |
| FR-051 | Track tool execution, failures and retries. | P0 |
| FR-052 | Verify action outcomes using authoritative responses or records. | P0 |
| FR-053 | Escalate ambiguous, high-risk or unresolved issues. | P0 |
| FR-054 | Explain findings with source references and confidence/limitations. | P0 |
| FR-055 | Prevent prompt injection or untrusted source content from changing tool permissions. | P0 |
| FR-056 | Support contextual follow-up questions within authorized scope. | P1 |

### Agent operating principle

The LLM coordinates the work. It does not own the financial truth, authorization policy or final case status.

The following are deterministic or policy-enforced responsibilities:

- Monetary calculations.
- Record matching.
- Status validation.
- Authorization checks.
- Idempotency checks.
- Tool input validation.
- Action execution constraints.
- Case closure conditions.

### Recommended workflow stages

1. Intent understanding.
2. Entity and timeframe resolution.
3. Context retrieval.
4. Financial investigation.
5. Evidence validation.
6. Policy and risk evaluation.
7. Action planning.
8. Approval, where required.
9. Tool execution.
10. Result verification.
11. Monitoring and follow-up.
12. Resolution or escalation.

### Acceptance criteria

- The agent cannot invent transaction, settlement or bank statuses.
- The agent cannot access another organization or location's records.
- Tool calls are validated by backend policy, not trusted because the model requested them.
- Restricted actions cannot execute without required approval.
- Tool success is not treated as proof of business resolution.
- Failed or ambiguous investigations reach a human-review state.
- Every consequential action has a traceable audit event.

## 6.5 M05 — Case and Resolution Management

**Objective:** Manage the lifecycle of financial and operational issues.

| ID | Requirement | Priority |
|---|---|---|
| FR-057 | Create an investigation case from a financial exception. | P0 |
| FR-058 | Associate relevant transactions, settlement entries and bank records. | P0 |
| FR-059 | Generate an evidence package. | P0 |
| FR-060 | Assign owner, priority, category and due date where appropriate. | P1 |
| FR-061 | Create support requests through authorized integrations. | P1 |
| FR-062 | Record external support reference and submission response. | P1 |
| FR-063 | Monitor external status changes where supported. | P1 |
| FR-064 | Generate follow-up tasks and reminders. | P1 |
| FR-065 | Maintain a chronological case timeline. | P0 |
| FR-066 | Escalate cases to authorized human operators. | P0 |
| FR-067 | Verify the final outcome before closure. | P0 |
| FR-068 | Prevent closure when required evidence or conditions are missing. | P0 |
| FR-069 | Support manual case notes and reviewed status updates. | P1 |
| FR-070 | Export authorized case records and evidence. | P1 |

### Case categories

- Settlement delay.
- Missing payout.
- Partial settlement.
- Bank credit mismatch.
- Failed payment.
- Refund pending.
- Duplicate transaction.
- Chargeback or dispute.
- Provider API or synchronization issue.
- Data-quality issue.

### Proposed case lifecycle

`Detected → Investigating → Evidence Ready → Approval Required → Action Submitted → Awaiting Response → Resolution Verification → Resolved`

Alternative terminal or hold states:

- Escalated.
- Rejected.
- Cancelled with reason.
- Unable to verify.
- Closed as duplicate with linked case.

A case may transition only through explicitly permitted state transitions. All transitions must record actor, timestamp, reason and related evidence.

### Acceptance criteria

- Every case has a unique internal identifier.
- A case can be traced to its originating exception or user request.
- Evidence is immutable or versioned after submission.
- External submission is not claimed unless the integration confirms acceptance and returns an appropriate reference.
- Case closure requires category-specific verification conditions.
- A case cannot be closed by an LLM-generated statement alone.

## 6.6 M06 — Proactive Monitoring and Alerts

**Objective:** Detect important financial and operational exceptions before a merchant manually reports them.

| ID | Requirement | Priority |
|---|---|---|
| FR-071 | Monitor configured settlement windows. | P1 |
| FR-072 | Detect unusual settlement delays. | P1 |
| FR-073 | Detect repeated failed payouts. | P1 |
| FR-074 | Identify duplicate or anomalous transactions. | P1 |
| FR-075 | Detect recurring discrepancy patterns. | P1 |
| FR-076 | Monitor refund status where source data is available. | P1 |
| FR-077 | Support configurable alert thresholds. | P1 |
| FR-078 | Notify merchants through configured channels. | P1 |
| FR-079 | Escalate critical exceptions. | P1 |
| FR-080 | Suppress duplicate alerts and provide alert history. | P1 |

### Alert severity

- Informational.
- Warning.
- High priority.
- Critical.

Every alert should include affected account/location, source data, detection time, severity, reason and recommended next step.

The system must distinguish a genuine anomaly from a normal processing delay. An anomaly is not proof of fraud.

## 6.7 M07 — Financial Intelligence and Business Analytics

**Objective:** Help merchants understand financial performance and recurring operational problems.

| ID | Requirement | Priority |
|---|---|---|
| FR-081 | Generate daily, weekly and monthly financial summaries. | P1 |
| FR-082 | Compare collection and settlement trends. | P1 |
| FR-083 | Analyze payment failure rates. | P1 |
| FR-084 | Analyze refund, reversal and chargeback trends. | P1 |
| FR-085 | Identify recurring financial discrepancies. | P1 |
| FR-086 | Compare performance across authorized locations. | P1 |
| FR-087 | Generate downloadable reports. | P1 |
| FR-088 | Support natural-language analytical questions. | P1 |
| FR-089 | Generate evidence-backed operational insights. | P1 |
| FR-090 | Provide forecasts only when data sufficiency and model validation requirements are met. | P2 |

### Example questions

- Which provider has the most settlement delays?
- What amount is currently unmatched?
- Which outlet has the highest refund rate?
- What percentage of settlements are automatically reconciled?
- Which discrepancy category is recurring most often?

Analytics must display time range, coverage, source and calculation definitions. Forecasts must be labelled as estimates.

## 6.8 M08 — Multi-Store and Organization Management

**Objective:** Support businesses with multiple outlets, entities, accounts and employees.

| ID | Requirement | Priority |
|---|---|---|
| FR-091 | Create and manage business organizations. | P0 |
| FR-092 | Support multiple business entities where applicable. | P1 |
| FR-093 | Create and manage store locations. | P1 |
| FR-094 | Associate provider accounts with authorized entities and locations. | P1 |
| FR-095 | Associate bank accounts with authorized business entities. | P1 |
| FR-096 | Provide consolidated and location-specific dashboards. | P1 |
| FR-097 | Invite employees and assign roles. | P1 |
| FR-098 | Enforce location- and entity-level data access. | P0 |
| FR-099 | Generate consolidated reports. | P1 |
| FR-100 | Maintain an auditable history of permission changes. | P0 |

### Proposed roles

- Organization Owner.
- Organization Administrator.
- Finance Manager.
- Store Manager.
- Operations Agent.
- Accountant.
- Read-only Auditor.

Permissions must be enforced at the API and data-access layers, not only by hiding interface elements.

## 6.9 M09 — Conversational and Multilingual Interface

**Objective:** Make financial operations accessible to merchants with different language preferences and technical abilities.

| ID | Requirement | Priority |
|---|---|---|
| FR-101 | Provide text-based conversational interaction. | P0 |
| FR-102 | Support contextual follow-up questions. | P1 |
| FR-103 | Provide voice input where supported. | P2 |
| FR-104 | Provide text-to-speech where supported. | P2 |
| FR-105 | Support English initially. | P0 |
| FR-106 | Support Hindi with tested financial terminology. | P1 |
| FR-107 | Design for additional Indian languages. | P2 |
| FR-108 | Explain financial terminology in simple language. | P0 |
| FR-109 | Preserve context across authorized investigation sessions. | P1 |

Potential future languages: Punjabi, Tamil, Telugu, Bengali and Marathi. Language support must be evaluated for numerical accuracy, intent preservation, financial vocabulary and dialect variation.

## 6.10 M10 — Security, Governance and Audit

**Objective:** Protect merchant information and ensure every autonomous action is accountable.

| ID | Requirement | Priority |
|---|---|---|
| FR-110 | Secure user authentication. | P0 |
| FR-111 | Implement role-based access control. | P0 |
| FR-112 | Encrypt sensitive information in transit and at rest. | P0 |
| FR-113 | Store provider credentials in an appropriate secrets-management system. | P0 |
| FR-114 | Mask sensitive account information. | P0 |
| FR-115 | Maintain detailed audit events. | P0 |
| FR-116 | Record agent tool executions and outcomes. | P0 |
| FR-117 | Record approval and rejection decisions. | P0 |
| FR-118 | Enforce tenant-level data isolation. | P0 |
| FR-119 | Support authorized data export. | P1 |
| FR-120 | Support documented retention and deletion policies. | P0 |
| FR-121 | Enforce configurable action permissions. | P0 |
| FR-122 | Monitor security and operational events. | P0 |
| FR-123 | Detect and respond to unauthorized or anomalous access. | P0 |

---

# 7. End-to-End User Journeys

## 7.1 Journey A — Merchant onboarding

1. Merchant registers and verifies identity according to the selected onboarding policy.
2. Merchant creates or joins a business organization.
3. Merchant selects business type and adds operating locations if applicable.
4. Merchant connects a payment-provider account through an authorized flow or imports a supported report.
5. Merchant adds bank information through an authorized integration or imports a bank statement.
6. SettleSaathi validates file schema, source and account mapping.
7. The system normalizes and deduplicates data.
8. The reconciliation engine performs initial matching.
9. Merchant sees matched, pending and exception records with data coverage information.
10. Merchant configures alerts and agent permissions.

**Success condition:** The merchant can view source-backed financial records and understand what is matched, pending or unresolved.

## 7.2 Journey B — Automated discrepancy investigation

1. Reconciliation identifies a discrepancy or the merchant reports one.
2. The system creates an exception with source references.
3. The agent resolves the relevant entity, account and timeframe.
4. The agent retrieves related records using authorized tools.
5. Deterministic services calculate the discrepancy and validate source statuses.
6. The agent prepares an evidence-backed diagnosis or identifies what is missing.
7. A workflow is selected based on issue type and policy.
8. Permitted actions execute automatically; restricted actions require approval.
9. The case is monitored through provider events or scheduled checks.
10. The outcome is verified against authoritative records.
11. The case is resolved, escalated or marked unable to verify.

**Success condition:** The issue reaches a supported terminal state with evidence, or is escalated with a complete investigation package.

## 7.3 Journey C — Natural-language financial query

1. Merchant asks a question.
2. Agent identifies intent and resolves the timeframe and account.
3. Agent retrieves relevant records.
4. Deterministic services calculate totals or run reconciliation.
5. Results are validated for completeness and source freshness.
6. Agent explains the result, including caveats and source references.

**Success condition:** Merchant receives a traceable answer without fabricated figures or unsupported claims.

## 7.4 Journey D — Multi-store overview

1. Owner selects the organization dashboard.
2. System aggregates authorized location-level records.
3. Exceptions are grouped by location and category.
4. Agent identifies recurring patterns using available evidence.
5. Owner assigns tasks to authorized employees.
6. Managers track assigned cases.

**Success condition:** Owner understands and manages financial operations across all authorized locations.

## 7.5 Journey E — Approval of an external action

1. Agent prepares a support submission or another policy-controlled action.
2. The approval service evaluates the action class and actor permissions.
3. The user sees the action, destination, data to be shared and expected consequence.
4. The authorized user approves or rejects.
5. The system records approver, scope, timestamp and decision.
6. If approved, the action is executed with an idempotency key.
7. The system verifies the external response and stores the returned reference.
8. The case timeline is updated.

**Success condition:** No external action occurs without the required approval and a verifiable execution result.

---

# 8. Agent Governance and Bounded Autonomy

## 8.1 Authorization classes

### Class A — Read-only autonomous actions

Allowed without additional approval, within the user's existing data permissions:

- Retrieve transactions and settlement records.
- Read bank statement entries already authorized for the organization.
- Run reconciliation.
- Generate financial summaries.
- Identify discrepancies.
- Prepare investigation reports.
- Read case status.
- Monitor existing cases.
- Generate internal notifications.

### Class B — Pre-authorized low-risk actions

May execute independently only if the organization explicitly enables the action and scope:

- Create internal cases.
- Assign internal tasks according to configured rules.
- Send internal notifications.
- Refresh provider data.
- Generate follow-up reminders.
- Submit a narrowly defined support request if pre-authorization is configured and the destination and payload are within the approved policy.

### Class C — Restricted actions

Require the appropriate human approval or remain unavailable:

- Initiating refunds.
- Transferring funds.
- Changing bank accounts.
- Changing settlement configurations.
- Initiating financial reversals.
- Submitting high-impact disputes or legally significant declarations.
- Changing credentials or permissions.
- Irreversible or high-value financial operations.

The AI cannot override these restrictions.

## 8.2 Policy enforcement sequence

Every consequential action must pass the following sequence:

1. Authenticate the requesting user or system actor.
2. Resolve organization, entity, account and resource scope.
3. Validate the action against role permissions.
4. Classify the action and assess risk.
5. Check organization policy and thresholds.
6. Determine whether approval is required.
7. Validate action parameters and destination.
8. Check idempotency and duplicate execution risk.
9. Execute through an authorized adapter.
10. Verify the response and business outcome.
11. Record an audit event.
12. Update the workflow or case state.

The LLM must never be the enforcement point for these checks.

## 8.3 Approval requirements

An approval request should show:

- Requested action.
- Reason for the action.
- Organization and affected account.
- Recipient or destination system.
- Data that will be shared or changed.
- Amount, where applicable.
- Risks and reversibility.
- Evidence supporting the request.
- Expiration time for the approval.
- Approve and reject controls.

Approval must be bound to the exact action payload or a payload hash. Material changes to the action require renewed approval.

## 8.4 Escalation conditions

Escalate when:

- Diagnosis confidence is low or evidence conflicts.
- Required source records are missing.
- A restricted action is requested.
- Unauthorized access is suspected.
- A provider API is unavailable beyond retry policy.
- Repeated tool failures occur.
- A high-value or high-impact exception exceeds configured thresholds.
- Merchant authorization is missing or ambiguous.
- A case cannot satisfy closure conditions.

## 8.5 Agent failure handling

- Use bounded retries with exponential backoff and jitter for transient errors.
- Do not retry non-idempotent actions unless idempotency is guaranteed.
- Persist workflow checkpoints.
- Make tool errors visible to the case timeline.
- Avoid repeating a submitted support case after an uncertain timeout; first query submission status using the idempotency or external reference.
- Move exhausted workflows to a review queue rather than looping indefinitely.

---

# 9. Case Lifecycle and State Machine

## 9.1 Case states

| State | Meaning | Allowed next states |
|---|---|---|
| Detected | Exception or user issue has been registered | Investigating, Duplicate, Cancelled |
| Investigating | Evidence retrieval and diagnosis are underway | Evidence Ready, Escalated, Unable to Verify |
| Evidence Ready | Required evidence has been assembled | Approval Required, Action Submitted, Escalated |
| Approval Required | Required approval is pending | Action Submitted, Rejected, Escalated, Cancelled |
| Action Submitted | Authorized action was accepted by the destination | Awaiting Response, Resolution Verification, Escalated |
| Awaiting Response | Waiting for external status or new data | Resolution Verification, Escalated, Unable to Verify |
| Resolution Verification | Checking evidence for final outcome | Resolved, Investigating, Escalated, Unable to Verify |
| Resolved | Closure conditions are satisfied | Reopened only under an explicit policy |
| Escalated | Human intervention is required | Investigating, Resolution Verification, Resolved, Rejected |
| Rejected | Request or action was rejected with reason | Investigating, Cancelled, Escalated |
| Unable to Verify | Available evidence cannot establish an outcome | Investigating, Escalated |
| Cancelled | Case was cancelled with reason | Terminal unless explicitly reopened |
| Duplicate | Linked to another case | Terminal unless explicitly reopened |

## 9.2 Closure conditions

A case may be marked resolved only when its issue-specific conditions are satisfied. Example for a missing bank settlement:

- Provider settlement record exists and is authoritative for the provider-reported status.
- Corresponding bank credit is found and matched, or another approved authoritative resolution record is available.
- Amount and currency match under the applicable settlement calculation.
- Any residual difference is explained by documented adjustments or explicitly accepted by an authorized reviewer.
- Evidence is attached to the case.

A message from an LLM, successful API HTTP response or support-ticket creation is not sufficient proof of financial resolution.

---

# 10. Multi-Provider Integration Specification

## 10.1 Adapter architecture

Each provider integration must implement a common internal contract while retaining provider-specific capabilities and limitations.

Conceptual flow:

`Provider API / Webhook / Report / Bank Statement`

`→ Provider Adapter`

`→ Ingestion and Validation`

`→ Canonical Financial Records`

`→ Reconciliation and Exception Services`

`→ Agent and Case Workflows`

## 10.2 Common adapter capabilities

Where supported by the provider, an adapter may implement:

- Authentication and credential validation.
- Account and merchant profile lookup.
- Transaction retrieval.
- Refund and reversal retrieval.
- Settlement batch and line-item retrieval.
- Payout or transfer status retrieval.
- Fee and adjustment retrieval.
- Webhook signature verification.
- Webhook event normalization.
- Incremental synchronization.
- Pagination and rate-limit handling.
- Health and connection-status reporting.

Not every provider supports every operation. The adapter must declare its actual capabilities instead of pretending all providers offer identical interfaces.

## 10.3 Connector capability registry

Each connected account should maintain a capability record, for example:

- `transactions.read`
- `refunds.read`
- `settlements.read`
- `settlement_entries.read`
- `payouts.read`
- `webhooks.receive`
- `support_cases.create`
- `support_cases.read`

The registry must include access state, supported API version, last validation time and limitations.

## 10.4 Synchronization requirements

- Support incremental and backfill synchronization.
- Use provider cursor or timestamp semantics where documented.
- Handle pagination.
- Respect rate limits.
- Verify webhooks where possible.
- Deduplicate by provider event ID or stable event identity.
- Tolerate out-of-order webhook delivery.
- Reconcile delayed updates without overwriting authoritative history.
- Record source freshness and synchronization gaps.
- Provide a controlled manual resync path.

## 10.5 File import requirements

- File upload must be tied to an organization, provider/account and file type.
- Validate file format, schema, encoding and size.
- Provide a mapping preview before import when column mappings are uncertain.
- Record row-level validation errors.
- Support partial acceptance only when safe and clearly reported.
- Store original file securely with access controls and retention policy.
- Deduplicate repeated imports.
- Record parser and mapping version.
- Never silently discard malformed rows.

## 10.6 Bank-data integration strategy

Initial supported path:

1. Bank statement upload using supported CSV/XLSX formats.
2. Selected PDF statement extraction with a review step.
3. Later, authorized integrations through eligible partners or applicable frameworks.

Direct access to bank accounts must not be assumed. Account Aggregator participation and data access have specific eligibility, consent and regulatory conditions. SettleSaathi must not ask for bank login credentials, OTPs or UPI PINs.

---

# 11. Canonical Data Model

The canonical model must preserve financial provenance and provider-specific meaning.

## 11.1 Core entities

| Entity | Purpose | Key relationships |
|---|---|---|
| Organization | Merchant's top-level workspace | Has entities, users, locations and connections |
| BusinessEntity | Legal or operational business entity | Belongs to organization; owns accounts |
| Location | Store or outlet | Belongs to organization/entity |
| User | Authenticated person | Has role and scoped permissions |
| ProviderConnection | Provider integration instance | Belongs to organization and account scope |
| ProviderAccount | Merchant/provider account | Linked to provider connection and entity |
| BankAccountReference | Masked bank account metadata | Linked to business entity and data source |
| PaymentTransaction | Original payment event | Linked to provider account and related records |
| Refund | Refund event or record | Linked to original payment where available |
| Reversal | Reversal record | Linked to transaction or settlement |
| SettlementBatch | Provider settlement grouping | Contains settlement entries |
| SettlementEntry | Transaction-level settlement item | Linked to transaction and batch |
| Adjustment | Fee, tax, refund, reversal or other adjustment | Linked to batch or entry |
| Payout | Provider-reported payout to bank | Linked to settlement batch and bank reference |
| BankTransaction | Imported or authorized bank record | Linked to bank data source |
| ReconciliationMatch | Match relationship and evidence | Links two or more financial records |
| Exception | Unresolved or anomalous condition | Linked to source records and case |
| InvestigationCase | Operational issue | Links exceptions, evidence, actions and events |
| AgentRun | Agent workflow execution | Links context, tools and final state |
| Approval | User authorization decision | Binds actor, action payload and scope |
| AuditEvent | Traceable system activity | Linked to actor, resource and action |
| ImportJob | File/API ingestion execution | Links source, file, rows and validation results |

## 11.2 Required provenance fields

Every imported financial record should retain, as applicable:

- Internal record ID.
- Organization ID.
- Business entity and location IDs.
- Provider name and provider account ID.
- External provider reference.
- Record type.
- Original status and normalized status.
- Amount in minor units.
- Currency.
- Event/transaction timestamp and timezone context.
- Provider-created and provider-updated timestamps where available.
- Ingestion timestamp.
- Source channel (API, webhook, file, manual entry).
- Source file, API request or event reference.
- Parser/adapter version.
- Data quality and validation status.

## 11.3 Data integrity rules

- Financial source records should be append-only or versioned; corrections must be traceable.
- A normalized status must not replace the original provider status.
- Duplicate records must be detected using provider-specific identity rules.
- Derived aggregates must be reproducible from underlying records and calculation versions.
- Currency must always be explicit.
- Timezone and business-date semantics must be explicit.
- Bank account identifiers must be masked in normal UI views.
- All records must be scoped to an organization and authorized entity.

---

# 12. Proposed Technical Architecture

## 12.1 Architectural principles

- API-first application design.
- Modular domain boundaries.
- Provider-specific adapters.
- Event-driven ingestion where supported.
- Deterministic financial processing.
- Stateful, bounded agent workflows.
- Tenant-aware data access.
- Auditable action execution.
- Independent scaling of ingestion, reconciliation and agent workloads.
- Modular monolith first; service extraction when justified.

## 12.2 Logical architecture layers

### Layer 1 — Experience

- Merchant web application.
- Finance console.
- Operations console.
- Conversational assistant.
- Responsive mobile experience.

### Layer 2 — Application and API

- Authentication and session management.
- Organization and user management.
- Authorization and policy service.
- API gateway/application API.
- Notification preferences.

### Layer 3 — Integration and ingestion

- Provider adapters.
- Webhook receivers.
- Scheduled synchronization workers.
- File import pipeline.
- Bank statement parsing.
- Data validation and deduplication.

### Layer 4 — Financial domain services

- Canonical ledger/record service.
- Settlement processing.
- Reconciliation engine.
- Exception detection.
- Financial aggregation and reporting.

### Layer 5 — Agent and workflow services

- Intent and entity resolution.
- Context retrieval.
- Agent orchestration.
- Tool registry.
- Policy and approval gateway.
- Case management.
- Monitoring and escalation.

### Layer 6 — Persistence

- Relational database.
- Object storage for source files and evidence.
- Cache and queue infrastructure.
- Audit event storage.
- Optional vector index for policy/document retrieval.

### Layer 7 — Observability and operations

- Structured logs.
- Distributed traces.
- Service metrics.
- Workflow metrics.
- Security alerts.
- Data-quality dashboards.

## 12.3 Proposed technology stack

| Component | Candidate technology | Rationale / notes |
|---|---|---|
| Frontend | React + Vite | Fast local development experience for the hackathon prototype |
| Backend | Python + FastAPI served by Uvicorn | Typed API services and a simple local runtime |
| Python tooling | uv + project-local `.venv` | Reproducible dependencies; never use globally installed project packages |
| Agent orchestration | LangGraph or equivalent stateful workflow engine | Explicit state, branching and checkpoints |
| Financial computation | Python with integer minor units/Decimal | Exact calculations and reproducibility |
| Database | SQLite with foreign keys and WAL mode | Self-contained relational system of record for the complete prototype |
| Background processing | Synchronous application services / FastAPI background tasks | Persist job state in SQLite; no queue infrastructure for Release 0 |
| File storage | Private local `storage/` directory | Synthetic source files and evidence packages; replaceable with S3 later |
| Vector retrieval | Deferred | Not required unless a validated policy/document retrieval need emerges |
| LLM | Sarvam AI and/or other evaluated models | Model choice subject to quality, cost, privacy and tool-call evaluation |
| Document extraction | PyMuPDF, pdfplumber and validated extraction tools | PDF statement processing; manual review fallback required |
| Identity | Seeded local demo users and roles | Demonstrates scoped roles without requiring an external identity service |
| Observability | Structured logs, correlation IDs and audit events | Lightweight prototype visibility; OpenTelemetry is optional |
| Deployment | Local frontend development server + Uvicorn | Repeatable, self-contained prototype runtime |
| CI/CD | GitHub Actions or equivalent | Tests, security checks and deployment automation |

These are the selected Release 0 technologies. Production-scale infrastructure may be reconsidered only after the hackathon prototype demonstrates the complete workflow.

## 12.4 Initial deployment topology

For Release 0, use a self-contained modular monolith:

- React/Vite frontend.
- FastAPI application served locally by Uvicorn.
- SQLite database in a private local data directory.
- Private local file storage for synthetic source files and evidence packages.
- Synchronous services or FastAPI background tasks for imports, reconciliation and mock case monitoring.
- Optional model provider behind a narrow adapter.

Use `uv` and a project-local `.venv` for all Python commands. Use Mermaid for all diagrams in implementation documentation. Do not add PostgreSQL, Redis, Celery, RabbitMQ, containers, or production observability infrastructure to Release 0 unless the prototype cannot meet a verified requirement without it.

---

# 13. API and Event Design Requirements

Detailed OpenAPI contracts will be defined during the system-design phase. The following domains and behavior are required.

## 13.1 API domains

- `/auth` — authentication/session integration.
- `/organizations` — organizations and business entities.
- `/users` — users, invitations and roles.
- `/locations` — store locations.
- `/connections` — provider and bank-data connections.
- `/imports` — file upload, mapping, validation and import jobs.
- `/transactions` — payment records, refunds and reversals.
- `/settlements` — batches, entries and payouts.
- `/bank-transactions` — imported or authorized bank records.
- `/reconciliation` — runs, matches, exceptions and reviews.
- `/cases` — investigations, evidence and timelines.
- `/approvals` — action approval and rejection.
- `/agent` — conversational sessions and workflow status.
- `/reports` — analytics and exports.
- `/notifications` — user notification state and preferences.
- `/audit` — authorized event and action history.

## 13.2 API requirements

- Every request must be authenticated unless explicitly public and safe.
- Organization and resource scope must be derived from validated identity and permissions.
- Use pagination and stable sorting for collection endpoints.
- Use idempotency keys for consequential create/submit actions.
- Validate content type, payload size and schema.
- Use consistent error contracts.
- Include correlation IDs.
- Apply rate limits and abuse controls.
- Avoid exposing raw provider credentials or sensitive identifiers.
- Use optimistic concurrency or version checks where conflicting updates are possible.

## 13.3 Webhook requirements

- Verify signatures where supported.
- Reject or quarantine invalid signatures.
- Deduplicate events.
- Persist the received event before asynchronous processing.
- Handle out-of-order delivery.
- Support retries and dead-letter handling.
- Record provider event ID, receipt time and processing result.
- Never trust webhook payload text as instructions to the AI agent.

## 13.4 Domain events

Examples:

- `payment.transaction.ingested`
- `settlement.batch.updated`
- `settlement.payout.reported`
- `bank.statement.imported`
- `bank.transaction.ingested`
- `reconciliation.run.completed`
- `reconciliation.exception.created`
- `case.created`
- `case.state.changed`
- `approval.requested`
- `approval.decided`
- `agent.action.executed`
- `agent.action.failed`
- `case.resolution.verified`

Events must carry identifiers and provenance, not unnecessary personal or financial data.

---

# 14. Non-Functional Requirements

These are initial targets for validation, not production guarantees.

| Category | Requirement / proposed target |
|---|---|
| Financial accuracy | Exact arithmetic for authoritative monetary calculations |
| Reproducibility | Same input and rules version produce the same deterministic reconciliation output |
| Reliability | Idempotent ingestion and consequential action execution |
| Dashboard performance | Target under 3 seconds for normal operational views under agreed test load |
| Import throughput | Initial benchmark target: 50,000 normalized rows in 60 seconds on documented hardware; revise after profiling |
| Agent response | Target under 30 seconds for standard internal investigations, excluding provider latency and lengthy imports |
| Pilot availability | Target 99.5% after deployment and monitoring are established |
| Production availability | Long-term target 99.9%, subject to architecture and operating budget |
| Scalability | Support multiple organizations and provider accounts with tenant isolation |
| Security | Encryption, least privilege, scoped credentials and audit logs |
| Maintainability | Clear module boundaries and documented integration contracts |
| Accessibility | Responsive interface and accessible controls |
| Localization | English initially; Hindi after quality validation |
| Observability | Correlated request, ingestion and agent workflow traces |
| Recovery | Documented backup, restore and disaster-recovery procedures before production |
| Data retention | Configurable by data class, legal obligation and customer agreement |

## 14.1 Resilience requirements

- Retry transient failures with exponential backoff and jitter.
- Use circuit breakers where repeated provider failures can overload systems.
- Preserve queued work across worker restarts.
- Do not lose an acknowledged ingestion event.
- Provide a dead-letter and operator review path.
- Make synchronization freshness visible.
- Avoid unbounded agent retries or loops.

## 14.2 Performance measurement

Benchmarks must record:

- Hardware and deployment topology.
- Record count and distribution.
- Provider count and format.
- Match complexity.
- Cold and warm performance.
- API latency percentiles.
- Import throughput.
- Queue delay.
- Agent tool latency.
- Error and retry rate.

---

# 15. Security, Privacy and Compliance Requirements

This section establishes engineering controls and areas for legal assessment. It is not a legal opinion or a certification of compliance.

## 15.1 Authentication and authorization

- Use secure authentication and session management.
- Support MFA where appropriate, especially for privileged users and consequential actions.
- Enforce role-based and resource-scoped access.
- Apply least privilege to human users, service accounts and provider connectors.
- Revalidate authorization on every backend operation.
- Revoke sessions and credentials after relevant account or role changes.

## 15.2 Data protection

- Encrypt data in transit and at rest.
- Mask bank account and personal identifiers in the UI.
- Store provider credentials in a secrets manager.
- Rotate and revoke credentials securely.
- Minimize personal data in prompts, model context and logs.
- Define data retention by data type.
- Support applicable access, correction, deletion and grievance processes where required.
- Maintain processor and subprocessor inventories.
- Assess cross-border data processing and contractual obligations.

## 15.3 Payment-data safety

SettleSaathi must never request or store:

- UPI PINs.
- OTPs.
- Card CVVs.
- Bank-login passwords.
- Full authentication secrets.

Use official provider APIs, authorized partner interfaces or user-provided files. Do not scrape authenticated provider interfaces without authorization.

## 15.4 AI governance

- Use only the minimum data necessary for a model request.
- Evaluate provider/model data retention and processing terms.
- Ground financial answers in retrieved data.
- Label assumptions and missing information.
- Treat uploaded files, webhooks and provider descriptions as untrusted data, never as executable instructions.
- Defend against prompt injection and tool misuse.
- Restrict tools by organization, user, account, action and scope.
- Record model, prompt/workflow version and tool outcomes where appropriate.
- Provide human review for sensitive decisions.

## 15.5 Indian regulatory considerations

Implementation must be reviewed against applicable Indian laws, RBI directions and relevant payment-network requirements. Key topics include:

- Digital Personal Data Protection Act, 2023 and applicable notified Rules, including phased commencement provisions.
- RBI Account Aggregator framework and participant eligibility/consent requirements where that route is considered.
- Payment-provider contractual and API terms.
- Data security, incident response and retention obligations applicable to the business model.
- Payment-data and card-data requirements if future product scope ever handles those data classes.

Do not assume that SettleSaathi is automatically an Account Aggregator, regulated payment entity or authorized participant. Any such role would require separate legal and regulatory assessment.

---

# 16. Risks, Dependencies and Mitigations

| Risk / dependency | Potential impact | Mitigation |
|---|---|---|
| Provider API limitations or no production access | Connector may not be viable for a pilot | Confirm access early; provide file import fallback |
| Inconsistent provider reporting | False or incomplete reconciliation | Provider-specific normalization and test fixtures |
| Missing bank references | Ambiguous payout matching | Candidate matching with review; never force a match |
| Statement PDF extraction errors | Incorrect bank data | Validate totals and rows; review low-confidence extraction |
| False reconciliation matches | Financial misinformation | Deterministic rules, confidence gates and match audits |
| Agent misinterpretation | Wrong workflow | Tool schemas, evidence checks and deterministic policy |
| Unauthorized action | Financial or reputational harm | Independent authorization gateway and approvals |
| Provider downtime | Stale data and delayed cases | Queues, retries and visible freshness state |
| Sensitive data exposure | Privacy and security harm | Data minimization, encryption, scoped access and monitoring |
| Multi-provider complexity | Long delivery timeline | Incremental connectors and stable canonical model |
| Insufficient pilot data | Weak validation | Synthetic test corpus followed by authorized merchant data |
| Unclear monetization | Limited adoption | Merchant interviews and willingness-to-pay validation |
| External support integration unavailable | Cannot submit or monitor cases automatically | Evidence-pack export and official channel handoff |

---

# 17. Release Plan and Prioritization

## Release 0 — Hackathon prototype

**Objective:** Demonstrate one complete autonomous financial discrepancy workflow.

Scope:

- Synthetic provider datasets.
- Bank statement CSV import.
- Canonical data normalization.
- Deterministic reconciliation.
- Exception classification.
- Agent investigation and evidence generation.
- Internal case creation.
- Explicit authorization for simulated support submission.
- Mock support endpoint.
- Case timeline and status tracking.
- Verification and escalation.
- Audit history.

Exit criteria:

- Demo scenario can run end-to-end.
- False closure is prevented in test cases.
- Restricted actions are blocked without approval.
- All important events are traceable.
- Synthetic data is clearly labelled.

## Release 1 — Merchant pilot

**Objective:** Validate the workflow using authorized merchant data.

Scope:

- Secure merchant onboarding.
- One live payment-provider integration, subject to access approval.
- One additional provider or file connector chosen through pilot demand.
- CSV/XLSX bank and settlement imports.
- Selected PDF statement extraction.
- Reconciliation and exception management.
- Agent investigation.
- Case management and audit.
- Configurable permissions.
- Basic notifications.
- Operational monitoring.

Exit criteria:

- Pilot merchants can regularly reconcile supported data.
- Accuracy is measured against reviewed records.
- Provider access and data handling are contractually and operationally approved.
- Support workflow limitations are transparent.

## Release 2 — Multi-provider operations platform

**Objective:** Expand integrations and multi-location operations.

Scope:

- Additional provider connectors.
- Webhook ingestion.
- Scheduled synchronization.
- Multi-store management.
- Advanced roles and approvals.
- Authorized support-channel integrations.
- Financial reporting and case analytics.
- Hindi merchant assistant after evaluation.

Exit criteria:

- More than one provider can be used within the same organization.
- Provider differences do not break common reconciliation workflows.
- Multi-tenant and location access controls pass security testing.

## Release 3 — Advanced intelligence platform

**Objective:** Introduce predictive operations and enterprise capabilities.

Scope:

- Predictive anomaly detection.
- Advanced financial forecasting.
- Accounting and ERP integrations.
- Voice-based merchant assistant.
- Advanced operational automation.
- Enterprise SSO and governance.
- Partner-enabled banking data connections.
- Configurable workflow policies.

Exit criteria:

- Predictive functions are validated against historical holdout data.
- Forecasts communicate uncertainty and limitations.
- Enterprise controls are independently reviewed.

---

# 18. Testing and Quality Strategy

## 18.1 Unit tests

- Monetary arithmetic and rounding.
- Provider status normalization.
- Fee and adjustment calculations.
- Exact and composite matching.
- Partial and consolidated payout matching.
- Deduplication keys.
- Case transition rules.
- Authorization policy decisions.
- Idempotency logic.

## 18.2 Integration tests

- Provider adapter contract tests.
- Webhook signature and replay tests.
- Pagination and rate-limit tests.
- File import and row-level validation tests.
- Database transaction and rollback tests.
- Queue retry and dead-letter tests.
- Object storage access controls.
- Agent tool schema and timeout tests.

## 18.3 End-to-end scenarios

1. Exact match: payment → settlement entry → bank credit.
2. Consolidated payout: multiple settlement batches → one bank credit.
3. Partial settlement.
4. Settlement reported but bank credit missing.
5. Bank credit arrives after a delay.
6. Duplicate payment or duplicate file import.
7. Refund and reversal affecting net settlement.
8. Fee or tax adjustment.
9. Conflicting provider records.
10. Malformed or incomplete statement.
11. Provider API unavailable.
12. Webhook delivered multiple times and out of order.
13. Support submission timeout with uncertain acceptance.
14. Agent attempts restricted action without approval.
15. Case attempts to close without evidence.
16. User attempts to access another organization.

## 18.4 AI evaluation

Evaluate:

- Intent classification accuracy.
- Entity/timeframe extraction accuracy.
- Tool selection correctness.
- Grounded answer rate.
- Unsupported claim rate.
- Tool argument validity.
- Unauthorized tool-call rejection.
- Prompt-injection resistance.
- Escalation appropriateness.
- Multi-turn context retention.
- Multilingual numerical and financial terminology accuracy.

Use a fixed evaluation dataset with expected tool traces and expected outcomes. Do not evaluate agents only by whether the final answer sounds convincing.

## 18.5 Security tests

- Tenant isolation tests.
- Role and permission tests.
- Credential exposure scans.
- Webhook forgery/replay tests.
- Prompt injection tests using untrusted documents and events.
- API rate-limit and abuse tests.
- Sensitive-data logging tests.
- Approval replay and payload-tampering tests.

## 18.6 Release gate

No production release should proceed while there are known critical defects involving financial correctness, tenant isolation, unauthorized action execution or false case closure.

---

# 19. Acceptance Criteria for the First End-to-End Product Demonstration

The first demonstration is successful when all of the following are true:

## Data ingestion

- A synthetic payment report is imported.
- A synthetic settlement report is imported.
- A synthetic bank statement is imported.
- Each record retains its source and import provenance.
- Duplicate import does not duplicate transactions.

## Reconciliation

- Payment records are matched to settlement entries.
- Settlement payouts are matched to bank credits where evidence exists.
- Partial and unmatched amounts are identified.
- Amounts are calculated exactly.
- The system explains why a record matched or remained unmatched.

## Agent investigation

- Merchant can ask about a discrepancy in natural language.
- Agent retrieves records within the merchant's scope.
- Agent uses deterministic reconciliation results.
- Agent prepares an evidence package.
- Agent does not invent a root cause when evidence is insufficient.

## Bounded execution

- Internal case creation works.
- Simulated external submission requires the configured authorization.
- Duplicate submission is prevented.
- The system records the action and result.

## Verification

- Case remains open while the financial outcome is unresolved.
- New bank or provider evidence can trigger verification.
- Case closes only when the configured condition is satisfied.
- Mismatched amounts or conflicting records trigger escalation.

## Audit and security

- All consequential actions appear in the audit history.
- Users cannot access another organization's data.
- Restricted actions are rejected without approval.
- Source data is clearly marked as synthetic in the demo.

---

# 20. Open Product and Business Decisions

These decisions do not block the product baseline, but must be resolved before the relevant production capability is built.

1. Which payment provider will be the first live integration?
2. Which second provider is most valuable to target merchants?
3. Which specific provider APIs and scopes can be obtained under merchant/partner authorization?
4. Which bank statement formats will be supported at pilot launch?
5. Which authorized support channels expose case creation and status retrieval?
6. What is the final merchant pricing model?
7. Which cloud region and deployment model will be used?
8. What retention periods apply to each financial and personal-data category?
9. Which LLM provider/model satisfies quality, latency, cost and data-handling requirements?
10. Which notifications are supported at launch: in-app, email, SMS or messaging integrations?
11. Which roles can approve which actions and thresholds?
12. What merchant cohort and baseline metrics will be used for pilot evaluation?
13. What legal and regulatory assessments are required for the final operating model?

---

# 21. Assumptions and Constraints

## 21.1 Assumptions

- Merchants can access or export at least some payment-provider and bank records.
- Provider APIs and report schemas differ and may have access constraints.
- Provider access may require merchant onboarding, approval or commercial agreements.
- Bank statement data may be incomplete or inconsistent.
- Some support channels will not expose machine-readable case APIs.
- Merchants need both simplified and advanced experiences.
- AI model calls can fail, time out or produce incorrect interpretations.

## 21.2 Constraints

- Live integrations must not be fabricated or represented as active without authorization.
- No financial credentials or authentication secrets should be collected by SettleSaathi.
- All monetary calculations must be deterministic and reproducible.
- The AI agent cannot bypass permissions or approval controls.
- The product cannot guarantee that a provider or bank will resolve an issue.
- Product claims and KPI improvements must be supported by measured evidence.

---

# 22. Glossary

| Term | Definition |
|---|---|
| Collection | Payment amount successfully collected from a customer, according to the source record |
| Settlement | Provider-reported process of calculating and transferring merchant proceeds |
| Settlement batch | Group of settlement entries processed together by a provider |
| Settlement entry | Transaction-level item included in a settlement batch |
| Payout | Provider-reported transfer or payout instruction to the merchant's bank |
| Bank credit | Credit entry appearing in an authorized bank-data source |
| UTR | Unique Transaction Reference used in supported payment/bank rails |
| Reconciliation | Process of matching related records and explaining differences |
| Exception | A record or relationship that cannot be confidently reconciled or requires attention |
| Candidate match | A possible record match that has not been confirmed |
| Evidence package | Collection of source records, references and calculations supporting an investigation |
| Agent run | One persisted execution of an AI-assisted workflow |
| Bounded autonomy | Agent execution constrained by permissions, policy, approved tools and verification requirements |
| Idempotency | Property ensuring repeated execution of the same request does not create duplicate effects |
| Canonical data model | Provider-independent representation of normalized financial records |
| Account Aggregator | Regulated framework participant facilitating consent-based financial information sharing under applicable rules |
| False closure | Case marked resolved without satisfying its required verification conditions |

---

# 23. Research and Reference Register

The following official or primary references are starting points for implementation research. API versions, access requirements, endpoint availability, contractual terms and regulatory commencement must be rechecked before implementation.

## Payment-provider documentation

1. [Paytm — Settlement Order Detail API](https://business.paytm.com/docs/api/settlement-order-detail-api/)
2. [Paytm — Callback and Webhook Documentation](https://business.paytm.com/docs/callback-and-webhook/)
3. [Paytm — Settlement Introduction](https://business.paytm.com/docs/settlement-introduction)
4. [Paytm — Merchant Settlement Support](https://business.paytm.com/support/how-can-i-check-my-settlements)
5. [Cashfree — Settlement and Reconciliation Guide](https://www.cashfree.com/settlement-and-reconciliation-guide/)

## Payments ecosystem

6. [NPCI — UPI HELP Assistant pilot circular](https://www.npci.org.in/uploads/UPI_OC_No_227_FY_2025_26_Introduction_of_UPI_HELP_Assistant_a_pilot_an_AI_powered_support_for_UPI_payments_cd501de8f3.pdf)
7. [NPCI — UPI FAQs](https://www.npci.org.in/what-we-do/upi/faqs)
8. [NPCI — UPI Settlement Process](https://www.npci.org.in/PDF/npci/others/UPI-Settlement-Process.pdf)

## Banking and data protection

9. [RBI — NBFC Account Aggregator Master Directions](https://systemhealth.rbi.org.in/Scripts/BS_ViewMasDirections.aspx_id%3D10598%281%29.html)
10. [Government of India — Account Aggregator Framework](https://www.financialservices.gov.in/account-aggregator-framework)
11. [MeitY — Digital Personal Data Protection Rules, 2025](https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa?pageTitle=Digital-Personal-Data-Protection-Rules-2025)
12. [India Code — Digital Personal Data Protection Act, 2023](https://www.indiacode.nic.in/indiacode/handle/123456789/22037?view_type=browse)

---

# 24. Product Baseline and Next Deliverables

This PRD is the baseline for the next project phase. Changes to scope, autonomy, data access, financial logic or case closure rules should be documented and versioned.

The next deliverables, to be created from this PRD, are:

1. **UX and application specification:** Screen inventory, navigation, user flows, states, interaction details and responsive behavior.
2. **Agent workflow specification:** Agent state machine, tool registry, tool schemas, policies, approval flows, retries, checkpoints and evaluation cases.
3. **System architecture and API specification:** Database schema, service/module boundaries, API contracts, provider adapter interfaces, event contracts, deployment and observability.
4. **Implementation backlog:** Epics, user stories, acceptance tests, priorities, dependencies and release gates.

## Final product statement

SettleSaathi is an autonomous merchant operations platform that brings payment providers, banking records and business workflows into one intelligent system.

It does not merely tell merchants what happened to their money. It helps them investigate, act and establish what actually happened.

**SettleSaathi — Know your money. Understand your operations. Let your AI teammate handle the work.**

---

**Document owner:** SettleSaathi Product & Engineering  
**Version:** 1.0  
**Status:** Proposed requirements baseline; subject to product validation, provider access confirmation, legal review and implementation design.
