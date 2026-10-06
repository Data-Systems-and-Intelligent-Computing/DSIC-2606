import argparse
import csv
import hashlib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import re
from zoneinfo import ZoneInfo


def compute_sha256(filepath: Path) -> str:
    sha256 = hashlib.sha256()
    with filepath.open("rb") as file:
        for chunk in iter(lambda: file.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def parse_timestamp(filename: str, source_timezone: str) -> datetime:
    stem = Path(filename).stem

    if not re.fullmatch(r"\d{8}_\d{6}", stem):
        raise ValueError(
            f"Nama file tidak memiliki format timestamp YYYYMMDD_HHMMSS: {filename}"
        )

    try:
        local_time = datetime.strptime(stem, "%Y%m%d_%H%M%S")
    except ValueError as exc:
        raise ValueError(
            f"Nama file tidak memiliki timestamp yang valid: {filename}"
        ) from exc

    if source_timezone == "Asia/Jakarta":
        local_time = local_time.replace(tzinfo=ZoneInfo("Asia/Jakarta"))
    else:
        local_time = local_time.replace(tzinfo=timezone.utc)

    return local_time.astimezone(timezone.utc)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Membuat manifest WAV secara deterministik."
    )
    parser.add_argument("--input", required=True, help="Folder WAV sumber")
    parser.add_argument(
        "--corpus-root",
        required=True,
        help="Akar korpus untuk membuat source_path relatif",
    )
    parser.add_argument("--device_id", required=True, help="Label perangkat/sesi")
    parser.add_argument("--output", required=True, help="Path CSV manifest")
    parser.add_argument(
        "--source-timezone",
        required=True,
        choices=["Asia/Jakarta", "UTC"],
        help="Zona waktu yang digunakan pada nama file",
    )
    parser.add_argument(
        "--selection",
        required=True,
        choices=["all", "modal-size"],
        help="Gunakan 'modal-size' untuk aturan seleksi Fase 1",
    )
    args = parser.parse_args()

    input_dir = Path(args.input).resolve()
    corpus_root = Path(args.corpus_root).resolve()
    output_path = Path(args.output)

    try:
        input_dir.relative_to(corpus_root)
    except ValueError:
        parser.error("--input harus berada di dalam --corpus-root")

    wav_files = sorted(
        path for path in input_dir.iterdir()
        if path.is_file() and path.suffix.lower() == ".wav"
    )
    if not wav_files:
        parser.error(f"Tidak ada file WAV di {input_dir}")

    # Validasi semua timestamp sebelum seleksi agar nama yang rusak
    # tidak diam-diam lolos hanya karena ukuran filenya berbeda.
    timestamps = {}
    for filepath in wav_files:
        try:
            timestamps[filepath] = parse_timestamp(
                filepath.name, args.source_timezone
            )
        except ValueError as exc:
            parser.error(str(exc))

    sizes = Counter(path.stat().st_size for path in wav_files)
    selected_files = wav_files

    if args.selection == "modal-size":
        highest_frequency = max(sizes.values())
        modal_sizes = [
            size for size, count in sizes.items()
            if count == highest_frequency
        ]

        if len(modal_sizes) != 1:
            parser.error(
                f"Ukuran modal tidak tunggal: {modal_sizes}. "
                "Jangan seleksi otomatis; tinjau korpus dan aturannya."
            )

        modal_size = modal_sizes[0]
        selected_files = [
            path for path in wav_files
            if path.stat().st_size == modal_size
        ]
        excluded_files = [
            path for path in wav_files
            if path.stat().st_size != modal_size
        ]
    else:
        excluded_files = []

    rows = []
    for filepath in selected_files:
        timestamp_utc = timestamps[filepath]
        filename_stem = filepath.stem
        relative_source_path = filepath.relative_to(corpus_root).as_posix()

        rows.append({
            "recording_id": f"{args.device_id}_{filename_stem}",
            "device_id": args.device_id,
            "start_time": timestamp_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_path": relative_source_path,
            "file_size_bytes": filepath.stat().st_size,
            "sha256": compute_sha256(filepath),
            "expected_object_uri": (
                f"s3://audiomoth/{args.device_id}/"
                f"{timestamp_utc:%Y-%m-%d}/{filepath.name}"
            ),
            "expected_metadata": f"{args.device_id}_{filename_stem}",
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Jumlah file sumber : {len(wav_files)}")
    print(f"Jumlah di manifest : {len(selected_files)}")
    print(f"Jumlah dikecualikan: {len(excluded_files)}")
    for filepath in excluded_files:
        print(f"  Dikecualikan: {filepath.name} ({filepath.stat().st_size} byte)")
    print(f"Manifest ditulis ke: {output_path}")
    print(
        "Catatan: simpan aturan seleksi dan nama file yang dikecualikan "
        "di laporan korpus serta logbook."
    )


if __name__ == "__main__":
    main()
