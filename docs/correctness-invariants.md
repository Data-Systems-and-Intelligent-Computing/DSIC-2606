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
| **I3 — Referential violation** | `object_uri` pada metadata menunjuk ke URI/path yang salah atau tidak sesuai acuan. | `recording_id`, `object_uri`, dan `object_uri` acuan. |
| **I4 — Orphan object** | Ada objek di storage tanpa baris metadata yang merujuk kepadanya. | Daftar objek di storage dibandingkan dengan `object_uri` pada tabel Iceberg. |
| **I5 — Dangling metadata** | Ada baris metadata yang menunjuk ke objek yang tidak ada di storage. | `recording_id`, `object_uri`, dan daftar objek aktual di storage. |
| **I6 — Checksum mismatch** | Isi objek berbeda dari berkas acuan. | `sha256` acuan dibandingkan dengan hash objek aktual; `file_size_bytes` juga diperiksa. |
| **I7 — Extra metadata** | Ada `recording_id` di tabel Iceberg yang tidak terdapat pada daftar acuan. | `recording_id` pada tabel Iceberg dibandingkan dengan daftar ID acuan. |

Sebagian invarian memerlukan daftar objek aktual dari storage selain kolom `expected_metadata.csv`. Karena itu `expected_metadata.csv` sendiri tidak cukup untuk mendeteksi orphan atau dangling object.
