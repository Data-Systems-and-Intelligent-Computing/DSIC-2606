import unittest

from src.reconciliation.invariants import normalize_object_uri, reconcile_i3_i5


def row(recording_id, uri):
    return {"recording_id": recording_id, "object_uri": uri}


class ReferentialInvariantTests(unittest.TestCase):
    def test_uri_normalization_changes_only_s3_scheme(self):
        self.assertEqual(normalize_object_uri("s3a://audio//leading.wav"), "s3://audio//leading.wav")

    def test_i3_passes_for_expected_uri_and_s3a_equivalent(self):
        expected = [row("a", "s3://audio/path/a.wav")]
        actual = [row("a", "s3a://audio/path/a.wav")]
        result = reconcile_i3_i5(expected, actual, [{"uri": "s3://audio/path/a.wav"}])
        self.assertTrue(result["I3_referential"]["passed"])

    def test_i3_reports_wrong_uri_and_expected_cross_invariants(self):
        expected = [row("a", "s3://audio/path/a.wav")]
        actual = [row("a", "s3://audio/wrong/a.wav")]
        objects = [{"uri": "s3://audio/path/a.wav"}]
        result = reconcile_i3_i5(expected, actual, objects)
        self.assertEqual(result["I3_referential"]["violations"], [{
            "recording_id": "a",
            "expected_object_uri": "s3://audio/path/a.wav",
            "actual_object_uri": "s3://audio/wrong/a.wav",
        }])
        self.assertEqual(result["I4_no_orphan"]["orphan_object_uris"], ["s3://audio/path/a.wav"])
        self.assertEqual(result["I5_no_dangling"]["dangling_metadata"], [{
            "recording_id": "a", "object_uri": "s3://audio/wrong/a.wav"
        }])


if __name__ == "__main__":
    unittest.main()
