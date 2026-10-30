# Bukti Sesi Fase 3 — 14 Oktober 2026

Catatan ini merangkum perintah dan keluaran yang dikirim pengguna dari terminal VM pada 14 Oktober 2026. Perintah tidak dijalankan ulang saat dokumentasi ini dibuat.

## Batas sesi dan status

- VM `dsic-lab-01`, zona `asia-southeast2-a`, project `sigerciv1`.
- Waktu start yang tercatat di logbook: 22:09:17 WIB; snapshot environment pukul 22:09:56 WIB.
- CPU sesi: Intel(R) Xeon(R) CPU @ 2.20GHz, 4 CPU.
- `sudo make up`, `sudo make ps`, dan `sudo make check` berhasil; `make check` menyatakan `lingkungan sama dengan environment.lock.txt`.
- Aktivitas unggah berikut terjadi setelah snapshot environment. Waktu tepat aktivitas unggah tidak tersedia dari keluaran yang dibagikan.
- Belum ada eksekusi ingest B0/B1 atau F0 yang dilaporkan. Probe event hanya memakai JSON dummy.
- Status akhir stack dan waktu stop VM untuk sesi ini belum dilaporkan.

## Pemeriksaan awal MinIO dan korpus

Perintah yang dijalankan:

```bash
find /data/corpus/main -maxdepth 1 -type f -iname '*.wav' | wc -l
sudo docker compose --env-file versions.env --env-file .env run --rm --no-deps --entrypoint python3 minio-init /opt/lab/scripts/minio_buckets.py count
```

Keluaran yang dikirim:

```text
300
audiomoth 0
warehouse 0
```

Pemeriksaan klien:

```bash
command -v mc || true
command -v aws || true
python3 -c 'import boto3; print("boto3 tersedia")' 2>&1
```

Keluaran: tidak ada path yang tercetak untuk `mc` atau `aws`; `boto3 tersedia`.

## Probe urutan file dengan JSON dummy

Tiga event dummy dibuat di `/data/results/source-order-probe-20261014/events`; setiap file berisi 10 ID dummy. Waktu modifikasi sengaja dibuat tidak mengikuti nomor nama file.

Skrip pembuatan event yang dikirim pengguna:

```bash
sudo python3 - <<'PY'
import json
import os
from datetime import datetime
from pathlib import Path

folder = Path("/data/results/source-order-probe-20261014/events")
events = [
    ("event-01.json", 1, "2026-10-14T10:03:00+00:00"),
    ("event-02.json", 2, "2026-10-14T10:01:00+00:00"),
    ("event-03.json", 3, "2026-10-14T10:02:00+00:00"),
]

for filename, batch_id, modified in events:
    recording_ids = [f"DUMMY-{batch_id:02d}-{i:02d}" for i in range(10)]
    path = folder / filename
    path.write_text(
        json.dumps({"batch_id": batch_id, "recording_ids": recording_ids}) + "\n",
        encoding="utf-8",
    )
    timestamp = datetime.fromisoformat(modified).timestamp()
    os.utime(path, (timestamp, timestamp))
    print(f"{filename}: batch_id={batch_id}, jumlah_ID={len(recording_ids)}, mtime={modified}")
PY
```

Perintah yang dikirim pengguna untuk mengubah probe agar memakai `local[2]` setelah worker gagal membaca mount `/results`:

```bash
sudo python3 - <<'PY'
from pathlib import Path

path = Path("/data/results/source-order-probe-20261014/probe.py")
text = path.read_text()
old = 'SparkSession.builder.appName("source-order-probe").getOrCreate()'
new = 'SparkSession.builder.master("local[2]").appName("source-order-probe").getOrCreate()'

if old not in text:
    raise SystemExit("Baris SparkSession yang diharapkan tidak ditemukan; file tidak diubah.")

text = text.replace(old, new, 1)
text = text.replace(
    'stream = (',
    'print(f"PROBE_MASTER={spark.sparkContext.master}", flush=True)\n\nstream = (',
    1,
)
path.write_text(text)
print("Probe diperbarui; mode Spark:", "local[2]" in text)
PY
```

Keluaran yang dikirim:

```text
event-01.json: batch_id=1, jumlah_ID=10, mtime=2026-10-14T10:03:00+00:00
event-02.json: batch_id=2, jumlah_ID=10, mtime=2026-10-14T10:01:00+00:00
event-03.json: batch_id=3, jumlah_ID=10, mtime=2026-10-14T10:02:00+00:00
```

Percobaan cluster sebelumnya gagal karena worker tidak memiliki mount `/results`; galatnya menyebut `SparkFileNotFoundException` untuk `event-02.json`. Pemeriksaan mount worker hanya menunjukkan `/data/corpus/main -> /data/raw`.

