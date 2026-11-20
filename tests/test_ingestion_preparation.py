import unittest
from unittest.mock import patch
from pathlib import Path

from src.ingestion.write_metadata import validate_metadata_table
from src.ingestion.write_object import mounted_source_path, object_target, prepare_upload_record
from src.ingestion.microbatch import _process_event, load_frozen_batches, load_manifest, validate_event_source

ROOT = Path(__file__).resolve().parents[1]


class IngestionPreparationTests(unittest.TestCase):
    def test_object_target_splits_bucket_and_key(self):
        self.assertEqual(
            object_target("s3://audiomoth/MAIN_5JAM/2026-09-24/a.wav"),
            ("audiomoth", "MAIN_5JAM/2026-09-24/a.wav"),
        )

    def test_object_target_rejects_non_s3_and_empty_key(self):
        for value in ("http://audiomoth/key", "s3://audiomoth", "s3://audiomoth/key?x=1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                object_target(value)

    def test_source_path_maps_only_main_manifest_files_to_mount(self):
        self.assertEqual(
            mounted_source_path("data/raw/audiomoth/main/file.WAV", "/data/raw"),
            Path("/data/raw/file.WAV"),
        )
        with self.assertRaises(ValueError):
            mounted_source_path("data/raw/audiomoth/robustness/file.WAV")

    def test_prepare_upload_record_uses_manifest_identity_and_threshold(self):
        row = {
            "recording_id": "RID-1",
            "source_path": "data/raw/audiomoth/main/file.WAV",
            "expected_object_uri": "s3://audiomoth/prefix/file.WAV",
            "file_size_bytes": "3520800",
            "sha256": "a" * 64,
        }
        prepared = prepare_upload_record(row, "/data/raw", 5 * 1024**2, 5 * 1024**2)
        self.assertEqual(prepared["source_path"].replace("\\", "/"), "/data/raw/file.WAV")
        self.assertEqual(prepared["bucket"], "audiomoth")
        self.assertEqual(prepared["multipart_threshold_bytes"], 5 * 1024**2)

    def test_metadata_table_must_be_in_lab_catalog(self):
        self.assertEqual(validate_metadata_table("lab.main.recordings"), "lab.main.recordings")
        for value in ("other.main.recordings", "lab.main;drop.table", "lab.main"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_metadata_table(value)

    def test_process_event_puts_each_object_before_its_metadata_commit(self):
        manifest = {
            f"RID-{index}": {
                "recording_id": f"RID-{index}",
                "device_id": "DEVICE",
                "start_time": "2026-01-01T00:00:00Z",
                "source_path": "data/raw/audiomoth/main/file.WAV",
                "file_size_bytes": "1",
                "sha256": "a" * 64,
                "expected_object_uri": f"s3://audiomoth/key-{index}",
            }
            for index in range(10)
        }
        event = {"batch_id": 0, "recording_ids": list(manifest)}
        calls = []

        def put(_client, item):
            calls.append(("put", item["recording_id"]))
            return {"recording_id": item["recording_id"]}

        def append(_spark, records, table):
            calls.append(("metadata", records[0]["recording_id"]))

        with patch("src.ingestion.microbatch.prepare_upload_record", side_effect=lambda row, *_: row), \
             patch("src.ingestion.microbatch.upload_recording", side_effect=put), \
             patch("src.ingestion.microbatch.append_metadata", side_effect=append):
            _process_event(
                object(), event, manifest, Path("/unused"), 1, 1,
                "lab.main.recordings", object(), expected_spark_batch_id=0,
            )

        self.assertEqual(
            calls,
            [item for rid in manifest for item in (("put", rid), ("metadata", rid))],
        )

    def test_process_event_rejects_wrong_spark_order_before_any_write(self):
        with patch("src.ingestion.microbatch.upload_recording") as put:
            with self.assertRaisesRegex(RuntimeError, "replay order mismatch"):
                _process_event(
                    object(), {"batch_id": 1, "recording_ids": []}, {}, Path("/unused"),
                    1, 1, "lab.main.recordings", object(), expected_spark_batch_id=0,
                )
            put.assert_not_called()

    def test_idempotent_process_event_uses_object_guard_then_metadata_upsert(self):
        manifest = {
            f"RID-{index}": {
                "recording_id": f"RID-{index}",
                "device_id": "DEVICE",
                "start_time": "2026-01-01T00:00:00Z",
                "source_path": "data/raw/audiomoth/main/file.WAV",
                "file_size_bytes": "1",
                "sha256": "a" * 64,
                "expected_object_uri": f"s3://audiomoth/key-{index}",
            }
            for index in range(10)
        }
        event = {"batch_id": 0, "recording_ids": list(manifest)}
        calls = []

        def guard(_client, item, **_kwargs):
            calls.append(("object", item["recording_id"]))
            return {"decision": "SUDAH ADA", "bytes_verified": 1}

        def upsert(_spark, records, table):
            calls.append(("metadata", records[0]["recording_id"]))
            return {"inserted": 1, "already_present": 0}

        with patch("src.ingestion.microbatch.prepare_upload_record", side_effect=lambda row, *_: row), \
             patch("src.ingestion.microbatch.guard_object", side_effect=guard), \
             patch("src.ingestion.microbatch.upsert_metadata", side_effect=upsert), \
             patch("src.ingestion.microbatch.upload_recording") as put, \
             patch("src.ingestion.microbatch.append_metadata") as append:
            _process_event(
                object(), event, manifest, Path("/unused"), 1, 1,
                "lab.main.recordings", object(), expected_spark_batch_id=0,
                idempotence_enabled=True, idempotence_config={"object_guard": {"download_chunk_bytes": 8}},
            )

        self.assertEqual(
            calls,
            [item for rid in manifest for item in (("object", rid), ("metadata", rid))],
        )
        put.assert_not_called()
        append.assert_not_called()

    def test_duplicate_recording_id_event_fails_before_any_write(self):
        ids = [f"RID-{index}" for index in range(9)] + ["RID-0"]
        event = {"batch_id": 0, "recording_ids": ids}
        with patch("src.ingestion.microbatch.upload_recording") as put:
            with self.assertRaisesRegex(ValueError, "duplicate recording_id"):
                _process_event(
                    object(), event, {}, Path("/unused"), 1, 1,
                    "lab.main.recordings", object(), expected_spark_batch_id=0,
                )
            put.assert_not_called()

    def test_frozen_main_batch_and_replay_files_agree(self):
        batches = load_frozen_batches(ROOT / "data/batches/batch_order_main.csv")
        manifest = load_manifest(ROOT / "data/manifests/manifest_main.csv")
        validate_event_source(ROOT / "data/replay/main/events", batches)
        self.assertEqual((len(batches), len(manifest)), (30, 300))
        self.assertEqual(len({rid for batch in batches for rid in batch}), 300)


if __name__ == "__main__":
    unittest.main()
