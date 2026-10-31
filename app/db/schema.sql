-- SettleSaathi SQLite Canonical Schema v1.0

CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stores (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    location TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bank_accounts (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    account_alias TEXT NOT NULL UNIQUE,
    account_name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_artifacts (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,
    file_name TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    storage_path TEXT NOT NULL,
    record_count INTEGER NOT NULL DEFAULT 0,
    ingested_at TEXT NOT NULL,
    CONSTRAINT uq_artifact_digest UNIQUE (organization_id, source_type, schema_version, sha256)
);

CREATE INDEX IF NOT EXISTS idx_artifacts_digest ON source_artifacts(organization_id, sha256);

CREATE TABLE IF NOT EXISTS import_jobs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    artifact_id TEXT REFERENCES source_artifacts(id) ON DELETE SET NULL,
    source_type TEXT NOT NULL,
    status TEXT NOT NULL, -- PENDING, PROCESSING, COMPLETED, FAILED
    total_records INTEGER NOT NULL DEFAULT 0,
    processed_records INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    errors_json TEXT,
    idempotent_replay INTEGER NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_import_jobs_artifact ON import_jobs(organization_id, artifact_id);

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    store_id TEXT NOT NULL REFERENCES stores(id),
    provider TEXT NOT NULL,
    provider_transaction_id TEXT NOT NULL,
    merchant_reference TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    status TEXT NOT NULL,
    payment_method TEXT NOT NULL,
    gross_amount TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    source_artifact_id TEXT NOT NULL REFERENCES source_artifacts(id) ON DELETE CASCADE,
    source_row_number INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    CONSTRAINT uq_txn_provider_id UNIQUE (organization_id, provider, provider_transaction_id)
);

CREATE INDEX IF NOT EXISTS idx_transactions_lookup ON transactions(organization_id, provider_transaction_id);
CREATE INDEX IF NOT EXISTS idx_transactions_occurred ON transactions(organization_id, occurred_at);

CREATE TABLE IF NOT EXISTS settlement_batches (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    provider_settlement_id TEXT NOT NULL,
    payout_reference TEXT NOT NULL,
    settlement_date TEXT NOT NULL,
    reported_status TEXT NOT NULL,
    gross_amount TEXT NOT NULL,
    fee_amount TEXT NOT NULL,
    tax_amount TEXT NOT NULL,
    adjustment_amount TEXT NOT NULL,
    net_amount TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    source_artifact_id TEXT NOT NULL REFERENCES source_artifacts(id) ON DELETE CASCADE,
    source_row_number INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    CONSTRAINT uq_settle_provider_id UNIQUE (organization_id, provider, provider_settlement_id)
);

CREATE INDEX IF NOT EXISTS idx_settlements_lookup ON settlement_batches(organization_id, provider_settlement_id);
CREATE INDEX IF NOT EXISTS idx_settlements_payout_ref ON settlement_batches(organization_id, payout_reference);

CREATE TABLE IF NOT EXISTS settlement_line_items (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    provider_settlement_id TEXT NOT NULL,
    line_item_id TEXT NOT NULL,
    source_reference TEXT NOT NULL,
    line_type TEXT NOT NULL,
    amount TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    source_artifact_id TEXT NOT NULL REFERENCES source_artifacts(id) ON DELETE CASCADE,
    source_row_number INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    CONSTRAINT uq_line_item_id UNIQUE (organization_id, line_item_id)
);

CREATE INDEX IF NOT EXISTS idx_line_items_batch ON settlement_line_items(organization_id, provider_settlement_id);
CREATE INDEX IF NOT EXISTS idx_line_items_source_ref ON settlement_line_items(organization_id, source_reference);

CREATE TABLE IF NOT EXISTS bank_entries (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    statement_entry_id TEXT NOT NULL,
    bank_account_alias TEXT NOT NULL REFERENCES bank_accounts(account_alias),
    booking_date TEXT NOT NULL,
    direction TEXT NOT NULL,
    amount TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    narration TEXT NOT NULL,
    utr_reference TEXT,
    source_artifact_id TEXT NOT NULL REFERENCES source_artifacts(id) ON DELETE CASCADE,
    source_row_number INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    CONSTRAINT uq_bank_entry_id UNIQUE (organization_id, statement_entry_id)
);

CREATE INDEX IF NOT EXISTS idx_bank_entries_lookup ON bank_entries(organization_id, statement_entry_id);
CREATE INDEX IF NOT EXISTS idx_bank_entries_utr ON bank_entries(organization_id, utr_reference);
CREATE INDEX IF NOT EXISTS idx_bank_entries_booking ON bank_entries(organization_id, booking_date);

CREATE TABLE IF NOT EXISTS mock_support_updates (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    case_reference TEXT NOT NULL,
    event_at TEXT NOT NULL,
    status TEXT NOT NULL,
    summary TEXT NOT NULL,
    terminal_outcome INTEGER NOT NULL,
    evidence_reference TEXT NOT NULL,
    source_artifact_id TEXT NOT NULL REFERENCES source_artifacts(id) ON DELETE CASCADE,
    source_row_number INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    CONSTRAINT uq_support_update UNIQUE (organization_id, case_reference, event_at)
);

CREATE INDEX IF NOT EXISTS idx_support_case ON mock_support_updates(organization_id, case_reference);

CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    actor_type TEXT NOT NULL DEFAULT 'system',
    actor_id TEXT NOT NULL DEFAULT 'system',
    correlation_id TEXT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_hash TEXT,
    details_json TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_events(organization_id, entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_correlation ON audit_events(organization_id, correlation_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_events(organization_id, created_at);

CREATE TABLE IF NOT EXISTS reconciliation_runs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    rule_version TEXT NOT NULL,
    status TEXT NOT NULL, -- PENDING, COMPLETED, FAILED
    as_of_date TEXT NOT NULL,
    summary_counts_json TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_reconciliation_runs_org ON reconciliation_runs(organization_id, started_at);

CREATE TABLE IF NOT EXISTS reconciliation_results (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES reconciliation_runs(id) ON DELETE CASCADE,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    scenario_id TEXT,
    status TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    collected_amount TEXT NOT NULL,
    settled_amount TEXT NOT NULL,
    bank_credited_amount TEXT NOT NULL,
    discrepancy_amount TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    input_record_ids_json TEXT NOT NULL,
    matched_record_ids_json TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    explanation TEXT NOT NULL,
    case_needed INTEGER NOT NULL DEFAULT 0,
    requires_approval INTEGER NOT NULL DEFAULT 0,
    evaluated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reconciliation_results_run ON reconciliation_results(run_id);
CREATE INDEX IF NOT EXISTS idx_reconciliation_results_scenario ON reconciliation_results(organization_id, scenario_id);
CREATE INDEX IF NOT EXISTS idx_reconciliation_results_status ON reconciliation_results(organization_id, status);

CREATE TABLE IF NOT EXISTS cases (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    reconciliation_result_id TEXT REFERENCES reconciliation_results(id) ON DELETE SET NULL,
    case_type TEXT NOT NULL,
    status TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'MEDIUM',
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    decision_summary TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cases_org ON cases(organization_id);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(organization_id, status);
CREATE INDEX IF NOT EXISTS idx_cases_subject ON cases(organization_id, subject_type, subject_id);
CREATE INDEX IF NOT EXISTS idx_cases_result ON cases(organization_id, reconciliation_result_id);

CREATE TABLE IF NOT EXISTS case_events (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    actor_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    event_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    details_json TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_case_events_case ON case_events(case_id, created_at);
CREATE INDEX IF NOT EXISTS idx_case_events_org ON case_events(organization_id, created_at);

CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,
    action_class TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    requested_by_type TEXT NOT NULL,
    requested_by_id TEXT NOT NULL,
    approved_by TEXT,
    approved_at TEXT,
    expires_at TEXT NOT NULL,
    rejection_reason TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_approvals_case ON approvals(case_id);
CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(organization_id, status);

CREATE TABLE IF NOT EXISTS external_action_attempts (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    approval_id TEXT REFERENCES approvals(id) ON DELETE SET NULL,
    idempotency_key TEXT NOT NULL,
    action_type TEXT NOT NULL,
    status TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    response_json TEXT,
    error_message TEXT,
    executed_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    CONSTRAINT uq_action_idempotency UNIQUE (organization_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_action_attempts_case ON external_action_attempts(case_id);
CREATE INDEX IF NOT EXISTS idx_action_attempts_idem ON external_action_attempts(organization_id, idempotency_key);


