"""Constants, synthetic identities, and configuration for the SettleSaathi data generator."""

from datetime import datetime, timezone

# Synthetic organization and business identities
SYNTHETIC_MERCHANT_NAME = "Aarav Stores Demo Pvt. Ltd."
ORGANIZATION_ID = "org_aarav_demo"

# Demo retail stores
STORE_INDIRANAGAR = "store_indiranagar"
STORE_KORAMANGALA = "store_koramangala"
STORE_NAMES = {
    STORE_INDIRANAGAR: "Indiranagar Demo Store",
    STORE_KORAMANGALA: "Koramangala Demo Store",
}

# Provider and banking identities
PROVIDER_CODE = "PAYTM_MOCK"
PROVIDER_DISPLAY_NAME = "Paytm Mock Connector"
BANK_ACCOUNT_ALIAS = "bank_acc_4092"
BANK_ACCOUNT_DISPLAY = "Demo Business Account •••• 4092"

# Currencies and units
CURRENCY_INR = "INR"

# Versioning and determinism baselines
DATASET_VERSION = "v1"
SCHEMA_VERSION = "1.0"
DEFAULT_RANDOM_SEED = 42

# Fixed as-of timestamp: 2026-10-30T18:30:00Z (corresponds to Midnight 31 Oct 2026 IST)
FIXED_AS_OF_TIMESTAMP = "2026-10-30T18:30:00Z"
FIXED_AS_OF_DATE = "2026-10-30"

# Synthetic non-routable ID prefixes
PREFIX_TRANSACTION = "mock_txn_"
PREFIX_SETTLEMENT = "mock_settle_"
PREFIX_LINE_ITEM = "mock_line_"
PREFIX_BANK_ENTRY = "mock_bank_"
PREFIX_CASE = "mock_case_"
PREFIX_UTR = "mock_utr_"
PREFIX_ORDER = "mock_ord_"
PREFIX_TICKET = "mock_ticket_"

# Mandatory synthetic notice header / disclaimer
SYNTHETIC_NOTICE = "Synthetic demo data — not a live provider or bank connection"

