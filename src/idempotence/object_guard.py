"""Idempotent MinIO object guard with verification of the actual stored bytes."""

from __future__ import annotations

import hashlib
from typing import Callable, Mapping

from src.idempotence.conflict_guard import IdempotenceConflictError
from src.idempotence.object_key import canonical_object_target
from src.ingestion.write_object import upload_recording


def _is_missing_object(exc: Exception) -> bool:
    response = getattr(exc, "response", {})
    error = response.get("Error", {}) if isinstance(response, dict) else {}
    code = str(error.get("Code", ""))
    status = response.get("ResponseMetadata", {}).get("HTTPStatusCode") if isinstance(response, dict) else None
    return code in {"NoSuchKey", "NotFound", "404"} or status == 404


def _hash_body(body, chunk_bytes: int) -> tuple[int, str]:
    if chunk_bytes <= 0:
        raise ValueError("download_chunk_bytes must be positive")
    digest = hashlib.sha256()
    size = 0
    try:
        while True:
            chunk = body.read(chunk_bytes)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
    finally:
        close = getattr(body, "close", None)
        if close:
            close()
    return size, digest.hexdigest()


def guard_object(
    client,
    item: Mapping[str, object],
    *,
    download_chunk_bytes: int = 1024 * 1024,
    put: Callable = upload_recording,
) -> dict:
    """Return PUT or SUDAH ADA; reject mismatches without overwriting the old key."""
    recording_id = str(item["recording_id"])
    bucket, key = canonical_object_target(recording_id, str(item["expected_object_uri"]))
    if bucket != str(item["bucket"]) or key != str(item["object_key"]):
        raise ValueError(f"prepared object target differs from manifest for {recording_id}")

    try:
        head = client.head_object(Bucket=bucket, Key=key)
    except Exception as exc:
        if not _is_missing_object(exc):
            raise
        receipt = put(client, item)
        return {"decision": "PUT", "recording_id": recording_id, "bytes_verified": int(item["file_size_bytes"]),
                "receipt": receipt}

    expected_size = int(item["file_size_bytes"])
    if int(head.get("ContentLength", -1)) != expected_size:
        raise IdempotenceConflictError(
            f"object CONFLICT for {recording_id}: existing size differs from manifest"
        )

    response = client.get_object(Bucket=bucket, Key=key)
    actual_size, actual_sha = _hash_body(response["Body"], download_chunk_bytes)
    expected_sha = str(item["sha256"]).strip().lower()
    if actual_size != expected_size or actual_sha != expected_sha:
        raise IdempotenceConflictError(
            f"object CONFLICT for {recording_id}: downloaded bytes differ from manifest"
        )
    return {"decision": "SUDAH ADA", "recording_id": recording_id,
            "bytes_verified": actual_size, "etag": str(head.get("ETag", "")).strip('"')}