Probe kemudian dijalankan dengan Spark `local[2]`. Perintah pemeriksaan hasil:

```bash
grep 'PROBE' /tmp/source-order-probe-20261014.log
```

Keluaran:

```text
PROBE_MASTER=local[2]
PROBE micro_batch=0 file=event-02.json event_batch=2
PROBE micro_batch=1 file=event-03.json event_batch=3
PROBE micro_batch=2 file=event-01.json event_batch=1
```

Pada probe lokal ini, file dibaca menurut waktu modifikasi yang paling awal di antara file yang tersedia, bukan urutan leksikal namanya. Ini pengamatan eksploratif, bukan uji replay 30 batch dan bukan eksekusi treatment.

## Unggah WAV manual dan pemeriksaan multipart

Manifest lokal diperiksa dengan skrip Python satu kali. Keluaran yang dikirim:

```text
Jumlah URI: 300
Bucket: ['audiomoth']
Prefix: ['MAIN_5JAM/2026-09-24']
Contoh URI: s3://audiomoth/MAIN_5JAM/2026-09-24/20260924_133000.WAV
```

Pengguna melaporkan skrip Boto3 di VM mengunggah 300 WAV dari `/data/corpus/main` ke URI manifest, lalu memverifikasi ukuran dan SHA-256:

```text
Terunggah: 25/300
Terunggah: 50/300
Terunggah: 75/300
Terunggah: 100/300
Terunggah: 125/300
Terunggah: 150/300
Terunggah: 175/300
Terunggah: 200/300
Terunggah: 225/300
Terunggah: 250/300
Terunggah: 275/300
Terunggah: 300/300
Objek terverifikasi: 300
Total byte: 1056240000
HASIL: COCOK
```

**Batas bukti kode unggah:** isi heredoc Boto3 yang ditempel ke percakapan tampil terpotong dan tercampur (`PYint...`), sehingga sumber lengkap yang benar-benar dieksekusi tidak dapat disalin dengan akurat ke repositori. Catatan ini menyimpan keluaran yang tersedia dan tidak merekonstruksi skrip yang hilang. Jangan menaruh kredensial `.env` di logbook atau bukti.

Verifikasi multipart dijalankan dan keluaran berhasil disimpan di VM:

```bash
cd /data/lab/dsic-lab-stack
set -o pipefail
sudo make verify-multipart 2>&1 | sudo tee /data/results/verify-multipart-20261014.log
```

Keluaran:

```text
docker compose --env-file versions.env --env-file .env run --rm --no-deps -T --entrypoint python3 minio-init /opt/lab/scripts/minio_buckets.py multipart
Container dsic2606-minio-init-run-0d5328619c21 Creating
Container dsic2606-minio-init-run-0d5328619c21 Created
objek diperiksa: 300
objek multipart: 0 (harus 0)
```

Percobaan pertama memakai `tee` tanpa `sudo` dan gagal menyimpan file karena `Permission denied`; perintah kedua di atas berhasil menyimpan log.

## Interpretasi dan pekerjaan tersisa

- Upload 300 WAV ini dilakukan manual dari VM ke MinIO. Itu membuktikan unggahan manual beserta kecocokan ukuran/hash dan pemeriksaan 300 objek single-part; itu **belum** membuktikan pipeline B0/B1 melakukan PUT.
- Panduan Fase 3 tetap meminta pipeline melakukan PUT WAV lalu menulis metadata Iceberg. Sebelum F0, ikuti reset terkontrol sesuai protokol; karena objek manual sudah ada, konfirmasi penanganannya kepada pembimbing sebelum reset atau ingest.
- Kode replay 30 event yang berasal dari `batch_order_main.csv`, `src/ingestion/microbatch.py`, eksekusi B0/F0 dan B1/F0, serta rekonsiliasi hasil belum dikerjakan.

## Perintah tambahan yang terekam

Pemeriksaan layanan:

```bash
cd /data/lab/dsic-lab-stack
sudo make up
sudo make ps
sudo make check
```

Manifest URI diperiksa dari repo dengan skrip Python berikut:

```bash
cd /data/work/DSIC-2606
python3 - <<'PY'
import csv
from urllib.parse import urlparse

with open("data/manifests/manifest_main.csv", newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

uris = [row["expected_object_uri"] for row in rows]
print("Jumlah URI:", len(uris))
print("Bucket:", sorted({urlparse(uri).netloc for uri in uris}))
print("Prefix:", sorted({"/".join(urlparse(uri).path.strip("/").split("/")[:2]) for uri in uris}))
print("Contoh URI:", uris[0])
PY
```

