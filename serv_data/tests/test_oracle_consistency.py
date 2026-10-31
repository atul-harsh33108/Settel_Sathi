"""Test consistency of the expected_results.json test oracle."""

import json
import tempfile
import unittest
from pathlib import Path
from serv_data.src.generator import SyntheticDataGenerator


class TestOracleConsistency(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.tmp_dir.name)
        gen = SyntheticDataGenerator(output_dir=self.output_dir, seed=42)
        gen.generate()
        with open(self.output_dir / "expected_results.json", "r", encoding="utf-8") as f:
            self.oracle = json.load(f)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_all_scenarios_covered(self):
        """Verify all 10 scenarios (SCN-01 to SCN-10) are present in oracle."""
        scenarios = self.oracle.get("scenarios", {})
        for i in range(1, 11):
            key = f"SCN-{i:02d}"
            self.assertIn(key, scenarios, f"Missing scenario {key} in oracle")

    def test_scn02_hero_scenario_contract(self):
        """Verify the ₹18,450 missing settlement contract for SCN-02."""
        scn02 = self.oracle["scenarios"]["SCN-02"]
        self.assertEqual(scn02["expected_collected_amount"], "18450.00")
        self.assertEqual(scn02["expected_settled_amount"], "18450.00")
        self.assertEqual(scn02["expected_bank_credit"], "0.00")
        self.assertEqual(scn02["expected_status"], "UNMATCHED")
        self.assertTrue(scn02["expected_case_needed"])
        self.assertTrue(scn02["requires_approval"])


if __name__ == "__main__":
    unittest.main()

