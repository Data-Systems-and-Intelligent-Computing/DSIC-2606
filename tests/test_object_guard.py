import hashlib
import io
import unittest

from src.idempotence.conflict_guard import IdempotenceConflictError
from src.idempotence.object_guard import guard_object


class MissingObject(Exception):
    response = {"Error": {"Code": "NoSuchKey"}, "ResponseMetadata": {"HTTPStatusCode": 404}}


class FakeS3:
    def __init__(self, payload=None, size=None, metadata_sha="not-trusted"):
        self.payload = payload
        self.size = len(payload) if size is None and payload is not None else size
        self.metadata_sha = metadata_sha
        self.get_calls = 0

    def head_object(self, Bucket, Key):
        if self.payload is None:
            raise MissingObject("missing")
        return {"ContentLength": self.size, "ETag": '"etag-1"', "Metadata": {"sha256": self.metadata_sha}}

    def get_object(self, Bucket, Key):
        self.get_calls += 1
        return {"Body": io.BytesIO(self.payload)}


def item_for(payload):
    return {
        "recording_id": "RID-1",
        "expected_object_uri": "s3://audiomoth/canonical/RID-1.WAV",
        "bucket": "audiomoth",
        "object_key": "canonical/RID-1.WAV",
        "file_size_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


class ObjectGuardTests(unittest.TestCase):
    def test_missing_object_is_put(self):
        client = FakeS3()
        puts = []

        def put(_client, item):
            puts.append(item["recording_id"])
            return {"etag": "put-etag"}

        result = guard_object(client, item_for(b"wav"), put=put)
        self.assertEqual(result["decision"], "PUT")
        self.assertEqual(puts, ["RID-1"])
        self.assertEqual(client.get_calls, 0)

    def test_existing_exact_bytes_are_verified_even_if_metadata_lies(self):
        payload = b"same wav bytes"
        client = FakeS3(payload, metadata_sha="0" * 64)
        result = guard_object(client, item_for(payload), download_chunk_bytes=3)
        self.assertEqual(result["decision"], "SUDAH ADA")
        self.assertEqual(result["bytes_verified"], len(payload))
        self.assertEqual(client.get_calls, 1)

    def test_existing_different_bytes_conflict_without_put(self):
        client = FakeS3(b"different")
        puts = []
        with self.assertRaisesRegex(IdempotenceConflictError, "object CONFLICT"):
            guard_object(client, item_for(b"expected"), put=lambda *_: puts.append("PUT"))
        self.assertEqual(puts, [])

    def test_existing_size_mismatch_conflicts_without_download_or_put(self):
        client = FakeS3(b"abc", size=999)
        puts = []
        with self.assertRaisesRegex(IdempotenceConflictError, "size differs"):
            guard_object(client, item_for(b"abc"), put=lambda *_: puts.append("PUT"))
        self.assertEqual(client.get_calls, 0)
        self.assertEqual(puts, [])


if __name__ == "__main__":
    unittest.main()
