# Batas commit pada alur ingest

## Satu rekaman

1. Driver membaca satu event JSON dari landing Spark. Event berisi 10 `recording_id` dan harus cocok tepat dengan batch yang sama di `batch_order_main.csv`.
2. Untuk setiap ID sesuai urutan event, driver mencari baris manifest dan berkas WAV pada mount read-only `/data/raw`.
3. Kode memeriksa ukuran dan SHA-256 WAV terhadap manifest.
4. B0/B1 mengirim WAV ke bucket/key dari `expected_object_uri` melalui MinIO S3 API. PUT dianggap selesai setelah `upload_file` berhasil dan `HEAD` mengonfirmasi ukuran serta metadata SHA-256. Buktinya `OBJECT_PUT_COMPLETED`. B2/P1 lebih dulu memeriksa objek yang ada: bila belum ada, PUT; bila ada, unduh byte objek dan hitung SHA-256; hanya ukuran dan hash yang cocok menghasilkan `SUDAH ADA`. Ketidakcocokan menghasilkan `CONFLICT`, tanpa menimpa objek.
5. Sesudah objek siap, B0/B1 menambahkan satu baris Iceberg; batas commit metadata adalah saat `.append()` berhasil kembali (`ICEBERG_COMMIT_COMPLETED`). B2/P1 menjalankan `MERGE` berdasarkan `recording_id`: baris sama menjadi no-op, nilai berbeda menjadi `CONFLICT`; keberhasilan MERGE adalah batas upsert (`ICEBERG_UPSERT_COMPLETED`).
6. Setelah sepuluh rekaman dalam event selesai, Spark callback kembali. Barulah Spark mencatat commit micro-batch pada checkpoint. Feeder baru kemudian menerbitkan event berikutnya.

Tabel `lab.main.recordings` adalah keputusan implementasi Fase 3; tabel `lab.smoke.t` milik smoke test instrumen dan tidak dipakai sebagai tabel penelitian. Reset lab harus dijalankan sesuai prosedur sebelum F0 supaya tabel dan bucket mulai kosong.

## Arti kegagalan untuk baseline at-least-once

B0 dan B1 sama-sama tidak memeriksa apakah objek atau baris metadata sudah pernah ditulis. Jika driver mati setelah PUT tetapi sebelum commit Iceberg, percobaan ulang dapat PUT ulang key yang sama. Jika mati setelah commit Iceberg tetapi sebelum Spark menyimpan commit micro-batch, percobaan ulang dapat menambahkan baris metadata duplikat. B2 dan P1 dirancang memakai pemeriksaan objek berbasis byte serta upsert metadata. Dalam rancangan faktorial, pasangan B0/B1 dan B2/P1 hanya berbeda pada lokasi checkpoint; pasangan B0/B2 dan B1/P1 hanya berbeda pada flag idempotence. Perilaku B2/P1 masih perlu diuji pada stack Lightsail.

## Batas bukti saat ini

Implementasi B0/B1 dan F0/restart-nya telah dibuktikan di Lightsail. Guard sink idempotent juga diuji pada objek/tabel probe, lalu B2/F0 berjalan dengan 300 objek, 300 baris metadata, dan 30 batch yang cocok. Bukti tersedia di `docs/evidence/`. Perilaku B2 pada fault/restart dan hasil P1 masih harus diuji dari log eksekusi VM.
