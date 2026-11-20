"""Metadata idempotence via Iceberg MERGE on recording_id."""

from __future__ import annotations

from typing import Mapping, Sequence

from src.idempotence.conflict_guard import IdempotenceConflictError, require_unique_recording_ids
from src.ingestion.write_metadata import validate_metadata_table


METADATA_COLUMNS = (
    "recording_id", "device_id", "start_time", "object_uri", "file_size_bytes", "sha256"
)


def metadata_conflicting_fields(expected: Mapping[str, object], actual: Mapping[str, object]) -> list[str]:
    """List ground-truth columns whose existing row disagrees with the manifest."""
    conflicts = []
    for column in METADATA_COLUMNS:
        left, right = expected.get(column), actual.get(column)
        if column == "file_size_bytes":
            left = None if left is None else int(left)
            right = None if right is None else int(right)
        elif column == "sha256":
            left = None if left is None else str(left).strip().lower()
            right = None if right is None else str(right).strip().lower()
        elif left is not None:
            left = str(left)
            right = None if right is None else str(right)
        if left != right:
            conflicts.append(column)
    return conflicts


def normalize_metadata_records(records: Sequence[Mapping[str, object]]) -> list[dict]:
    if not records:
        raise ValueError("cannot upsert an empty metadata batch")
    require_unique_recording_ids(records)
    normalized = []
    for record in records:
        missing = set(METADATA_COLUMNS).difference(record)
        if missing:
            raise ValueError(f"metadata record missing fields: {', '.join(sorted(missing))}")
        normalized.append({
            "recording_id": str(record["recording_id"]).strip(),
            "device_id": str(record["device_id"]),
            "start_time": str(record["start_time"]),
            "object_uri": str(record["object_uri"]),
            "file_size_bytes": int(record["file_size_bytes"]),
            "sha256": str(record["sha256"]).strip().lower(),
        })
    return normalized


def _spark_dataframe(spark, records: list[dict]):
    from pyspark.sql.types import LongType, StringType, StructField, StructType

    schema = StructType([
        StructField("recording_id", StringType(), nullable=False),
        StructField("device_id", StringType(), nullable=False),
        StructField("start_time", StringType(), nullable=False),
        StructField("object_uri", StringType(), nullable=False),
        StructField("file_size_bytes", LongType(), nullable=False),
        StructField("sha256", StringType(), nullable=False),
    ])
    return spark.createDataFrame(records, schema=schema)


def upsert_metadata(spark, records: Sequence[Mapping[str, object]], table: str) -> dict:
    """No-op identical rows, insert missing rows, and fail on changed existing rows."""
    table = validate_metadata_table(table)
    normalized = normalize_metadata_records(records)
    source = _spark_dataframe(spark, normalized)
    source_view = "dsic_idempotence_metadata_source"
    source.createOrReplaceTempView(source_view)
    try:
        target = spark.table(table).alias("target")
        source_alias = spark.table(source_view).alias("source")
        from pyspark.sql import functions as F

        joined = target.join(source_alias, F.col("target.recording_id") == F.col("source.recording_id"), "inner")
        selected = [F.col(f"target.{column}").alias(column) for column in METADATA_COLUMNS]
        existing_rows = [row.asDict(recursive=True) for row in joined.select(*selected).collect()]
        existing_by_id = {}
        for row in existing_rows:
            recording_id = str(row["recording_id"])
            if recording_id in existing_by_id:
                raise IdempotenceConflictError(
                    f"metadata CONFLICT for {recording_id}: multiple existing rows"
                )
            existing_by_id[recording_id] = row
        expected_by_id = {record["recording_id"]: record for record in normalized}
        for recording_id, actual in existing_by_id.items():
            differences = metadata_conflicting_fields(expected_by_id[recording_id], actual)
            if differences:
                raise IdempotenceConflictError(
                    f"metadata CONFLICT for {recording_id}: differing fields {', '.join(differences)}"
                )
        already_present = len(existing_by_id)

        spark.sql(f"""
            MERGE INTO {table} AS target
            USING {source_view} AS source
            ON target.recording_id = source.recording_id
            WHEN NOT MATCHED THEN INSERT (
                recording_id, device_id, start_time, object_uri, file_size_bytes, sha256
            ) VALUES (
                source.recording_id, source.device_id, source.start_time,
                source.object_uri, source.file_size_bytes, source.sha256
            )
        """)
        return {"inserted": len(normalized) - already_present, "already_present": already_present}
    finally:
        spark.catalog.dropTempView(source_view)
