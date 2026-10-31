"""Negative and invalid test fixture generator for import parser robustness testing."""

import csv
from pathlib import Path
import shutil
from typing import Optional


def generate_invalid_fixtures(output_dir: Path, mirror_to_root: Optional[Path] = None) -> None:
    """Generate separate invalid CSV fixtures in the specified directory."""
    invalid_dir = Path(output_dir) / "invalid"
    invalid_dir.mkdir(parents=True, exist_ok=True)

    # 1. Malformed decimal in gross_amount ("18.45.00")
    with open(invalid_dir / "malformed_decimal.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "provider", "provider_transaction_id", "merchant_reference", "store_id",
            "occurred_at", "status", "payment_method", "gross_amount", "currency"
        ])
        writer.writerow([
            "PAYTM_MOCK", "mock_txn_bad_dec_001", "mock_ord_bad_001", "store_indiranagar",
            "2026-10-29T10:00:00Z", "SUCCESS", "UPI", "18.45.00", "INR"
        ])

    # 2. Invalid date ("31-02-2026" or non-ISO timestamp)
    with open(invalid_dir / "invalid_date.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "provider", "provider_settlement_id", "payout_reference", "settlement_date",
            "reported_status", "gross_amount", "fee_amount", "tax_amount",
            "adjustment_amount", "net_amount", "currency"
        ])
        writer.writerow([
            "PAYTM_MOCK", "mock_settle_bad_date", "mock_utr_bad_date", "31-02-2026",
            "PROCESSED", "18450.00", "0.00", "0.00", "0.00", "18450.00", "INR"
        ])

    # 3. Unsupported currency ("USD" instead of "INR")
    with open(invalid_dir / "unsupported_currency.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "provider", "provider_transaction_id", "merchant_reference", "store_id",
            "occurred_at", "status", "payment_method", "gross_amount", "currency"
        ])
        writer.writerow([
            "PAYTM_MOCK", "mock_txn_bad_curr", "mock_ord_bad_curr", "store_indiranagar",
            "2026-10-29T10:00:00Z", "SUCCESS", "UPI", "100.00", "USD"
        ])

    # 4. Missing required field (missing provider_transaction_id)
    with open(invalid_dir / "missing_required_field.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "provider", "provider_transaction_id", "merchant_reference", "store_id",
            "occurred_at", "status", "payment_method", "gross_amount", "currency"
        ])
        writer.writerow([
            "PAYTM_MOCK", "", "mock_ord_missing_id", "store_indiranagar",
            "2026-10-29T10:00:00Z", "SUCCESS", "UPI", "500.00", "INR"
        ])

    # 5. Duplicate upload rows (identical row repeated)
    with open(invalid_dir / "duplicate_rows.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "statement_entry_id", "bank_account_alias", "booking_date", "direction",
            "amount", "currency", "narration", "utr_reference"
        ])
        row = ["mock_bank_dup_entry", "bank_acc_4092", "2026-10-29", "CREDIT", "5000.00", "INR", "NEFT-PAYTM-dup", "mock_utr_dup"]
        writer.writerow(row)
        writer.writerow(row)

    # 6. Unmatched reference in settlement line items (references non-existent transaction)
    with open(invalid_dir / "unmatched_reference.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "provider_settlement_id", "line_item_id", "source_reference", "line_type", "amount", "currency"
        ])
        writer.writerow([
            "mock_settle_nonexistent", "mock_line_ghost", "mock_txn_ghost_9999", "PAYMENT", "1000.00", "INR"
        ])

    if mirror_to_root:
        mirror_invalid = Path(mirror_to_root) / "invalid"
        mirror_invalid.mkdir(parents=True, exist_ok=True)
        for invalid_file in invalid_dir.glob("*.csv"):
            shutil.copy2(invalid_file, mirror_invalid / invalid_file.name)

