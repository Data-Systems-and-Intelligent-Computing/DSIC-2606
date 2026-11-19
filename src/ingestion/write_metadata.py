"""Append frozen metadata rows to the experiment Iceberg table."""
from __future__ import annotations

import re
from typing import Mapping, Sequence


_TABLE_PATTERN = re.compile(r"^lab\.[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$")
_METADATA_COLUMNS = (
    "recording_id",
    "device_id",
    "start_time",
    "object_uri",
    "file_size_bytes",
    "sha256",
)


def validate_metadata_table(table_name: str) -> str:
    """Accept only a simple three-part identifier in the configured Iceberg catalog."""
    if not isinstance(table_name, str) or not _TABLE_PATTERN.fullmatch(table_name):
        raise ValueError("metadata table must be a three-part lab.namespace.table identifier")
    return table_name


def ensure_metadata_table(spark, table_name: str) -> None:
    """Create the experiment namespace and table after the run's preflight/reset."""
    validate_metadata_table(table_name)
    _, namespace, table = table_name.split(".")
    spark.sql(f"CREATE NAMESPACE IF NOT EXISTS lab.{namespace}")
    spark.sql(
        f"""CREATE TABLE IF NOT EXISTS lab.{namespace}.{table} (
            recording_id STRING,
            device_id STRING,
            start_time STRING,
            object_uri STRING,
            file_size_bytes BIGINT,
            sha256 STRING
        ) USING iceberg"""
    )


def append_metadata(spark, records: Sequence[Mapping[str, object]], table: str) -> None:
    """Append one recording row in one Iceberg transaction and wait for its commit."""
    validate_metadata_table(table)
    if not records:
        raise ValueError("cannot append an empty metadata batch")

    from pyspark.sql.types import LongType, StringType, StructField, StructType

    schema = StructType(
        [
            StructField("recording_id", StringType(), nullable=False),
            StructField("device_id", StringType(), nullable=False),
            StructField("start_time", StringType(), nullable=False),
            StructField("object_uri", StringType(), nullable=False),
            StructField("file_size_bytes", LongType(), nullable=False),
            StructField("sha256", StringType(), nullable=False),
        ]
    )
    values = []
    for record in records:
        missing = set(_METADATA_COLUMNS).difference(record)
        if missing:
            raise ValueError(f"metadata record missing fields: {', '.join(sorted(missing))}")
        values.append(
            {
                "recording_id": str(record["recording_id"]),
                "device_id": str(record["device_id"]),
                "start_time": str(record["start_time"]),
                "object_uri": str(record["object_uri"]),
                "file_size_bytes": int(record["file_size_bytes"]),
                "sha256": str(record["sha256"]).lower(),
            }
        )
    spark.createDataFrame(values, schema=schema).writeTo(table).append()
