"""Test financial balance and referential integrity of generated synthetic data."""

import tempfile
import unittest
from pathlib import Path
from serv_data.src.generator import SyntheticDataGenerator
from serv_data.src.validator import FixtureValidator


class TestFinancialIntegrity(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.tmp_dir.name)
        gen = SyntheticDataGenerator(output_dir=self.output_dir, seed=42)
        gen.generate()
        self.validator = FixtureValidator(self.output_dir)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_settlement_arithmetic_balances(self):
        """Ensure gross - fee - tax + adjustment equals net without floating point drift."""
        self.validator._validate_settlement_math()
        self.assertEqual(len(self.validator.errors), 0, f"Math errors: {self.validator.errors}")

    def test_referential_integrity(self):
        """Ensure line items strictly reference defined transactions and settlements."""
        self.validator._validate_referential_integrity()
        self.assertEqual(len(self.validator.errors), 0, f"Integrity errors: {self.validator.errors}")


if __name__ == "__main__":
    unittest.main()

