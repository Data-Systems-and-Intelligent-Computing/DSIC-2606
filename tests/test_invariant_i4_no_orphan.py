import unittest

from src.reconciliation.invariants import reconcile_i3_i5


class OrphanObjectInvariantTests(unittest.TestCase):
    def test_i4_passes_when_every_object_is_referenced(self):
        expected = [{"recording_id": "a", "object_uri": "s3://audio/a.wav"}]
        actual = list(expected)
        objects = [{"uri": "s3://audio/a.wav", "size": 12, "etag": "abc"}]
        result = reconcile_i3_i5(expected, actual, objects)
        self.assertTrue(result["I4_no_orphan"]["passed"])
        self.assertEqual(result["I4_no_orphan"]["orphan_object_count"], 0)

    def test_i4_reports_exact_unreferenced_object_without_other_violations(self):
        expected = [{"recording_id": "a", "object_uri": "s3://audio/a.wav"}]
        actual = list(expected)
        objects = [
            {"uri": "s3://audio/a.wav"},
            {"uri": "s3://audio/stray.wav"},
        ]
        result = reconcile_i3_i5(expected, actual, objects)
        self.assertEqual(result["I4_no_orphan"]["orphan_object_uris"], ["s3://audio/stray.wav"])
        self.assertTrue(result["I3_referential"]["passed"])
        self.assertTrue(result["I5_no_dangling"]["passed"])


if __name__ == "__main__":
    unittest.main()
