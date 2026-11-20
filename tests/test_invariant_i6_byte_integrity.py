import hashlib
import unittest

from src.reconciliation.invariants import reconcile_i6_i7


class ByteIntegrityInvariantTests(unittest.TestCase):
    def test_i6_passes_for_expected_size_and_actual_sha256(self):
        content = b"wav-bytes"
        expected = [{
            "recording_id": "a", "object_uri": "s3://audio/a.wav",
            "file_size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
        }]
        observed = {"s3://audio/a.wav": {"size": len(content), "sha256": hashlib.sha256(content).hexdigest()}}
        result = reconcile_i6_i7(expected, expected, observed)
        self.assertTrue(result["I6_byte_integrity"]["passed"])
        self.assertEqual(result["I6_byte_integrity"]["hashed_object_count"], 1)
        self.assertEqual(result["I6_byte_integrity"]["hashed_byte_count"], len(content))

    def test_i6_reports_exact_recording_on_byte_corruption_only(self):
        good = b"wav-bytes"
        changed = b"Wav-bytes"
        expected = [{
            "recording_id": "a", "object_uri": "s3://audio/a.wav",
            "file_size_bytes": len(good), "sha256": hashlib.sha256(good).hexdigest(),
        }]
        observed = {"s3://audio/a.wav": {"size": len(changed), "sha256": hashlib.sha256(changed).hexdigest()}}
        result = reconcile_i6_i7(expected, expected, observed)
        self.assertEqual(result["I6_byte_integrity"]["checksum_mismatch_count"], 1)
        self.assertEqual(result["I6_byte_integrity"]["checksum_mismatches"][0]["recording_id"], "a")
        self.assertTrue(result["I7_no_extras"]["passed"])


if __name__ == "__main__":
    unittest.main()
