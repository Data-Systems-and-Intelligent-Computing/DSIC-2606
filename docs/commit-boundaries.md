# Batas commit pada alur ingest

## Satu rekaman

1. Driver membaca satu event JSON dari landing Spark. Event berisi 10 `recording_id` dan harus cocok tepat dengan batch yang sama di `batch_order_main.csv`.
2. Untuk setiap ID sesuai urutan event, driver mencari baris manifest dan berkas WAV pada mount read-only `/data/raw`.
3. Kode memeriksa ukuran dan SHA-256 WAV terhadap manifest.
4. B0/B1 mengirim WAV ke bucket/key dari `expected_object_uri` melalui MinIO S3 API. PUT dianggap selesai setelah `upload_file` berhasil dan `HEAD` mengonfirmasi ukuran serta metadata SHA-256. Buktinya `OBJECT_PUT_COMPLETED`. B2/P1 lebih dulu memeriksa objek yang ada: bila belum ada, PUT; bila ada, unduh byte objek dan hitung SHA-256; hanya ukuran dan hash yang cocok menghasilkan `SUDAH ADA`. Ketidakcocokan menghasilkan `CONFLICT`, tanpa menimpa objek.
5. Sesudah objek siap, B0/B1 menambahkan satu baris Iceberg; batas commit metadata adalah saat `.append()` berhasil kembali (`ICEBERG_COMMIT_COMPLETED`). B2/P1 menjalankan `MERGE` berdasarkan `recording_id`: baris sama menjadi no-op, nilai berbeda menjadi `CONFLICT`; keberhasilan MERGE adalah batas upsert (`ICEBERG_UPSERT_COMPLETED`).
6. Setelah sepuluh rekaman dalam event selesai, Spark callback kembali. Barulah Spark mencatat commit micro-batch pada checkpoint. Feeder baru kemudian menerbitkan event berikutnya.

## Titik injeksi restart F1–F3

Ketiga fault memakai `batch_id=14` agar membandingkan posisi yang sama di batch tengah. F1 memakai `record_index=5`; F2 dan F3 memakai `record_index=10` karena keduanya berhenti pada batas akhir micro-batch.

- **F1 — setelah PUT objek, sebelum metadata target:** hook berada di dalam loop rekaman, tepat sebelum append/upsert metadata target.
- **F2 — setelah seluruh metadata batch di-commit, sebelum commit Spark:** hook berjalan setelah metadata rekaman ke-10 berhasil ditulis, tetapi masih di dalam `foreachBatch`. Karena callback belum kembali, commit batch 14 belum boleh ada pada checkpoint.
- **F3 — setelah commit Spark, sebelum feeder menerbitkan event berikutnya:** hook berjalan setelah `awaitTermination()` dan pemeriksaan bahwa commit Spark untuk batch 14 sudah tercatat, tepat sebelum event 15 dipublikasikan.

Setiap hook menulis marker kunci=nilai secara atomik dengan `target` di baris pertama, lalu menunggu harness mengirim SIGKILL. Snapshot pra-pemulihan memeriksa jumlah objek dan metadata parsial, keberadaan metadata target, serta offset/commit checkpoint sesuai titik fault. Recovery memakai `RUN_ID` yang sama dan `FAULT_POINT=F0`, tanpa reset di antara attempt.

Tabel `lab.main.recordings` adalah keputusan implementasi Fase 3; tabel `lab.smoke.t` milik smoke test instrumen dan tidak dipakai sebagai tabel penelitian. Reset lab harus dijalankan sesuai prosedur sebelum F0 supaya tabel dan bucket mulai kosong.

## Arti kegagalan untuk baseline at-least-once

B0 dan B1 sama-sama tidak memeriksa apakah objek atau baris metadata sudah pernah ditulis. Jika driver mati setelah PUT tetapi sebelum commit Iceberg, percobaan ulang dapat PUT ulang key yang sama. Jika mati setelah commit Iceberg tetapi sebelum Spark menyimpan commit micro-batch, percobaan ulang dapat menambahkan baris metadata duplikat. B2 dan P1 dirancang memakai pemeriksaan objek berbasis byte serta upsert metadata. Dalam rancangan faktorial, pasangan B0/B1 dan B2/P1 hanya berbeda pada lokasi checkpoint; pasangan B0/B2 dan B1/P1 hanya berbeda pada flag idempotence. Probe sink idempotence serta F0 B0/B1/B2/P1 telah dijalankan di Lightsail; fault/restart F1 juga telah diuji dua kali per treatment.

## Batas bukti saat ini

Implementasi B0/B1 dan F0/restart-nya telah dibuktikan di Lightsail. Guard sink idempotent diuji pada probe; F0 B0/B1/B2/P1 masing-masing selesai dengan 300 objek, 300 baris metadata, dan 30 batch yang cocok. B1 dan P1 memakai checkpoint persistent, sedangkan B0 dan B2 memakai checkpoint ephemeral. Perilaku F1 telah diuji dua kali per treatment. Hook F2/F3 tersedia dalam kode, tetapi run VM dan audit F2/F3 dengan commit ini masih harus dilakukan.
