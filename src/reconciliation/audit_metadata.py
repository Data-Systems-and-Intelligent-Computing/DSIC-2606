"""Read the complete frozen metadata projection from an Iceberg table."""

from __future__ import annotations

from src.ingestion.write_metadata import validate_metadata_table

METADATA_COLUMNS = (
    "recording_id",
    "device_id",
    "start_time",
    "object_uri",
    "file_size_bytes",
    "sha256",
)


def read_metadata_rows(spark, table: str) -> list[dict[str, object]]:
    """Collect the columns used by I1–I7 after validating the table identifier."""
    table = validate_metadata_table(table)
    rows = spark.table(table).select(*METADATA_COLUMNS).collect()
    return [row.asDict(recursive=True) for row in rows]
