#!/usr/bin/env python3
"""Metadata-only EDA for frozen AudioMoth corpus manifests.

Reads CSV manifests only; it never opens or inspects audio file contents.
Example:
  python run_eda.py --manifest Main=... --manifest Kantin=... \
    --manifest Embung_D=... --manifest Kebun_Raya=... --out-dir eda_output
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

REQUIRED = {
    "recording_id", "device_id", "start_time", "source_path",
    "file_size_bytes", "sha256", "expected_object_uri", "expected_metadata",
}


def parse_time(raw: str) -> datetime:
    value = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    if value.utcoffset() is None:
        raise ValueError("timestamp has no explicit timezone")
    return value


def read_manifest(label: str, path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = set(reader.fieldnames or [])
        missing = sorted(REQUIRED - headers)
        if missing:
            raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")
        for line, raw in enumerate(reader, start=2):
            row = {key: (raw.get(key) or "").strip() for key in REQUIRED}
            row["_label"] = label
            row["_path"] = str(path)
            row["_line"] = line
            for column in REQUIRED:
                if not row[column]:
                    issues.append(issue(label, path, line, "missing_value", f"Kolom {column} kosong"))
            try:
                row["_time"] = parse_time(row["start_time"])
            except (ValueError, TypeError) as exc:
                row["_time"] = None
                issues.append(issue(label, path, line, "invalid_timestamp", str(exc)))
            try:
                row["_size"] = int(row["file_size_bytes"])
                if row["_size"] < 0:
                    raise ValueError("ukuran negatif")
            except (ValueError, TypeError):
                row["_size"] = None
                issues.append(issue(label, path, line, "invalid_file_size", "file_size_bytes bukan integer non-negatif"))
            rows.append(row)
    return rows, issues


def issue(label: str, path: Path | str, line: int | str, kind: str, detail: str, **extra: Any) -> dict[str, Any]:
    return {"manifest": label, "source_csv": str(path), "csv_line": line, "type": kind, "detail": detail, **extra}


def profile(label: str, path: Path, rows: list[dict[str, Any]], expected_gap: float, issues: list[dict[str, Any]]) -> dict[str, Any]:
    sizes = [r["_size"] for r in rows if r["_size"] is not None]
    devices = sorted({r["device_id"] for r in rows if r["device_id"]})
    if len(devices) > 1:
        issues.append(issue(label, path, "", "multiple_device_ids", f"Manifest memuat device_id berbeda: {', '.join(devices)}"))

    for column, kind in (("recording_id", "duplicate_recording_id"), ("source_path", "duplicate_source_path"), ("expected_object_uri", "duplicate_object_uri"), ("sha256", "duplicate_sha256")):
        values: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            if row[column]:
                values[row[column]].append(row)
        for value, matches in values.items():
            if len(matches) > 1:
                issues.append(issue(label, path, ",".join(str(x["_line"]) for x in matches), kind,
                                    f"Nilai berulang pada {len(matches)} baris", value=value))

    valid_times = sorted((r for r in rows if r["_time"] is not None), key=lambda r: r["_time"])
    gaps: Counter[float] = Counter()
    for prev, curr in zip(valid_times, valid_times[1:]):
        delta = (curr["_time"] - prev["_time"]).total_seconds()
        gaps[delta] += 1
        if delta != expected_gap:
            issues.append(issue(label, path, curr["_line"], "unexpected_time_gap",
                                f"Selisih {delta:g} detik; ekspektasi {expected_gap:g} detik",
                                previous_recording_id=prev["recording_id"], recording_id=curr["recording_id"],
                                gap_seconds=delta, expected_gap_seconds=expected_gap))
    size_counts = Counter(sizes)
    if len(size_counts) > 1:
        modal = size_counts.most_common(1)[0][0]
        for row in rows:
            if row["_size"] is not None and row["_size"] != modal:
                issues.append(issue(label, path, row["_line"], "non_modal_file_size",
                                    f"Ukuran {row['_size']} byte; ukuran terbanyak {modal} byte",
                                    recording_id=row["recording_id"], file_size_bytes=row["_size"], modal_size_bytes=modal))

    return {
        "manifest": label,
        "csv": str(path),
        "files": len(rows),
        "unique_device_ids": devices,
        "time_start_utc": valid_times[0]["_time"].isoformat() if valid_times else None,
        "time_end_utc": valid_times[-1]["_time"].isoformat() if valid_times else None,
        "first_to_last_hours": round((valid_times[-1]["_time"] - valid_times[0]["_time"]).total_seconds() / 3600, 6) if len(valid_times) > 1 else 0,
        "size_bytes": {
            "total": sum(sizes), "min": min(sizes) if sizes else None,
            "max": max(sizes) if sizes else None,
            "mean": round(statistics.mean(sizes), 2) if sizes else None,
            "median": statistics.median(sizes) if sizes else None,
            "unique_value_counts": {str(k): v for k, v in sorted(size_counts.items())},
            "total_MiB": round(sum(sizes) / (1024 * 1024), 3),
        },
        "time_gap_counts_seconds": {str(k): v for k, v in sorted(gaps.items())},
        "unique_sha256": len({r["sha256"] for r in rows if r["sha256"]}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", action="append", required=True, metavar="LABEL=CSV",
                        help="Manifest to analyze; repeat for each location/session")
    parser.add_argument("--expected-gap-seconds", type=float, default=60,
                        help="Expected start-to-start interval (default: 60 seconds)")
    parser.add_argument("--out-dir", type=Path, default=Path("eda_output"),
                        help="Directory for JSON summary and anomaly CSV (default: eda_output)")
    args = parser.parse_args()
    if args.expected_gap_seconds <= 0:
        parser.error("--expected-gap-seconds must be positive")

    manifests: list[tuple[str, Path]] = []
    for item in args.manifest:
        if "=" not in item:
            parser.error(f"invalid --manifest {item!r}; expected LABEL=CSV")
        label, raw_path = item.split("=", 1)
        if not label.strip() or not raw_path.strip():
            parser.error(f"invalid --manifest {item!r}; label and path are required")
        manifests.append((label.strip(), Path(raw_path.strip())))

    all_rows: list[dict[str, Any]] = []
    all_issues: list[dict[str, Any]] = []
    summaries = []
    for label, path in manifests:
        rows, read_issues = read_manifest(label, path)
        all_rows.extend(rows)
        all_issues.extend(read_issues)
        summaries.append(profile(label, path, rows, args.expected_gap_seconds, all_issues))

    global_values: dict[str, dict[str, list[dict[str, Any]]]] = {
        c: defaultdict(list) for c in ("recording_id", "source_path", "expected_object_uri", "sha256")
    }
    for row in all_rows:
        for column, values in global_values.items():
            if row[column]:
                values[row[column]].append(row)
    for column, values in global_values.items():
        for value, matches in values.items():
            if len({x["_label"] for x in matches}) > 1:
                all_issues.append(issue("ALL", "", ",".join(f"{x['_label']}:{x['_line']}" for x in matches),
                                        f"cross_manifest_duplicate_{column}", f"Nilai ditemukan pada beberapa manifest", value=value))

    summary = {
        "description": "Metadata-only corpus EDA; audio contents are not read.",
        "expected_start_to_start_gap_seconds": args.expected_gap_seconds,
        "manifests": summaries,
        "combined": {"files": len(all_rows), "unique_sha256": len({r["sha256"] for r in all_rows if r["sha256"]}),
                     "total_size_bytes": sum(r["_size"] or 0 for r in all_rows),
                     "total_size_MiB": round(sum(r["_size"] or 0 for r in all_rows) / (1024 * 1024), 3)},
        "anomaly_count": len(all_issues),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.out_dir / "eda_summary.json"
    issues_path = args.out_dir / "eda_anomalies.csv"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    fields = sorted({key for row in all_issues for key in row}) or ["manifest", "source_csv", "csv_line", "type", "detail"]
    with issues_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_issues)

    for item in summaries:
        sizes = item["size_bytes"]
        print(f"{item['manifest']}: {item['files']} rows; device_id={item['unique_device_ids']}; "
              f"size {sizes['min']}..{sizes['max']} bytes ({sizes['unique_value_counts']}); "
              f"gaps={item['time_gap_counts_seconds']}; span={item['first_to_last_hours']} h")
    print(f"Combined: {summary['combined']['files']} rows, {summary['combined']['total_size_MiB']} MiB")
    print(f"Review {len(all_issues)} flagged findings in {issues_path}; summary: {summary_path}")
    print("Flags are review prompts, not automatic proof of corruption or permission to alter the frozen corpus.")


if __name__ == "__main__":
    main()
