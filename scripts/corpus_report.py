#!/usr/bin/env python3
"""Report frozen-corpus counts from the manifest, batch order, and provenance."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data/manifests/manifest_main.csv"
DEFAULT_BATCH_ORDER = ROOT / "data/batches/batch_order_main.csv"
DEFAULT_CONFIG_DIR = ROOT / "data/manifests/device_provenance"
DEFAULT_RAW_DIR = ROOT / "data/raw/audiomoth/main"
TIMESTAMP_PATTERN = re.compile(r"^\d{8}_\d{6}$")
DEVICE_ID_PATTERN = re.compile(r"^Device ID\s*:\s*(\S+)\s*$", re.MULTILINE)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def parse_aware_utc(value: str, *, context: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        result = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{context}: timestamp tidak valid: {value!r}") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(f"{context}: timestamp harus menyertakan zona waktu: {value!r}")
    return result.astimezone(timezone.utc)


def filename_timestamp_utc(filename: str, source_timezone: ZoneInfo) -> datetime:
    stem = Path(filename).stem
    if not TIMESTAMP_PATTERN.fullmatch(stem):
        raise ValueError(f"Nama WAV tidak mengikuti YYYYMMDD_HHMMSS: {filename}")
    try:
        local = datetime.strptime(stem, "%Y%m%d_%H%M%S").replace(
            tzinfo=source_timezone
        )
    except ValueError as exc:
        raise ValueError(f"Nama WAV memuat timestamp tidak valid: {filename}") from exc
    return local.astimezone(timezone.utc)


def timestamp_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_physical_device_ids(config_dir: Path) -> set[str]:
    config_files = sorted(config_dir.glob("*_CONFIG.TXT"))
    if not config_files:
        raise ValueError(f"Tidak ada *_CONFIG.TXT di {config_dir}")

    device_ids: set[str] = set()
    for path in config_files:
        content = path.read_text(encoding="utf-8-sig")
        match = DEVICE_ID_PATTERN.search(content)
        if not match:
            raise ValueError(f"Device ID tidak ditemukan di {path}")
        device_ids.add(match.group(1))
    return device_ids


def get_manifest_report(path: Path) -> tuple[list[dict[str, str]], Counter[int], datetime, datetime]:
    rows = read_csv(path)
    if not rows:
        raise ValueError(f"Manifest kosong: {path}")

    required = {"recording_id", "start_time", "file_size_bytes"}
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"Kolom manifest tidak ditemukan: {sorted(missing)}")

    recording_ids = [row["recording_id"].strip() for row in rows]
    if any(not recording_id for recording_id in recording_ids):
        raise ValueError("Manifest memiliki recording_id kosong")
    if len(recording_ids) != len(set(recording_ids)):
        raise ValueError("Manifest memiliki recording_id duplikat")

    sizes: Counter[int] = Counter()
    timestamps: list[datetime] = []
    for number, row in enumerate(rows, start=2):
        try:
            size = int(row["file_size_bytes"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{path.name}, baris {number}: file_size_bytes tidak valid") from exc
        if size < 0:
            raise ValueError(f"{path.name}, baris {number}: file_size_bytes negatif")
        sizes[size] += 1
        timestamps.append(
            parse_aware_utc(row["start_time"], context=f"{path.name}, baris {number}")
        )

    return rows, sizes, min(timestamps), max(timestamps)


def validate_batch_order(path: Path, manifest_rows: list[dict[str, str]]) -> dict[int, int]:
    rows = read_csv(path)
    required = {"batch_number", "recording_id"}
    if not rows:
        raise ValueError(f"Batch order kosong: {path}")
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"Kolom batch order tidak ditemukan: {sorted(missing)}")

    per_batch: Counter[int] = Counter()
    ordered_ids: list[str] = []
    for number, row in enumerate(rows, start=2):
        try:
            batch_number = int(row["batch_number"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{path.name}, baris {number}: batch_number tidak valid") from exc
        per_batch[batch_number] += 1
        ordered_ids.append(row["recording_id"].strip())

    manifest_ids = [row["recording_id"].strip() for row in manifest_rows]
    if len(ordered_ids) != len(set(ordered_ids)):
        raise ValueError("Batch order memiliki recording_id duplikat")
    if set(ordered_ids) != set(manifest_ids) or len(ordered_ids) != len(manifest_ids):
        raise ValueError("ID batch order tidak sama dengan recording_id pada manifest")
    return dict(sorted(per_batch.items()))


def get_raw_report(
    raw_dir: Path, source_timezone: ZoneInfo
) -> tuple[int, int, Counter[int], datetime, datetime] | None:
    if not raw_dir.is_dir():
        return None
    files = sorted(
        path for path in raw_dir.iterdir()
        if path.is_file() and path.suffix.lower() == ".wav"
    )
    if not files:
        return None

    sizes: Counter[int] = Counter()
    timestamps: list[datetime] = []
    total_bytes = 0
    for path in files:
        size = path.stat().st_size
        total_bytes += size
        sizes[size] += 1
        timestamps.append(filename_timestamp_utc(path.name, source_timezone))
    return len(files), total_bytes, sizes, min(timestamps), max(timestamps)


def format_distribution(sizes: Counter[int]) -> str:
    return "; ".join(
        f"{size:,} byte: {count} file" for size, count in sorted(sizes.items())
    )


def format_batch_distribution(batch_sizes: dict[int, int]) -> str:
    distribution = Counter(batch_sizes.values())
    return "; ".join(
        f"{batch_count} batch x {items_per_batch} recording_id"
        for items_per_batch, batch_count in sorted(distribution.items())
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Menghitung ringkasan korpus dari manifest, batch order, dan CONFIG.TXT."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--batch-order", type=Path, default=DEFAULT_BATCH_ORDER)
    parser.add_argument("--config-dir", type=Path, default=DEFAULT_CONFIG_DIR)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--source-timezone", default="Asia/Jakarta")
    args = parser.parse_args()

    try:
        source_timezone = ZoneInfo(args.source_timezone)
        manifest_rows, sizes, earliest, latest = get_manifest_report(args.manifest)
        batches = validate_batch_order(args.batch_order, manifest_rows)
        physical_devices = get_physical_device_ids(args.config_dir)
        raw = get_raw_report(args.raw_dir, source_timezone)

        if len(manifest_rows) != sum(batches.values()):
            raise ValueError("Jumlah penempatan batch berbeda dari jumlah baris manifest")
        if any(count != 10 for count in batches.values()):
            raise ValueError("Tidak semua batch berisi tepat 10 recording_id")

        print("Korpus eksperimen Main (dari manifest):")
        print(f"  jumlah berkas       : {len(manifest_rows)}")
        print(f"  total byte          : {sum(int(row['file_size_bytes']) for row in manifest_rows):,}")
        print(f"  perangkat fisik     : {len(physical_devices)} (Device ID unik dari CONFIG.TXT)")
        print(f"  rentang waktu UTC   : {timestamp_text(earliest)} s.d. {timestamp_text(latest)}")
        print(f"  jumlah batch beku   : {len(batches)}")
        print(f"  distribusi ukuran   : {format_distribution(sizes)}")
        print(f"  ukuran tiap batch   : {format_batch_distribution(batches)}")

        if raw is None:
            print(f"Korpus sumber mentah : tidak dihitung (folder tidak tersedia: {args.raw_dir})")
        else:
            raw_count, raw_bytes, raw_sizes, raw_earliest, raw_latest = raw
            print("Korpus sumber mentah (dari folder raw, termasuk file yang dikecualikan):")
            print(f"  jumlah berkas       : {raw_count}")
            print(f"  total byte          : {raw_bytes:,}")
            print(f"  rentang waktu UTC   : {timestamp_text(raw_earliest)} s.d. {timestamp_text(raw_latest)}")
            print(f"  distribusi ukuran   : {format_distribution(raw_sizes)}")

        if len(physical_devices) != 1:
            print("PERINGATAN: jumlah Device ID unik bukan satu; tinjau provenance sebelum melaporkan.", file=sys.stderr)
    except (OSError, ValueError, ZoneInfoNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
