import unittest

from src.reconciliation.audit_objects import list_bucket_objects, manifest_buckets


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


if __name__ == "__main__":
    unittest.main()
