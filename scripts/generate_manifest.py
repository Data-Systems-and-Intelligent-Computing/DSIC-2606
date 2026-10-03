import os
import hashlib
import csv
import argparse
from datetime import datetime, timedelta


def compute_sha256(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()   


def parse_timestamp(filename, was_local_wib):
    name = os.path.splitext(filename)[0]
    try:
        dt = datetime.strptime(name, "%Y%m%d_%H%M%S")
    except ValueError:
        return None
    if was_local_wib:
        dt = dt - timedelta(hours=7)
    return dt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Folder berisi file WAV")
    parser.add_argument("--device_id", required=True, help="Kode device/lokasi")
    parser.add_argument("--output", required=True, help="Path file manifest CSV output")
    parser.add_argument("--local_wib", default="true", help="true/false - device time lokal WIB?")
    args = parser.parse_args()

    was_local_wib = args.local_wib.lower() == "true"
    wav_files = sorted([f for f in os.listdir(args.input) if f.upper().endswith(".WAV")])

    if not wav_files:
        print(f"PERINGATAN: tidak ada file .WAV ditemukan di {args.input}")
        return

    print(f"Memproses {len(wav_files)} file dari {args.input} ...")
    rows = []

    for filename in wav_files:
        filepath = os.path.join(args.input, filename)
        name_no_ext = os.path.splitext(filename)[0]
        ts = parse_timestamp(filename, was_local_wib)
        ts_str = ts.strftime("%Y-%m-%dT%H:%M:%SZ") if ts else "UNKNOWN"
        date_str = ts.strftime("%Y-%m-%d") if ts else "unknown-date"

        rows.append({
            "recording_id": f"{args.device_id}_{name_no_ext}",
            "device_id": args.device_id,
            "start_time": ts_str,
            "source_path": f"{args.input}/{filename}",
            "file_size_bytes": os.path.getsize(filepath),
            "sha256": compute_sha256(filepath),
            "expected_object_uri": f"s3://audiomoth/{args.device_id}/{date_str}/{filename}",
            "expected_metadata": f"{args.device_id}_{name_no_ext}",
        })

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"  -> {len(rows)} baris ditulis ke {args.output}")


if __name__ == "__main__":
    main()