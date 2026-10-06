"""Build the Iceberg ground-truth CSV from a frozen per-corpus manifest.

This script copies manifest values only; it does not read or modify WAV files.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


SOURCE_FOR_TARGET = {
    "recording_id": "recording_id",
    "device_id": "device_id",
    "start_time": "start_time",
    "object_uri": "expected_object_uri",
    "file_size_bytes": "file_size_bytes",
    "sha256": "sha256",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Bentuk expected_metadata.csv secara deterministik dari manifest; "
            "tidak membaca atau mengubah berkas WAV."
        )
    )
    parser.add_argument(
        "--manifest",
        default="data/manifests/manifest_main.csv",
        help="CSV manifest sumber (default: manifest_main.csv)",
    )
    parser.add_argument(
        "--schema",
        default="schemas/metadata_record.schema.json",
        help="JSON Schema untuk memeriksa daftar kolom target",
    )
    parser.add_argument(
        "--output",
        default="data/ground_truth/expected_metadata.csv",
        help="Path CSV ground truth yang akan dibuat",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Izinkan menimpa output yang sudah berisi data",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest)
    schema_path = Path(args.schema)
    output_path = Path(args.output)

    if not manifest_path.is_file():
        raise SystemExit(f"Manifest tidak ditemukan: {manifest_path}")
    if not schema_path.is_file():
        raise SystemExit(f"Schema tidak ditemukan: {schema_path}")

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    output_fields = list(schema.get("properties", {}).keys())
    if set(output_fields) != set(SOURCE_FOR_TARGET):
        raise SystemExit(
            "Kolom properties pada schema tidak sama dengan pemetaan builder. "
            f"Schema: {output_fields}; pemetaan: {list(SOURCE_FOR_TARGET)}"
        )
    if set(schema.get("required", [])) != set(SOURCE_FOR_TARGET):
        raise SystemExit("Schema harus mewajibkan tepat enam kolom metadata.")

    if output_path.exists() and output_path.stat().st_size > 0 and not args.overwrite:
        raise SystemExit(
            f"Output sudah berisi data: {output_path}. "
            "Tinjau dahulu; gunakan --overwrite hanya jika memang ingin menggantinya."
        )

    with manifest_path.open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        source_fields = set(reader.fieldnames or [])
        needed_source_fields = set(SOURCE_FOR_TARGET.values())
        missing_headers = sorted(needed_source_fields - source_fields)
        if missing_headers:
            raise SystemExit(f"Kolom manifest hilang: {missing_headers}")

        rows = []
        seen_ids = set()
        for line_number, source in enumerate(reader, start=2):
            row = {
                target: (source.get(source_field) or "").strip()
                for target, source_field in SOURCE_FOR_TARGET.items()
            }

            empty_fields = [name for name, value in row.items() if not value]
            if empty_fields:
                raise SystemExit(
                    f"Nilai kosong pada baris manifest {line_number}: {empty_fields}"
                )

            recording_id = row["recording_id"]
            if recording_id in seen_ids:
                raise SystemExit(
                    f"recording_id duplikat pada baris manifest {line_number}: "
                    f"{recording_id}"
                )
            seen_ids.add(recording_id)

            start_time = row["start_time"]
            if not start_time.endswith("Z"):
                raise SystemExit(
                    f"start_time harus UTC kanonis berakhiran Z, baris "
                    f"{line_number}: {start_time}"
                )
            try:
                parsed_time = datetime.fromisoformat(start_time[:-1] + "+00:00")
            except ValueError as exc:
                raise SystemExit(
                    f"start_time tidak valid pada baris {line_number}: {start_time}"
                ) from exc
            if parsed_time.tzinfo is None or parsed_time.utcoffset() != timezone.utc.utcoffset(parsed_time):
                raise SystemExit(
                    f"start_time tidak merepresentasikan UTC pada baris {line_number}: "
                    f"{start_time}"
                )

            try:
                size_bytes = int(row["file_size_bytes"])
            except ValueError as exc:
                raise SystemExit(
                    f"file_size_bytes bukan bilangan bulat pada baris {line_number}"
                ) from exc
            if size_bytes < 1:
                raise SystemExit(
                    f"file_size_bytes harus lebih dari nol pada baris {line_number}"
                )
            row["file_size_bytes"] = str(size_bytes)

            if not SHA256_RE.fullmatch(row["sha256"]):
                raise SystemExit(
                    f"sha256 harus 64 digit heksadesimal huruf kecil pada baris "
                    f"{line_number}: {row['sha256']}"
                )

            uri = urlsplit(row["object_uri"])
            if uri.scheme not in {"s3", "s3a"} or not uri.netloc or not uri.path.strip("/"):
                raise SystemExit(
                    f"object_uri harus berisi skema s3/s3a, bucket, dan path "
                    f"pada baris {line_number}: {row['object_uri']}"
                )

            rows.append(row)

    if not rows:
        raise SystemExit("Manifest tidak memiliki baris data.")

    # Stable output order regardless of input row order.
    rows.sort(key=lambda row: row["recording_id"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=output_fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Baris manifest dibaca : {len(rows)}")
    print(f"recording_id unik     : {len(seen_ids)}")
    print(f"Baris ground truth    : {len(rows)}")
    print(f"Kolom                 : {', '.join(output_fields)}")
    print(f"Output                : {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
