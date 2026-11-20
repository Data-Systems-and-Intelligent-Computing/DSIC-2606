"""Read every object in the dataset's manifest buckets from the S3 API."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from src.reconciliation.invariants import normalize_object_uri


def manifest_buckets(expected_rows: Iterable[Mapping[str, object]]) -> list[str]:
    """Return sorted distinct buckets referenced by valid expected object URIs."""
    buckets = set()
    for row in expected_rows:
        uri = normalize_object_uri(row.get("object_uri"))
        if uri is None:
            raise ValueError(f"invalid expected object_uri for {row.get('recording_id')!r}")
        buckets.add(uri.removeprefix("s3://").split("/", 1)[0])
    if not buckets:
        raise ValueError("expected metadata contains no object buckets")
    return sorted(buckets)


def list_bucket_objects(s3_client, bucket: str) -> list[dict[str, object]]:
    """List all objects using the paginator; never silently stop at page one."""
    paginator = s3_client.get_paginator("list_objects_v2")
    found: list[dict[str, object]] = []
    for page in paginator.paginate(Bucket=bucket):
        for item in page.get("Contents", []):
            key = str(item["Key"])
            found.append({
                "uri": f"s3://{bucket}/{key}",
                "bucket": bucket,
                "key": key,
                "size": int(item["Size"]),
                "etag": str(item.get("ETag", "")).strip('"'),
            })
    return found


def list_expected_bucket_objects(s3_client, expected_rows: Iterable[Mapping[str, object]]) -> list[dict[str, object]]:
    """Read complete listings for all buckets named by the frozen manifest."""
    buckets = manifest_buckets(expected_rows)
    return [obj for bucket in buckets for obj in list_bucket_objects(s3_client, bucket)]
