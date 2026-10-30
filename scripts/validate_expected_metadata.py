"""Compare the frozen expected-metadata CSV with its source manifest."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


FIELD_MAP = {
    "recording_id": "recording_id",
    "device_id": "device_id",
    "start_time": "start_time",
    "object_uri": "expected_object_uri",
    "file_size_bytes": "file_size_bytes",
    "sha256": "sha256",
}


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"CSV tidak memiliki header: {path}")
        return list(reader.fieldnames), list(reader)


def _utc_instant(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp tidak memiliki zona waktu")
    return parsed.astimezone(timezone.utc)


def _uri_identity(value: str) -> tuple[str, str]:
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"s3", "s3a"} or not parsed.netloc or not parsed.path.strip("/"):
        raise ValueError("URI harus berbentuk s3:// atau s3a:// dengan bucket dan object key")
    return parsed.netloc, parsed.path.lstrip("/")


def _same_value(field: str, actual: str, expected: str) -> bool:
    if field == "start_time":
        return _utc_instant(actual) == _utc_instant(expected)
    if field == "object_uri":
        return _uri_identity(actual) == _uri_identity(expected)
    if field == "file_size_bytes":
        return int(actual) == int(expected)
    return actual == expected


def validate_rows(
    manifest_rows: list[dict[str, str]], expected_rows: list[dict[str, str]]
) -> list[str]:
    errors: list[str] = []

    def index_rows(rows: list[dict[str, str]], label: str) -> dict[str, dict[str, str]]:
        indexed: dict[str, dict[str, str]] = {}
        for line_number, row in enumerate(rows, start=2):
            recording_id = (row.get("recording_id") or "").strip()
            if not recording_id:
                errors.append(f"{label} baris {line_number}: recording_id kosong")
            elif recording_id in indexed:
                errors.append(f"{label}: recording_id duplikat {recording_id}")
            else:
                indexed[recording_id] = row
        return indexed

    manifest_by_id = index_rows(manifest_rows, "manifest")
    expected_by_id = index_rows(expected_rows, "expected_metadata")

    missing = sorted(manifest_by_id.keys() - expected_by_id.keys())
    extra = sorted(expected_by_id.keys() - manifest_by_id.keys())
    if missing:
        errors.append(f"expected_metadata kehilangan {len(missing)} recording_id: {missing[:5]}")
    if extra:
        errors.append(f"expected_metadata memiliki {len(extra)} recording_id asing: {extra[:5]}")

    for recording_id in sorted(manifest_by_id.keys() & expected_by_id.keys()):
        manifest_row = manifest_by_id[recording_id]
        expected_row = expected_by_id[recording_id]
        for target_field, source_field in FIELD_MAP.items():
            left = (expected_row.get(target_field) or "").strip()
            right = (manifest_row.get(source_field) or "").strip()
            if not left or not right:
                errors.append(f"{recording_id}: nilai {target_field} kosong")
                continue
            try:
                same = _same_value(target_field, left, right)
            except (ValueError, OverflowError):
                same = False
            if not same:
                errors.append(
                    f"{recording_id}: {target_field} berbeda "
                    f"(expected_metadata={left!r}, manifest={right!r})"
                )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Memeriksa expected_metadata.csv terhadap manifest sumber."
    )
    parser.add_argument("--manifest", default="data/manifests/manifest_main.csv")
    parser.add_argument("--expected", default="data/ground_truth/expected_metadata.csv")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    expected_path = Path(args.expected)
    try:
        manifest_fields, manifest_rows = read_csv(manifest_path)
        expected_fields, expected_rows = read_csv(expected_path)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    missing_source = sorted(set(FIELD_MAP.values()) - set(manifest_fields))
    missing_target = sorted(set(FIELD_MAP) - set(expected_fields))
    if missing_source or missing_target:
        parser.error(
            f"Kolom tidak lengkap: manifest={missing_source}, expected={missing_target}"
        )

    errors = validate_rows(manifest_rows, expected_rows)
    print(f"Baris manifest        : {len(manifest_rows)}")
    print(f"Baris expected        : {len(expected_rows)}")
    if errors:
        print(f"Selisih               : {len(errors)}")
        for error in errors[:20]:
            print(f"  - {error}")
        if len(errors) > 20:
            print(f"  ... {len(errors) - 20} selisih lain")
        print("HASIL: TIDAK COCOK")
        return 1

    print("Selisih               : 0")
    print("HASIL: COCOK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
