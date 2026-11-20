import unittest
import hashlib
import json
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from src.reconciliation.audit_objects import hash_expected_objects, list_bucket_objects, manifest_buckets
from src.reconciliation.reconcile import reconcile_spark_table


class FakePaginator:
    def paginate(self, **kwargs):
        self.kwargs = kwargs
        yield {"Contents": [{"Key": "prefix/a.wav", "Size": 10, "ETag": '"etag-a"'}]}
        yield {"Contents": [{"Key": "prefix/b.wav", "Size": 20, "ETag": '"etag-b"'}]}


class FakeS3:
    def get_paginator(self, operation):
        self.operation = operation
        self.paginator = FakePaginator()
        return self.paginator

    def get_object(self, **kwargs):
        self.get_object_args = kwargs
        return {"Body": BytesIO(b"abcdef")}


class FakeRow(dict):
    def asDict(self, recursive=True):
        return dict(self)


class FakeDataFrame:
    def __init__(self, rows):
        self.rows = rows

    def select(self, *columns):
        return self

    def collect(self):
        return [FakeRow(row) for row in self.rows]


class FakeSpark:
    def __init__(self, rows):
        self.rows = rows

    def table(self, table):
        return FakeDataFrame(self.rows)


class OneObjectPaginator:
    def paginate(self, **kwargs):
        yield {"Contents": [{"Key": "main/a.wav", "Size": 6, "ETag": '"e"'}]}


class OneObjectS3:
    def get_paginator(self, operation):
        return OneObjectPaginator()

    def get_object(self, **kwargs):
        return {"Body": BytesIO(b"abcdef")}


class ReconciliationReaderTests(unittest.TestCase):
    def test_manifest_buckets_are_derived_and_deduplicated(self):
        rows = [
            {"recording_id": "a", "object_uri": "s3://audio/main/a.wav"},
            {"recording_id": "b", "object_uri": "s3a://audio/main/b.wav"},
        ]
        self.assertEqual(manifest_buckets(rows), ["audio"])

    def test_object_reader_consumes_every_page_and_normalizes_etag(self):
        client = FakeS3()
        objects = list_bucket_objects(client, "audio")
        self.assertEqual(client.operation, "list_objects_v2")
        self.assertEqual(client.paginator.kwargs, {"Bucket": "audio"})
        self.assertEqual([obj["uri"] for obj in objects], [
            "s3://audio/prefix/a.wav", "s3://audio/prefix/b.wav"
        ])
        self.assertEqual([obj["etag"] for obj in objects], ["etag-a", "etag-b"])
        self.assertEqual([obj["size"] for obj in objects], [10, 20])

    def test_hash_reader_downloads_only_listed_expected_objects_in_chunks(self):
        client = FakeS3()
        expected = [{"recording_id": "a", "object_uri": "s3://audio/main/a.wav"}]
        listed = [{"uri": "s3://audio/main/a.wav"}, {"uri": "s3://audio/stray.wav"}]
        hashes, byte_count = hash_expected_objects(client, expected, listed, chunk_bytes=2)
        self.assertEqual(client.get_object_args, {"Bucket": "audio", "Key": "main/a.wav"})
        self.assertEqual(byte_count, 6)
        self.assertEqual(hashes["s3://audio/main/a.wav"], {
            "sha256": hashlib.sha256(b"abcdef").hexdigest(), "size": 6
        })

    def test_spark_reconciliation_combines_all_seven_invariants(self):
        checksum = hashlib.sha256(b"abcdef").hexdigest()
        fields = {
            "recording_id": "a", "device_id": "device-a", "start_time": "2026-09-24T06:30:00Z",
            "object_uri": "s3://audio/main/a.wav", "file_size_bytes": 6, "sha256": checksum,
        }
        with TemporaryDirectory() as folder:
            expected_path = Path(folder) / "expected.csv"
            expected_path.write_text(
                "recording_id,device_id,start_time,object_uri,file_size_bytes,sha256\n"
                f"a,device-a,2026-09-24T06:30:00Z,s3://audio/main/a.wav,6,{checksum}\n",
                encoding="utf-8",
            )
            result = reconcile_spark_table(FakeSpark([fields]), "lab.main.recordings", expected_path, OneObjectS3())
        self.assertTrue(result["all_pass"])
        self.assertTrue(result["exact_recovery"])
        self.assertEqual(result["hashed_byte_count"], 6)
        self.assertEqual(result["I7_no_extras"]["extra_recording_ids"], [])
        schema_path = Path(__file__).resolve().parents[1] / "schemas" / "reconciliation_result.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        try:
            import jsonschema
        except ImportError:
            self.assertTrue(set(schema["required"]).issubset(result))
        else:
            jsonschema.validate(result, schema)


if __name__ == "__main__":
    unittest.main()