Perintah/skrip yang tidak disalin utuh ke bukti ini tidak direkonstruksi. Secara khusus, heredoc pengunggah Boto3 yang terlihat di percakapan rusak/terpotong; yang tersedia adalah keluaran unggah dan verifikasinya.

## Sesi lanjutan — 15 Oktober 2026

Pengguna melaporkan waktu PowerShell `2026-10-15 13:23:31 +07:00` sebelum menyalakan VM. Perintah start berhasil dan status GCP setelahnya `RUNNING`; waktu transisi persis belum diambil dari `lastStartTimestamp`.

Perintah yang dijalankan melalui SSH:

```bash
cat /var/lib/dsic-lab/environment.txt
cd /data/lab/dsic-lab-stack
sudo make up
sudo make ps
sudo make check
```

Snapshot yang dikirim: `captured_utc=2026-10-15T06:24:29Z`, CPU Intel(R) Xeon(R) CPU @ 2.20GHz, 4 CPU; memori 16.369.284 KB; Ubuntu 24.04.5 LTS, kernel `7.0.0-1013-gcp`; Docker 29.8.2 (build `7fc2dff`), Compose v5.6.0. Layanan terangkat dan `make check` menyatakan `lingkungan sama dengan environment.lock.txt`.

Perintah verifikasi sebelum reset dan pemeriksaan versi klien:

```bash
cd /data/lab/dsic-lab-stack
set -o pipefail
sudo make verify-multipart 2>&1 | sudo tee /data/results/verify-multipart-manual-20261015.log
python3 -c 'import boto3, botocore; print("boto3", boto3.__version__); print("botocore", botocore.__version__)'
```

Keluaran yang dikirim:

```text
objek diperiksa: 300
objek multipart: 0 (harus 0)
boto3 1.34.46
botocore 1.34.46
```

Ambang multipart yang dipakai unggahan manual belum terverifikasi, dan keluaran ini tidak mencantumkan ETag per objek. Tidak ada reset atau ingest yang dilaporkan.

Pengguna kemudian mengirim keluaran daftar ETag dari prefix `MAIN_5JAM/2026-09-24/`. Keluaran berakhir dengan `# object_count=300`; contoh baris yang dikirim memuat objek 3.520.800 byte dan ETag 32 karakter heksadesimal tanpa akhiran jumlah part. Daftar lengkap berada di VM pada `/data/results/etags-manual-20261015.tsv`. Ini bukti unggah manual; bukan bukti PUT oleh pipeline. Ambang multipart unggah manual masih belum terverifikasi.

Salinan lokal bukti tersebut tersedia di `docs/evidence/etags-manual-20261015.tsv` dan `docs/evidence/verify-multipart-manual-20261015.log`. TSV memuat 300 baris objek, satu header, dan satu penanda jumlah (`object_count=300`). Log verifikasi mencatat 300 objek diperiksa dan 0 multipart.

## Generator event replay — 15 Oktober 2026

Perintah yang dijalankan pengguna di PowerShell:

```powershell
python scripts/generate_batch_events.py `
  --batch-order data/batches/batch_order_main.csv `
  --output-dir data/replay/main/events
```

Keluaran yang dilaporkan:

```text
Total batch : 30
ID per batch: 10
Output      : data\replay\main\events
```

Pemeriksaan pengguna menemukan 30 file. `event-000.json` berisi `batch_id: 0` dan sepuluh ID pertama, dari `MAIN_5JAM_20260924_133000` sampai `MAIN_5JAM_20260924_133900`. `event-029.json` berisi `batch_id: 29` dan sepuluh ID terakhir, dari `MAIN_5JAM_20260924_182000` sampai `MAIN_5JAM_20260924_182900`. Ini baru artefak replay lokal; belum dibaca Spark dan belum membuktikan ingest.

Sebelum uji dengan Spark cluster, tentukan jalur event yang dapat dibaca worker. Probe terdahulu gagal pada `/results` karena mount itu tidak tersedia di worker.

## Verifikasi event replay terhadap batch order — 15 Oktober 2026

Pengguna menjalankan pemeriksaan lokal atas semua file event dan membandingkan `batch_id` serta urutan `recording_ids` dengan `batch_order_main.csv`. Keluaran yang dilaporkan:

```text
COCOK: 30 event, 300 recording_id sesuai batch_order_main.csv
```

Ini membuktikan kesesuaian artefak event lokal dengan batch order beku. Pemeriksaan tidak menjalankan Spark, tidak membaca WAV, dan bukan bukti ingest B0/B1.
