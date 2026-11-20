import hashlib
import unittest

from src.reconciliation.invariants import reconcile_i6_i7


class ExtraMetadataInvariantTests(unittest.TestCase):
    def test_i7_passes_when_actual_ids_are_expected(self):
        expected = [{
            "recording_id": "a", "object_uri": "s3://audio/a.wav",
            "file_size_bytes": 1, "sha256": hashlib.sha256(b"a").hexdigest(),
        }]
        result = reconcile_i6_i7(expected, expected, {"s3://audio/a.wav": {"size": 1, "sha256": expected[0]["sha256"]}})
        self.assertTrue(result["I7_no_extras"]["passed"])

    def test_i7_reports_exact_foreign_recording_id(self):
        expected = [{
            "recording_id": "a", "object_uri": "s3://audio/a.wav",
            "file_size_bytes": 1, "sha256": hashlib.sha256(b"a").hexdigest(),
        }]
        actual = expected + [{"recording_id": "foreign", "object_uri": "s3://audio/foreign.wav"}]
        result = reconcile_i6_i7(expected, actual, {"s3://audio/a.wav": {"size": 1, "sha256": expected[0]["sha256"]}})
        self.assertEqual(result["I7_no_extras"]["extra_recording_ids"], ["foreign"])
        self.assertEqual(result["I7_no_extras"]["extra_metadata_row_count"], 1)
        self.assertTrue(result["I6_byte_integrity"]["passed"])


if __name__ == "__main__":
    unittest.main()
