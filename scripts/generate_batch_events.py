"""Generate one JSON event per frozen batch-order batch."""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def load_batches(manifest_path: Path, batch_size: int, expected_batches: int):
    with manifest_path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        required = {"batch_number", "position_in_batch", "recording_id"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(
                f"CSV tidak memiliki kolom wajib: {', '.join(sorted(missing))}"
            )

        grouped = defaultdict(list)
        for line_number, row in enumerate(reader, start=2):
            try:
                batch_number = int(row["batch_number"])
                position = int(row["position_in_batch"])
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Nomor batch/posisi tidak valid pada baris {line_number}"
                ) from error
            recording_id = (row["recording_id"] or "").strip()
            if not recording_id:
                raise ValueError(f"recording_id kosong pada baris {line_number}")
            grouped[batch_number].append((position, recording_id))

    batch_numbers = sorted(grouped)
    if batch_numbers != list(range(expected_batches)):
        raise ValueError(
            f"Diharapkan {expected_batches} batch bernomor 0 sampai "
            f"{expected_batches - 1}; ditemukan {batch_numbers}"
        )

    batches = []
    for batch_number in batch_numbers:
        members = sorted(grouped[batch_number])
        positions = [position for position, _ in members]
        if positions != list(range(batch_size)):
            raise ValueError(
                f"Batch {batch_number} harus berisi tepat {batch_size} posisi "
                f"0 sampai {batch_size - 1}; ditemukan {positions}"
            )
        ids = [recording_id for _, recording_id in members]
        if len(set(ids)) != len(ids):
            raise ValueError(f"recording_id duplikat dalam batch {batch_number}")
        batches.append(ids)
    return batches


def main():
    parser = argparse.ArgumentParser(
        description="Buat JSON event dengan batch_id dan recording_ids dari CSV urutan batch."
    )
    parser.add_argument(
        "--batch-order",
        type=Path,
        required=True,
        help="CSV keluaran freeze_batch_order.py",
    )
    parser.add_argument(
        "--output-dir", type=Path, required=True, help="Folder JSON event keluaran"
    )
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--expected-batches", type=int, default=30)
    args = parser.parse_args()

    if args.batch_size <= 0 or args.expected_batches <= 0:
        parser.error("--batch-size dan --expected-batches harus lebih dari 0")

    try:
        batches = load_batches(args.batch_order, args.batch_size, args.expected_batches)
    except (OSError, ValueError) as error:
        parser.error(str(error))

    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error(
            f"Folder output tidak kosong; file lama tidak akan ditimpa: {args.output_dir}"
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    # Nomor batch di CSV dimulai dari 0; pertahankan nomor itu di event dan nama file.
    for batch_number, recording_ids in enumerate(batches):
        event = {"batch_id": batch_number, "recording_ids": recording_ids}
        output_path = args.output_dir / f"event-{batch_number:03d}.json"
        output_path.write_text(
            json.dumps(event, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    print(f"Total batch : {len(batches)}")
    print(f"ID per batch: {args.batch_size}")
    print(f"Output      : {args.output_dir}")


if __name__ == "__main__":
    main()
