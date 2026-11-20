import unittest

from src.reconciliation.invariants import reconcile_i1_i2


class UniquenessInvariantTests(unittest.TestCase):
    def test_i2_passes_with_one_row_per_recording_id(self):
        result = reconcile_i1_i2(["a", "b"], ["a", "b"])
        self.assertTrue(result["I2_uniqueness"]["passed"])
        self.assertEqual(result["I2_uniqueness"]["duplicate_recording_count"], 0)

    def test_i2_reports_duplicate_logical_ids_and_excess_rows(self):
        result = reconcile_i1_i2(["a", "b", "c"], ["a", "a", "a", "b"])
        self.assertFalse(result["I2_uniqueness"]["passed"])
        self.assertEqual(result["I2_uniqueness"]["duplicate_recording_count"], 1)
        self.assertEqual(result["I2_uniqueness"]["excess_duplicate_rows"], 2)
        self.assertEqual(result["I2_uniqueness"]["duplicate_ids_and_row_counts"], {"a": 3})

    def test_empty_actual_ids_fail_i2_without_counting_as_missing_ids(self):
        result = reconcile_i1_i2(["a"], ["a", None])
        self.assertTrue(result["I1_completeness"]["passed"])
        self.assertFalse(result["I2_uniqueness"]["passed"])
        self.assertEqual(result["I2_uniqueness"]["invalid_recording_id_rows"], 1)


if __name__ == "__main__":
    unittest.main()
