# Correctness Invariants (Acuan Kebenaran Metadata)

## 1. Skema dan Aturan Pencocokan

`expected_metadata.csv` memuat satu baris untuk setiap `recording_id`, dengan kolom:

- `recording_id`
- `device_id`
- `start_time`
- `object_uri`
- `file_size_bytes`
- `sha256`

Nilai `object_uri` diambil dari kolom `expected_object_uri` pada manifes sumber. Nama kolom pada tabel tujuan adalah `object_uri`.

### Asal nilai acuan

`expected_metadata.csv` dibentuk dari manifes yang sudah dibekukan, sebelum pipeline ingest dijalankan. Aturannya mengikuti `configs/dataset.yaml` dan `scripts/generate_manifest.py`:

- `recording_id` adalah `device_id` ditambah `_` dan stem nama WAV. Contoh: `MAIN_5JAM_20260924_133000`.
- `start_time` adalah waktu pada nama berkas yang ditafsirkan sebagai `Asia/Jakarta`, lalu dinormalisasi ke UTC.
- `object_uri` memakai bucket `audiomoth`, label sesi sebagai prefix, tanggal dari `start_time` UTC, dan nama berkas asli. Contoh: `s3://audiomoth/MAIN_5JAM/2026-09-24/20260924_133000.WAV`.
- `device_id`, `file_size_bytes`, dan `sha256` disalin dari baris manifest yang sama.

Skrip `scripts/validate_expected_metadata.py` membandingkan ground truth dengan manifest sumber. Untuk URI, hanya skema `s3` dan `s3a` yang dinormalisasi; bucket dan object key tetap harus sama. Untuk waktu, kedua nilai dibandingkan sebagai instant berzona waktu. Validasi ini memeriksa acuan sebelum ingest, bukan membuktikan hasil pipeline.

### Pencocokan sama persis

Kolom berikut harus sama persis dengan nilai acuan:

- `recording_id`
- `device_id`
- `file_size_bytes`
- `sha256`

### Kesetaraan secara makna

- `start_time` dibandingkan sebagai waktu yang menyatakan instant UTC yang sama, bukan sebagai string mentah. Nilainya harus memiliki zona waktu yang eksplisit.
- `object_uri` setara jika menunjuk ke bucket dan object key yang sama. Prefix skema `s3://` dan `s3a://` boleh dinormalisasi; bucket dan path setelahnya harus sama.

### Tidak menjadi nilai acuan tetap

Kolom runtime seperti `ingestion_time` dan `run_id` tidak dimasukkan ke `expected_metadata.csv` dan tidak dibandingkan karena nilainya dapat berbeda antar-eksekusi.

## 2. Pemetaan Invarian I1–I7

| Invarian | Kondisi yang harus dideteksi | Data yang dipakai |
|---|---|---|
| **I1 — Missing metadata** | Ada `recording_id` yang diharapkan tetapi tidak ada di tabel Iceberg. | `recording_id` pada tabel Iceberg dibandingkan dengan daftar acuan. |
| **I2 — Duplicate metadata** | Satu `recording_id` muncul lebih dari sekali di tabel Iceberg. | `recording_id`; setiap ID harus unik. |
| **I3 — Referential violation** | Metadata untuk ID yang dikenal tidak sesuai nilai acuan: URI menunjuk ke objek yang salah, atau isi kolom metadata beku tidak sama. | `recording_id`, `device_id`, `start_time`, `object_uri`, `file_size_bytes`, dan `sha256` dibandingkan dengan baris expected; URI dan waktu memakai aturan kesetaraan semantik di atas. |
| **I4 — Orphan object** | Ada objek di storage tanpa baris metadata yang merujuk kepadanya. | Daftar objek di storage dibandingkan dengan `object_uri` pada tabel Iceberg. |
| **I5 — Dangling metadata** | Ada baris metadata yang menunjuk ke objek yang tidak ada di storage. | `recording_id`, `object_uri`, dan daftar objek aktual di storage. |
| **I6 — Checksum mismatch** | Isi objek berbeda dari berkas acuan. | `sha256` acuan dibandingkan dengan hash objek aktual; `file_size_bytes` juga diperiksa. |
| **I7 — Extra metadata** | Ada `recording_id` di tabel Iceberg yang tidak terdapat pada daftar acuan. | `recording_id` pada tabel Iceberg dibandingkan dengan daftar ID acuan. |

Sebagian invarian memerlukan daftar objek aktual dari storage selain kolom `expected_metadata.csv`. Karena itu `expected_metadata.csv` sendiri tidak cukup untuk mendeteksi orphan atau dangling object.

### Keputusan operasional untuk rekonsiliasi I3–I5

- URI dinormalisasi hanya pada skema (`s3://` dan `s3a://` dianggap setara). Nama bucket dan object key dibandingkan persis, tanpa mengubah kapitalisasi atau prefix.
- Objek dibaca dari seluruh halaman `ListObjectsV2` untuk setiap bucket yang dirujuk expected metadata. Objek yang tidak terpetakan atau tidak dirujuk tetap dilaporkan sebagai orphan; tidak diabaikan berdasarkan nama prefix.
- Bila `object_uri` metadata diubah ke URI yang tidak ada, I3 dan I5 harus berbunyi, dan objek asli yang tak lagi dirujuk juga membuat I4 berbunyi. Bila objek tambahan disisipkan, hanya I4 berbunyi. Bila objek dihapus sementara metadata tetap ada, hanya I5 berbunyi.
- I6 mengunduh byte setiap objek acuan yang ditemukan di listing, lalu menghitung SHA-256 aktual per potongan 1 MiB dan membandingkan ukuran serta hash dengan `expected_metadata.csv`. Ini membuktikan byte objek, bukan metadata checksum yang tersimpan; satu rekonsiliasi Main dapat membaca sekitar 1.056.240.000 byte.
- Pemetaan objek memakai URI bucket+key yang dinormalisasi; object key yang tidak dirujuk metadata tetap dilaporkan I4. I6 memetakan objek acuan ke `recording_id` lewat URI beku pada expected metadata, bukan dengan menebak dari nama file.
