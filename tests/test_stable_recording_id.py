import csv
import unittest
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "dataset.yaml"

MANIFESTS = [
    ROOT / "data" / "manifests" / "manifest_main.csv",
    ROOT / "data" / "manifests" / "manifest_kantin.csv",
    ROOT / "data" / "manifests" / "manifest_embungd.csv",
    ROOT / "data" / "manifests" / "manifest_kebunraya.csv",
]


def parse_explicit_timestamp(value):
    """Parse timestamp yang wajib membawa zona waktu; hasil dinormalisasi ke UTC."""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"Timestamp tidak memiliki zona waktu: {value!r}")

    return parsed.astimezone(timezone.utc)


class StableRecordingIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with CONFIG_PATH.open("r", encoding="utf-8") as stream:
            cls.config = yaml.safe_load(stream)["dataset"]

        cls.source_tz = ZoneInfo(cls.config["source_timezone"])
        cls.seen_recording_ids = set()
        cls.seen_uris = set()

    def test_naive_timestamp_digagalkan(self):
        with self.assertRaises(ValueError):
            parse_explicit_timestamp("2026-09-24T06:30:00")

    def test_manifest_identity_uri_dan_utc_konsisten(self):
        for manifest_path in MANIFESTS:
            with self.subTest(manifest=manifest_path.name):
                self.assertTrue(manifest_path.is_file(), f"Manifest tidak ditemukan: {manifest_path}")

                with manifest_path.open("r", encoding="utf-8-sig", newline="") as stream:
                    rows = list(csv.DictReader(stream))

                self.assertTrue(rows, f"Manifest kosong: {manifest_path}")

                for row in rows:
                    filename = Path(row["source_path"]).name
                    filename_stem = Path(filename).stem

                    # ID harus selalu berasal dari device_id dan nama file.
                    expected_id = self.config["recording_id"]["rule"].format(
                        device_id=row["device_id"],
                        filename_stem=filename_stem,
                    )
                    self.assertEqual(row["recording_id"], expected_id)

                    # Nama file berisi waktu lokal; manifest harus menyimpannya
                    # sebagai waktu UTC dengan zona waktu eksplisit.
                    local_naive = datetime.strptime(filename_stem, "%Y%m%d_%H%M%S")
                    expected_utc = local_naive.replace(
                        tzinfo=self.source_tz
                    ).astimezone(timezone.utc)
                    manifest_utc = parse_explicit_timestamp(row["start_time"])
                    self.assertEqual(manifest_utc, expected_utc)

                    # URI memakai tanggal UTC, device_id, dan nama file asli.
                    expected_uri = self.config["expected_object_uri"]["rule"].format(
                        scheme=self.config["expected_object_uri"]["scheme"],
                        bucket=self.config["expected_object_uri"]["bucket"],
                        device_id=row["device_id"],
                        start_time_utc_date=manifest_utc.strftime("%Y-%m-%d"),
                        original_filename=filename,
                    )
                    self.assertEqual(row["expected_object_uri"], expected_uri)

                    expected_metadata = self.config["expected_metadata"]["rule"].format(
                        recording_id=expected_id
                    )
                    self.assertEqual(row["expected_metadata"], expected_metadata)

                    # ID dan URI harus unik di seluruh empat manifest.
                    self.assertNotIn(row["recording_id"], self.seen_recording_ids)
                    self.assertNotIn(row["expected_object_uri"], self.seen_uris)
                    self.seen_recording_ids.add(row["recording_id"])
                    self.seen_uris.add(row["expected_object_uri"])


if __name__ == "__main__":
    unittest.main()