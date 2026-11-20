"""Run deterministic one-event-per-micro-batch B0/B1 ingestion."""
from __future__ import annotations

import csv
import json
import logging
import os
import re
from pathlib import Path

import yaml

# spark-submit executes this file by path; make the repository package visible
# to both the driver and its Python workers.
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.checkpointing.treatment_config import resolve_checkpoint_location
from src.idempotence.metadata_upsert import upsert_metadata
from src.idempotence.object_guard import guard_object
from src.idempotence.conflict_guard import require_unique_recording_ids
from src.ingestion.source_replay import ReplayFeeder
from src.ingestion.write_metadata import append_metadata, ensure_metadata_table, validate_metadata_table
from src.ingestion.write_object import create_s3_client, prepare_upload_record, upload_recording

LOGGER = logging.getLogger("dsic.ingestion")
EVENT_PATTERN = re.compile(r"^event-(\d{3,})\.json$")


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_manifest(path: Path) -> dict[str, dict[str, str]]:
    required = {"recording_id", "device_id", "start_time", "source_path",
                "file_size_bytes", "sha256", "expected_object_uri"}
    records: dict[str, dict[str, str]] = {}
    with Path(path).open("r", newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"manifest missing columns: {', '.join(sorted(missing))}")
        for line, row in enumerate(reader, start=2):
            recording_id = (row.get("recording_id") or "").strip()
            if not recording_id or recording_id in records:
                raise ValueError(f"empty or duplicate recording_id at manifest line {line}")
            row["recording_id"] = recording_id
            row["file_size_bytes"] = str(int(row["file_size_bytes"]))
            row["sha256"] = row["sha256"].strip().lower()
            if len(row["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in row["sha256"]):
                raise ValueError(f"invalid SHA-256 in manifest for {recording_id}")
            records[recording_id] = row
    return records


def load_frozen_batches(path: Path, batch_size: int = 10, expected_batches: int = 30) -> list[list[str]]:
    groups: dict[int, list[tuple[int, str]]] = {}
    with Path(path).open("r", newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        required = {"batch_number", "position_in_batch", "recording_id"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"batch order missing columns: {', '.join(sorted(missing))}")
        for row in reader:
            batch_id = int(row["batch_number"])
            position = int(row["position_in_batch"])
            groups.setdefault(batch_id, []).append((position, row["recording_id"].strip()))
    if sorted(groups) != list(range(expected_batches)):
        raise ValueError(f"expected batches 0..{expected_batches - 1}; found {sorted(groups)}")
    batches = []
    for batch_id in range(expected_batches):
        entries = sorted(groups[batch_id])
        if [position for position, _ in entries] != list(range(batch_size)):
            raise ValueError(f"batch {batch_id} must have positions 0..{batch_size - 1}")
        ids = [recording_id for _, recording_id in entries]
        if len(set(ids)) != batch_size:
            raise ValueError(f"batch {batch_id} contains duplicate recording IDs")
        batches.append(ids)
    flattened = [recording_id for batch in batches for recording_id in batch]
    if len(flattened) != len(set(flattened)):
        raise ValueError("batch_order_main.csv contains duplicate IDs across batches")
    return batches


def validate_event_source(event_source: Path, frozen_batches: list[list[str]]) -> None:
    paths = sorted(event_source.glob("event-*.json"))
    if len(paths) != len(frozen_batches):
        raise ValueError(f"expected {len(frozen_batches)} replay events; found {len(paths)}")
    for batch_id, path in enumerate(paths):
        if path.name != f"event-{batch_id:03d}.json":
            raise ValueError(f"unexpected event name or gap: {path.name}")
        event = json.loads(path.read_text(encoding="utf-8"))
        if event.get("batch_id") != batch_id or event.get("recording_ids") != frozen_batches[batch_id]:
            raise ValueError(f"{path.name} does not match batch_order_main.csv")


def _load_configs(root: Path, treatment: str):
    def read(name):
        with (root / "configs" / name).open(encoding="utf-8-sig") as stream:
            return yaml.safe_load(stream)
    treatments = read("treatments.yaml")["treatments"]
    checkpoint = read("checkpoint.yaml")["checkpoint"]
    environment = read("environment.yaml")["environment"]
    ingestion = read("ingestion.yaml")["ingestion"]
    idempotence = read("idempotence.yaml")["idempotence"]
    if treatment not in {"B0", "B1", "B2", "P1"} or treatment not in treatments:
        raise ValueError("TREATMENT must be B0, B1, B2, or P1")
    return treatments[treatment], checkpoint, environment, ingestion, idempotence


def _process_event(spark, event: dict, manifest: dict, corpus_root: Path,
                   threshold: int, part_size: int, table: str, s3_client,
                   expected_spark_batch_id: int, idempotence_enabled: bool = False,
                   idempotence_config: dict | None = None) -> int:
    event_id = int(event["batch_id"])
    if event_id != expected_spark_batch_id:
        raise RuntimeError(
            f"replay order mismatch before writes: event {event_id} arrived in "
            f"Spark micro-batch {expected_spark_batch_id}"
        )
    recording_ids = event["recording_ids"]
    if len(recording_ids) != 10:
        raise ValueError(f"event {event_id} must contain 10 recording IDs")
    # Validate the full event before touching either sink.
    require_unique_recording_ids([{"recording_id": rid} for rid in recording_ids])
    idempotence_config = idempotence_config or {}
    object_policy = idempotence_config.get("object_guard", {})
    chunk_bytes = int(object_policy.get("download_chunk_bytes", 1024 * 1024))

    # Keep each record's boundaries explicit: confirmed object PUT, then one
    # Iceberg append commit. This is the observable F1/F2 boundary in later phases.
    for recording_id in recording_ids:
        if recording_id not in manifest:
            raise ValueError(f"event {event_id} references unknown ID {recording_id}")
        source = manifest[recording_id]
        upload_item = prepare_upload_record(source, str(corpus_root), threshold, part_size)
        if idempotence_enabled:
            object_result = guard_object(
                s3_client, upload_item, download_chunk_bytes=chunk_bytes
            )
            LOGGER.info(
                "OBJECT_GUARD_DECISION batch_id=%d recording_id=%s decision=%s bytes_verified=%d",
                event_id, recording_id, object_result["decision"], object_result["bytes_verified"],
            )
        else:
            upload_recording(s3_client, upload_item)
        metadata_row = {
            "recording_id": recording_id,
            "device_id": source["device_id"],
            "start_time": source["start_time"],
            "object_uri": source["expected_object_uri"],
            "file_size_bytes": int(source["file_size_bytes"]),
            "sha256": source["sha256"],
        }
        if idempotence_enabled:
            result = upsert_metadata(spark, [metadata_row], table=table)
            LOGGER.info(
                "ICEBERG_UPSERT_COMPLETED batch_id=%d recording_id=%s inserted=%d already_present=%d",
                event_id, recording_id, result["inserted"], result["already_present"],
            )
        else:
            append_metadata(spark, [metadata_row], table=table)
            LOGGER.info("ICEBERG_COMMIT_COMPLETED batch_id=%d recording_id=%s rows=1",
                        event_id, recording_id)

    LOGGER.info("REPLAY_BATCH_COMPLETED batch_id=%d recording_ids=%s",
                event_id, json.dumps(recording_ids, separators=(",", ":")))
    return event_id


def _latest_spark_commit(checkpoint_location: Path):
    commits = checkpoint_location / "commits"
    if not commits.is_dir():
        return None
    numbers = [int(path.name) for path in commits.iterdir()
               if path.is_file() and path.name.isdecimal()]
    return max(numbers) if numbers else None


def _latest_landing_event(landing: Path):
    ids = [int(match.group(1)) for path in landing.iterdir()
           if path.is_file() and (match := EVENT_PATTERN.fullmatch(path.name))]
    return max(ids) if ids else None


def _audit_f0(spark, table: str, manifest: dict, s3_client) -> None:
    rows = [row.asDict(recursive=True) for row in spark.table(table).collect()]
    if len(rows) != 300:
        raise RuntimeError(f"F0 metadata row count: expected 300, found {len(rows)}")
    by_id = {}
    for row in rows:
        rid = row["recording_id"]
        if rid in by_id:
            raise RuntimeError(f"duplicate metadata row for {rid}")
        by_id[rid] = row
    if set(by_id) != set(manifest):
        raise RuntimeError("F0 metadata recording IDs differ from the 300-row manifest")
    fields = {
        "device_id": "device_id", "start_time": "start_time",
        "object_uri": "expected_object_uri", "file_size_bytes": "file_size_bytes",
        "sha256": "sha256",
    }
    for rid, expected in manifest.items():
        for actual_field, source_field in fields.items():
            left, right = by_id[rid][actual_field], expected[source_field]
            if actual_field == "file_size_bytes":
                right = int(right)
            if left != right:
                raise RuntimeError(f"metadata {actual_field} differs from manifest for {rid}")

    expected_by_bucket: dict[str, set[str]] = {}
    for row in manifest.values():
        bucket, key = row["expected_object_uri"].removeprefix("s3://").split("/", 1)
        expected_by_bucket.setdefault(bucket, set()).add(key)
    if len(expected_by_bucket) != 1:
        raise RuntimeError("main manifest must target exactly one object-store bucket")
    bucket, expected_keys = next(iter(expected_by_bucket.items()))
    response = s3_client.list_objects_v2(Bucket=bucket)
    actual_keys = {item["Key"] for item in response.get("Contents", [])}
    if response.get("IsTruncated"):
        raise RuntimeError("F0 object audit exceeded one page; pagination is required")
    if actual_keys != expected_keys:
        raise RuntimeError(f"F0 object keys differ: expected 300, found {len(actual_keys)}")
    for recording_id, expected in manifest.items():
        object_bucket, object_key = expected["expected_object_uri"].removeprefix("s3://").split("/", 1)
        head = s3_client.head_object(Bucket=object_bucket, Key=object_key)
        if int(head["ContentLength"]) != int(expected["file_size_bytes"]):
            raise RuntimeError(f"object size differs from manifest for {recording_id}")
        if head.get("Metadata", {}).get("sha256") != expected["sha256"]:
            raise RuntimeError(f"object SHA-256 metadata differs from manifest for {recording_id}")
    LOGGER.info("F0_RECONCILIATION objects=%d metadata_rows=%d distinct_recording_ids=%d object_head_checks=%d",
                len(actual_keys), len(rows), len(by_id), len(actual_keys))


def run_replay(spark, run_id: str | None = None, treatment: str | None = None) -> None:
    root = repository_root()
    run_id = run_id or os.environ.get("RUN_ID")
    treatment = treatment or os.environ.get("TREATMENT")
    if not run_id or not treatment:
        raise ValueError("RUN_ID and TREATMENT are required")

    treatment_config, checkpoint_config, environment, ingestion, idempotence_config = _load_configs(root, treatment)
    checkpoint_location = Path(resolve_checkpoint_location(
        treatment_config["checkpoint_location"],
        persistent_root=checkpoint_config.get("persistent_root"),
        ephemeral_root=checkpoint_config.get("ephemeral_root"),
        run_id=run_id,
        treatment=treatment,
    ))
    landing_root = Path(os.environ["REPLAY_LANDING_ROOT"])
    event_source = Path(os.environ.get("REPLAY_EVENT_SOURCE", root / "data/replay/main/events"))
    manifest_path = Path(os.environ.get("MANIFEST_PATH", root / "data/manifests/manifest_main.csv"))
    batch_order_path = Path(os.environ.get("BATCH_ORDER_PATH", root / "data/batches/batch_order_main.csv"))
    corpus_root = Path(os.environ.get("CORPUS_ROOT", "/data/raw"))
    if not corpus_root.is_dir():
        raise FileNotFoundError(f"mounted corpus path does not exist: {corpus_root}")

    manifest = load_manifest(manifest_path)
    batches = load_frozen_batches(batch_order_path)
    if len(manifest) != 300 or len(batches) != 30:
        raise ValueError("Main F0 requires exactly 300 manifest rows in 30 batches")
    if {rid for batch in batches for rid in batch} != set(manifest):
        raise ValueError("batch_order_main.csv and manifest contain different IDs")
    validate_event_source(event_source, batches)

    table = validate_metadata_table(ingestion["metadata_table"])
    threshold = int(environment["multipart"]["threshold_bytes"])
    part_size = int(environment["multipart"]["part_size_bytes"])
    feeder = ReplayFeeder(landing_root, run_id, event_source)
    landing = feeder.landing
    s3_client = create_s3_client()
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper(),
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    LOGGER.info("experiment_identity run_id=%s treatment=%s", run_id, treatment)

    # This is the treatment config used for the comparison. Run identity is
    # logged separately, so only checkpoint_location changes between B0/B1.
    effective_config = {
        "checkpoint_location": str(checkpoint_location),
        "idempotence_enabled": bool(treatment_config["idempotence_enabled"]),
        "replay_event_source": str(event_source),
        "replay_landing_root": str(landing_root),
        "manifest_path": str(manifest_path),
        "batch_order_path": str(batch_order_path),
        "corpus_root": str(corpus_root),
        "metadata_table": table,
        "max_files_per_trigger": 1,
        "batch_size": 10,
        "expected_micro_batches": 30,
        "object_store_endpoint": os.environ["S3_ENDPOINT"],
        "upload_multipart_threshold_bytes": threshold,
        "upload_multipart_part_size_bytes": part_size,
        "idempotence_policy": idempotence_config,
    }
    LOGGER.info("EFFECTIVE_CONFIG %s", json.dumps(effective_config, sort_keys=True, separators=(",", ":")))

    ensure_metadata_table(spark, table)
    feeder.publish_initial()

    from pyspark.sql.types import ArrayType, LongType, StringType, StructField, StructType
    event_schema = StructType([
        StructField("batch_id", LongType(), nullable=False),
        StructField("recording_ids", ArrayType(StringType(), containsNull=False), nullable=False),
    ])
    while True:
        processed = []

        def process_microbatch(batch_df, spark_batch_id):
            rows = batch_df.collect()
            if not rows:
                return
            if len(rows) != 1:
                raise RuntimeError(f"micro-batch {spark_batch_id}: expected one event, found {len(rows)}")
            event = {"batch_id": int(rows[0]["batch_id"]),
                     "recording_ids": list(rows[0]["recording_ids"])}
            if event["batch_id"] >= len(batches) or event["recording_ids"] != batches[event["batch_id"]]:
                raise RuntimeError(f"event {event['batch_id']} differs from frozen batch order")
            processed.append(_process_event(spark, event, manifest, corpus_root,
                                            threshold, part_size, table, s3_client,
                                            int(spark_batch_id),
                                            idempotence_enabled=bool(treatment_config["idempotence_enabled"]),
                                            idempotence_config=idempotence_config))

        query = (spark.readStream.schema(event_schema)
                 .option("maxFilesPerTrigger", 1)
                 .option("multiLine", "true")
                 .json(str(landing))
                 .writeStream.option("checkpointLocation", str(checkpoint_location))
                 .foreachBatch(process_microbatch)
                 .trigger(availableNow=True).start())
        query.awaitTermination()

        committed = _latest_spark_commit(checkpoint_location)
        if processed:
            if processed[-1] != committed:
                raise RuntimeError(f"last processed event {processed[-1]} != Spark commit {committed}")
            completed = processed[-1]
        else:
            completed = committed
        latest_landing = _latest_landing_event(landing)
        if completed is None or latest_landing != completed:
            raise RuntimeError(f"cannot advance feeder: checkpoint={completed}, landing={latest_landing}")
        if completed == len(batches) - 1:
            break
        published = feeder.after_batch_completed(completed)
        if published is None:
            raise RuntimeError("feeder did not publish the next event after completed checkpoint")
        LOGGER.info("REPLAY_EVENT_PUBLISHED batch_id=%d file=%s", published.batch_id, published.path.name)

    _audit_f0(spark, table, manifest, s3_client)
    LOGGER.info("INGESTION_FINISHED treatment=%s run_id=%s batches=%d", treatment, run_id, len(batches))


def main() -> None:
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.appName("DSIC-2606-ingestion").getOrCreate()
    try:
        run_replay(spark)
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
