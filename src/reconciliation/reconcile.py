"""Command-line reconciliation for metadata invariants I1 and I2."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

# spark-submit sets sys.path[0] to this module's directory; imports use src.*.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingestion.write_metadata import validate_metadata_table
from src.reconciliation.invariants import reconcile_i1_i2


def read_expected_ids(path: Path) -> list[str]:
    with Path(path).open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or "recording_id" not in reader.fieldnames:
            raise ValueError(f"expected metadata CSV needs a recording_id column: {path}")
        return [(row.get("recording_id") or "").strip() for row in reader]


def reconcile_spark_table(spark, table: str, expected_path: Path) -> dict:
    table = validate_metadata_table(table)
    expected_ids = read_expected_ids(expected_path)
    actual_ids = [row["recording_id"] for row in spark.table(table).select("recording_id").collect()]
    result = reconcile_i1_i2(expected_ids, actual_ids)
    result["metadata_table"] = table
    result["expected_metadata_path"] = str(expected_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected", type=Path, default=Path("/workspace/data/ground_truth/expected_metadata.csv"))
    parser.add_argument("--table", default="lab.main.recordings")
    args = parser.parse_args()
    try:
        from pyspark.sql import SparkSession

        spark = SparkSession.builder.appName("DSIC-2606-reconcile-I1-I2").getOrCreate()
        try:
            result = reconcile_spark_table(spark, args.table, args.expected)
        finally:
            spark.stop()
    except Exception as exc:
        print(json.dumps({"all_pass": False, "error": str(exc)}, sort_keys=True))
        return 1
    print("I1_I2_RECONCILIATION " + json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
