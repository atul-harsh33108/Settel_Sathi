"""Test synthetic data safety and non-exposure of real personal or financial identifiers."""

import tempfile
import unittest
from pathlib import Path
from serv_data.src.generator import SyntheticDataGenerator
from serv_data.src.validator import FixtureValidator


class TestSafetyAndLabels(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.tmp_dir.name)
        gen = SyntheticDataGenerator(output_dir=self.output_dir, seed=42)
        gen.generate()
        self.validator = FixtureValidator(self.output_dir)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_no_real_identity_or_credential_patterns(self):
        """Ensure no real phone, PAN, Aadhaar, or live endpoints exist in any generated artifact."""
        self.validator._validate_safety_and_prefixes()
        self.assertEqual(len(self.validator.errors), 0, f"Safety errors found: {self.validator.errors}")


if __name__ == "__main__":
    unittest.main()

