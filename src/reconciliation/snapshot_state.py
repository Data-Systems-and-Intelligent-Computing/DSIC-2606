"""Read-only evidence snapshot of object and metadata state before recovery."""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.fault_injection.fault_plan import load_fault_plan
from src.ingestion.microbatch import load_frozen_batches, load_manifest
from src.checkpointing.treatment_config import resolve_checkpoint_location
from src.ingestion.write_metadata import validate_metadata_table
from src.ingestion.write_object import create_s3_client
from src.reconciliation.audit_metadata import read_metadata_rows
from src.reconciliation.audit_objects import list_expected_bucket_objects


def _write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def create_snapshot(spark, *, run_id: str, treatment: str, output_dir: Path,
                    plan_path: Path, manifest_path: Path, batch_order_path: Path,
                    table: str, s3_client) -> dict:
    plan = load_fault_plan(plan_path, "F1")
    if plan.batch_id is None or plan.record_index is None:
        raise ValueError("snapshot requires a frozen F1 plan")
    manifest = load_manifest(manifest_path)
    batches = load_frozen_batches(batch_order_path)
    target_id = batches[plan.batch_id][plan.record_index - 1]
    target = manifest[target_id]
    rows = read_metadata_rows(spark, validate_metadata_table(table))
    expected_objects = [
        {"recording_id": rid, "object_uri": row["expected_object_uri"]}
        for rid, row in manifest.items()
    ]
    objects = list_expected_bucket_objects(s3_client, expected_objects)
    metadata_ids = [str(row.get("recording_id") or "") for row in rows]
    object_uris = {str(row["uri"]) for row in objects}
    target_uri = str(target["expected_object_uri"])
    expected_object_count = plan.batch_id * 10 + plan.record_index
    expected_metadata_count = expected_object_count - 1
    prior_ids = batches[plan.batch_id][:plan.record_index - 1]
    metadata_id_set = set(metadata_ids)

    root = Path(__file__).resolve().parents[2]
    with (root / "configs" / "treatments.yaml").open(encoding="utf-8-sig") as stream:
        treatment_configs = yaml.safe_load(stream)["treatments"]
    with (root / "configs" / "checkpoint.yaml").open(encoding="utf-8-sig") as stream:
        checkpoint_config = yaml.safe_load(stream)["checkpoint"]
    checkpoint_template = treatment_configs[treatment]["checkpoint_location"]
    checkpoint_path = Path(resolve_checkpoint_location(
        checkpoint_template,
        persistent_root=checkpoint_config.get("persistent_root"),
        ephemeral_root=checkpoint_config.get("ephemeral_root"),
        run_id=run_id,
        treatment=treatment,
    ))
    persistent = "{persistent_root}" in checkpoint_template
    checkpoint_state = {
        "kind": "persistent" if persistent else "ephemeral",
        "path": str(checkpoint_path),
        "path_exists_in_snapshot_container": checkpoint_path.is_dir(),
        "target_offset_exists": (checkpoint_path / "offsets" / str(plan.batch_id)).is_file(),
        "target_commit_exists": (checkpoint_path / "commits" / str(plan.batch_id)).is_file(),
    }

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    _write_csv(output_dir / "objects.csv", objects,
               ["uri", "bucket", "key", "size", "etag"])
    _write_csv(output_dir / "metadata.csv", rows,
               ["recording_id", "device_id", "start_time", "object_uri", "file_size_bytes", "sha256"])
    checks = {
        "target_object_exists": target_uri in object_uris,
        "target_metadata_absent": target_id not in metadata_id_set,
        "all_prior_records_in_target_batch_have_metadata": all(rid in metadata_id_set for rid in prior_ids),
        "metadata_count_is_expected": len(rows) == expected_metadata_count,
        "object_count_is_expected": len(objects) == expected_object_count,
    }
    if persistent:
        checks["persistent_target_offset_exists"] = checkpoint_state["target_offset_exists"]
        checks["persistent_target_commit_absent"] = not checkpoint_state["target_commit_exists"]
    summary = {
        "run_id": run_id, "treatment": treatment, "fault_point": "F1",
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "batch_id": plan.batch_id, "record_index": plan.record_index,
        "target_recording_id": target_id, "target_object_uri": target_uri,
        "expected_object_count": expected_object_count,
        "actual_object_count": len(objects),
        "expected_metadata_rows": expected_metadata_count,
        "actual_metadata_rows": len(rows), "checks": checks,
        "all_checks_pass": all(checks.values()),
        "checkpoint_state": checkpoint_state,
        "read_only": True,
    }
    (output_dir / "snapshot.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=os.environ.get("RUN_ID"), required=not os.environ.get("RUN_ID"))
    parser.add_argument("--treatment", default=os.environ.get("TREATMENT"), required=not os.environ.get("TREATMENT"))
    parser.add_argument("--plan", type=Path, default=Path("/workspace/fault_plans/F1_after_object_before_metadata.yaml"))
    parser.add_argument("--manifest", type=Path, default=Path("/workspace/data/manifests/manifest_main.csv"))
    parser.add_argument("--batch-order", type=Path, default=Path("/workspace/data/batches/batch_order_main.csv"))
    parser.add_argument("--table", default="lab.main.recordings")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    output_dir = args.output_dir or Path("/results/raw") / args.run_id / "pra"
    try:
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.appName("DSIC-2606-F1-pre-recovery-snapshot").getOrCreate()
        try:
            result = create_snapshot(
                spark, run_id=args.run_id, treatment=args.treatment,
                output_dir=output_dir, plan_path=args.plan,
                manifest_path=args.manifest, batch_order_path=args.batch_order,
                table=args.table, s3_client=create_s3_client(),
            )
        finally:
            spark.stop()
    except Exception as exc:
        print(json.dumps({"all_checks_pass": False, "error": str(exc)}, sort_keys=True))
        return 1
    print("F1_PRE_RECOVERY_SNAPSHOT " + json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["all_checks_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
