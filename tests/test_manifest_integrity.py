import csv
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = [
    ROOT / "data" / "manifests" / "manifest_main.csv",
    ROOT / "data" / "manifests" / "manifest_kantin.csv",
    ROOT / "data" / "manifests" / "manifest_embungd.csv",
    ROOT / "data" / "manifests" / "manifest_kebunraya.csv",
]

SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


def read_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def validate_rows(rows):
    """Return manifest integrity errors for recording IDs and SHA-256 values."""
    errors = []
    seen_ids = set()

    for row_number, row in enumerate(rows, start=2):
        recording_id = (row.get("recording_id") or "").strip()
        if not recording_id:
            errors.append(f"baris {row_number}: recording_id kosong")
        elif recording_id in seen_ids:
            errors.append(f"baris {row_number}: recording_id duplikat {recording_id!r}")
        else:
            seen_ids.add(recording_id)

        sha256 = (row.get("sha256") or "").strip()
        if not sha256:
            errors.append(f"baris {row_number}: SHA-256 kosong")
        elif not SHA256_PATTERN.fullmatch(sha256):
            errors.append(f"baris {row_number}: SHA-256 tidak valid")

    return errors


class ManifestIntegrityTests(unittest.TestCase):
    def test_semua_manifest_memiliki_id_unik_dan_hash_valid(self):
        for manifest in MANIFESTS:
            self.assertTrue(manifest.is_file(), f"Manifest tidak ditemukan: {manifest}")
            rows = read_rows(manifest)
            self.assertTrue(rows, f"Manifest kosong: {manifest}")
            self.assertEqual(validate_rows(rows), [], manifest.name)

    def test_duplikat_recording_id_ditolak(self):
        rows = [
            {"recording_id": "MAIN_20260924_133000", "sha256": "a" * 64},
            {"recording_id": "MAIN_20260924_133000", "sha256": "b" * 64},
        ]

        self.assertTrue(any("duplikat" in error for error in validate_rows(rows)))

    def test_recording_id_kosong_dan_hash_kosong_atau_invalid_ditolak(self):
        rows = [
            {"recording_id": "", "sha256": ""},
            {"recording_id": "MAIN_20260924_133001", "sha256": "not-a-hash"},
        ]

        errors = validate_rows(rows)
        self.assertTrue(any("recording_id kosong" in error for error in errors))
        self.assertTrue(any("SHA-256 kosong" in error for error in errors))
        self.assertTrue(any("SHA-256 tidak valid" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
