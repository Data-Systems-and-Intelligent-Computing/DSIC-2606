"""Run isolated idempotence checks against the lab MinIO and Iceberg catalog.

This probe uses one tiny temporary object under ``_lab_probe`` and one unique
table under ``lab.smoke``. It does not touch the frozen corpus or experiment
table. The resources are removed in ``finally``.
"""

from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import uuid
from pathlib import Path

# spark-submit sets sys.path[0] to this scripts directory, not the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.idempotence.conflict_guard import IdempotenceConflictError
from src.idempotence.metadata_upsert import upsert_metadata
from src.idempotence.object_guard import guard_object
from src.ingestion.write_object import create_s3_client


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)
    print(f"[LULUS] {message}", flush=True)


def _delete_prefix(client, bucket: str, prefix: str) -> None:
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        objects = [{"Key": item["Key"]} for item in page.get("Contents", [])]
        for offset in range(0, len(objects), 1000):
            client.delete_objects(
                Bucket=bucket,
                Delete={"Objects": objects[offset:offset + 1000], "Quiet": True},
            )
    remaining = [
        item["Key"]
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix)
        for item in page.get("Contents", [])
    ]
    if remaining:
        raise RuntimeError(f"probe cleanup left objects under {bucket}/{prefix}: {remaining}")


def run_probe(spark) -> None:
    probe_id = uuid.uuid4().hex[:16]
    recording_id = f"LAB-PROBE-{probe_id}"
    bucket = "audiomoth"
    key = f"_lab_probe/{probe_id}/probe.wav"
    uri = f"s3://{bucket}/{key}"
    table = f"lab.smoke.idem_probe_{probe_id}"
    warehouse_prefix = f"_lab_probe/{probe_id}/iceberg/"
    payload = b"DSIC idempotence probe WAV placeholder\n"
    digest = hashlib.sha256(payload).hexdigest()
    client = create_s3_client()

    fd, source_name = tempfile.mkstemp(prefix="dsic-idem-probe-", suffix=".bin")
    source_path = Path(source_name)
    table_touched = False
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
        item = {
            "recording_id": recording_id,
            "source_path": str(source_path),
            "expected_object_uri": uri,
            "bucket": bucket,
            "object_key": key,
            "file_size_bytes": len(payload),
            "sha256": digest,
            "multipart_threshold_bytes": 5 * 1024 * 1024,
            "multipart_part_size_bytes": 5 * 1024 * 1024,
        }

        first = guard_object(client, item)
        _require(first["decision"] == "PUT", "objek yang belum ada menghasilkan tepat satu PUT")
        second = guard_object(client, item)
        _require(second["decision"] == "SUDAH ADA", "byte objek identik dikenali sebagai SUDAH ADA")

        bad_item = dict(item, sha256="0" * 64)
        try:
            guard_object(client, bad_item)
        except IdempotenceConflictError:
            pass
        else:
            raise RuntimeError("objek dengan checksum berbeda tidak ditolak")
        body = client.get_object(Bucket=bucket, Key=key)["Body"]
        try:
            actual = body.read()
        finally:
            body.close()
        _require(actual == payload, "konflik objek tidak menimpa byte lama")

        table_touched = True
        spark.sql("CREATE NAMESPACE IF NOT EXISTS lab.smoke")
        spark.sql(f"""CREATE TABLE {table} (
            recording_id STRING, device_id STRING, start_time STRING,
            object_uri STRING, file_size_bytes BIGINT, sha256 STRING
        ) USING iceberg LOCATION 's3://warehouse/{warehouse_prefix}'""")
        metadata = {
            "recording_id": recording_id,
            "device_id": "LAB-PROBE",
            "start_time": "2026-01-01T00:00:00Z",
            "object_uri": uri,
            "file_size_bytes": len(payload),
            "sha256": digest,
        }
        inserted = upsert_metadata(spark, [metadata], table)
        _require(inserted == {"inserted": 1, "already_present": 0}, "MERGE pertama memasukkan satu baris")
        repeated = upsert_metadata(spark, [metadata], table)
        _require(repeated == {"inserted": 0, "already_present": 1}, "MERGE ulang identik menjadi no-op")

        conflicting = dict(metadata, device_id="DIFFERENT")
        try:
            upsert_metadata(spark, [conflicting], table)
        except IdempotenceConflictError:
            pass
        else:
            raise RuntimeError("metadata berbeda tidak ditolak sebagai konflik")
        rows = spark.table(table).where(f"recording_id = '{recording_id}'").collect()
        _require(len(rows) == 1 and rows[0]["device_id"] == "LAB-PROBE",
                 "konflik metadata tidak menimpa baris lama")
        print(f"IDEMPOTENCE_PROBE_PASSED table={table} object_uri={uri}", flush=True)
    finally:
        try:
            if table_touched:
                spark.sql(f"DROP TABLE IF EXISTS {table}")
        finally:
            try:
                _delete_prefix(client, bucket, f"_lab_probe/{probe_id}/")
            finally:
                try:
                    _delete_prefix(client, "warehouse", warehouse_prefix)
                finally:
                    source_path.unlink(missing_ok=True)
        if table_touched:
            print(f"IDEMPOTENCE_PROBE_CLEANUP table_dropped=true object_prefix_empty=true warehouse_prefix_empty=true probe_id={probe_id}", flush=True)


def main() -> None:
    from pyspark.sql import SparkSession

    spark = SparkSession.builder.appName("DSIC-2606-idempotence-probe").getOrCreate()
    try:
        run_probe(spark)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
