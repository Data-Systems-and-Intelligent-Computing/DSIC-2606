"""Read every object in the dataset's manifest buckets from the S3 API."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from urllib.parse import urlsplit

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


def hash_expected_objects(
    s3_client,
    expected_rows: Iterable[Mapping[str, object]],
    listed_objects: Iterable[Mapping[str, object]],
    chunk_bytes: int = 1024 * 1024,
) -> tuple[dict[str, dict[str, object]], int]:
    """Download each expected object that exists and compute its actual SHA-256.

    Missing objects are skipped here and reported by I5. A GET failure for an
    object that was listed is raised, so a failed read can never look like a
    successful checksum audit.
    """
    if chunk_bytes <= 0:
        raise ValueError("chunk_bytes must be positive")
    expected_uris = {
        uri
        for row in expected_rows
        if (uri := normalize_object_uri(row.get("object_uri"))) is not None
    }
    listed_uris = {
        uri
        for obj in listed_objects
        if (uri := normalize_object_uri(obj.get("uri"))) is not None
    }
    hashes: dict[str, dict[str, object]] = {}
    total_bytes = 0
    for uri in sorted(expected_uris & listed_uris):
        parsed = urlsplit(uri)
        bucket = parsed.netloc
        key = parsed.path[1:]
        response = s3_client.get_object(Bucket=bucket, Key=key)
        body = response["Body"]
        digest = hashlib.sha256()
        size = 0
        try:
            while True:
                chunk = body.read(chunk_bytes)
                if not chunk:
                    break
                digest.update(chunk)
                size += len(chunk)
        finally:
            close = getattr(body, "close", None)
            if close is not None:
                close()
        hashes[uri] = {"sha256": digest.hexdigest(), "size": size}
        total_bytes += size
    return hashes, total_bytes
