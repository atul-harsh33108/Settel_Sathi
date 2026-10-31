"""Deterministic synthetic data generator engine for SettleSaathi."""

import csv
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from serv_data.src.constants import (
    DATASET_VERSION,
    SCHEMA_VERSION,
    DEFAULT_RANDOM_SEED,
    FIXED_AS_OF_TIMESTAMP,
)
from serv_data.src.scenarios import build_scenarios


def compute_sha256(file_path: Path) -> str:
    """Compute the SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class SyntheticDataGenerator:
    """Generates deterministic, verified synthetic datasets for SettleSaathi."""

    def __init__(
        self,
        output_dir: Path,
        dataset_version: str = DATASET_VERSION,
        seed: int = DEFAULT_RANDOM_SEED,
        as_of_timestamp: str = FIXED_AS_OF_TIMESTAMP,
    ):
        self.output_dir = Path(output_dir)
        self.dataset_version = dataset_version
        self.seed = seed
        self.as_of_timestamp = as_of_timestamp

    def generate(self, mirror_to_root: Optional[Path] = None) -> Dict[str, Any]:
        """Generate all CSV/JSON fixtures, manifest, and test oracle."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        (
            transactions,
            settlements,
            line_items,
            bank_entries,
            support_updates,
            oracle_map,
        ) = build_scenarios()

        # 1. Write transactions.csv
        txn_path = self.output_dir / "transactions.csv"
        txn_headers = [
            "provider",
            "provider_transaction_id",
            "merchant_reference",
            "store_id",
            "occurred_at",
            "status",
            "payment_method",
            "gross_amount",
            "currency",
        ]
        with open(txn_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=txn_headers)
            writer.writeheader()
            for t in transactions:
                writer.writerow(t.to_csv_row())

        # 2. Write settlements.csv
        settle_path = self.output_dir / "settlements.csv"
        settle_headers = [
            "provider",
            "provider_settlement_id",
            "payout_reference",
            "settlement_date",
            "reported_status",
            "gross_amount",
            "fee_amount",
            "tax_amount",
            "adjustment_amount",
            "net_amount",
            "currency",
        ]
        with open(settle_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=settle_headers)
            writer.writeheader()
            for s in settlements:
                writer.writerow(s.to_csv_row())

        # 3. Write settlement_line_items.csv
        line_path = self.output_dir / "settlement_line_items.csv"
        line_headers = [
            "provider_settlement_id",
            "line_item_id",
            "source_reference",
            "line_type",
            "amount",
            "currency",
        ]
        with open(line_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=line_headers)
            writer.writeheader()
            for li in line_items:
                writer.writerow(li.to_csv_row())

        # 4. Write bank_statement.csv
        bank_path = self.output_dir / "bank_statement.csv"
        bank_headers = [
            "statement_entry_id",
            "bank_account_alias",
            "booking_date",
            "direction",
            "amount",
            "currency",
            "narration",
            "utr_reference",
        ]
        with open(bank_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=bank_headers)
            writer.writeheader()
            for b in bank_entries:
                writer.writerow(b.to_csv_row())

        # 5. Write mock_support_updates.json
        support_path = self.output_dir / "mock_support_updates.json"
        with open(support_path, "w", encoding="utf-8") as f:
            json.dump([su.to_dict() for su in support_updates], f, indent=2)

        # 6. Write expected_results.json (Test Oracle)
        oracle_path = self.output_dir / "expected_results.json"
        oracle_payload = {
            "dataset_version": self.dataset_version,
            "as_of_timestamp": self.as_of_timestamp,
            "description": "Deterministic test oracle for SettleSaathi Release 0 reconciliation and case workflows.",
            "scenarios": {k: v.to_dict() for k, v in oracle_map.items()},
        }
        with open(oracle_path, "w", encoding="utf-8") as f:
            json.dump(oracle_payload, f, indent=2)

        # 7. Collect file metadata & compute SHA-256
        data_files = [
            "transactions.csv",
            "settlements.csv",
            "settlement_line_items.csv",
            "bank_statement.csv",
            "mock_support_updates.json",
            "expected_results.json",
        ]

        files_meta = {}
        for fname in data_files:
            fpath = self.output_dir / fname
            files_meta[fname] = {
                "sha256": compute_sha256(fpath),
                "size_bytes": fpath.stat().st_size,
            }

        # 8. Write manifest.json
        manifest = {
            "dataset_version": self.dataset_version,
            "schema_version": SCHEMA_VERSION,
            "seed": self.seed,
            "as_of_timestamp": self.as_of_timestamp,
            "scenarios": list(oracle_map.keys()),
            "record_counts": {
                "transactions": len(transactions),
                "settlements": len(settlements),
                "settlement_line_items": len(line_items),
                "bank_entries": len(bank_entries),
                "mock_support_updates": len(support_updates),
            },
            "files": files_meta,
        }

        manifest_path = self.output_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        # Optional: Mirror to root fixtures directory
        if mirror_to_root:
            mirror_dir = Path(mirror_to_root)
            mirror_dir.mkdir(parents=True, exist_ok=True)
            for fname in data_files + ["manifest.json"]:
                src = self.output_dir / fname
                dst = mirror_dir / fname
                shutil.copy2(src, dst)

        return manifest

