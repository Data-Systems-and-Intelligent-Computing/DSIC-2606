import unittest

from src.idempotence.conflict_guard import DuplicateRecordingError
from src.idempotence.metadata_upsert import metadata_conflicting_fields, normalize_metadata_records


def metadata(recording_id="RID-1"):
    return {
        "recording_id": recording_id,
        "device_id": "DEVICE",
        "start_time": "2026-01-01T00:00:00Z",
        "object_uri": "s3://audiomoth/MAIN/2026-01-01/RID-1.WAV",
        "file_size_bytes": "123",
        "sha256": "A" * 64,
    }


class MetadataUpsertPolicyTests(unittest.TestCase):
    def test_equal_existing_metadata_is_a_noop_candidate(self):
        expected = normalize_metadata_records([metadata()])[0]
        actual = dict(expected, file_size_bytes=123, sha256="a" * 64)
        self.assertEqual(metadata_conflicting_fields(expected, actual), [])

    def test_any_changed_ground_truth_field_is_a_conflict(self):
        expected = normalize_metadata_records([metadata()])[0]
        actual = dict(expected, object_uri="s3://audiomoth/wrong.wav")
        self.assertEqual(metadata_conflicting_fields(expected, actual), ["object_uri"])

    def test_duplicate_recording_id_in_one_merge_source_is_rejected(self):
        with self.assertRaises(DuplicateRecordingError):
            normalize_metadata_records([metadata(), metadata()])

    def test_missing_metadata_fields_are_rejected(self):
        record = metadata()
        record.pop("sha256")
        with self.assertRaisesRegex(ValueError, "sha256"):
            normalize_metadata_records([record])


if __name__ == "__main__":
    unittest.main()
