import csv
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, help="Path manifest CSV sumber")
    parser.add_argument("--batch_size", type=int, default=10)
    parser.add_argument("--output", required=True, help="Path output frozen_batch_order CSV")
    args = parser.parse_args()

    with open(args.manifest, newline="") as f:
        rows = list(csv.DictReader(f))

    # Bekukan urutan: sorted ascending berdasarkan recording_id
    rows_sorted = sorted(rows, key=lambda r: r["recording_id"])

    output_rows = []
    for i, row in enumerate(rows_sorted):
        batch_number = i // args.batch_size
        position_in_batch = i % args.batch_size
        output_rows.append({
            "global_position": i,
            "batch_number": batch_number,
            "position_in_batch": position_in_batch,
            "recording_id": row["recording_id"],
            "is_first_in_batch": position_in_batch == 0,
            "is_last_in_batch": None,  # diisi di pass kedua
        })

    # Tandai posisi terakhir tiap batch (berguna buat titik sabotase F1/F2/F3 nanti)
    total_batches = output_rows[-1]["batch_number"] + 1
    for b in range(total_batches):
        members = [r for r in output_rows if r["batch_number"] == b]
        members[-1]["is_last_in_batch"] = True
    for r in output_rows:
        if r["is_last_in_batch"] is None:
            r["is_last_in_batch"] = False

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output_rows[0].keys())
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Total file     : {len(output_rows)}")
    print(f"Ukuran batch   : {args.batch_size}")
    print(f"Total batch    : {total_batches}")
    print(f"Tersimpan di   : {args.output}")


if __name__ == "__main__":
    main()