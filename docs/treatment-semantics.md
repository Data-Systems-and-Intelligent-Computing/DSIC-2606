# Semantik Treatment B0, B1, B2, dan P1

## Apa yang disimpan checkpoint

Checkpoint Spark Structured Streaming menyimpan informasi progres pemrosesan agar driver dapat mengetahui posisi dan keadaan stream saat pekerjaan dilanjutkan. Dalam eksperimen ini, kedua treatment memakai lokasi checkpoint yang eksplisit.

## B0: checkpoint sementara

B0 adalah baseline at-least-once tanpa perlindungan idempotence. Istilah **OFF** pada B0 bukan berarti Spark tidak membuat atau memakai direktori checkpoint. Artinya, checkpoint diarahkan ke penyimpanan sementara di dalam kontainer driver:

```text
{ephemeral_root}/{run_id}/{treatment}
```

Dengan akar instrumen `/checkpoints/ephemeral`, contoh path untuk `pilot-001` adalah `/checkpoints/ephemeral/pilot-001/B0`. Akar ini memakai `tmpfs` milik kontainer. Isinya hilang ketika kontainer driver dihapus.

B0 dirancang sebagai baseline yang masuk akal: aplikasi melakukan penulisan objek dan metadata seperti alur ingest biasa, lalu mengandalkan progres checkpoint Spark tanpa menambahkan perlindungan idempotence di tingkat aplikasi. Ini bukan baseline yang sengaja merusak atau melemahkan data. B1 memakai alur dan perilaku penulisan yang sama; perbedaan treatment hanya lokasi checkpoint, sementara B0 menaruh checkpoint pada penyimpanan sementara.

## B1: checkpoint persisten

B1 memakai template path per-run yang sama, tetapi di bawah akar persisten:

```text
{persistent_root}/{run_id}/{treatment}
```

Dengan akar instrumen `/checkpoints/persistent`, contoh path untuk `pilot-001` adalah `/checkpoints/persistent/pilot-001/B1`. Akar ini berada pada bind mount disk VM sehingga checkpoint bertahan ketika kontainer driver diganti.

## Aturan idempotence v1 untuk B2 dan P1 — Hari 8

Keputusan berikut ditulis sebelum implementasi B2. B2 dan P1 menggunakan aturan objek dan metadata yang sama; konfigurasi `idempotence_enabled` memilih penulis idempotent. Kunci objek tetap URI beku `expected_object_uri` dari manifest: stabil antar-run, tanpa `run_id`, UUID, atau waktu ingest.

### Pemeriksaan objek dan checksum

Jika kunci objek belum ada, penulis memvalidasi WAV lokal terhadap ukuran dan SHA-256 manifest, lalu melakukan PUT seperti jalur B0/B1. Jika objek sudah ada, penulis memeriksa ukuran, mengunduh isi objek secara streaming, dan menghitung SHA-256 atas byte yang diterima. Objek hanya berstatus `SUDAH ADA` jika ukuran dan SHA-256 aktual sama dengan manifest. Metadata SHA-256 yang tersimpan pada header objek tidak dijadikan bukti byte karena header itu hanya catatan yang dikirim klien. Biaya baca ulang objek dicatat sebagai bagian biaya treatment; satu replay penuh dapat membaca hingga sekitar 1.056.240.000 byte.

Jika ukuran atau SHA-256 objek yang ada tidak cocok, hasilnya `CONFLICT`: penulis tidak menimpa objek, tidak menulis metadata untuk rekaman tersebut, dan menggagalkan run dengan galat eksplisit. Konflik tidak dilewati diam-diam.

### Konflik dan upsert metadata

Sebelum memproses event, pipeline menolak event yang berisi `recording_id` ganda. Untuk setiap rekaman, `MERGE` Iceberg memakai `recording_id` sebagai kunci. Jika baris sudah ada dan keenam kolom ground truth (`recording_id`, `device_id`, `start_time`, `object_uri`, `file_size_bytes`, `sha256`) sama dengan manifest, hasilnya no-op tanpa menambah baris. Jika salah satu nilainya berbeda, hasilnya `CONFLICT` dan run gagal; baris lama tidak ditimpa otomatis.

Urutannya tetap: pastikan objek ada atau berhasil PUT dan tervalidasi, lalu lakukan upsert metadata. Log mencatat keputusan guard (`PUT`, `SUDAH ADA`, atau `CONFLICT`) serta hasil upsert. Karena konflik menggagalkan run, rekonsiliator dapat melaporkan keadaan parsial tanpa aturan pemulihan yang menyembunyikan ketidakcocokan.

Aturan ini dibekukan untuk uji B2/P1 Hari 8–9. Jika uji pilot menunjukkan cacat, hentikan dan catat keputusan baru sebelum mengubah aturan atau menjalankan matriks.

## Batas perbandingan treatment

Lokasi checkpoint adalah satu-satunya kunci konfigurasi yang membedakan B0 dan B1. Akar checkpoint tidak ditempatkan di MinIO; MinIO adalah object storage/sink yang diuji, sedangkan checkpoint disimpan pada volume sementara atau disk VM sesuai treatment. Self-test instrumen T5a–T5c memverifikasi penanda persistent bertahan, penanda ephemeral hilang pada kontainer baru, dan mount ephemeral bertipe `tmpfs`.

Perilaku B0/B1 pada F0 dan restart sudah diuji; B2/P1 memakai kebijakan idempotence yang sama. Probe sink idempotence dan B2/F0 telah lulus di Lightsail. Bukti B2/F0 ada di `docs/evidence/b2-f0-20261120.log` dan ringkasannya di `docs/logbook.md`. P1/F0 serta fault/restart B2/P1 masih belum dijalankan.
