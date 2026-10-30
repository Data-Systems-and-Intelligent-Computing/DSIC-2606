import csv
import tempfile
import unittest
from pathlib import Path

from scripts.validate_expected_metadata import read_csv, validate_rows


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "manifests" / "manifest_main.csv"
EXPECTED = ROOT / "data" / "ground_truth" / "expected_metadata.csv"


class ExpectedMetadataConsistencyTests(unittest.TestCase):
    def test_expected_metadata_cocok_dengan_manifest(self):
        _, manifest_rows = read_csv(MANIFEST)
        _, expected_rows = read_csv(EXPECTED)
        self.assertEqual(validate_rows(manifest_rows, expected_rows), [])

    def test_perubahan_hash_di_salina_dideteksi(self):
        _, manifest_rows = read_csv(MANIFEST)
        _, expected_rows = read_csv(EXPECTED)
        altered_rows = [dict(row) for row in expected_rows]
        altered_rows[0]["sha256"] = "0" * 64

        errors = validate_rows(manifest_rows, altered_rows)
        self.assertTrue(any("sha256 berbeda" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
