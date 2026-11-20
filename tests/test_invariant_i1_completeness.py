import unittest

from src.reconciliation.invariants import reconcile_i1_i2


class CompletenessInvariantTests(unittest.TestCase):
    def test_i1_passes_when_every_expected_id_is_present(self):
        result = reconcile_i1_i2(["a", "b", "c"], ["c", "a", "b"])
        self.assertTrue(result["I1_completeness"]["passed"])
        self.assertEqual(result["I1_completeness"]["missing_count"], 0)
        self.assertEqual(result["I1_completeness"]["missing_rate"], 0)

    def test_i1_reports_expected_ids_missing_from_actual_metadata(self):
        result = reconcile_i1_i2(["a", "b", "c", "d"], ["a", "c"])
        self.assertFalse(result["I1_completeness"]["passed"])
        self.assertEqual(result["I1_completeness"]["missing_ids"], ["b", "d"])
        self.assertEqual(result["I1_completeness"]["missing_rate"], 0.5)

    def test_empty_or_duplicate_ground_truth_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "empty recording_id"):
            reconcile_i1_i2(["a", ""], ["a"])
        with self.assertRaisesRegex(ValueError, "duplicate recording_id"):
            reconcile_i1_i2(["a", "a"], ["a"])


if __name__ == "__main__":
    unittest.main()
