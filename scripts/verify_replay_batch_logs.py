"""Compare REPLAY_BATCH_COMPLETED lines with the frozen batch order."""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


_BATCH_LINE = re.compile(r"REPLAY_BATCH_COMPLETED batch_id=(\d+) recording_ids=(\[.*\])")


def read_expected_batches(path: Path, batch_size: int = 10, expected_count: int = 30) -> list[list[str]]:
    groups: dict[int, list[tuple[int, str]]] = {}
    with Path(path).open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        required = {"batch_number", "position_in_batch", "recording_id"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"batch-order CSV missing columns: {', '.join(sorted(missing))}")
        for row in reader:
            batch_id = int(row["batch_number"])
            groups.setdefault(batch_id, []).append((int(row["position_in_batch"]), row["recording_id"].strip()))
    if sorted(groups) != list(range(expected_count)):
        raise ValueError(f"expected {expected_count} batches; found {sorted(groups)}")
    result = []
    for batch_id in range(expected_count):
        entries = sorted(groups[batch_id])
        if [position for position, _ in entries] != list(range(batch_size)):
            raise ValueError(f"batch {batch_id} does not have positions 0..{batch_size - 1}")
        result.append([rid for _, rid in entries])
    return result


def read_logged_batches(path: Path) -> list[list[str]]:
    batches = []
    ids = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        match = _BATCH_LINE.search(line)
        if not match:
            continue
        batch_id = int(match.group(1))
        recording_ids = json.loads(match.group(2))
        if batch_id != len(batches):
            raise ValueError(f"{path}: expected logged batch {len(batches)}, found {batch_id}")
        if not isinstance(recording_ids, list) or len(recording_ids) != 10:
            raise ValueError(f"{path}: batch {batch_id} must log exactly 10 recording IDs")
        batches.append(recording_ids)
        ids.extend(recording_ids)
    if len(batches) != 30:
        raise ValueError(f"{path}: expected 30 completed batches, found {len(batches)}")
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate recording IDs across logged batches")
    return batches


def verify_log(path: Path, expected: list[list[str]]) -> None:
    actual = read_logged_batches(path)
    if actual != expected:
        mismatch = next(i for i, (left, right) in enumerate(zip(actual, expected)) if left != right)
        raise ValueError(f"{path}: composition/order mismatch in batch {mismatch}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-order", type=Path, default=Path("data/batches/batch_order_main.csv"))
    parser.add_argument("logs", type=Path, nargs="+", help="one or more B0/B1 log files")
    args = parser.parse_args()
    try:
        expected = read_expected_batches(args.batch_order)
        for log in args.logs:
            verify_log(log, expected)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    for log in args.logs:
        print(f"{log}: 30 batch x 10 ID COCOK dengan batch_order_main.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
