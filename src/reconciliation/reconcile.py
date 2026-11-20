"""Command-line reconciliation for metadata invariants I1 through I7."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
import time

# spark-submit sets sys.path[0] to this module's directory; imports use src.*.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingestion.write_metadata import validate_metadata_table
from src.ingestion.write_object import create_s3_client
from src.reconciliation.audit_metadata import read_metadata_rows
from src.reconciliation.audit_objects import hash_expected_objects, list_expected_bucket_objects
from src.reconciliation.invariants import reconcile_i1_i2, reconcile_i3_i5, reconcile_i6_i7


def read_expected_rows(path: Path) -> list[dict[str, str]]:
    with Path(path).open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        required = {"recording_id", "device_id", "start_time", "object_uri", "file_size_bytes", "sha256"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"expected metadata CSV needs columns {sorted(required)}: {path}")
        return [{key: (value or "").strip() for key, value in row.items()} for row in reader]


def reconcile_spark_table(spark, table: str, expected_path: Path, s3_client) -> dict:
    started = time.perf_counter()
    table = validate_metadata_table(table)
    expected_rows = read_expected_rows(expected_path)
    actual_rows = read_metadata_rows(spark, table)
    object_rows = list_expected_bucket_objects(s3_client, expected_rows)
    object_hashes, hashed_bytes = hash_expected_objects(s3_client, expected_rows, object_rows)
    result = reconcile_i1_i2(
        [row.get("recording_id") for row in expected_rows],
        [row.get("recording_id") for row in actual_rows],
    )
    result.update(reconcile_i3_i5(expected_rows, actual_rows, object_rows))
    result.update(reconcile_i6_i7(expected_rows, actual_rows, object_hashes))
    result["metadata_table"] = table
    result["expected_metadata_path"] = str(expected_path)
    result["hashed_byte_count"] = hashed_bytes
    result["duration_seconds"] = round(time.perf_counter() - started, 3)
    result["all_pass"] = all(result[f"I{index}_" + name]["passed"] for index, name in (
        (1, "completeness"), (2, "uniqueness"), (3, "referential"),
        (4, "no_orphan"), (5, "no_dangling"), (6, "byte_integrity"),
        (7, "no_extras"),
    ))
    result["exact_recovery"] = result["all_pass"]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected", type=Path, default=Path("/workspace/data/ground_truth/expected_metadata.csv"))
    parser.add_argument("--table", default="lab.main.recordings")
    args = parser.parse_args()
    started = time.perf_counter()
    try:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("DSIC-2606-reconcile-I1-I7").getOrCreate()
        try:
            result = reconcile_spark_table(spark, args.table, args.expected, create_s3_client())
        finally:
            spark.stop()
        result["duration_seconds"] = round(time.perf_counter() - started, 3)
    except Exception as exc:
        print(json.dumps({"all_pass": False, "error": str(exc)}, sort_keys=True))
        return 1
    print("I1_I7_RECONCILIATION " + json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
