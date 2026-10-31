# SettleSaathi Data Strategy & Synthetic Simulation Engine

**Directory:** `serv_data/`  
**Purpose:** Owns the canonical data dictionary, schema contracts, fixed synthetic scenario generator, validation engine, and test oracle for SettleSaathi Release 0.

The `seed` is included in the manifest for reproducibility and future generator extensions. Current scenario records are fixed, so changing the seed does not change their contents.

---

## 1. Directory Structure

```text
serv_data/
├── contracts/
│   ├── data_dictionary.md         # Canonical data dictionary & ER diagram
│   └── schema_specs.md            # Field-by-field CSV/JSON contracts and compatibility rules
├── src/
│   ├── constants.py               # Fictional merchant, stores, prefixes, seed, timestamps
│   ├── models.py                  # Dataclasses and serialization formatting
│   ├── scenarios.py               # Complete scenario definitions SCN-01 through SCN-10
│   ├── generator.py               # Deterministic CSV/JSON generator and SHA-256 hasher
│   ├── invalid_fixtures.py        # Negative test fixture generator (invalid/ directory)
│   ├── validator.py               # Mathematical balance and safety scanner
│   └── cli.py                     # Unified CLI tool
├── tests/
│   ├── test_determinism.py        # Byte-for-byte reproducibility test
│   ├── test_financial_integrity.py# Arithmetic balance and referential integrity tests
│   ├── test_safety_and_labels.py  # Checks for absence of real identity data
│   └── test_oracle_consistency.py # Tests oracle against generated scenarios
├── fixtures/
│   └── v1/                        # Active Release 0 fixture bundle (mirrored to fixtures/synthetic/v1/)
│       ├── manifest.json          # Bundle manifest with SHA-256 checksums
│       ├── transactions.csv       # Customer payments (21 rows)
│       ├── settlements.csv        # Provider payouts (11 rows)
│       ├── settlement_line_items.csv # Line item links (21 rows)
│       ├── bank_statement.csv     # Bank credits (6 rows)
│       ├── mock_support_updates.json # Simulated support events (2 entries)
│       ├── expected_results.json  # Authoritative test oracle (10 scenarios)
│       ├── validation_report.md   # Automated audit report
│       ├── HANDOFF.md             # Developer handoff guide
│       └── invalid/               # 6 negative test fixtures for parser tests
└── README.md
```

---

## 2. CLI Commands

### Generate Fixtures
```powershell
uv run python serv_data/src/cli.py generate --output serv_data/fixtures/v1 --mirror fixtures/synthetic/v1
```

### Validate Fixtures
```powershell
uv run python serv_data/src/cli.py validate --fixture-dir serv_data/fixtures/v1
```

### Test Determinism (Repeatability)
```powershell
uv run python serv_data/src/cli.py test-determinism
```

### Run Automated Tests
```powershell
uv run python -m unittest discover -s serv_data/tests -p "test_*.py"
```

---

## 3. Core Scenarios Included

- **`SCN-01`**: Standard full reconciliation (₹12,500.00).
- **`SCN-02`**: **Hero Hackathon Demo** — ₹18,450.00 expected sales, provider reports settled, but bank credit is missing (`UNMATCHED`). Triggers approval-gated case draft.
- **`SCN-03`**: In-flight settlement within T+1 window (recommend wait).
- **`SCN-04`**: Partial settlement match (₹3,500 settled out of ₹5,000 expected).
- **`SCN-05`**: Fee, tax, and chargeback adjustment explained (₹10,000 gross -> ₹9,623 net).
- **`SCN-06`**: Duplicate transaction row handled and deduplicated.
- **`SCN-07`**: Customer refund balanced.
- **`SCN-08`**: Multi-batch payout consolidated into a single bank credit.
- **`SCN-09`**: Terminal support resolution verified with authoritative UTR credit.
- **`SCN-10`**: Ambiguous support status blocks false closure.

