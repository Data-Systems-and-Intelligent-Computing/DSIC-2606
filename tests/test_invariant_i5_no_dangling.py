import unittest

from src.reconciliation.invariants import reconcile_i3_i5


class DanglingMetadataInvariantTests(unittest.TestCase):
    def test_i5_passes_when_every_metadata_uri_exists(self):
        expected = [{"recording_id": "a", "object_uri": "s3://audio/a.wav"}]
        actual = list(expected)
        result = reconcile_i3_i5(expected, actual, [{"uri": "s3://audio/a.wav"}])
        self.assertTrue(result["I5_no_dangling"]["passed"])

    def test_i5_reports_deleted_object_without_other_violations(self):
        expected = [{"recording_id": "a", "object_uri": "s3://audio/a.wav"}]
        actual = list(expected)
        result = reconcile_i3_i5(expected, actual, [])
        self.assertEqual(result["I5_no_dangling"]["dangling_metadata"], [
            {"recording_id": "a", "object_uri": "s3://audio/a.wav"}
        ])
        self.assertTrue(result["I3_referential"]["passed"])
        self.assertTrue(result["I4_no_orphan"]["passed"])


if __name__ == "__main__":
    unittest.main()
