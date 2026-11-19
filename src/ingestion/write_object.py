"""MinIO writer used by the ingestion driver."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import Mapping
from urllib.parse import urlsplit

MAIN_SOURCE_PREFIX = ("data", "raw", "audiomoth", "main")


def object_target(uri: str) -> tuple[str, str]:
    parsed = urlsplit(uri.strip())
    if parsed.scheme not in {"s3", "s3a"} or not parsed.netloc:
        raise ValueError(f"expected s3://bucket/key URI, got {uri!r}")
    key = parsed.path.lstrip("/")
    if not key or parsed.query or parsed.fragment:
        raise ValueError(f"expected a bucket and plain object key, got {uri!r}")
    return parsed.netloc, key


def mounted_source_path(source_path: str, raw_root: str = "/data/raw") -> Path:
    parts = PurePosixPath(source_path.strip().replace("\\", "/")).parts
    if parts[:4] != MAIN_SOURCE_PREFIX or len(parts) != 5:
        raise ValueError("Main source_path must be data/raw/audiomoth/main/<filename>")
    filename = parts[4]
    if filename in {"", ".", ".."}:
        raise ValueError("manifest source_path has an unsafe filename")
    return Path(raw_root) / filename


def sha256_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def prepare_upload_record(
    manifest_row: Mapping[str, str],
    raw_root: str,
    multipart_threshold_bytes: int,
    multipart_part_size_bytes: int,
) -> dict:
    bucket, key = object_target(manifest_row["expected_object_uri"])
    return {
        "recording_id": manifest_row["recording_id"],
        "source_path": str(mounted_source_path(manifest_row["source_path"], raw_root)),
        "expected_object_uri": manifest_row["expected_object_uri"],
        "bucket": bucket,
        "object_key": key,
        "file_size_bytes": int(manifest_row["file_size_bytes"]),
        "sha256": manifest_row["sha256"].strip().lower(),
        "multipart_threshold_bytes": int(multipart_threshold_bytes),
        "multipart_part_size_bytes": int(multipart_part_size_bytes),
    }


def create_s3_client():
    """Create a client from the lab-injected endpoint and credentials."""
    import boto3
    from botocore.config import Config

    endpoint = os.environ.get("S3_ENDPOINT")
    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if not endpoint or not access_key or not secret_key:
        raise RuntimeError("S3_ENDPOINT and AWS credentials are required")
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def upload_recording(client, item: Mapping[str, object]) -> dict:
    """PUT one validated WAV; return only after MinIO confirms it with HEAD."""
    from boto3.s3.transfer import TransferConfig

    source = Path(str(item["source_path"]))
    recording_id = str(item["recording_id"])
    expected_size = int(item["file_size_bytes"])
    expected_sha = str(item["sha256"]).lower()
    actual_size, actual_sha = sha256_file(source)
    if actual_size != expected_size:
        raise ValueError(f"source size mismatch: {recording_id}")
    if actual_sha != expected_sha:
        raise ValueError(f"source SHA-256 mismatch: {recording_id}")

    transfer = TransferConfig(
        multipart_threshold=int(item["multipart_threshold_bytes"]),
        multipart_chunksize=int(item["multipart_part_size_bytes"]),
        max_concurrency=1,
        use_threads=False,
    )
    client.upload_file(
        str(source),
        str(item["bucket"]),
        str(item["object_key"]),
        ExtraArgs={"Metadata": {"recording_id": recording_id, "sha256": actual_sha}},
        Config=transfer,
    )
    head = client.head_object(Bucket=str(item["bucket"]), Key=str(item["object_key"]))
    if int(head["ContentLength"]) != expected_size:
        raise IOError(f"uploaded object size mismatch: {recording_id}")
    if head.get("Metadata", {}).get("sha256") != expected_sha:
        raise IOError(f"uploaded object checksum metadata mismatch: {recording_id}")
    receipt = {
        "recording_id": recording_id,
        "object_uri": str(item["expected_object_uri"]),
        "bytes": expected_size,
        "etag": head.get("ETag", "").strip('"'),
    }
    print("OBJECT_PUT_COMPLETED " + json.dumps(receipt, sort_keys=True, separators=(",", ":")), flush=True)
    return receipt
