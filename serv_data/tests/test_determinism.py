"""Test repeatability and byte-for-byte determinism of the data generator."""

import tempfile
import unittest
from pathlib import Path
from serv_data.src.generator import SyntheticDataGenerator, compute_sha256


class TestDeterminism(unittest.TestCase):
    def test_generator_repeatability(self):
        """Prove that two runs with identical inputs produce identical SHA-256 hashes."""
        with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
            dir1 = Path(tmp1)
            dir2 = Path(tmp2)

            gen1 = SyntheticDataGenerator(output_dir=dir1, seed=42, as_of_timestamp="2026-10-30T18:30:00Z")
            m1 = gen1.generate()

            gen2 = SyntheticDataGenerator(output_dir=dir2, seed=42, as_of_timestamp="2026-10-30T18:30:00Z")
            m2 = gen2.generate()

            # Compare all generated file hashes
            for fname in m1["files"].keys():
                self.assertIn(fname, m2["files"], f"File {fname} missing from run 2")
                hash1 = m1["files"][fname]["sha256"]
                hash2 = m2["files"][fname]["sha256"]
                self.assertEqual(hash1, hash2, f"Hash mismatch for {fname}")

            # Also check manifest file hash
            manifest_hash1 = compute_sha256(dir1 / "manifest.json")
            manifest_hash2 = compute_sha256(dir2 / "manifest.json")
            self.assertEqual(manifest_hash1, manifest_hash2, "Manifest hashes do not match")


if __name__ == "__main__":
    unittest.main()

