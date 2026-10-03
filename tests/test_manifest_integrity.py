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


class ManifestIntegrityTests(unittest.TestCase):
    def test_recording_id_tidak_kosong_dan_unik(self):
        semua_id = []

        for manifest in MANIFESTS:
            self.assertTrue(manifest.is_file(), f"Manifest tidak ditemukan: {manifest}")
            rows = read_rows(manifest)
            self.assertTrue(rows, f"Manifest kosong: {manifest}")

            for nomor_baris, row in enumerate(rows, start=2):
                recording_id = (row.get("recording_id") or "").strip()
                self.assertTrue(
                    recording_id,
                    f"{manifest.name}, baris {nomor_baris}: recording_id kosong",
                )
                semua_id.append(recording_id)

        self.assertEqual(
            len(semua_id),
            len(set(semua_id)),
            "Ada recording_id duplikat di antara manifest",
        )

    def test_sha256_tidak_kosong_dan_formatnya_valid(self):
        for manifest in MANIFESTS:
            self.assertTrue(manifest.is_file(), f"Manifest tidak ditemukan: {manifest}")
            rows = read_rows(manifest)

            for nomor_baris, row in enumerate(rows, start=2):
                sha256 = (row.get("sha256") or "").strip()
                self.assertRegex(
                    sha256,
                    SHA256_PATTERN,
                    f"{manifest.name}, baris {nomor_baris}: SHA-256 kosong "
                    "atau bukan 64 karakter hexadecimal",
                )


if __name__ == "__main__":
    unittest.main()